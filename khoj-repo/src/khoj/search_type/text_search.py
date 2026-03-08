import asyncio
import logging
import math
from pathlib import Path
from typing import List, Optional, Tuple, Type, Union

import requests
import torch
from asgiref.sync import sync_to_async
from django.contrib.postgres.search import SearchQuery, SearchRank
from sentence_transformers import util

from khoj.database.adapters import EntryAdapters, get_default_search_model
from khoj.database.models import Agent, KhojUser
from khoj.database.models import Entry as DbEntry
from khoj.processor.content.text_to_entries import TextToEntries
from khoj.utils import state
from khoj.utils.helpers import get_absolute_path, rrf_fuse, timer
from khoj.utils.jsonl import load_jsonl
from khoj.utils.models import BaseEncoder
from khoj.utils.rawconfig import Entry, SearchResponse
from khoj.utils.state import SearchType

logger = logging.getLogger(__name__)

search_type_to_embeddings_type = {
    SearchType.Org.value: DbEntry.EntryType.ORG,
    SearchType.Markdown.value: DbEntry.EntryType.MARKDOWN,
    SearchType.Plaintext.value: DbEntry.EntryType.PLAINTEXT,
    SearchType.Pdf.value: DbEntry.EntryType.PDF,
    SearchType.Github.value: DbEntry.EntryType.GITHUB,
    SearchType.Notion.value: DbEntry.EntryType.NOTION,
    SearchType.All.value: None,
}


def extract_entries(jsonl_file) -> List[Entry]:
    "Load entries from compressed jsonl"
    return list(map(Entry.from_dict, load_jsonl(jsonl_file)))


def compute_embeddings(
    entries_with_ids: List[Tuple[int, Entry]],
    bi_encoder: BaseEncoder,
    embeddings_file: Path,
    regenerate=False,
    normalize=True,
):
    "Compute (and Save) Embeddings or Load Pre-Computed Embeddings"
    new_embeddings = torch.tensor([], device=state.device)
    existing_embeddings = torch.tensor([], device=state.device)
    create_index_msg = ""
    # Load pre-computed embeddings from file if exists and update them if required
    if embeddings_file.exists() and not regenerate:
        corpus_embeddings: torch.Tensor = torch.load(get_absolute_path(embeddings_file), map_location=state.device)
        logger.debug(f"Loaded {len(corpus_embeddings)} text embeddings from {embeddings_file}")
    else:
        corpus_embeddings = torch.tensor([], device=state.device)
        create_index_msg = " Creating index from scratch."

    # Encode any new entries in the corpus and update corpus embeddings
    new_entries = [entry.compiled for id, entry in entries_with_ids if id == -1]
    if new_entries:
        logger.info(f"📩 Indexing {len(new_entries)} text entries.{create_index_msg}")
        new_embeddings = bi_encoder.encode(
            new_entries, convert_to_tensor=True, device=state.device, show_progress_bar=True
        )

    # Extract existing embeddings from previous corpus embeddings
    existing_entry_ids = [id for id, _ in entries_with_ids if id != -1]
    if existing_entry_ids:
        existing_embeddings = torch.index_select(
            corpus_embeddings, 0, torch.tensor(existing_entry_ids, device=state.device)
        )

    # Set corpus embeddings to merger of existing and new embeddings
    corpus_embeddings = torch.cat([existing_embeddings, new_embeddings], dim=0)
    if normalize:
        # Normalize embeddings for faster lookup via dot product when querying
        corpus_embeddings = util.normalize_embeddings(corpus_embeddings)

    # Save regenerated or updated embeddings to file
    torch.save(corpus_embeddings, embeddings_file)
    logger.info(f"📩 Saved computed text embeddings to {embeddings_file}")

    return corpus_embeddings


def load_embeddings(
    embeddings_file: Path,
):
    "Load pre-computed embeddings from file if exists and update them if required"
    if embeddings_file.exists():
        corpus_embeddings: torch.Tensor = torch.load(get_absolute_path(embeddings_file), map_location=state.device)
        logger.debug(f"Loaded {len(corpus_embeddings)} text embeddings from {embeddings_file}")
        return util.normalize_embeddings(corpus_embeddings)

    return None


async def dense_search(
    query_embedding: torch.Tensor,
    user: KhojUser,
    k: int = 10,
    max_distance: Optional[float] = None,
    file_type: Optional[DbEntry.EntryType] = None,
    agent: Optional[Agent] = None,
    raw_query: str = "",
) -> List[DbEntry]:
    "Search for entries using dense vector similarity"

    # Get default max_distance if not provided
    if max_distance is None:
        search_model = await sync_to_async(get_default_search_model)()
        if search_model.bi_encoder_confidence_threshold:
            max_distance = search_model.bi_encoder_confidence_threshold
        else:
            max_distance = math.inf

    # Find relevant entries using vector search
    with timer("Search Time", logger, state.device):
        hits = EntryAdapters.search_with_embeddings(
            raw_query=raw_query,
            embeddings=query_embedding,
            max_results=k,
            file_type_filter=file_type,
            max_distance=max_distance,
            user=user,
            agent=agent,
        ).all()
        hits = await sync_to_async(list)(hits)  # type: ignore[call-arg]

    return hits


async def sparse_search(
    query_text: str,
    user: KhojUser,
    k: int = 10,
    file_type: Optional[DbEntry.EntryType] = None,
    agent: Optional[Agent] = None,
) -> List[DbEntry]:
    "Search for entries using PostgreSQL full-text search (sparse vectors)"
    # Create search query and rank annotation
    search_query = SearchQuery(query_text)

    # Build queryset with rank annotation
    queryset = DbEntry.objects.annotate(rank=SearchRank("search_vector", search_query))

    # Filter by search vector matching the query and user
    queryset = queryset.filter(search_vector=search_query, user=user)

    # Apply optional file_type filter
    if file_type is not None:
        queryset = queryset.filter(file_type=file_type)

    # Apply optional agent filter
    if agent is not None:
        queryset = queryset.filter(agent=agent)

    # Order by rank descending and limit to top k results
    queryset = queryset.order_by("-rank")[:k]

    # Execute query asynchronously
    results = await sync_to_async(list)(queryset)

    return results


async def hybrid_search(
    query_text: str,
    query_embedding: torch.Tensor,
    user: KhojUser,
    k: int = 10,
    alpha: float = 0.6,
    file_type: Optional[DbEntry.EntryType] = None,
    agent: Optional[Agent] = None,
) -> List[DbEntry]:
    """
    Hybrid search combining dense (vector) and sparse (text) search with alpha-weighted RRF fusion.

    Args:
        query_text: The raw query string for sparse search
        query_embedding: The dense vector embedding for dense search
        user: The user performing the search
        k: Number of results to return (default 10)
        alpha: Weight for dense results; sparse results get (1 - alpha) weight (default 0.6)
        file_type: Optional filter by entry file type
        agent: Optional agent context filter

    Returns:
        List of top k DbEntry results from fused search
    """
    # Validate alpha parameter
    if not 0.0 <= alpha <= 1.0:
        raise ValueError(f"alpha must be between 0 and 1, got {alpha}")

    # Run both searches concurrently
    dense_task = dense_search(
        query_embedding=query_embedding,
        user=user,
        k=k,
        file_type=file_type,
        agent=agent,
        raw_query=query_text,
    )
    sparse_task = sparse_search(
        query_text=query_text,
        user=user,
        k=k,
        file_type=file_type,
        agent=agent,
    )
    results = await asyncio.gather(dense_task, sparse_task, return_exceptions=True)

    # Handle exceptions
    dense_results = results[0] if not isinstance(results[0], Exception) else []
    sparse_results = results[1] if not isinstance(results[1], Exception) else []

    if isinstance(results[0], Exception):
        logger.error(f"Dense search failed: {results[0]}")
    if isinstance(results[1], Exception):
        logger.error(f"Sparse search failed: {results[1]}")

    # Convert DbEntry results to dict format for RRF fusion
    dense_results_dicts = [{"id": entry.id, "entry": entry} for entry in dense_results]
    sparse_results_dicts = [{"id": entry.id, "entry": entry} for entry in sparse_results]

    # Fuse results using alpha-weighted RRF
    # alpha weight applied to dense results, (1 - alpha) weight to sparse results
    fused_results = _rrf_fuse_weighted(
        results_lists=[dense_results_dicts, sparse_results_dicts],
        weights=[alpha, 1.0 - alpha],
        k=60,
        limit=k,
    )

    # Extract DbEntry objects from fused results
    return [result["entry"] for result in fused_results]


def _rrf_fuse_weighted(
    results_lists: List[List[dict]],
    weights: List[float],
    k: int = 60,
    limit: int = 10,
) -> List[dict]:
    """
    Reciprocal Rank Fusion (RRF) for combining multiple ranked result lists with per-source weights.

    Weighted RRF formula: score = sum(weight * 1 / (k + rank + 1)) for each result list
    Results are deduplicated by ID and sorted by final weighted RRF score descending.

    Args:
        results_lists: List of result lists, where each result is a dict with 'id' or 'entry' key
        weights: List of weights corresponding to each result list
        k: RRF constant (default 60), higher values give more weight to lower-ranked items
        limit: Maximum number of results to return (default 10)

    Returns:
        List of fused results sorted by weighted RRF score descending, limited to `limit` items
    """
    if not results_lists or not weights:
        return []

    # Track weighted RRF scores and result data by unique ID
    scores: dict[str, float] = {}
    results_by_id: dict[str, dict] = {}

    for results, weight in zip(results_lists, weights):
        if not results:
            continue

        for rank, result in enumerate(results):
            # Get unique identifier for the result
            result_id = result.get("id") or result.get("entry")
            if result_id is None:
                continue  # Skip results without identifiable ID

            # Convert ID to string for consistent hashing
            result_id = str(result_id)

            # Calculate weighted RRF contribution: weight * 1 / (k + rank + 1)
            rrf_score = weight * 1.0 / (k + rank + 1)

            # Accumulate score across all result lists
            scores[result_id] = scores.get(result_id, 0.0) + rrf_score

            # Store the result data (prefer first occurrence)
            if result_id not in results_by_id:
                results_by_id[result_id] = result

    # Sort results by weighted RRF score descending
    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    # Return limited results preserving order
    return [results_by_id[result_id] for result_id in sorted_ids[:limit]]


async def query(
    raw_query: str,
    user: KhojUser,
    type: SearchType = SearchType.All,
    question_embedding: Union[torch.Tensor, None] = None,
    max_distance: float = None,
    agent: Optional[Agent] = None,
) -> Tuple[List[dict], List[Entry]]:
    "Search for entries that answer the query"

    file_type = search_type_to_embeddings_type[type.value]

    query = raw_query
    search_model = await sync_to_async(get_default_search_model)()

    # Encode the query using the bi-encoder
    if question_embedding is None:
        with timer("Query Encode Time", logger, state.device):
            question_embedding = state.embeddings_model[search_model.name].embed_query(query)

    # Call dense_search for vector similarity search
    hits = await dense_search(
        query_embedding=question_embedding,
        user=user,
        k=10,
        max_distance=max_distance,
        file_type=file_type,
        agent=agent,
        raw_query=raw_query,
    )

    return hits


def collate_results(hits, dedupe=True):
    hit_ids = set()
    hit_hashes = set()
    for hit in hits:
        if dedupe and (hit.hashed_value in hit_hashes or hit.corpus_id in hit_ids):
            continue

        else:
            hit_hashes.add(hit.hashed_value)
            hit_ids.add(hit.corpus_id)
            yield SearchResponse.model_validate(
                {
                    "entry": hit.raw,
                    "score": hit.distance,
                    "corpus_id": str(hit.corpus_id),
                    "additional": {
                        "source": hit.file_source,
                        "file": hit.file_path,
                        "uri": hit.url,
                        "compiled": hit.compiled,
                        "heading": hit.heading,
                    },
                }
            )


def deduplicated_search_responses(hits: List[SearchResponse]):
    hit_ids = set()
    for hit in hits:
        if hit.additional["compiled"] in hit_ids:
            continue

        else:
            hit_ids.add(hit.additional["compiled"])
            yield SearchResponse.model_validate(
                {
                    "entry": hit.entry,
                    "score": hit.score,
                    "corpus_id": hit.corpus_id,
                    "additional": {
                        "source": hit.additional["source"],
                        "file": hit.additional["file"],
                        "uri": hit.additional["uri"],
                        "query": hit.additional["query"],
                        "compiled": hit.additional["compiled"],
                        "heading": hit.additional["heading"],
                    },
                }
            )


def rerank_and_sort_results(hits, query, rank_results, search_model_name):
    # Rerank results if explicitly requested, if can use inference server
    # AND if we have more than one result
    rank_results = (rank_results or state.cross_encoder_model[search_model_name].inference_server_enabled()) and len(
        list(hits)
    ) > 1

    # Score all retrieved entries using the cross-encoder
    if rank_results:
        hits = cross_encoder_score(query, hits, search_model_name)

    # Sort results by cross-encoder score followed by bi-encoder score
    hits = sort_results(rank_results=rank_results, hits=hits)

    return hits


def setup(
    text_to_entries: Type[TextToEntries],
    files: dict[str, str],
    regenerate: bool,
    user: KhojUser,
    config=None,
) -> Tuple[int, int]:
    if config:
        num_new_embeddings, num_deleted_embeddings = text_to_entries(config).process(
            files=files, user=user, regenerate=regenerate
        )
    else:
        num_new_embeddings, num_deleted_embeddings = text_to_entries().process(
            files=files, user=user, regenerate=regenerate
        )

    if files:
        file_names = [file_name for file_name in files]

        logger.info(
            f"Deleted {num_deleted_embeddings} entries. Created {num_new_embeddings} new entries for user {user} from files {file_names[:10]} ..."
        )

    return num_new_embeddings, num_deleted_embeddings


def cross_encoder_score(query: str, hits: List[SearchResponse], search_model_name: str) -> List[SearchResponse]:
    """Score all retrieved entries using the cross-encoder"""
    try:
        with timer("Cross-Encoder Predict Time", logger, state.device):
            cross_scores = state.cross_encoder_model[search_model_name].predict(query, hits)
    except requests.exceptions.HTTPError as e:
        logger.error(f"Failed to rerank documents using the inference endpoint. Error: {e}.", exc_info=True)
        cross_scores = [0.0] * len(hits)

    # Convert cross-encoder scores to distances and pass in hits for reranking
    for idx in range(len(cross_scores)):
        hits[idx]["cross_score"] = 1 - cross_scores[idx]

    return hits


def sort_results(rank_results: bool, hits: List[dict]) -> List[dict]:
    """Order results by cross-encoder score followed by bi-encoder score"""
    with timer("Rank Time", logger, state.device):
        hits.sort(key=lambda x: x["score"])  # sort by bi-encoder score
        if rank_results:
            hits.sort(key=lambda x: x["cross_score"])  # sort by cross-encoder score
    return hits


def expand_window(entry: DbEntry, window_size: int = 2) -> List[DbEntry]:
    """Fetch adjacent chunks around the given entry for context expansion.

    Args:
        entry: The central DbEntry to expand around
        window_size: Number of chunks to fetch on each side (default 2)

    Returns:
        List of DbEntry objects including the original and adjacent chunks,
        ordered by chunk_index. Returns [entry] if entry has no chunk_index
        or if an error occurs.
    """
    try:
        # Check if entry has chunk_index attribute and it's not None
        if not hasattr(entry, "chunk_index") or entry.chunk_index is None:
            return [entry]

        # Get the entry's file_id and chunk_index
        file_id = entry.file_id
        chunk_index = entry.chunk_index

        # Query adjacent entries within the window range
        adjacent_entries = (
            DbEntry.objects.filter(
                file_id=file_id,
                chunk_index__range=[chunk_index - window_size, chunk_index + window_size]
            )
            .order_by("chunk_index")
        )

        return list(adjacent_entries)
    except Exception as e:
        logger.error(f"Failed to expand window for entry {entry.id}: {e}")
        return [entry]

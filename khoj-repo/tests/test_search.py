"""
Tests for search module - additional search functionality.

Tests for search functionality including:
- Dense search (vector similarity search)
- Sparse search (full-text search)
- Hybrid search (combining dense and sparse)
- Result collation and deduplication
- RRF fusion algorithms
- Query processing
"""

import pytest
import torch
from unittest.mock import MagicMock, AsyncMock, patch

from khoj.database.models import Entry as DbEntry
from khoj.search_type import text_search
from khoj.utils.state import SearchType
from tests.helpers import (
    acreate_user,
    acreate_subscription,
    UserFactory,
    SubscriptionFactory,
)


# ----------------------------------------------------------------------------------------------------
# Test text_search module has required functions
# ----------------------------------------------------------------------------------------------------
def test_text_search_module_has_dense_search():
    """Text search module should have dense_search function."""
    assert hasattr(text_search, "dense_search")
    assert callable(text_search.dense_search)


def test_text_search_module_has_sparse_search():
    """Text search module should have sparse_search function."""
    assert hasattr(text_search, "sparse_search")
    assert callable(text_search.sparse_search)


def test_text_search_module_has_hybrid_search():
    """Text search module should have hybrid_search function."""
    assert hasattr(text_search, "hybrid_search")
    assert callable(text_search.hybrid_search)


def test_text_search_module_has_query_function():
    """Text search module should have query function."""
    assert hasattr(text_search, "query")
    assert callable(text_search.query)


def test_text_search_module_has_collate_results():
    """Text search module should have collate_results function."""
    assert hasattr(text_search, "collate_results")
    assert callable(text_search.collate_results)


# ----------------------------------------------------------------------------------------------------
# Test search_type_to_embeddings_type mapping
# ----------------------------------------------------------------------------------------------------
def test_search_type_to_embeddings_type_mapping():
    """Search type to embeddings type mapping should work correctly."""
    mapping = text_search.search_type_to_embeddings_type
    
    # Verify all search types are mapped
    assert SearchType.Org.value in mapping
    assert SearchType.Markdown.value in mapping
    assert SearchType.Plaintext.value in mapping
    assert SearchType.Pdf.value in mapping
    assert SearchType.Github.value in mapping
    assert SearchType.Notion.value in mapping
    assert SearchType.All.value in mapping
    
    # Verify All maps to None (means all types)
    assert mapping[SearchType.All.value] is None


# ----------------------------------------------------------------------------------------------------
# Test collate_results function
# ----------------------------------------------------------------------------------------------------
def test_collate_results_with_no_duplicates():
    """collate_results should return all results when there are no duplicates."""
    # Create mock hits
    mock_hit1 = MagicMock()
    mock_hit1.hashed_value = "hash1"
    mock_hit1.corpus_id = "corpus1"
    mock_hit1.raw = "content1"
    mock_hit1.distance = 0.1
    mock_hit1.file_source = "file"
    mock_hit1.file_path = "/test/file1.md"
    mock_hit1.url = None
    mock_hit1.compiled = "compiled1"
    mock_hit1.heading = "Heading 1"
    
    mock_hit2 = MagicMock()
    mock_hit2.hashed_value = "hash2"
    mock_hit2.corpus_id = "corpus2"
    mock_hit2.raw = "content2"
    mock_hit2.distance = 0.2
    mock_hit2.file_source = "file"
    mock_hit2.file_path = "/test/file2.md"
    mock_hit2.url = None
    mock_hit2.compiled = "compiled2"
    mock_hit2.heading = "Heading 2"
    
    hits = [mock_hit1, mock_hit2]
    
    # Call collate_results
    results = list(text_search.collate_results(hits, dedupe=True))
    
    # Assert
    assert len(results) == 2
    assert results[0].entry == "content1"
    assert results[1].entry == "content2"


def test_collate_results_with_duplicates():
    """collate_results should deduplicate results."""
    # Create mock hits with duplicate hashed values
    mock_hit1 = MagicMock()
    mock_hit1.hashed_value = "same_hash"
    mock_hit1.corpus_id = "corpus1"
    mock_hit1.raw = "content1"
    mock_hit1.distance = 0.1
    mock_hit1.file_source = "file"
    mock_hit1.file_path = "/test/file1.md"
    mock_hit1.url = None
    mock_hit1.compiled = "compiled1"
    mock_hit1.heading = "Heading 1"
    
    mock_hit2 = MagicMock()
    mock_hit2.hashed_value = "same_hash"  # Same hash as hit1
    mock_hit2.corpus_id = "corpus2"
    mock_hit2.raw = "content2"
    mock_hit2.distance = 0.2
    mock_hit2.file_source = "file"
    mock_hit2.file_path = "/test/file2.md"
    mock_hit2.url = None
    mock_hit2.compiled = "compiled2"
    mock_hit2.heading = "Heading 2"
    
    hits = [mock_hit1, mock_hit2]
    
    # Call collate_results with deduplication
    results = list(text_search.collate_results(hits, dedupe=True))
    
    # Assert - only one result should be returned
    assert len(results) == 1


def test_collate_results_without_dedupe():
    """collate_results should return all results when dedupe is False."""
    # Create mock hits with duplicate hashed values
    mock_hit1 = MagicMock()
    mock_hit1.hashed_value = "same_hash"
    mock_hit1.corpus_id = "corpus1"
    mock_hit1.raw = "content1"
    mock_hit1.distance = 0.1
    mock_hit1.file_source = "file"
    mock_hit1.file_path = "/test/file1.md"
    mock_hit1.url = None
    mock_hit1.compiled = "compiled1"
    mock_hit1.heading = "Heading 1"
    
    mock_hit2 = MagicMock()
    mock_hit2.hashed_value = "same_hash"
    mock_hit2.corpus_id = "corpus2"
    mock_hit2.raw = "content2"
    mock_hit2.distance = 0.2
    mock_hit2.file_source = "file"
    mock_hit2.file_path = "/test/file2.md"
    mock_hit2.url = None
    mock_hit2.compiled = "compiled2"
    mock_hit2.heading = "Heading 2"
    
    hits = [mock_hit1, mock_hit2]
    
    # Call collate_results without deduplication
    results = list(text_search.collate_results(hits, dedupe=False))
    
    # Assert - both results should be returned
    assert len(results) == 2


# ----------------------------------------------------------------------------------------------------
# Test deduplicated_search_responses function
# ----------------------------------------------------------------------------------------------------
def test_deduplicated_search_responses():
    """deduplicated_search_responses should remove duplicate compiled content."""
    from khoj.utils.rawconfig import SearchResponse
    
    # Create mock responses with duplicate compiled content
    response1 = SearchResponse(
        entry="content1",
        score=0.1,
        corpus_id="corpus1",
        additional={
            "source": "file",
            "file": "/test/file1.md",
            "uri": None,
            "query": None,
            "compiled": "same compiled content",
            "heading": "Heading 1"
        }
    )
    
    response2 = SearchResponse(
        entry="content2",
        score=0.2,
        corpus_id="corpus2",
        additional={
            "source": "file",
            "file": "/test/file2.md",
            "uri": None,
            "query": None,
            "compiled": "same compiled content",  # Same compiled content
            "heading": "Heading 2"
        }
    )
    
    responses = [response1, response2]
    
    # Call deduplicated_search_responses
    results = list(text_search.deduplicated_search_responses(responses))
    
    # Assert - only one result should be returned
    assert len(results) == 1


# ----------------------------------------------------------------------------------------------------
# Test _rrf_fuse_weighted function
# ----------------------------------------------------------------------------------------------------
def test_rrf_fuse_weighted_combines_results():
    """RRF fusion should combine results from multiple sources."""
    # Create mock result lists
    dense_results = [
        {"id": "doc1", "entry": "entry1"},
        {"id": "doc2", "entry": "entry2"},
    ]
    
    sparse_results = [
        {"id": "doc2", "entry": "entry2"},
        {"id": "doc3", "entry": "entry3"},
    ]
    
    results_lists = [dense_results, sparse_results]
    weights = [0.6, 0.4]
    
    # Call _rrf_fuse_weighted
    fused = text_search._rrf_fuse_weighted(results_lists, weights, k=60, limit=3)
    
    # Assert results are fused
    assert len(fused) <= 3
    # doc2 should be at the top since it's in both lists
    assert fused[0]["id"] == "doc2"


def test_rrf_fuse_weighted_empty_input():
    """RRF fusion should handle empty input."""
    # Empty results
    fused = text_search._rrf_fuse_weighted([], [], k=60, limit=10)
    assert fused == []
    
    # Empty weights
    fused = text_search._rrf_fuse_weighted([[]], [], k=60, limit=10)
    assert fused == []


def test_rrf_fuse_weighted_respects_limit():
    """RRF fusion should respect the limit parameter."""
    # Create many results
    results = []
    for i in range(20):
        results.append({"id": f"doc{i}", "entry": f"entry{i}"})
    
    fused = text_search._rrf_fuse_weighted([results], [1.0], k=60, limit=5)
    
    # Assert only 5 results are returned
    assert len(fused) == 5


# ----------------------------------------------------------------------------------------------------
# Test hybrid_search alpha validation
# ----------------------------------------------------------------------------------------------------
@pytest.mark.anyio
@pytest.mark.django_db(transaction=True)
async def test_hybrid_search_validates_alpha(default_user):
    """Hybrid search should validate alpha parameter."""
    # Create a mock query embedding
    query_embedding = torch.tensor([0.1] * 384)
    
    # Test with invalid alpha > 1
    with pytest.raises(ValueError):
        await text_search.hybrid_search(
            query_text="test query",
            query_embedding=query_embedding,
            user=default_user,
            k=10,
            alpha=1.5  # Invalid - should be 0-1
        )
    
    # Test with invalid alpha < 0
    with pytest.raises(ValueError):
        await text_search.hybrid_search(
            query_text="test query",
            query_embedding=query_embedding,
            user=default_user,
            k=10,
            alpha=-0.5  # Invalid - should be 0-1
        )


# ----------------------------------------------------------------------------------------------------
# Test sort_results function
# ----------------------------------------------------------------------------------------------------
def test_sort_results_by_bi_encoder_score():
    """sort_results should sort by bi-encoder score when not reranking."""
    # Create mock hits with scores
    hits = [
        {"score": 0.5, "cross_score": 0.9},
        {"score": 0.1, "cross_score": 0.3},
        {"score": 0.3, "cross_score": 0.5},
    ]
    
    # Sort without cross-encoder reranking
    sorted_hits = text_search.sort_results(rank_results=False, hits=hits)
    
    # Assert sorted by score
    assert sorted_hits[0]["score"] == 0.1
    assert sorted_hits[1]["score"] == 0.3
    assert sorted_hits[2]["score"] == 0.5


def test_sort_results_by_cross_encoder_score():
    """sort_results should sort by cross-encoder score when reranking."""
    # Create mock hits with scores
    hits = [
        {"score": 0.5, "cross_score": 0.9},
        {"score": 0.1, "cross_score": 0.3},
        {"score": 0.3, "cross_score": 0.5},
    ]
    
    # Sort with cross-encoder reranking
    sorted_hits = text_search.sort_results(rank_results=True, hits=hits)
    
    # Assert sorted by cross_score
    assert sorted_hits[0]["cross_score"] == 0.3
    assert sorted_hits[1]["cross_score"] == 0.5
    assert sorted_hits[2]["cross_score"] == 0.9


# ----------------------------------------------------------------------------------------------------
# Test expand_window function
# ----------------------------------------------------------------------------------------------------
@pytest.mark.django_db
def test_expand_window_returns_single_entry_without_chunk_index():
    """expand_window should return single entry when no chunk_index."""
    from khoj.database.models import Entry
    
    # Create a mock entry without chunk_index
    mock_entry = MagicMock(spec=Entry)
    mock_entry.id = 1
    mock_entry.chunk_index = None
    
    result = text_search.expand_window(mock_entry, window_size=2)
    
    # Should return a list with just the entry
    assert len(result) == 1
    assert result[0] == mock_entry


@pytest.mark.django_db
def test_expand_window_returns_single_entry_without_attribute():
    """expand_window should return single entry when chunk_index attribute missing."""
    # Create a mock entry without chunk_index attribute
    mock_entry = MagicMock()
    del mock_entry.chunk_index  # Remove the attribute
    
    result = text_search.expand_window(mock_entry, window_size=2)
    
    # Should return a list with just the entry
    assert len(result) == 1
    assert result[0] == mock_entry


# ----------------------------------------------------------------------------------------------------
# Test cross_encoder_score function
# ----------------------------------------------------------------------------------------------------
def test_cross_encoder_score_returns_hits():
    """cross_encoder_score should return hits with cross_score."""
    from khoj.utils.rawconfig import SearchResponse
    
    # Create mock hits
    hits = [
        SearchResponse(
            entry="content1",
            score=0.1,
            corpus_id="corpus1",
            additional={
                "source": "file",
                "file": "/test/file1.md",
                "uri": None,
                "query": None,
                "compiled": "compiled1",
                "heading": "Heading 1"
            }
        ),
        SearchResponse(
            entry="content2",
            score=0.2,
            corpus_id="corpus2",
            additional={
                "source": "file",
                "file": "/test/file2.md",
                "uri": None,
                "query": None,
                "compiled": "compiled2",
                "heading": "Heading 2"
            }
        ),
    ]
    
    # Mock the cross_encoder_model state
    mock_model = MagicMock()
    mock_model.predict = MagicMock(return_value=[0.8, 0.6])
    mock_model.inference_server_enabled = MagicMock(return_value=False)
    
    with patch("khoj.search_type.text_search.state") as mock_state:
        mock_state.cross_encoder_model = {"default": mock_model}
        
        result = text_search.cross_encoder_score("test query", hits, "default")
    
    # Assert cross_scores are added
    assert "cross_score" in result[0]
    assert "cross_score" in result[1]
    # Scores should be inverted (1 - original)
    assert result[0]["cross_score"] == pytest.approx(0.2)
    assert result[1]["cross_score"] == pytest.approx(0.4)


# ----------------------------------------------------------------------------------------------------
# Test rerank_and_sort_results function
# ----------------------------------------------------------------------------------------------------
def test_rerank_and_sort_results_reranks_when_enabled():
    """rerank_and_sort_results should rerank when requested."""
    from khoj.utils.rawconfig import SearchResponse
    
    # Create mock hits
    hits = [
        SearchResponse(
            entry="content1",
            score=0.1,
            corpus_id="corpus1",
            additional={
                "source": "file",
                "file": "/test/file1.md",
                "uri": None,
                "query": None,
                "compiled": "compiled1",
                "heading": "Heading 1"
            }
        ),
        SearchResponse(
            entry="content2",
            score=0.2,
            corpus_id="corpus2",
            additional={
                "source": "file",
                "file": "/test/file2.md",
                "uri": None,
                "query": None,
                "compiled": "compiled2",
                "heading": "Heading 2"
            }
        ),
    ]
    
    # Mock cross_encoder_model
    mock_model = MagicMock()
    mock_model.inference_server_enabled = MagicMock(return_value=True)
    mock_model.predict = MagicMock(return_value=[0.9, 0.1])
    
    with patch("khoj.search_type.text_search.state") as mock_state:
        mock_state.cross_encoder_model = {"default": mock_model}
        
        result = text_search.rerank_and_sort_results(
            hits=hits,
            query="test query",
            rank_results=True,
            search_model_name="default"
        )
    
    # Results should be reranked by cross_encoder score
    # cross_score = 1 - predict, so 0.1 becomes 0.9, 0.9 becomes 0.1
    # Lower score is better, so 0.1 should come first
    assert result[0].entry == "content2"


# ----------------------------------------------------------------------------------------------------
# Test setup function
# ----------------------------------------------------------------------------------------------------
def test_setup_function_exists():
    """setup function should exist and be callable."""
    assert callable(text_search.setup)


# ----------------------------------------------------------------------------------------------------
# Test compute_embeddings function
# ----------------------------------------------------------------------------------------------------
def test_compute_embeddings_function_exists():
    """compute_embeddings function should exist and be callable."""
    assert callable(text_search.compute_embeddings)


# ----------------------------------------------------------------------------------------------------
# Test load_embeddings function
# ----------------------------------------------------------------------------------------------------
def test_load_embeddings_function_exists():
    """load_embeddings function should exist and be callable."""
    assert callable(text_search.load_embeddings)

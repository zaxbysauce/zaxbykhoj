#!/usr/bin/env python3
"""
Phase 6 Retrieval Benchmark
Evaluates if tri-vector support is needed based on Phase 1-5 performance.

Gate condition: Proceed to Phase 6 only if MAP@10 < 0.95

This script measures retrieval performance metrics including:
- MAP@10 (Mean Average Precision at 10) - PRIMARY GATE METRIC
- nDCG@10 (normalized Discounted Cumulative Gain at 10)
- Recall@10, Recall@50, Recall@100
- MRR (Mean Reciprocal Rank)

Usage:
    python benchmark_retrieval.py --dataset msmarco_mini --output results.json
    python benchmark_retrieval.py --dataset synthetic --k 10 --hybrid-alpha 0.6
"""

import argparse
import asyncio
import json
import logging
import math
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Any
from pathlib import Path

import numpy as np
import torch
from asgiref.sync import sync_to_async

# Configure Django settings before importing Khoj models
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "khoj.app.settings")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import django
django.setup()

# Import Khoj components after Django setup
from khoj.utils.config import RagConfig
from khoj.search_type.text_search import dense_search, sparse_search, hybrid_search
from khoj.database.models import KhojUser, Entry as DbEntry, SearchModelConfig
from khoj.database.adapters import EntryAdapters, get_default_search_model
from khoj.utils import state
from khoj.utils.helpers import timer
from khoj.processor.embeddings import EmbeddingsModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Color codes for terminal output
class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"


def colorize(text: str, color: str) -> str:
    """Apply color to text for terminal output."""
    return f"{color}{text}{Colors.RESET}"


@dataclass
class RetrievalMetrics:
    """Container for retrieval performance metrics."""
    map_at_10: float
    ndcg_at_10: float
    recall_at_10: float
    recall_at_50: float
    recall_at_100: float
    mrr: float
    
    # Additional metadata
    total_queries: int = 0
    dataset_name: str = ""
    timestamp: str = ""
    config: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for JSON serialization."""
        return {
            "metrics": {
                "map_at_10": round(self.map_at_10, 4),
                "ndcg_at_10": round(self.ndcg_at_10, 4),
                "recall_at_10": round(self.recall_at_10, 4),
                "recall_at_50": round(self.recall_at_50, 4),
                "recall_at_100": round(self.recall_at_100, 4),
                "mrr": round(self.mrr, 4),
            },
            "metadata": {
                "total_queries": self.total_queries,
                "dataset_name": self.dataset_name,
                "timestamp": self.timestamp or datetime.now().isoformat(),
                "config": self.config or {},
            }
        }


@dataclass
class BenchmarkQuery:
    """Single query with relevant documents for benchmarking."""
    query_id: str
    query_text: str
    relevant_doc_ids: Set[str]
    relevance_scores: Dict[str, float]  # doc_id -> relevance score (0-1)


class RetrievalBenchmark:
    """Benchmark for evaluating retrieval performance."""
    
    def __init__(self, config: RagConfig, user: KhojUser = None):
        """
        Initialize the benchmark with configuration.
        
        Args:
            config: RagConfig with feature flags
            user: Optional user for search context
        """
        self.config = config
        self.user = user
        self.embeddings_model = None
        self.search_model = None
        
    async def initialize(self):
        """Initialize embeddings model and search configuration."""
        self.search_model = await sync_to_async(get_default_search_model)()
        
        # Initialize embeddings model if not already done
        if not hasattr(state, 'embeddings_model') or state.embeddings_model is None:
            state.embeddings_model = {}
        
        if self.search_model.name not in state.embeddings_model:
            state.embeddings_model[self.search_model.name] = EmbeddingsModel(
                model_name=self.search_model.bi_encoder,
                model_kwargs=self.search_model.bi_encoder_model_config
            )
        
        self.embeddings_model = state.embeddings_model[self.search_model.name]
        logger.info(f"Initialized embeddings model: {self.search_model.bi_encoder}")
    
    def compute_ap_at_k(self, retrieved_ids: List[str], relevant_ids: Set[str], k: int = 10) -> float:
        """
        Compute Average Precision at k.
        
        AP@k = (1/R) * sum_{i=1}^{k} P@i * rel(i)
        where R is number of relevant docs, P@i is precision at i, rel(i) is 1 if doc i is relevant
        
        Args:
            retrieved_ids: List of retrieved document IDs in rank order
            relevant_ids: Set of relevant document IDs
            k: Cutoff rank
            
        Returns:
            Average Precision at k
        """
        if not relevant_ids:
            return 0.0
        
        retrieved_ids = retrieved_ids[:k]
        num_relevant = len(relevant_ids)
        
        precision_sum = 0.0
        num_hits = 0
        
        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in relevant_ids:
                num_hits += 1
                precision_at_i = num_hits / (i + 1)
                precision_sum += precision_at_i
        
        return precision_sum / min(num_relevant, k)
    
    def compute_dcg_at_k(self, retrieved_ids: List[str], relevance_scores: Dict[str, float], k: int = 10) -> float:
        """
        Compute Discounted Cumulative Gain at k.
        
        DCG@k = sum_{i=1}^{k} (2^rel(i) - 1) / log2(i + 1)
        
        Args:
            retrieved_ids: List of retrieved document IDs in rank order
            relevance_scores: Dict mapping doc_id to relevance score
            k: Cutoff rank
            
        Returns:
            DCG at k
        """
        dcg = 0.0
        for i, doc_id in enumerate(retrieved_ids[:k]):
            rel = relevance_scores.get(doc_id, 0.0)
            # Use log2(i + 2) because ranks are 1-indexed
            dcg += (2 ** rel - 1) / math.log2(i + 2)
        return dcg
    
    def compute_ndcg_at_k(self, retrieved_ids: List[str], relevance_scores: Dict[str, float], k: int = 10) -> float:
        """
        Compute normalized Discounted Cumulative Gain at k.
        
        nDCG@k = DCG@k / IDCG@k
        where IDCG is the ideal DCG (perfect ranking)
        
        Args:
            retrieved_ids: List of retrieved document IDs in rank order
            relevance_scores: Dict mapping doc_id to relevance score
            k: Cutoff rank
            
        Returns:
            nDCG at k (0.0 to 1.0)
        """
        dcg = self.compute_dcg_at_k(retrieved_ids, relevance_scores, k)
        
        # Compute ideal DCG (perfect ranking)
        ideal_relevances = sorted(relevance_scores.values(), reverse=True)
        idcg = 0.0
        for i, rel in enumerate(ideal_relevances[:k]):
            idcg += (2 ** rel - 1) / math.log2(i + 2)
        
        if idcg == 0:
            return 0.0
        
        return dcg / idcg
    
    def compute_recall_at_k(self, retrieved_ids: List[str], relevant_ids: Set[str], k: int = 10) -> float:
        """
        Compute Recall at k.
        
        Recall@k = |{relevant docs in top k}| / |{all relevant docs}|
        
        Args:
            retrieved_ids: List of retrieved document IDs in rank order
            relevant_ids: Set of relevant document IDs
            k: Cutoff rank
            
        Returns:
            Recall at k (0.0 to 1.0)
        """
        if not relevant_ids:
            return 0.0
        
        retrieved_set = set(retrieved_ids[:k])
        num_relevant_retrieved = len(retrieved_set & relevant_ids)
        
        return num_relevant_retrieved / len(relevant_ids)
    
    def compute_mrr(self, retrieved_ids: List[str], relevant_ids: Set[str]) -> float:
        """
        Compute Mean Reciprocal Rank.
        
        MRR = (1/|Q|) * sum_{q} 1 / rank_q
        where rank_q is the rank of the first relevant doc for query q
        
        For a single query, it's just 1 / rank of first relevant doc
        
        Args:
            retrieved_ids: List of retrieved document IDs in rank order
            relevant_ids: Set of relevant document IDs
            
        Returns:
            Reciprocal rank (0.0 to 1.0)
        """
        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in relevant_ids:
                return 1.0 / (i + 1)
        return 0.0
    
    async def retrieve_for_query(self, query: BenchmarkQuery, k: int = 100) -> List[str]:
        """
        Retrieve documents for a query using configured search method.
        
        Args:
            query: BenchmarkQuery with query text
            k: Number of results to retrieve
            
        Returns:
            List of retrieved document IDs
        """
        # Encode the query
        query_embedding = self.embeddings_model.embed_query(query.query_text)
        query_embedding_tensor = torch.tensor(query_embedding, device=state.device)
        
        # Choose search method based on configuration
        if self.config.hybrid_search_enabled:
            results = await hybrid_search(
                query_text=query.query_text,
                query_embedding=query_embedding_tensor,
                user=self.user,
                k=k,
                alpha=self.config.hybrid_alpha,
            )
        elif self.config.tri_vector_search_enabled:
            # Tri-vector search not fully implemented yet
            logger.warning("Tri-vector search requested but not fully implemented, falling back to dense")
            results = await dense_search(
                query_embedding=query_embedding_tensor,
                user=self.user,
                k=k,
                raw_query=query.query_text,
            )
        else:
            # Default to dense search
            results = await dense_search(
                query_embedding=query_embedding_tensor,
                user=self.user,
                k=k,
                raw_query=query.query_text,
            )
        
        # Extract document IDs from results
        doc_ids = []
        for entry in results:
            # Use entry ID or file_path as identifier
            doc_id = str(entry.id)
            doc_ids.append(doc_id)
        
        return doc_ids
    
    async def evaluate_query(self, query: BenchmarkQuery, k_values: List[int] = None) -> Dict[str, float]:
        """
        Evaluate a single query and compute all metrics.
        
        Args:
            query: BenchmarkQuery to evaluate
            k_values: List of k values for recall computation
            
        Returns:
            Dictionary of metric names to values
        """
        if k_values is None:
            k_values = [10, 50, 100]
        
        max_k = max(k_values)
        retrieved_ids = await self.retrieve_for_query(query, k=max_k)
        
        metrics = {
            "ap_at_10": self.compute_ap_at_k(retrieved_ids, query.relevant_doc_ids, k=10),
            "ndcg_at_10": self.compute_ndcg_at_k(retrieved_ids, query.relevance_scores, k=10),
            "mrr": self.compute_mrr(retrieved_ids, query.relevant_doc_ids),
        }
        
        for k in k_values:
            metrics[f"recall_at_{k}"] = self.compute_recall_at_k(retrieved_ids, query.relevant_doc_ids, k=k)
        
        return metrics
    
    async def run_benchmark(self, dataset: List[BenchmarkQuery], dataset_name: str = "") -> RetrievalMetrics:
        """
        Run full benchmark on a dataset and compute aggregate metrics.
        
        Args:
            dataset: List of BenchmarkQuery objects
            dataset_name: Name of the dataset for metadata
            
        Returns:
            RetrievalMetrics with aggregated results
        """
        logger.info(f"Running benchmark on {len(dataset)} queries...")
        
        all_metrics = []
        for i, query in enumerate(dataset):
            if (i + 1) % 10 == 0:
                logger.info(f"Processed {i + 1}/{len(dataset)} queries...")
            
            query_metrics = await self.evaluate_query(query)
            all_metrics.append(query_metrics)
        
        # Compute mean metrics
        map_at_10 = np.mean([m["ap_at_10"] for m in all_metrics])
        ndcg_at_10 = np.mean([m["ndcg_at_10"] for m in all_metrics])
        recall_at_10 = np.mean([m["recall_at_10"] for m in all_metrics])
        recall_at_50 = np.mean([m["recall_at_50"] for m in all_metrics])
        recall_at_100 = np.mean([m["recall_at_100"] for m in all_metrics])
        mrr = np.mean([m["mrr"] for m in all_metrics])
        
        config_dict = {
            "crag_enabled": self.config.crag_enabled,
            "hybrid_search_enabled": self.config.hybrid_search_enabled,
            "hybrid_alpha": self.config.hybrid_alpha,
            "contextual_chunking_enabled": self.config.contextual_chunking_enabled,
            "multi_scale_chunking_enabled": self.config.multi_scale_chunking_enabled,
            "tri_vector_search_enabled": self.config.tri_vector_search_enabled,
        }
        
        return RetrievalMetrics(
            map_at_10=map_at_10,
            ndcg_at_10=ndcg_at_10,
            recall_at_10=recall_at_10,
            recall_at_50=recall_at_50,
            recall_at_100=recall_at_100,
            mrr=mrr,
            total_queries=len(dataset),
            dataset_name=dataset_name,
            timestamp=datetime.now().isoformat(),
            config=config_dict,
        )


class SyntheticDatasetLoader:
    """Load or generate synthetic benchmark dataset with known relevant documents."""
    
    def __init__(self, user: KhojUser):
        self.user = user
    
    def create_synthetic_corpus(self, num_docs: int = 100) -> Dict[str, str]:
        """
        Create a synthetic corpus of documents for testing.
        
        Args:
            num_docs: Number of documents to create
            
        Returns:
            Dict mapping doc_id to document content
        """
        corpus = {}
        topics = [
            "machine learning", "deep learning", "neural networks",
            "natural language processing", "computer vision",
            "reinforcement learning", "supervised learning",
            "unsupervised learning", "transfer learning",
            "generative models", "transformers", "attention mechanisms"
        ]
        
        for i in range(num_docs):
            topic = topics[i % len(topics)]
            doc_id = f"doc_{i:04d}"
            
            # Create synthetic document content
            content = f"""
Document {i}: {topic.title()}

This document discusses various aspects of {topic}.
Key concepts include algorithms, methods, and applications.
The field has seen significant advances in recent years.
Researchers continue to develop new techniques for {topic}.

Practical applications span multiple industries including healthcare,
finance, transportation, and education. The impact of {topic} continues
to grow as more data becomes available and computational power increases.

Related topics: artificial intelligence, data science, big data analytics.
"""
            corpus[doc_id] = content
        
        return corpus
    
    async def index_corpus(self, corpus: Dict[str, str]) -> List[DbEntry]:
        """
        Index the corpus into the database.
        
        Args:
            corpus: Dict mapping doc_id to document content
            
        Returns:
            List of created Entry objects
        """
        from khoj.processor.content.plaintext.plaintext_to_entries import PlaintextToEntries
        
        entries = []
        for doc_id, content in corpus.items():
            entry = await sync_to_async(DbEntry.objects.create)(
                user=self.user,
                raw=content,
                compiled=content,
                file_type=DbEntry.EntryType.PLAINTEXT,
                file_path=f"/test/{doc_id}.txt",
            )
            entries.append(entry)
        
        logger.info(f"Indexed {len(entries)} documents")
        return entries
    
    def create_queries(self, corpus: Dict[str, str], num_queries: int = 20) -> List[BenchmarkQuery]:
        """
        Create synthetic queries with known relevant documents.
        
        Args:
            corpus: Dict mapping doc_id to document content
            num_queries: Number of queries to create
            
        Returns:
            List of BenchmarkQuery objects
        """
        queries = []
        topics = [
            ("machine learning algorithms", ["doc_0000", "doc_0012", "doc_0024"]),
            ("deep neural networks", ["doc_0001", "doc_0013"]),
            ("natural language processing techniques", ["doc_0003", "doc_0015"]),
            ("computer vision applications", ["doc_0004", "doc_0016"]),
            ("reinforcement learning methods", ["doc_0005", "doc_0017"]),
            ("supervised vs unsupervised learning", ["doc_0006", "doc_0007", "doc_0018", "doc_0019"]),
            ("transfer learning approaches", ["doc_0008", "doc_0020"]),
            ("generative AI models", ["doc_0009", "doc_0021"]),
            ("transformer architecture", ["doc_0010", "doc_0022"]),
            ("attention mechanisms in NLP", ["doc_0011", "doc_0023", "doc_0003"]),
        ]
        
        for i in range(min(num_queries, len(topics))):
            query_text, relevant_ids = topics[i]
            
            # Create relevance scores (all relevant docs have score 1.0)
            relevance_scores = {doc_id: 1.0 for doc_id in relevant_ids}
            
            query = BenchmarkQuery(
                query_id=f"query_{i:03d}",
                query_text=query_text,
                relevant_doc_ids=set(relevant_ids),
                relevance_scores=relevance_scores,
            )
            queries.append(query)
        
        return queries
    
    async def load_or_create(self, num_docs: int = 100, num_queries: int = 20) -> Tuple[List[BenchmarkQuery], Dict[str, str]]:
        """
        Load or create the synthetic benchmark dataset.
        
        Args:
            num_docs: Number of documents in corpus
            num_queries: Number of queries
            
        Returns:
            Tuple of (queries, corpus)
        """
        corpus = self.create_synthetic_corpus(num_docs)
        queries = self.create_queries(corpus, num_queries)
        
        # Index corpus if not already indexed
        existing_count = await sync_to_async(DbEntry.objects.filter(user=self.user).count)()
        if existing_count < num_docs:
            await self.index_corpus(corpus)
        
        return queries, corpus


class MSMarcMiniLoader:
    """Load MS-MARCO mini dataset for benchmarking."""
    
    def __init__(self, user: KhojUser, data_dir: Optional[str] = None):
        self.user = user
        self.data_dir = data_dir or os.path.join(os.path.dirname(__file__), "data", "benchmark")
    
    def download_msmarco_mini(self) -> bool:
        """
        Download MS-MARCO mini dataset if not available locally.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            
            # Check if already downloaded
            corpus_path = os.path.join(self.data_dir, "msmarco_corpus_mini.json")
            queries_path = os.path.join(self.data_dir, "msmarco_queries_mini.json")
            qrels_path = os.path.join(self.data_dir, "msmarco_qrels_mini.json")
            
            if os.path.exists(corpus_path) and os.path.exists(queries_path) and os.path.exists(qrels_path):
                logger.info("MS-MARCO mini dataset already exists locally")
                return True
            
            logger.info("Downloading MS-MARCO mini dataset...")
            
            # Try to download from HuggingFace datasets
            try:
                from datasets import load_dataset
                
                # Load a subset of MS-MARCO
                dataset = load_dataset("ms_marco", "v1.1", split="validation[:1000]")
                
                # Extract corpus, queries, and relevance judgments
                corpus = {}
                queries = []
                qrels = {}
                
                for i, item in enumerate(dataset):
                    query_id = str(item.get("query_id", i))
                    query_text = item.get("query", "")
                    passages = item.get("passages", {})
                    
                    # Extract passages
                    passage_texts = passages.get("passage_text", [])
                    is_selected = passages.get("is_selected", [])
                    
                    relevant_docs = []
                    for j, (text, selected) in enumerate(zip(passage_texts, is_selected)):
                        doc_id = f"{query_id}_{j}"
                        corpus[doc_id] = text
                        if selected:
                            relevant_docs.append(doc_id)
                    
                    if relevant_docs:
                        queries.append({
                            "query_id": query_id,
                            "query_text": query_text,
                            "relevant_docs": relevant_docs,
                        })
                        qrels[query_id] = {doc_id: 1.0 for doc_id in relevant_docs}
                
                # Save to files
                with open(corpus_path, "w") as f:
                    json.dump(corpus, f)
                with open(queries_path, "w") as f:
                    json.dump(queries, f)
                with open(qrels_path, "w") as f:
                    json.dump(qrels, f)
                
                logger.info(f"Downloaded MS-MARCO mini: {len(corpus)} docs, {len(queries)} queries")
                return True
                
            except ImportError:
                logger.warning("HuggingFace datasets not available, using fallback synthetic data")
                return False
                
        except Exception as e:
            logger.error(f"Failed to download MS-MARCO: {e}")
            return False
    
    async def load(self, max_queries: int = 100) -> Tuple[List[BenchmarkQuery], Dict[str, str]]:
        """
        Load MS-MARCO mini dataset.
        
        Args:
            max_queries: Maximum number of queries to load
            
        Returns:
            Tuple of (queries, corpus)
        """
        # Try to download first
        if not self.download_msmarco_mini():
            logger.warning("Using synthetic fallback instead of MS-MARCO")
            loader = SyntheticDatasetLoader(self.user)
            return await loader.load_or_create()
        
        corpus_path = os.path.join(self.data_dir, "msmarco_corpus_mini.json")
        queries_path = os.path.join(self.data_dir, "msmarco_queries_mini.json")
        qrels_path = os.path.join(self.data_dir, "msmarco_qrels_mini.json")
        
        # Load data
        with open(corpus_path, "r") as f:
            corpus = json.load(f)
        with open(queries_path, "r") as f:
            queries_data = json.load(f)
        with open(qrels_path, "r") as f:
            qrels = json.load(f)
        
        # Create BenchmarkQuery objects
        queries = []
        for qdata in queries_data[:max_queries]:
            query_id = qdata["query_id"]
            query_text = qdata["query_text"]
            relevant_docs = set(qdata["relevant_docs"])
            relevance_scores = qrels.get(query_id, {})
            
            query = BenchmarkQuery(
                query_id=query_id,
                query_text=query_text,
                relevant_doc_ids=relevant_docs,
                relevance_scores=relevance_scores,
            )
            queries.append(query)
        
        # Index corpus if needed
        existing_count = await sync_to_async(DbEntry.objects.filter(user=self.user).count)()
        if existing_count < len(corpus):
            loader = SyntheticDatasetLoader(self.user)
            await loader.index_corpus(corpus)
        
        return queries, corpus


def print_results_table(metrics: RetrievalMetrics):
    """Print metrics in a formatted table."""
    print()
    print(colorize("=" * 70, Colors.CYAN))
    print(colorize("  Phase 6 Retrieval Benchmark Results", Colors.BOLD + Colors.CYAN))
    print(colorize("=" * 70, Colors.CYAN))
    print()
    
    # Metrics table
    print(colorize("  Primary Metrics (Gate Conditions):", Colors.BOLD))
    print(f"    {'MAP@10:':<20} {metrics.map_at_10:.4f}  {'(GATE METRIC)':<15}")
    print(f"    {'nDCG@10:':<20} {metrics.ndcg_at_10:.4f}")
    print(f"    {'MRR:':<20} {metrics.mrr:.4f}")
    print()
    
    print(colorize("  Recall Metrics:", Colors.BOLD))
    print(f"    {'Recall@10:':<20} {metrics.recall_at_10:.4f}")
    print(f"    {'Recall@50:':<20} {metrics.recall_at_50:.4f}")
    print(f"    {'Recall@100:':<20} {metrics.recall_at_100:.4f}")
    print()
    
    # Configuration
    print(colorize("  Configuration:", Colors.BOLD))
    if metrics.config:
        for key, value in metrics.config.items():
            print(f"    {key:<30} {value}")
    print()
    
    print(colorize("=" * 70, Colors.CYAN))


def get_recommendation(metrics: RetrievalMetrics) -> Tuple[str, str]:
    """
    Get recommendation based on MAP@10 score.
    
    Returns:
        Tuple of (recommendation_text, color)
    """
    map_score = metrics.map_at_10
    
    if map_score >= 0.95:
        return (
            "SKIP Phase 6 - Current MAP@10 is excellent\n"
            "The Phase 1-5 implementation meets performance requirements.",
            Colors.GREEN
        )
    elif map_score >= 0.90:
        return (
            "OPTIONAL Phase 6 - Marginal gains expected\n"
            f"MAP@10 is good ({map_score:.4f}), but tri-vector could provide small improvements.",
            Colors.YELLOW
        )
    elif map_score >= 0.80:
        return (
            "PROCEED with Phase 6 - Tri-vector may help\n"
            f"MAP@10 is moderate ({map_score:.4f}). Tri-vector search could improve results.",
            Colors.YELLOW
        )
    else:
        return (
            "PROCEED with Phase 6 - Tri-vector recommended\n"
            f"MAP@10 is below target ({map_score:.4f}). Tri-vector search should help significantly.",
            Colors.RED
        )


def print_recommendation(metrics: RetrievalMetrics):
    """Print recommendation based on metrics."""
    recommendation, color = get_recommendation(metrics)
    
    print()
    print(colorize("  RECOMMENDATION", Colors.BOLD + color))
    print(colorize("  " + "-" * 66, color))
    for line in recommendation.split("\n"):
        print(colorize(f"  {line}", color))
    print(colorize("  " + "-" * 66, color))
    print()


async def main_async():
    """Async main function."""
    parser = argparse.ArgumentParser(
        description="Phase 6 Retrieval Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python benchmark_retrieval.py --dataset msmarco_mini --output results.json
  python benchmark_retrieval.py --dataset synthetic --num-docs 200 --num-queries 50
  python benchmark_retrieval.py --no-hybrid --hybrid-alpha 0.7 --k 20
        """
    )
    
    parser.add_argument(
        "--dataset",
        default="synthetic",
        choices=["msmarco_mini", "synthetic"],
        help="Dataset to use for benchmarking (default: synthetic)"
    )
    parser.add_argument(
        "--output",
        default="benchmark_results.json",
        help="Output JSON file for results (default: benchmark_results.json)"
    )
    parser.add_argument(
        "--k",
        type=int,
        default=10,
        help="Default retrieval depth (default: 10)"
    )
    parser.add_argument(
        "--num-docs",
        type=int,
        default=100,
        help="Number of documents for synthetic dataset (default: 100)"
    )
    parser.add_argument(
        "--num-queries",
        type=int,
        default=20,
        help="Number of queries for synthetic dataset (default: 20)"
    )
    parser.add_argument(
        "--max-queries",
        type=int,
        default=100,
        help="Maximum queries to load from MS-MARCO (default: 100)"
    )
    
    # Feature flags
    parser.add_argument(
        "--crag",
        action="store_true",
        default=None,
        help="Enable CRAG evaluation"
    )
    parser.add_argument(
        "--no-crag",
        action="store_true",
        help="Disable CRAG evaluation"
    )
    parser.add_argument(
        "--hybrid",
        action="store_true",
        default=None,
        help="Enable hybrid search"
    )
    parser.add_argument(
        "--no-hybrid",
        action="store_true",
        help="Disable hybrid search"
    )
    parser.add_argument(
        "--contextual-chunking",
        action="store_true",
        help="Enable contextual chunking"
    )
    parser.add_argument(
        "--multi-scale",
        action="store_true",
        help="Enable multi-scale chunking"
    )
    parser.add_argument(
        "--tri-vector",
        action="store_true",
        help="Enable tri-vector search (experimental)"
    )
    parser.add_argument(
        "--hybrid-alpha",
        type=float,
        default=0.6,
        help="Hybrid search alpha weight (0.0-1.0, default: 0.6)"
    )
    
    args = parser.parse_args()
    
    # Create configuration
    config = RagConfig()
    
    # Apply feature flags from command line
    if args.crag is not None:
        config.crag_enabled = args.crag
    if args.no_crag:
        config.crag_enabled = False
    if args.hybrid is not None:
        config.hybrid_search_enabled = args.hybrid
    if args.no_hybrid:
        config.hybrid_search_enabled = False
    if args.contextual_chunking:
        config.contextual_chunking_enabled = True
    if args.multi_scale:
        config.multi_scale_chunking_enabled = True
    if args.tri_vector:
        config.tri_vector_search_enabled = True
    
    config.hybrid_alpha = args.hybrid_alpha
    
    # Validate alpha
    if not 0.0 <= config.hybrid_alpha <= 1.0:
        logger.error("hybrid-alpha must be between 0.0 and 1.0")
        sys.exit(1)

    # Create or get test user
    user, created = await sync_to_async(KhojUser.objects.get_or_create)(
        username="benchmark_user",
        defaults={
            "email": "benchmark@example.com",
            "password": "benchmark",
        }
    )
    
    if created:
        logger.info("Created benchmark user")
    
    # Initialize benchmark
    benchmark = RetrievalBenchmark(config, user)
    await benchmark.initialize()
    
    # Load dataset
    logger.info(f"Loading {args.dataset} dataset...")
    
    if args.dataset == "msmarco_mini":
        loader = MSMarcMiniLoader(user)
        dataset, corpus = await loader.load(max_queries=args.max_queries)
    else:
        loader = SyntheticDatasetLoader(user)
        dataset, corpus = await loader.load_or_create(
            num_docs=args.num_docs,
            num_queries=args.num_queries
        )
    
    logger.info(f"Loaded {len(dataset)} queries with {len(corpus)} documents")
    
    # Run benchmark
    with timer("Benchmark execution", logger):
        metrics = await benchmark.run_benchmark(dataset, dataset_name=args.dataset)
    
    # Print results
    print_results_table(metrics)
    print_recommendation(metrics)
    
    # Save results to JSON
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(metrics.to_dict(), f, indent=2)
    
    logger.info(f"Results saved to {output_path}")
    
    # Return exit code based on recommendation
    if metrics.map_at_10 >= 0.95:
        return 0  # Success - no Phase 6 needed
    else:
        return 1  # Indicates Phase 6 is recommended


def main():
    """Main entry point."""
    try:
        exit_code = asyncio.run(main_async())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Benchmark interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Benchmark failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

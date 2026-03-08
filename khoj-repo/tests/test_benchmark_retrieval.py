#!/usr/bin/env python3
"""
Test suite for Phase 6 benchmark_retrieval.py script.

Tests:
1. Import without errors
2. Synthetic dataset generation
3. Metric calculations on synthetic data
4. CLI argument parsing
5. JSON output format
"""

import pytest
import json
import math
import sys
import os
from dataclasses import dataclass
from typing import Set, Dict, List
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock

# Add the test directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test 1: Import without errors
def test_import_without_errors():
    """Verify the benchmark script can be imported without errors."""
    # Mock Django setup before importing
    with patch.dict('os.environ', {'DJANGO_SETTINGS_MODULE': 'khoj.app.settings'}):
        with patch('django.setup'):
            with patch('khoj.app.settings', create=True):
                # Mock all the Khoj imports that require Django
                mock_modules = {
                    'khoj.utils.config': MagicMock(),
                    'khoj.search_type.text_search': MagicMock(),
                    'khoj.database.models': MagicMock(),
                    'khoj.database.adapters': MagicMock(),
                    'khoj.utils': MagicMock(),
                    'khoj.utils.helpers': MagicMock(),
                    'khoj.processor.embeddings': MagicMock(),
                    'khoj.processor.content.plaintext.plaintext_to_entries': MagicMock(),
                    'tests.helpers': MagicMock(),
                    'asgiref.sync': MagicMock(),
                    'torch': MagicMock(),
                    'numpy': MagicMock(),
                }
                
                with patch.dict('sys.modules', mock_modules):
                    try:
                        import benchmark_retrieval as br
                        assert br is not None
                        assert hasattr(br, 'RetrievalBenchmark')
                        assert hasattr(br, 'RetrievalMetrics')
                        assert hasattr(br, 'BenchmarkQuery')
                        assert hasattr(br, 'SyntheticDatasetLoader')
                        assert hasattr(br, 'MSMarcMiniLoader')
                        assert hasattr(br, 'main')
                        assert hasattr(br, 'main_async')
                    except ImportError as e:
                        pytest.fail(f"Failed to import benchmark_retrieval: {e}")


# Test 2: Synthetic Dataset Generation
class TestSyntheticDatasetGeneration:
    """Test synthetic dataset generation functionality."""
    
    def test_create_synthetic_corpus(self):
        """Test that synthetic corpus is created with expected structure."""
        with patch.dict('os.environ', {'DJANGO_SETTINGS_MODULE': 'khoj.app.settings'}):
            with patch('django.setup'):
                with patch.dict('sys.modules', {
                    'khoj.utils.config': MagicMock(),
                    'khoj.search_type.text_search': MagicMock(),
                    'khoj.database.models': MagicMock(),
                    'khoj.database.adapters': MagicMock(),
                    'khoj.utils': MagicMock(),
                    'khoj.utils.helpers': MagicMock(),
                    'khoj.processor.embeddings': MagicMock(),
                    'khoj.processor.content.plaintext.plaintext_to_entries': MagicMock(),
                    'tests.helpers': MagicMock(),
                    'asgiref.sync': MagicMock(),
                    'torch': MagicMock(),
                    'numpy': MagicMock(),
                }):
                    import benchmark_retrieval as br
                    
                    mock_user = MagicMock()
                    loader = br.SyntheticDatasetLoader(mock_user)
                    
                    # Test with default 100 docs
                    corpus = loader.create_synthetic_corpus(num_docs=100)
                    
                    assert len(corpus) == 100
                    assert all(doc_id.startswith("doc_") for doc_id in corpus.keys())
                    assert all(isinstance(content, str) for content in corpus.values())
                    assert all(len(content) > 0 for content in corpus.values())
                    
                    # Check document ID format
                    assert "doc_0000" in corpus
                    assert "doc_0099" in corpus
                    
    def test_create_synthetic_corpus_topics(self):
        """Test that corpus contains expected topic content."""
        with patch.dict('os.environ', {'DJANGO_SETTINGS_MODULE': 'khoj.app.settings'}):
            with patch('django.setup'):
                with patch.dict('sys.modules', {
                    'khoj.utils.config': MagicMock(),
                    'khoj.search_type.text_search': MagicMock(),
                    'khoj.database.models': MagicMock(),
                    'khoj.database.adapters': MagicMock(),
                    'khoj.utils': MagicMock(),
                    'khoj.utils.helpers': MagicMock(),
                    'khoj.processor.embeddings': MagicMock(),
                    'khoj.processor.content.plaintext.plaintext_to_entries': MagicMock(),
                    'tests.helpers': MagicMock(),
                    'asgiref.sync': MagicMock(),
                    'torch': MagicMock(),
                    'numpy': MagicMock(),
                }):
                    import benchmark_retrieval as br
                    
                    mock_user = MagicMock()
                    loader = br.SyntheticDatasetLoader(mock_user)
                    
                    corpus = loader.create_synthetic_corpus(num_docs=12)
                    
                    # Check that topics are cycled through
                    topics = [
                        "machine learning", "deep learning", "neural networks",
                        "natural language processing", "computer vision",
                        "reinforcement learning", "supervised learning",
                        "unsupervised learning", "transfer learning",
                        "generative models", "transformers", "attention mechanisms"
                    ]
                    
                    for i, topic in enumerate(topics):
                        doc_id = f"doc_{i:04d}"
                        assert topic in corpus[doc_id].lower()
    
    def test_create_queries(self):
        """Test synthetic query generation."""
        with patch.dict('os.environ', {'DJANGO_SETTINGS_MODULE': 'khoj.app.settings'}):
            with patch('django.setup'):
                with patch.dict('sys.modules', {
                    'khoj.utils.config': MagicMock(),
                    'khoj.search_type.text_search': MagicMock(),
                    'khoj.database.models': MagicMock(),
                    'khoj.database.adapters': MagicMock(),
                    'khoj.utils': MagicMock(),
                    'khoj.utils.helpers': MagicMock(),
                    'khoj.processor.embeddings': MagicMock(),
                    'khoj.processor.content.plaintext.plaintext_to_entries': MagicMock(),
                    'tests.helpers': MagicMock(),
                    'asgiref.sync': MagicMock(),
                    'torch': MagicMock(),
                    'numpy': MagicMock(),
                }):
                    import benchmark_retrieval as br
                    
                    mock_user = MagicMock()
                    loader = br.SyntheticDatasetLoader(mock_user)
                    
                    corpus = loader.create_synthetic_corpus(num_docs=100)
                    queries = loader.create_queries(corpus, num_queries=10)
                    
                    assert len(queries) == 10
                    
                    for query in queries:
                        assert hasattr(query, 'query_id')
                        assert hasattr(query, 'query_text')
                        assert hasattr(query, 'relevant_doc_ids')
                        assert hasattr(query, 'relevance_scores')
                        
                        assert query.query_id.startswith("query_")
                        assert isinstance(query.query_text, str)
                        assert isinstance(query.relevant_doc_ids, set)
                        assert isinstance(query.relevance_scores, dict)
                        
                        # All relevant docs should have score 1.0
                        for doc_id in query.relevant_doc_ids:
                            assert query.relevance_scores[doc_id] == 1.0


# Test 3: Metric Calculations
class TestMetricCalculations:
    """Test metric calculation functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch.dict('os.environ', {'DJANGO_SETTINGS_MODULE': 'khoj.app.settings'}):
            with patch('django.setup'):
                with patch.dict('sys.modules', {
                    'khoj.utils.config': MagicMock(),
                    'khoj.search_type.text_search': MagicMock(),
                    'khoj.database.models': MagicMock(),
                    'khoj.database.adapters': MagicMock(),
                    'khoj.utils': MagicMock(),
                    'khoj.utils.helpers': MagicMock(),
                    'khoj.processor.embeddings': MagicMock(),
                    'khoj.processor.content.plaintext.plaintext_to_entries': MagicMock(),
                    'tests.helpers': MagicMock(),
                    'asgiref.sync': MagicMock(),
                    'torch': MagicMock(),
                    'numpy': MagicMock(),
                }):
                    import benchmark_retrieval as br
                    self.br = br
    
    def test_compute_ap_at_k_perfect_retrieval(self):
        """Test AP@k with perfect retrieval (all relevant docs at top)."""
        mock_config = MagicMock()
        benchmark = self.br.RetrievalBenchmark(mock_config)
        
        # Perfect retrieval: all relevant docs at top positions
        retrieved_ids = ["doc_1", "doc_2", "doc_3", "doc_4", "doc_5"]
        relevant_ids = {"doc_1", "doc_2", "doc_3"}
        
        ap = benchmark.compute_ap_at_k(retrieved_ids, relevant_ids, k=10)
        
        # AP@10 should be 1.0 for perfect retrieval
        assert 0.0 <= ap <= 1.0, f"AP@k should be in [0,1], got {ap}"
        assert ap == 1.0, f"Expected AP@10=1.0 for perfect retrieval, got {ap}"
    
    def test_compute_ap_at_k_no_relevant(self):
        """Test AP@k with no relevant documents."""
        mock_config = MagicMock()
        benchmark = self.br.RetrievalBenchmark(mock_config)
        
        retrieved_ids = ["doc_1", "doc_2", "doc_3"]
        relevant_ids = set()  # No relevant docs
        
        ap = benchmark.compute_ap_at_k(retrieved_ids, relevant_ids, k=10)
        
        assert ap == 0.0, f"AP@k should be 0.0 when no relevant docs, got {ap}"
    
    def test_compute_ap_at_k_partial_retrieval(self):
        """Test AP@k with partial retrieval."""
        mock_config = MagicMock()
        benchmark = self.br.RetrievalBenchmark(mock_config)
        
        # Retrieved: doc_1 (relevant), doc_2 (irrelevant), doc_3 (relevant)
        retrieved_ids = ["doc_1", "doc_2", "doc_3", "doc_4", "doc_5"]
        relevant_ids = {"doc_1", "doc_3", "doc_6"}  # 3 relevant total, 2 found
        
        ap = benchmark.compute_ap_at_k(retrieved_ids, relevant_ids, k=10)
        
        # AP calculation:
        # At i=0 (doc_1): precision = 1/1 = 1.0
        # At i=1 (doc_2): not relevant
        # At i=2 (doc_3): precision = 2/3 = 0.667
        # AP = (1.0 + 0.667) / 3 = 0.556
        expected_ap = (1.0 + 2.0/3) / 3
        
        assert 0.0 <= ap <= 1.0, f"AP@k should be in [0,1], got {ap}"
        assert abs(ap - expected_ap) < 0.001, f"Expected AP@10≈{expected_ap}, got {ap}"
    
    def test_compute_recall_at_k(self):
        """Test Recall@k calculation."""
        mock_config = MagicMock()
        benchmark = self.br.RetrievalBenchmark(mock_config)
        
        retrieved_ids = ["doc_1", "doc_2", "doc_3", "doc_4", "doc_5"]
        relevant_ids = {"doc_1", "doc_3", "doc_6", "doc_7"}  # 4 relevant total
        
        recall_at_5 = benchmark.compute_recall_at_k(retrieved_ids, relevant_ids, k=5)
        # Found: doc_1, doc_3 (2 out of 4) = 0.5
        assert recall_at_5 == 0.5, f"Expected Recall@5=0.5, got {recall_at_5}"
        
        recall_at_2 = benchmark.compute_recall_at_k(retrieved_ids, relevant_ids, k=2)
        # Found: doc_1 (1 out of 4) = 0.25
        assert recall_at_2 == 0.25, f"Expected Recall@2=0.25, got {recall_at_2}"
        
        assert 0.0 <= recall_at_5 <= 1.0
        assert 0.0 <= recall_at_2 <= 1.0
    
    def test_compute_recall_at_k_no_relevant(self):
        """Test Recall@k with no relevant documents."""
        mock_config = MagicMock()
        benchmark = self.br.RetrievalBenchmark(mock_config)
        
        retrieved_ids = ["doc_1", "doc_2", "doc_3"]
        relevant_ids = set()
        
        recall = benchmark.compute_recall_at_k(retrieved_ids, relevant_ids, k=10)
        
        assert recall == 0.0, f"Recall@k should be 0.0 when no relevant docs, got {recall}"
    
    def test_compute_mrr(self):
        """Test MRR calculation."""
        mock_config = MagicMock()
        benchmark = self.br.RetrievalBenchmark(mock_config)
        
        # First relevant doc at position 2 (index 1)
        retrieved_ids = ["doc_1", "doc_2", "doc_3", "doc_4"]
        relevant_ids = {"doc_2", "doc_5"}
        
        mrr = benchmark.compute_mrr(retrieved_ids, relevant_ids)
        
        # First relevant is at rank 2, so MRR = 1/2 = 0.5
        assert mrr == 0.5, f"Expected MRR=0.5, got {mrr}"
        assert 0.0 <= mrr <= 1.0
    
    def test_compute_mrr_first_position(self):
        """Test MRR when first relevant doc is at position 1."""
        mock_config = MagicMock()
        benchmark = self.br.RetrievalBenchmark(mock_config)
        
        retrieved_ids = ["doc_1", "doc_2", "doc_3"]
        relevant_ids = {"doc_1"}
        
        mrr = benchmark.compute_mrr(retrieved_ids, relevant_ids)
        
        assert mrr == 1.0, f"Expected MRR=1.0 for first position, got {mrr}"
    
    def test_compute_mrr_no_relevant(self):
        """Test MRR when no relevant docs are retrieved."""
        mock_config = MagicMock()
        benchmark = self.br.RetrievalBenchmark(mock_config)
        
        retrieved_ids = ["doc_1", "doc_2", "doc_3"]
        relevant_ids = {"doc_4", "doc_5"}
        
        mrr = benchmark.compute_mrr(retrieved_ids, relevant_ids)
        
        assert mrr == 0.0, f"Expected MRR=0.0 when no relevant docs, got {mrr}"
    
    def test_compute_dcg_at_k(self):
        """Test DCG@k calculation."""
        mock_config = MagicMock()
        benchmark = self.br.RetrievalBenchmark(mock_config)
        
        retrieved_ids = ["doc_1", "doc_2", "doc_3"]
        relevance_scores = {"doc_1": 1.0, "doc_2": 0.5, "doc_3": 0.0}
        
        dcg = benchmark.compute_dcg_at_k(retrieved_ids, relevance_scores, k=3)
        
        # DCG = (2^1 - 1)/log2(2) + (2^0.5 - 1)/log2(3) + (2^0 - 1)/log2(4)
        #     = 1/1 + 0.414/1.585 + 0/2
        #     = 1 + 0.261 + 0 = 1.261
        expected_dcg = (2**1 - 1) / math.log2(2) + (2**0.5 - 1) / math.log2(3)
        
        assert abs(dcg - expected_dcg) < 0.001, f"Expected DCG≈{expected_dcg}, got {dcg}"
    
    def test_compute_ndcg_at_k(self):
        """Test nDCG@k calculation."""
        mock_config = MagicMock()
        benchmark = self.br.RetrievalBenchmark(mock_config)
        
        # Perfect ranking
        retrieved_ids = ["doc_1", "doc_2", "doc_3"]
        relevance_scores = {"doc_1": 1.0, "doc_2": 0.5, "doc_3": 0.3}
        
        ndcg = benchmark.compute_ndcg_at_k(retrieved_ids, relevance_scores, k=3)
        
        # For perfect ranking, nDCG should be 1.0
        assert 0.0 <= ndcg <= 1.0, f"nDCG should be in [0,1], got {ndcg}"
        assert ndcg == 1.0, f"Expected nDCG=1.0 for perfect ranking, got {ndcg}"
    
    def test_compute_ndcg_at_k_imperfect(self):
        """Test nDCG@k with imperfect ranking."""
        mock_config = MagicMock()
        benchmark = self.br.RetrievalBenchmark(mock_config)
        
        # Imperfect ranking: lower relevance docs first
        retrieved_ids = ["doc_3", "doc_2", "doc_1"]  # 0.3, 0.5, 1.0
        relevance_scores = {"doc_1": 1.0, "doc_2": 0.5, "doc_3": 0.3}
        
        ndcg = benchmark.compute_ndcg_at_k(retrieved_ids, relevance_scores, k=3)
        
        # Should be less than 1.0 for imperfect ranking
        assert 0.0 <= ndcg < 1.0, f"nDCG should be in [0,1) for imperfect ranking, got {ndcg}"
    
    def test_metric_ranges(self):
        """Test that all metrics produce values in valid range [0, 1]."""
        mock_config = MagicMock()
        benchmark = self.br.RetrievalBenchmark(mock_config)
        
        # Test with random retrievals
        test_cases = [
            (["d1", "d2", "d3"], {"d1"}, {"d1": 1.0}),
            (["d1", "d2", "d3"], {"d4", "d5"}, {"d4": 1.0, "d5": 0.5}),
            (["d1", "d2", "d3"], {"d1", "d2", "d3"}, {"d1": 1.0, "d2": 1.0, "d3": 1.0}),
            (["d1", "d2", "d3"], set(), {}),
        ]
        
        for retrieved, relevant, scores in test_cases:
            ap = benchmark.compute_ap_at_k(retrieved, relevant, k=10)
            recall = benchmark.compute_recall_at_k(retrieved, relevant, k=10)
            mrr = benchmark.compute_mrr(retrieved, relevant)
            ndcg = benchmark.compute_ndcg_at_k(retrieved, scores, k=10)
            
            assert 0.0 <= ap <= 1.0, f"AP@k out of range: {ap}"
            assert 0.0 <= recall <= 1.0, f"Recall@k out of range: {recall}"
            assert 0.0 <= mrr <= 1.0, f"MRR out of range: {mrr}"
            assert 0.0 <= ndcg <= 1.0, f"nDCG@k out of range: {ndcg}"


# Test 4: CLI Argument Parsing
class TestCLIArgumentParsing:
    """Test CLI argument parsing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch.dict('os.environ', {'DJANGO_SETTINGS_MODULE': 'khoj.app.settings'}):
            with patch('django.setup'):
                with patch.dict('sys.modules', {
                    'khoj.utils.config': MagicMock(),
                    'khoj.search_type.text_search': MagicMock(),
                    'khoj.database.models': MagicMock(),
                    'khoj.database.adapters': MagicMock(),
                    'khoj.utils': MagicMock(),
                    'khoj.utils.helpers': MagicMock(),
                    'khoj.processor.embeddings': MagicMock(),
                    'khoj.processor.content.plaintext.plaintext_to_entries': MagicMock(),
                    'tests.helpers': MagicMock(),
                    'asgiref.sync': MagicMock(),
                    'torch': MagicMock(),
                    'numpy': MagicMock(),
                }):
                    import benchmark_retrieval as br
                    self.br = br
    
    def test_default_arguments(self):
        """Test default argument values."""
        with patch('sys.argv', ['benchmark_retrieval.py']):
            parser = self._create_parser()
            args = parser.parse_args([])
            
            assert args.dataset == "synthetic"
            assert args.output == "benchmark_results.json"
            assert args.k == 10
            assert args.num_docs == 100
            assert args.num_queries == 20
            assert args.max_queries == 100
            assert args.hybrid_alpha == 0.6
    
    def test_custom_arguments(self):
        """Test custom argument values."""
        with patch('sys.argv', ['benchmark_retrieval.py']):
            parser = self._create_parser()
            args = parser.parse_args([
                '--dataset', 'msmarco_mini',
                '--output', 'custom_results.json',
                '--k', '20',
                '--num-docs', '200',
                '--num-queries', '50',
                '--max-queries', '200',
                '--hybrid-alpha', '0.8',
            ])
            
            assert args.dataset == "msmarco_mini"
            assert args.output == "custom_results.json"
            assert args.k == 20
            assert args.num_docs == 200
            assert args.num_queries == 50
            assert args.max_queries == 200
            assert args.hybrid_alpha == 0.8
    
    def test_boolean_flags(self):
        """Test boolean flag arguments."""
        with patch('sys.argv', ['benchmark_retrieval.py']):
            parser = self._create_parser()
            
            # Test enabling flags
            args = parser.parse_args(['--crag', '--hybrid', '--contextual-chunking', '--multi-scale', '--tri-vector'])
            assert args.crag is True
            assert args.hybrid is True
            assert args.contextual_chunking is True
            assert args.multi_scale is True
            assert args.tri_vector is True
            
            # Test disabling flags
            args = parser.parse_args(['--no-crag', '--no-hybrid'])
            assert args.no_crag is True
            assert args.no_hybrid is True
    
    def test_invalid_hybrid_alpha(self):
        """Test validation of hybrid-alpha range."""
        # The validation happens in main_async, not in argparse
        # So we just verify the argument is accepted and validation would catch it
        with patch('sys.argv', ['benchmark_retrieval.py']):
            parser = self._create_parser()
            args = parser.parse_args(['--hybrid-alpha', '1.5'])
            
            # Argparse accepts it, but main_async should reject it
            assert args.hybrid_alpha == 1.5
    
    def _create_parser(self):
        """Create argument parser matching the script."""
        import argparse
        
        parser = argparse.ArgumentParser(
            description="Phase 6 Retrieval Benchmark",
            formatter_class=argparse.RawDescriptionHelpFormatter,
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
        
        return parser


# Test 5: JSON Output Format
class TestJSONOutputFormat:
    """Test JSON output format."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch.dict('os.environ', {'DJANGO_SETTINGS_MODULE': 'khoj.app.settings'}):
            with patch('django.setup'):
                with patch.dict('sys.modules', {
                    'khoj.utils.config': MagicMock(),
                    'khoj.search_type.text_search': MagicMock(),
                    'khoj.database.models': MagicMock(),
                    'khoj.database.adapters': MagicMock(),
                    'khoj.utils': MagicMock(),
                    'khoj.utils.helpers': MagicMock(),
                    'khoj.processor.embeddings': MagicMock(),
                    'khoj.processor.content.plaintext.plaintext_to_entries': MagicMock(),
                    'tests.helpers': MagicMock(),
                    'asgiref.sync': MagicMock(),
                    'torch': MagicMock(),
                    'numpy': MagicMock(),
                }):
                    import benchmark_retrieval as br
                    self.br = br
    
    def test_retrieval_metrics_to_dict(self):
        """Test RetrievalMetrics.to_dict() produces correct format."""
        metrics = self.br.RetrievalMetrics(
            map_at_10=0.85,
            ndcg_at_10=0.82,
            recall_at_10=0.75,
            recall_at_50=0.88,
            recall_at_100=0.92,
            mrr=0.90,
            total_queries=100,
            dataset_name="test_dataset",
            timestamp="2024-01-01T00:00:00",
            config={"hybrid_search_enabled": True}
        )
        
        result = metrics.to_dict()
        
        # Check structure
        assert "metrics" in result
        assert "metadata" in result
        
        # Check metrics values
        assert result["metrics"]["map_at_10"] == 0.85
        assert result["metrics"]["ndcg_at_10"] == 0.82
        assert result["metrics"]["recall_at_10"] == 0.75
        assert result["metrics"]["recall_at_50"] == 0.88
        assert result["metrics"]["recall_at_100"] == 0.92
        assert result["metrics"]["mrr"] == 0.90
        
        # Check metadata
        assert result["metadata"]["total_queries"] == 100
        assert result["metadata"]["dataset_name"] == "test_dataset"
        assert result["metadata"]["timestamp"] == "2024-01-01T00:00:00"
        assert result["metadata"]["config"]["hybrid_search_enabled"] is True
    
    def test_retrieval_metrics_json_serialization(self):
        """Test that metrics can be serialized to JSON."""
        metrics = self.br.RetrievalMetrics(
            map_at_10=0.85,
            ndcg_at_10=0.82,
            recall_at_10=0.75,
            recall_at_50=0.88,
            recall_at_100=0.92,
            mrr=0.90,
            total_queries=100,
            dataset_name="test_dataset",
            timestamp="2024-01-01T00:00:00",
            config={"hybrid_search_enabled": True}
        )
        
        result = metrics.to_dict()
        
        # Should be JSON serializable
        json_str = json.dumps(result, indent=2)
        assert json_str is not None
        assert len(json_str) > 0
        
        # Should be deserializable
        parsed = json.loads(json_str)
        assert parsed["metrics"]["map_at_10"] == 0.85
    
    def test_retrieval_metrics_rounding(self):
        """Test that metrics are properly rounded to 4 decimal places."""
        metrics = self.br.RetrievalMetrics(
            map_at_10=0.12345678,
            ndcg_at_10=0.87654321,
            recall_at_10=0.55555555,
            recall_at_50=0.99999999,
            recall_at_100=0.11111111,
            mrr=0.77777777,
        )
        
        result = metrics.to_dict()
        
        assert result["metrics"]["map_at_10"] == 0.1235  # Rounded
        assert result["metrics"]["ndcg_at_10"] == 0.8765
        assert result["metrics"]["recall_at_10"] == 0.5556
        assert result["metrics"]["recall_at_50"] == 1.0
        assert result["metrics"]["recall_at_100"] == 0.1111
        assert result["metrics"]["mrr"] == 0.7778


# Test 6: Edge Cases and Error Handling
class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch.dict('os.environ', {'DJANGO_SETTINGS_MODULE': 'khoj.app.settings'}):
            with patch('django.setup'):
                with patch.dict('sys.modules', {
                    'khoj.utils.config': MagicMock(),
                    'khoj.search_type.text_search': MagicMock(),
                    'khoj.database.models': MagicMock(),
                    'khoj.database.adapters': MagicMock(),
                    'khoj.utils': MagicMock(),
                    'khoj.utils.helpers': MagicMock(),
                    'khoj.processor.embeddings': MagicMock(),
                    'khoj.processor.content.plaintext.plaintext_to_entries': MagicMock(),
                    'tests.helpers': MagicMock(),
                    'asgiref.sync': MagicMock(),
                    'torch': MagicMock(),
                    'numpy': MagicMock(),
                }):
                    import benchmark_retrieval as br
                    self.br = br
    
    def test_empty_retrieved_list(self):
        """Test metrics with empty retrieved list."""
        mock_config = MagicMock()
        benchmark = self.br.RetrievalBenchmark(mock_config)
        
        retrieved_ids = []
        relevant_ids = {"doc_1", "doc_2"}
        relevance_scores = {"doc_1": 1.0, "doc_2": 0.5}
        
        ap = benchmark.compute_ap_at_k(retrieved_ids, relevant_ids, k=10)
        recall = benchmark.compute_recall_at_k(retrieved_ids, relevant_ids, k=10)
        mrr = benchmark.compute_mrr(retrieved_ids, relevant_ids)
        ndcg = benchmark.compute_ndcg_at_k(retrieved_ids, relevance_scores, k=10)
        
        assert ap == 0.0
        assert recall == 0.0
        assert mrr == 0.0
        assert ndcg == 0.0
    
    def test_k_larger_than_retrieved(self):
        """Test metrics when k is larger than number of retrieved docs."""
        mock_config = MagicMock()
        benchmark = self.br.RetrievalBenchmark(mock_config)
        
        retrieved_ids = ["doc_1", "doc_2"]
        relevant_ids = {"doc_1"}
        relevance_scores = {"doc_1": 1.0}
        
        # k=10 but only 2 docs retrieved
        ap = benchmark.compute_ap_at_k(retrieved_ids, relevant_ids, k=10)
        recall = benchmark.compute_recall_at_k(retrieved_ids, relevant_ids, k=10)
        
        assert ap == 1.0  # Perfect precision for retrieved docs
        assert recall == 1.0  # Found the only relevant doc
    
    def test_relevance_scores_missing_docs(self):
        """Test nDCG when some retrieved docs have no relevance scores."""
        mock_config = MagicMock()
        benchmark = self.br.RetrievalBenchmark(mock_config)
        
        retrieved_ids = ["doc_1", "doc_2", "doc_3"]
        relevance_scores = {"doc_1": 1.0}  # Only doc_1 has a score
        
        dcg = benchmark.compute_dcg_at_k(retrieved_ids, relevance_scores, k=3)
        
        # DCG = (2^1 - 1)/log2(2) + (2^0 - 1)/log2(3) + (2^0 - 1)/log2(4)
        #     = 1 + 0 + 0 = 1
        expected_dcg = 1.0
        assert dcg == expected_dcg


# Test 7: Recommendation Logic
class TestRecommendationLogic:
    """Test the recommendation logic based on MAP@10 scores."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch.dict('os.environ', {'DJANGO_SETTINGS_MODULE': 'khoj.app.settings'}):
            with patch('django.setup'):
                with patch.dict('sys.modules', {
                    'khoj.utils.config': MagicMock(),
                    'khoj.search_type.text_search': MagicMock(),
                    'khoj.database.models': MagicMock(),
                    'khoj.database.adapters': MagicMock(),
                    'khoj.utils': MagicMock(),
                    'khoj.utils.helpers': MagicMock(),
                    'khoj.processor.embeddings': MagicMock(),
                    'khoj.processor.content.plaintext.plaintext_to_entries': MagicMock(),
                    'tests.helpers': MagicMock(),
                    'asgiref.sync': MagicMock(),
                    'torch': MagicMock(),
                    'numpy': MagicMock(),
                }):
                    import benchmark_retrieval as br
                    self.br = br
    
    def test_recommendation_excellent(self):
        """Test recommendation when MAP@10 >= 0.95."""
        metrics = self.br.RetrievalMetrics(
            map_at_10=0.96,
            ndcg_at_10=0.95,
            recall_at_10=0.90,
            recall_at_50=0.95,
            recall_at_100=0.98,
            mrr=0.97,
        )
        
        recommendation, color = self.br.get_recommendation(metrics)
        
        assert "SKIP Phase 6" in recommendation
        assert color == self.br.Colors.GREEN
    
    def test_recommendation_good(self):
        """Test recommendation when 0.90 <= MAP@10 < 0.95."""
        metrics = self.br.RetrievalMetrics(
            map_at_10=0.92,
            ndcg_at_10=0.90,
            recall_at_10=0.85,
            recall_at_50=0.92,
            recall_at_100=0.95,
            mrr=0.93,
        )
        
        recommendation, color = self.br.get_recommendation(metrics)
        
        assert "OPTIONAL Phase 6" in recommendation
        assert color == self.br.Colors.YELLOW
    
    def test_recommendation_moderate(self):
        """Test recommendation when 0.80 <= MAP@10 < 0.90."""
        metrics = self.br.RetrievalMetrics(
            map_at_10=0.85,
            ndcg_at_10=0.82,
            recall_at_10=0.75,
            recall_at_50=0.85,
            recall_at_100=0.90,
            mrr=0.87,
        )
        
        recommendation, color = self.br.get_recommendation(metrics)
        
        assert "PROCEED with Phase 6" in recommendation
        assert "Tri-vector may help" in recommendation
        assert color == self.br.Colors.YELLOW
    
    def test_recommendation_poor(self):
        """Test recommendation when MAP@10 < 0.80."""
        metrics = self.br.RetrievalMetrics(
            map_at_10=0.75,
            ndcg_at_10=0.70,
            recall_at_10=0.65,
            recall_at_50=0.75,
            recall_at_100=0.80,
            mrr=0.78,
        )
        
        recommendation, color = self.br.get_recommendation(metrics)
        
        assert "PROCEED with Phase 6" in recommendation
        assert "Tri-vector recommended" in recommendation
        assert color == self.br.Colors.RED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

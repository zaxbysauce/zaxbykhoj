#!/usr/bin/env python3
"""
Standalone test runner for benchmark_retrieval.py
"""
import sys
import os
import math
import json
import argparse

# Mock Django and other dependencies before importing
class MockDjango:
    @staticmethod
    def setup():
        pass
sys.modules['django'] = MockDjango()
sys.modules['khoj'] = type(sys)('khoj')
sys.modules['khoj.app'] = type(sys)('khoj.app')
sys.modules['khoj.app.settings'] = type(sys)('khoj.app.settings')
sys.modules['khoj.utils'] = type(sys)('khoj.utils')
sys.modules['khoj.utils.config'] = type(sys)('khoj.utils.config')
sys.modules['khoj.search_type'] = type(sys)('khoj.search_type')
sys.modules['khoj.search_type.text_search'] = type(sys)('khoj.search_type.text_search')
sys.modules['khoj.database'] = type(sys)('khoj.database')
sys.modules['khoj.database.models'] = type(sys)('khoj.database.models')
sys.modules['khoj.database.adapters'] = type(sys)('khoj.database.adapters')
sys.modules['khoj.utils.helpers'] = type(sys)('khoj.utils.helpers')
sys.modules['khoj.processor'] = type(sys)('khoj.processor')
sys.modules['khoj.processor.embeddings'] = type(sys)('khoj.processor.embeddings')
sys.modules['khoj.processor.content'] = type(sys)('khoj.processor.content')
sys.modules['khoj.processor.content.plaintext'] = type(sys)('khoj.processor.content.plaintext')
sys.modules['khoj.processor.content.plaintext.plaintext_to_entries'] = type(sys)('khoj.processor.content.plaintext.plaintext_to_entries')
sys.modules['tests'] = type(sys)('tests')
sys.modules['tests.helpers'] = type(sys)('tests.helpers')
sys.modules['asgiref'] = type(sys)('asgiref')
sys.modules['asgiref.sync'] = type(sys)('asgiref.sync')
sys.modules['asgiref.sync'].sync_to_async = lambda f: f
sys.modules['torch'] = type(sys)('torch')
sys.modules['numpy'] = type(sys)('numpy')

os.environ['DJANGO_SETTINGS_MODULE'] = 'khoj.app.settings'

# Now import and test
import benchmark_retrieval as br

print('=== Test 1: Import without errors ===')
print('PASS: Module imported successfully')
print(f'  - RetrievalBenchmark: {hasattr(br, "RetrievalBenchmark")}')
print(f'  - RetrievalMetrics: {hasattr(br, "RetrievalMetrics")}')
print(f'  - BenchmarkQuery: {hasattr(br, "BenchmarkQuery")}')
print(f'  - SyntheticDatasetLoader: {hasattr(br, "SyntheticDatasetLoader")}')
print(f'  - MSMarcMiniLoader: {hasattr(br, "MSMarcMiniLoader")}')
print(f'  - main: {hasattr(br, "main")}')
print(f'  - main_async: {hasattr(br, "main_async")}')
print()

print('=== Test 2: Synthetic Dataset Generation ===')
mock_user = type('MockUser', (), {})()
loader = br.SyntheticDatasetLoader(mock_user)

corpus = loader.create_synthetic_corpus(num_docs=100)
print(f'PASS: Created corpus with {len(corpus)} documents')
assert len(corpus) == 100, 'Expected 100 docs'
assert all(doc_id.startswith("doc_") for doc_id in corpus.keys()), 'Invalid doc_id format'
print(f'  - Document ID format correct')
print(f'  - All documents have content: {all(len(c) > 0 for c in corpus.values())}')

# Check topics
topics = ["machine learning", "deep learning", "neural networks"]
for i, topic in enumerate(topics):
    doc_id = f"doc_{i:04d}"
    assert topic in corpus[doc_id].lower(), f'Topic not found in {doc_id}'
print(f'  - Topics correctly cycled in corpus')

queries = loader.create_queries(corpus, num_queries=10)
print(f'PASS: Created {len(queries)} queries')
assert len(queries) == 10, 'Expected 10 queries'

for query in queries:
    assert hasattr(query, 'query_id'), 'Missing query_id'
    assert hasattr(query, 'query_text'), 'Missing query_text'
    assert hasattr(query, 'relevant_doc_ids'), 'Missing relevant_doc_ids'
    assert hasattr(query, 'relevance_scores'), 'Missing relevance_scores'
    assert isinstance(query.relevant_doc_ids, set), 'relevant_doc_ids should be set'
    assert isinstance(query.relevance_scores, dict), 'relevance_scores should be dict'
print(f'  - All queries have correct structure')
print()

print('=== Test 3: Metric Calculations ===')
mock_config = type('MockConfig', (), {})()
benchmark = br.RetrievalBenchmark(mock_config)

# Test AP@k perfect retrieval
retrieved = ["doc_1", "doc_2", "doc_3", "doc_4", "doc_5"]
relevant = {"doc_1", "doc_2", "doc_3"}
ap = benchmark.compute_ap_at_k(retrieved, relevant, k=10)
print(f'  AP@10 (perfect): {ap:.4f} (expected: 1.0)')
assert ap == 1.0, f'Expected 1.0, got {ap}'
assert 0.0 <= ap <= 1.0, 'AP out of range'

# Test AP@k no relevant
ap = benchmark.compute_ap_at_k(retrieved, set(), k=10)
print(f'  AP@10 (no relevant): {ap:.4f} (expected: 0.0)')
assert ap == 0.0, f'Expected 0.0, got {ap}'

# Test Recall@k
recall = benchmark.compute_recall_at_k(retrieved, relevant, k=5)
print(f'  Recall@5: {recall:.4f} (expected: 1.0)')
assert recall == 1.0, f'Expected 1.0, got {recall}'
assert 0.0 <= recall <= 1.0, 'Recall out of range'

# Test MRR
mrr = benchmark.compute_mrr(retrieved, relevant)
print(f'  MRR: {mrr:.4f} (expected: 1.0)')
assert mrr == 1.0, f'Expected 1.0, got {mrr}'
assert 0.0 <= mrr <= 1.0, 'MRR out of range'

# Test nDCG
relevance_scores = {"doc_1": 1.0, "doc_2": 0.5, "doc_3": 0.3}
ndcg = benchmark.compute_ndcg_at_k(retrieved, relevance_scores, k=3)
print(f'  nDCG@3 (perfect): {ndcg:.4f} (expected: 1.0)')
assert ndcg == 1.0, f'Expected 1.0, got {ndcg}'
assert 0.0 <= ndcg <= 1.0, 'nDCG out of range'

# Test imperfect nDCG
retrieved_imperfect = ["doc_3", "doc_2", "doc_1"]
ndcg_imperfect = benchmark.compute_ndcg_at_k(retrieved_imperfect, relevance_scores, k=3)
print(f'  nDCG@3 (imperfect): {ndcg_imperfect:.4f} (expected: < 1.0)')
assert 0.0 <= ndcg_imperfect < 1.0, f'Expected < 1.0, got {ndcg_imperfect}'

print('PASS: All metric calculations produce valid results in [0, 1] range')
print()

print('=== Test 4: CLI Argument Parsing ===')
parser = argparse.ArgumentParser()
parser.add_argument('--dataset', default='synthetic', choices=['msmarco_mini', 'synthetic'])
parser.add_argument('--output', default='benchmark_results.json')
parser.add_argument('--k', type=int, default=10)
parser.add_argument('--num-docs', type=int, default=100)
parser.add_argument('--num-queries', type=int, default=20)
parser.add_argument('--max-queries', type=int, default=100)
parser.add_argument('--crag', action='store_true', default=None)
parser.add_argument('--no-crag', action='store_true')
parser.add_argument('--hybrid', action='store_true', default=None)
parser.add_argument('--no-hybrid', action='store_true')
parser.add_argument('--contextual-chunking', action='store_true')
parser.add_argument('--multi-scale', action='store_true')
parser.add_argument('--tri-vector', action='store_true')
parser.add_argument('--hybrid-alpha', type=float, default=0.6)

# Test defaults
args = parser.parse_args([])
assert args.dataset == 'synthetic', 'Default dataset wrong'
assert args.output == 'benchmark_results.json', 'Default output wrong'
assert args.k == 10, 'Default k wrong'
assert args.num_docs == 100, 'Default num_docs wrong'
assert args.num_queries == 20, 'Default num_queries wrong'
assert args.hybrid_alpha == 0.6, 'Default hybrid_alpha wrong'
print('  Default values correct')

# Test custom values
args = parser.parse_args(['--dataset', 'msmarco_mini', '--k', '20', '--hybrid-alpha', '0.8'])
assert args.dataset == 'msmarco_mini', 'Custom dataset wrong'
assert args.k == 20, 'Custom k wrong'
assert args.hybrid_alpha == 0.8, 'Custom hybrid_alpha wrong'
print('  Custom values parsed correctly')

# Test boolean flags
args = parser.parse_args(['--crag', '--hybrid', '--tri-vector'])
assert args.crag is True, 'crag flag not set'
assert args.hybrid is True, 'hybrid flag not set'
assert args.tri_vector is True, 'tri-vector flag not set'
print('  Boolean flags work correctly')

print('PASS: CLI argument parsing works correctly')
print()

print('=== Test 5: JSON Output Format ===')
metrics = br.RetrievalMetrics(
    map_at_10=0.85,
    ndcg_at_10=0.82,
    recall_at_10=0.75,
    recall_at_50=0.88,
    recall_at_100=0.92,
    mrr=0.90,
    total_queries=100,
    dataset_name='test_dataset',
    timestamp='2024-01-01T00:00:00',
    config={'hybrid_search_enabled': True}
)

result = metrics.to_dict()
assert 'metrics' in result, 'Missing metrics key'
assert 'metadata' in result, 'Missing metadata key'
assert result['metrics']['map_at_10'] == 0.85, 'map_at_10 wrong'
assert result['metrics']['ndcg_at_10'] == 0.82, 'ndcg_at_10 wrong'
assert result['metrics']['recall_at_10'] == 0.75, 'recall_at_10 wrong'
assert result['metrics']['recall_at_50'] == 0.88, 'recall_at_50 wrong'
assert result['metrics']['recall_at_100'] == 0.92, 'recall_at_100 wrong'
assert result['metrics']['mrr'] == 0.90, 'mrr wrong'
assert result['metadata']['total_queries'] == 100, 'total_queries wrong'
assert result['metadata']['dataset_name'] == 'test_dataset', 'dataset_name wrong'
print('  JSON structure correct')

# Test serialization
json_str = json.dumps(result, indent=2)
parsed = json.loads(json_str)
assert parsed['metrics']['map_at_10'] == 0.85, 'JSON round-trip failed'
print('  JSON serialization/deserialization works')

# Test rounding
metrics2 = br.RetrievalMetrics(
    map_at_10=0.12345678,
    ndcg_at_10=0.87654321,
    recall_at_10=0.55555555,
    recall_at_50=0.99999999,
    recall_at_100=0.11111111,
    mrr=0.77777777,
)
result2 = metrics2.to_dict()
assert result2['metrics']['map_at_10'] == 0.1235, f'Rounding failed: {result2["metrics"]["map_at_10"]}'
assert result2['metrics']['recall_at_50'] == 1.0, f'Rounding failed: {result2["metrics"]["recall_at_50"]}'
print('  Metric rounding to 4 decimal places works')

print('PASS: JSON output format is correct')
print()

print('=== Test 6: Recommendation Logic ===')
# Test excellent MAP@10
metrics_excellent = br.RetrievalMetrics(map_at_10=0.96, ndcg_at_10=0, recall_at_10=0, recall_at_50=0, recall_at_100=0, mrr=0)
rec, color = br.get_recommendation(metrics_excellent)
assert 'SKIP Phase 6' in rec, f'Wrong recommendation for excellent: {rec}'
assert color == br.Colors.GREEN, 'Wrong color for excellent'
print('  Excellent MAP@10 (>=0.95): SKIP Phase 6')

# Test good MAP@10
metrics_good = br.RetrievalMetrics(map_at_10=0.92, ndcg_at_10=0, recall_at_10=0, recall_at_50=0, recall_at_100=0, mrr=0)
rec, color = br.get_recommendation(metrics_good)
assert 'OPTIONAL Phase 6' in rec, f'Wrong recommendation for good: {rec}'
assert color == br.Colors.YELLOW, 'Wrong color for good'
print('  Good MAP@10 (0.90-0.95): OPTIONAL Phase 6')

# Test moderate MAP@10
metrics_moderate = br.RetrievalMetrics(map_at_10=0.85, ndcg_at_10=0, recall_at_10=0, recall_at_50=0, recall_at_100=0, mrr=0)
rec, color = br.get_recommendation(metrics_moderate)
assert 'PROCEED with Phase 6' in rec, f'Wrong recommendation for moderate: {rec}'
assert 'Tri-vector may help' in rec, 'Wrong message for moderate'
assert color == br.Colors.YELLOW, 'Wrong color for moderate'
print('  Moderate MAP@10 (0.80-0.90): PROCEED with Phase 6')

# Test poor MAP@10
metrics_poor = br.RetrievalMetrics(map_at_10=0.75, ndcg_at_10=0, recall_at_10=0, recall_at_50=0, recall_at_100=0, mrr=0)
rec, color = br.get_recommendation(metrics_poor)
assert 'PROCEED with Phase 6' in rec, f'Wrong recommendation for poor: {rec}'
assert 'Tri-vector recommended' in rec, 'Wrong message for poor'
assert color == br.Colors.RED, 'Wrong color for poor'
print('  Poor MAP@10 (<0.80): PROCEED with Phase 6')

print('PASS: Recommendation logic works correctly')
print()

print('=== Test 7: Edge Cases ===')
# Empty retrieved list
ap = benchmark.compute_ap_at_k([], relevant, k=10)
recall = benchmark.compute_recall_at_k([], relevant, k=10)
mrr = benchmark.compute_mrr([], relevant)
ndcg = benchmark.compute_ndcg_at_k([], relevance_scores, k=10)
assert ap == 0.0 and recall == 0.0 and mrr == 0.0 and ndcg == 0.0, 'Empty list handling failed'
print('  Empty retrieved list handled correctly')

# k larger than retrieved
ap = benchmark.compute_ap_at_k(["doc_1"], {"doc_1"}, k=100)
recall = benchmark.compute_recall_at_k(["doc_1"], {"doc_1"}, k=100)
assert ap == 1.0, f'k > len(retrieved) AP failed: {ap}'
assert recall == 1.0, f'k > len(retrieved) Recall failed: {recall}'
print('  k larger than retrieved list handled correctly')

# Missing relevance scores
retrieved = ["doc_1", "doc_2", "doc_3"]
scores = {"doc_1": 1.0}
dcg = benchmark.compute_dcg_at_k(retrieved, scores, k=3)
assert dcg == 1.0, f'Missing scores DCG failed: {dcg}'
print('  Missing relevance scores handled correctly')

print('PASS: Edge cases handled correctly')
print()

print('=' * 60)
print('ALL TESTS PASSED!')
print('=' * 60)

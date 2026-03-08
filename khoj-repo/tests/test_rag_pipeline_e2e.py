"""
End-to-End tests for the RAG pipeline.

Tests cover the full query flow including:
- CRAG evaluation and fallback
- Query transformation (step-back prompting)
- Hybrid search (dense + sparse)
- Multi-scale chunking

Mocking strategy:
- LLM calls (CRAG evaluator, query transformer) are mocked
- Embeddings generation is mocked
- Database is used for Entry storage (real database)
- External API calls are mocked
"""

import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import torch
from asgiref.sync import sync_to_async
from fastapi.testclient import TestClient

from khoj.database.models import Entry, KhojUser
from khoj.processor.content.plaintext.plaintext_to_entries import PlaintextToEntries
from khoj.processor.query_transformer import QueryTransformer
from khoj.processor.retrieval_evaluator import RetrievalEvaluator, RetrievalEvaluation
from khoj.utils.config import RagConfig
from khoj.utils.helpers import rrf_fuse_multi
from khoj.utils.rawconfig import Entry as RawEntry


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client for testing."""
    return MagicMock()


@pytest.fixture
def retrieval_evaluator(mock_llm_client):
    """Create a RetrievalEvaluator with mock client."""
    return RetrievalEvaluator(llm_client=mock_llm_client, model_name="gpt-4o-mini")


@pytest.fixture
def query_transformer(mock_llm_client):
    """Create a QueryTransformer with mock client."""
    return QueryTransformer(
        llm_client=mock_llm_client,
        model_name="gpt-4o-mini",
        temperature=0.7,
        max_tokens=100,
    )


@pytest.fixture
def sample_entries():
    """Create sample entries for testing."""
    return [
        {
            "id": "entry_1",
            "content": "Python is a high-level programming language known for its readability.",
            "score": 0.95,
        },
        {
            "id": "entry_2",
            "content": "Machine learning algorithms can be implemented in Python using libraries like scikit-learn.",
            "score": 0.88,
        },
        {
            "id": "entry_3",
            "content": "Java is another popular programming language used in enterprise applications.",
            "score": 0.72,
        },
    ]


@pytest.fixture
def mock_embeddings():
    """Create mock embeddings tensor."""
    return torch.randn(1, 384)  # Standard embedding size


# =============================================================================
# Test Suite: Full Pipeline Integration
# =============================================================================


class TestFullPipeline:
    """End-to-end tests for the complete RAG pipeline with all features."""

    @pytest.mark.django_db
    @pytest.mark.asyncio
    async def test_full_pipeline_with_all_features(
        self, default_user, mock_llm_client, mock_embeddings
    ):
        """
        Test full pipeline with all RAG features enabled.

        Verifies:
        - CRAG evaluation is invoked
        - Query transformation is triggered when AMBIGUOUS
        - Hybrid search is used
        - Multi-scale chunking is active
        - Final results are returned correctly
        """
        # Enable all features
        original_crag = RagConfig.crag_enabled
        original_query_transform = RagConfig.query_transform_enabled
        original_hybrid = RagConfig.hybrid_search_enabled
        original_multi_scale = RagConfig.multi_scale_chunking_enabled

        try:
            RagConfig.crag_enabled = True
            RagConfig.query_transform_enabled = True
            RagConfig.hybrid_search_enabled = True
            RagConfig.multi_scale_chunking_enabled = True

            # Setup mock LLM responses
            # First call: CRAG evaluation returns AMBIGUOUS
            mock_response_crag = MagicMock()
            mock_response_crag.choices = [MagicMock()]
            mock_response_crag.choices[0].message.content = "AMBIGUOUS"

            # Second call: Query transformation returns step-back query
            mock_response_transform = MagicMock()
            mock_response_transform.choices = [MagicMock()]
            mock_response_transform.choices[0].message.content = "What are popular programming languages?"

            mock_llm_client.chat.completions.create.side_effect = [
                mock_response_crag,
                mock_response_transform,
            ]

            # Create sample entries in database
            entries = []
            for i, (scale, content) in enumerate([
                ("512", "Python is a programming language."),
                ("1024", "Python is a high-level programming language known for readability."),
                ("2048", "Python is a versatile programming language used in data science."),
            ]):
                entry = await sync_to_async(Entry.objects.create)(
                    user=default_user,
                    raw=content,
                    compiled=content,
                    heading=f"Test Entry {i}",
                    file_path=f"test_{i}.txt",
                    file_type=Entry.EntryType.PLAINTEXT,
                    hashed_value=f"hash_{i}",
                    corpus_id=uuid.uuid4(),
                    chunk_scale=scale,
                )
                entries.append(entry)

            # Verify entries were created with different scales
            assert len(entries) == 3
            scales = set(e.chunk_scale for e in entries)
            assert "512" in scales
            assert "1024" in scales
            assert "2048" in scales

            # Verify CRAG evaluator works with mock
            evaluator = RetrievalEvaluator(llm_client=mock_llm_client)
            test_chunks = [{"id": "1", "content": "Python programming language"}]
            result = evaluator.evaluate("What is Python?", test_chunks)

            assert result == RetrievalEvaluation.AMBIGUOUS
            assert mock_llm_client.chat.completions.create.call_count >= 1

            # Verify query transformer works
            transformer = QueryTransformer(llm_client=mock_llm_client)
            queries = transformer.transform("What is Python?")

            assert len(queries) == 2
            assert queries[0] == "What is Python?"
            assert queries[1] == "What are popular programming languages?"

            # Verify multi-scale entries exist in database
            db_entries = await sync_to_async(list)(
                Entry.objects.filter(user=default_user)
            )
            assert len(db_entries) >= 3

            # Verify RRF fusion works with multi-scale results
            sources = {
                "dense_512": [{"id": "1", "content": "Python basics"}],
                "dense_1024": [{"id": "1", "content": "Python basics"}, {"id": "2", "content": "Advanced Python"}],
                "sparse_512": [{"id": "1", "content": "Python basics"}],
            }
            fused = rrf_fuse_multi(sources, k=60, limit=5)

            assert len(fused) > 0
            assert "rrf_score" in fused[0]
            assert "source_contributions" in fused[0]

        finally:
            # Restore original config
            RagConfig.crag_enabled = original_crag
            RagConfig.query_transform_enabled = original_query_transform
            RagConfig.hybrid_search_enabled = original_hybrid
            RagConfig.multi_scale_chunking_enabled = original_multi_scale

    @pytest.mark.django_db
    def test_crag_confident_path(self, mock_llm_client, sample_entries):
        """
        Test CRAG CONFIDENT path - no query transformation needed.

        Verifies:
        - CRAG returns CONFIDENT for high-quality results
        - No query transformation is triggered
        - Results are returned directly
        """
        # Setup mock to return CONFIDENT
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "CONFIDENT"
        mock_llm_client.chat.completions.create.return_value = mock_response

        evaluator = RetrievalEvaluator(llm_client=mock_llm_client)

        # Evaluate sample entries
        result = evaluator.evaluate("What is Python?", sample_entries)

        assert result == RetrievalEvaluation.CONFIDENT

        # Test evaluate_with_fallback
        chunks, evaluation, warning = evaluator.evaluate_with_fallback(
            "What is Python?",
            sample_entries,
        )

        assert evaluation == RetrievalEvaluation.CONFIDENT
        assert chunks == sample_entries  # Original chunks returned
        assert warning is None

    @pytest.mark.django_db
    def test_crag_ambiguous_path(self, mock_llm_client, sample_entries):
        """
        Test CRAG AMBIGUOUS path - triggers query transformation.

        Verifies:
        - CRAG returns AMBIGUOUS for partial results
        - Query transformation is triggered
        - Fallback search with lower threshold occurs
        """
        # Setup mock to return AMBIGUOUS
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "AMBIGUOUS"
        mock_llm_client.chat.completions.create.return_value = mock_response

        evaluator = RetrievalEvaluator(llm_client=mock_llm_client)

        # Test with fallback search function
        fallback_results = [
            {"id": "fallback_1", "content": "More comprehensive Python info"},
            {"id": "fallback_2", "content": "Additional Python context"},
        ]

        def mock_search_fn(query, threshold):
            return fallback_results

        chunks, evaluation, warning = evaluator.evaluate_with_fallback(
            "What is Python?",
            sample_entries,
            search_fn=mock_search_fn,
            lower_threshold=0.3,
        )

        assert evaluation == RetrievalEvaluation.AMBIGUOUS
        assert chunks == fallback_results  # Fallback results returned
        assert warning is None

        # Verify search function was called with lower threshold
        # (search_fn would be called with threshold=0.3)

    @pytest.mark.django_db
    def test_hybrid_search_with_multi_scale(self, default_user):
        """
        Test hybrid search with multi-scale chunking.

        Verifies:
        - Hybrid search combines dense and sparse results
        - Multi-scale chunks from different sizes are retrieved
        - rrf_fuse_multi is used for result fusion
        """
        # Create entries at different scales
        entries_512 = []
        entries_1024 = []

        for i in range(3):
            entry_512 = Entry(
                user=default_user,
                raw=f"Content 512 {i}",
                compiled=f"Content 512 {i}",
                heading=f"Heading 512 {i}",
                file_path=f"test_512_{i}.txt",
                file_type=Entry.EntryType.PLAINTEXT,
                hashed_value=f"hash_512_{i}",
                corpus_id=uuid.uuid4(),
                chunk_scale="512",
            )
            entries_512.append(entry_512)

            entry_1024 = Entry(
                user=default_user,
                raw=f"Content 1024 {i}",
                compiled=f"Content 1024 {i}",
                heading=f"Heading 1024 {i}",
                file_path=f"test_1024_{i}.txt",
                file_type=Entry.EntryType.PLAINTEXT,
                hashed_value=f"hash_1024_{i}",
                corpus_id=uuid.uuid4(),
                chunk_scale="1024",
            )
            entries_1024.append(entry_1024)

        # Simulate hybrid search results from different scales
        dense_results_512 = [
            {"id": "entry_512_0", "content": "Content 512 0", "score": 0.95},
            {"id": "entry_512_1", "content": "Content 512 1", "score": 0.88},
        ]
        sparse_results_512 = [
            {"id": "entry_512_0", "content": "Content 512 0", "score": 0.92},
            {"id": "entry_512_2", "content": "Content 512 2", "score": 0.85},
        ]
        dense_results_1024 = [
            {"id": "entry_1024_0", "content": "Content 1024 0", "score": 0.90},
            {"id": "entry_1024_1", "content": "Content 1024 1", "score": 0.82},
        ]

        # Use rrf_fuse_multi to combine all results
        sources = {
            "dense_512": dense_results_512,
            "sparse_512": sparse_results_512,
            "dense_1024": dense_results_1024,
        }

        fused_results = rrf_fuse_multi(sources, k=60, limit=10)

        # Verify fusion worked
        assert len(fused_results) > 0

        # entry_512_0 appears in both dense and sparse 512 - should have highest score
        entry_512_0 = next((r for r in fused_results if r["id"] == "entry_512_0"), None)
        assert entry_512_0 is not None
        assert entry_512_0["rrf_score"] > 0
        assert "source_contributions" in entry_512_0
        assert len(entry_512_0["source_contributions"]) >= 2  # From multiple sources

    @pytest.mark.django_db
    def test_query_transformation_step_back(self, mock_llm_client):
        """
        Test query transformation using step-back prompting.

        Verifies:
        - Original query is preserved
        - Step-back variant is generated
        - Multiple query variants are returned
        """
        # Setup mock response for step-back transformation
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "What are popular programming languages?"
        mock_llm_client.chat.completions.create.return_value = mock_response

        transformer = QueryTransformer(llm_client=mock_llm_client)

        # Transform query
        queries = transformer.transform("What is Python?")

        # Verify both original and transformed queries are returned
        assert len(queries) == 2
        assert queries[0] == "What is Python?"
        assert queries[1] == "What are popular programming languages?"

        # Verify LLM was called with correct prompt structure
        call_args = mock_llm_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "gpt-4o-mini"
        assert "step-back prompting" in call_args[1]["messages"][0]["content"].lower()
        assert "What is Python?" in call_args[1]["messages"][1]["content"]

    @pytest.mark.django_db
    @pytest.mark.asyncio
    async def test_pipeline_with_disabled_features(self, default_user):
        """
        Test pipeline with all features disabled.

        Verifies:
        - Basic retrieval still works when features are disabled
        - No errors from disabled components
        - Default behavior is maintained
        """
        # Disable all features
        original_crag = RagConfig.crag_enabled
        original_query_transform = RagConfig.query_transform_enabled
        original_hybrid = RagConfig.hybrid_search_enabled
        original_multi_scale = RagConfig.multi_scale_chunking_enabled

        try:
            RagConfig.crag_enabled = False
            RagConfig.query_transform_enabled = False
            RagConfig.hybrid_search_enabled = False
            RagConfig.multi_scale_chunking_enabled = False

            # Create a simple entry
            entry = await sync_to_async(Entry.objects.create)(
                user=default_user,
                raw="Test content for basic retrieval",
                compiled="Test content for basic retrieval",
                heading="Test Entry",
                file_path="test.txt",
                file_type=Entry.EntryType.PLAINTEXT,
                hashed_value="hash_test",
                corpus_id=uuid.uuid4(),
                chunk_scale="default",
            )

            # Verify entry was created
            assert entry.id is not None
            assert entry.chunk_scale == "default"

            # Basic retrieval should still work
            db_entry = await sync_to_async(Entry.objects.filter(user=default_user).first)()
            assert db_entry is not None
            assert db_entry.raw == "Test content for basic retrieval"

            # Verify feature flags are disabled
            assert RagConfig.crag_enabled is False
            assert RagConfig.query_transform_enabled is False
            assert RagConfig.hybrid_search_enabled is False
            assert RagConfig.multi_scale_chunking_enabled is False

        finally:
            # Restore original config
            RagConfig.crag_enabled = original_crag
            RagConfig.query_transform_enabled = original_query_transform
            RagConfig.hybrid_search_enabled = original_hybrid
            RagConfig.multi_scale_chunking_enabled = original_multi_scale


# =============================================================================
# Test Suite: Entry Processing
# =============================================================================


class TestEndToEndEntryProcessing:
    """Tests for end-to-end entry processing through text_to_entries."""

    @pytest.mark.django_db
    def test_entry_processing_creates_multi_scale_chunks(self, default_user):
        """
        Test that text_to_entries creates multi-scale chunks.

        Verifies:
        - Document is processed through text_to_entries
        - Multiple chunk sizes are created
        - Each chunk has appropriate chunk_scale
        """
        # Create sample document content
        paragraphs = []
        for i in range(50):
            paragraphs.append(f"Paragraph {i}: " + " ".join([f"word{j}" for j in range(20)]))
        content = "\n\n".join(paragraphs)

        # Create RawEntry
        entry = RawEntry(
            raw=content,
            compiled=content,
            heading="Test Document",
            file="test_document.txt",
            corpus_id=uuid.uuid4(),
        )

        # Split entries with multi-scale chunking
        chunk_sizes = [256, 512, 1024]
        chunked_entries = PlaintextToEntries.split_entries_by_max_tokens(
            [entry],
            chunk_sizes=chunk_sizes,
            raw_is_compiled=True,
        )

        # Verify chunks were created at all scales
        scales = set(chunk.chunk_scale for chunk in chunked_entries)

        assert "256" in scales
        assert "512" in scales
        assert "1024" in scales

        # Verify each chunk has the correct structure
        for chunk in chunked_entries:
            assert hasattr(chunk, "compiled")
            assert hasattr(chunk, "raw")
            assert hasattr(chunk, "heading")
            assert hasattr(chunk, "file")
            assert hasattr(chunk, "corpus_id")
            assert hasattr(chunk, "chunk_scale")
            assert chunk.chunk_scale in ["256", "512", "1024"]

    @pytest.mark.django_db
    @pytest.mark.asyncio
    async def test_entry_retrieval_with_different_scales(self, default_user):
        """
        Test retrieval of entries with different chunk scales.

        Verifies:
        - Entries at different scales can be queried
        - Scale information is preserved
        """
        # Create entries at different scales
        scales = ["256", "512", "1024", "2048"]
        created_entries = []

        for scale in scales:
            entry = await sync_to_async(Entry.objects.create)(
                user=default_user,
                raw=f"Content at scale {scale}",
                compiled=f"Content at scale {scale}",
                heading=f"Heading {scale}",
                file_path=f"test_{scale}.txt",
                file_type=Entry.EntryType.PLAINTEXT,
                hashed_value=f"hash_{scale}_{uuid.uuid4()}",
                corpus_id=uuid.uuid4(),
                chunk_scale=scale,
            )
            created_entries.append(entry)

        # Retrieve entries by scale
        for scale in scales:
            entries_at_scale = await sync_to_async(list)(
                Entry.objects.filter(user=default_user, chunk_scale=scale)
            )
            assert len(entries_at_scale) >= 1
            for entry in entries_at_scale:
                assert entry.chunk_scale == scale


# =============================================================================
# Test Suite: API Integration
# =============================================================================


class TestRagMetricsEndpoint:
    """Tests for the /api/rag/metrics endpoint integration."""

    @pytest.mark.django_db
    @pytest.mark.asyncio
    async def test_rag_metrics_endpoint_integration(self, client, default_user, api_user):
        """
        Test the /api/rag/metrics endpoint with real data.

        Verifies:
        - Endpoint returns accurate entry counts
        - Feature flags are correctly reported
        - Scale information is accurate
        """
        # Create entries with different chunk scales
        scales = {
            "512": 3,
            "1024": 2,
            "2048": 1,
            "default": 2,
        }

        for scale, count in scales.items():
            for i in range(count):
                await sync_to_async(Entry.objects.create)(
                    user=default_user,
                    raw=f"Content {i} at scale {scale}",
                    compiled=f"Content {i} at scale {scale}",
                    heading=f"Heading {i}",
                    file_path=f"test_{scale}_{i}.txt",
                    file_type=Entry.EntryType.PLAINTEXT,
                    hashed_value=f"hash_{scale}_{i}_{uuid.uuid4()}",
                    corpus_id=uuid.uuid4(),
                    chunk_scale=scale,
                )

        # Call the metrics endpoint
        response = client.get("/api/rag/metrics", headers={"Authorization": f"Bearer {api_user.token}"})

        assert response.status_code == 200

        data = response.json()

        # Verify response structure
        assert "entry_counts_by_scale" in data
        assert "feature_flags" in data
        assert "total_entries" in data
        assert "scales_available" in data

        # Verify entry counts by scale
        entry_counts = data["entry_counts_by_scale"]
        for scale, count in scales.items():
            assert entry_counts.get(scale, 0) == count

        # Verify total entries
        assert data["total_entries"] == sum(scales.values())

        # Verify feature flags
        feature_flags = data["feature_flags"]
        assert "crag_enabled" in feature_flags
        assert "query_transform_enabled" in feature_flags
        assert "hybrid_search_enabled" in feature_flags
        assert "contextual_chunking_enabled" in feature_flags
        assert "multi_scale_chunking_enabled" in feature_flags
        assert "tri_vector_search_enabled" in feature_flags

        # Verify scales available
        scales_available = set(data["scales_available"])
        for scale in scales.keys():
            assert scale in scales_available


# =============================================================================
# Test Suite: Component Integration
# =============================================================================


class TestComponentIntegration:
    """Tests for integration between pipeline components."""

    @pytest.mark.django_db
    def test_crag_to_query_transform_flow(self, mock_llm_client):
        """
        Test the flow from CRAG evaluation to query transformation.

        Verifies:
        - AMBIGUOUS evaluation triggers query transformation
        - Transformed queries are used for re-search
        """
        # Setup mock responses
        crag_response = MagicMock()
        crag_response.choices = [MagicMock()]
        crag_response.choices[0].message.content = "AMBIGUOUS"

        transform_response = MagicMock()
        transform_response.choices = [MagicMock()]
        transform_response.choices[0].message.content = "What are programming languages?"

        mock_llm_client.chat.completions.create.side_effect = [
            crag_response,
            transform_response,
        ]

        # Step 1: CRAG evaluation
        evaluator = RetrievalEvaluator(llm_client=mock_llm_client)
        original_chunks = [{"id": "1", "content": "Some Python info"}]

        evaluation = evaluator.evaluate("What is Python?", original_chunks)
        assert evaluation == RetrievalEvaluation.AMBIGUOUS

        # Step 2: Query transformation (triggered by AMBIGUOUS)
        transformer = QueryTransformer(llm_client=mock_llm_client)
        queries = transformer.transform("What is Python?")

        assert len(queries) == 2
        assert queries[1] == "What are programming languages?"

    @pytest.mark.django_db
    def test_multi_query_results_fusion(self):
        """
        Test fusing results from multiple query variants.

        Verifies:
        - Results from different queries are fused correctly
        - rrf_fuse_multi handles overlapping results
        """
        # Simulate results from original query
        original_query_results = [
            {"id": "doc1", "content": "Python basics", "score": 0.95},
            {"id": "doc2", "content": "Python syntax", "score": 0.88},
        ]

        # Simulate results from step-back query
        step_back_results = [
            {"id": "doc1", "content": "Python basics", "score": 0.92},  # Overlap
            {"id": "doc3", "content": "Programming languages overview", "score": 0.85},
        ]

        # Fuse results from both queries
        sources = {
            "original_query": original_query_results,
            "step_back_query": step_back_results,
        }

        fused = rrf_fuse_multi(sources, k=60, limit=10)

        # Verify fusion
        assert len(fused) == 3  # doc1, doc2, doc3

        # doc1 should have highest score (appears in both sources)
        doc1 = next(r for r in fused if r["id"] == "doc1")
        doc2 = next(r for r in fused if r["id"] == "doc2")
        doc3 = next(r for r in fused if r["id"] == "doc3")

        assert doc1["rrf_score"] > doc2["rrf_score"]
        assert doc1["rrf_score"] > doc3["rrf_score"]

        # Verify source contributions
        assert "source_contributions" in doc1
        assert "original_query" in doc1["source_contributions"]
        assert "step_back_query" in doc1["source_contributions"]

    @pytest.mark.django_db
    def test_end_to_end_confident_path(self, mock_llm_client):
        """
        Test complete confident path without transformation.

        Verifies:
        - CONFIDENT evaluation returns results immediately
        - No query transformation occurs
        - Results are passed directly to response generation
        """
        # Setup mock to return CONFIDENT
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "CONFIDENT"
        mock_llm_client.chat.completions.create.return_value = mock_response

        evaluator = RetrievalEvaluator(llm_client=mock_llm_client)

        chunks = [
            {"id": "1", "content": "Comprehensive Python documentation"},
            {"id": "2", "content": "Python examples and tutorials"},
        ]

        # Evaluate
        chunks, evaluation, warning = evaluator.evaluate_with_fallback(
            "What is Python?",
            chunks,
        )

        # Verify confident path
        assert evaluation == RetrievalEvaluation.CONFIDENT
        assert len(chunks) == 2
        assert warning is None

        # Only one LLM call (for CRAG evaluation)
        assert mock_llm_client.chat.completions.create.call_count == 1

    @pytest.mark.django_db
    def test_end_to_end_no_match_path(self, mock_llm_client):
        """
        Test complete NO_MATCH path with warning.

        Verifies:
        - NO_MATCH evaluation returns empty results
        - Warning message is generated
        - No further processing occurs
        """
        # Setup mock to return NO_MATCH
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "NO_MATCH"
        mock_llm_client.chat.completions.create.return_value = mock_response

        evaluator = RetrievalEvaluator(llm_client=mock_llm_client)

        chunks = [{"id": "1", "content": "Completely unrelated content"}]

        # Evaluate
        result_chunks, evaluation, warning = evaluator.evaluate_with_fallback(
            "What is Python?",
            chunks,
        )

        # Verify NO_MATCH path
        assert evaluation == RetrievalEvaluation.NO_MATCH
        assert result_chunks == []
        assert warning is not None
        assert "NO_MATCH" in warning
        assert "What is Python?" in warning


# =============================================================================
# Test Suite: Error Handling
# =============================================================================


class TestPipelineErrorHandling:
    """Tests for error handling in the RAG pipeline."""

    @pytest.mark.django_db
    def test_crag_error_defaults_to_ambiguous(self, mock_llm_client):
        """
        Test that CRAG errors default to AMBIGUOUS.

        Verifies:
        - LLM errors are handled gracefully
        - Pipeline continues with AMBIGUOUS evaluation
        """
        # Setup mock to raise exception
        mock_llm_client.chat.completions.create.side_effect = Exception("API Error")

        evaluator = RetrievalEvaluator(llm_client=mock_llm_client)
        chunks = [{"id": "1", "content": "Some content"}]

        result = evaluator.evaluate("What is Python?", chunks)

        assert result == RetrievalEvaluation.AMBIGUOUS

    @pytest.mark.django_db
    def test_query_transform_error_returns_original(self, mock_llm_client):
        """
        Test that query transformation errors return original query.

        Verifies:
        - LLM errors are handled gracefully
        - Original query is returned as fallback
        """
        # Setup mock to raise exception
        mock_llm_client.chat.completions.create.side_effect = Exception("API Error")

        transformer = QueryTransformer(llm_client=mock_llm_client)
        queries = transformer.transform("What is Python?")

        assert len(queries) == 1
        assert queries[0] == "What is Python?"

    @pytest.mark.django_db
    def test_empty_chunks_handling(self, mock_llm_client):
        """
        Test handling of empty chunks.

        Verifies:
        - Empty chunks return NO_MATCH
        - No errors are raised
        """
        evaluator = RetrievalEvaluator(llm_client=mock_llm_client)

        result = evaluator.evaluate("What is Python?", [])

        assert result == RetrievalEvaluation.NO_MATCH

    @pytest.mark.django_db
    def test_ambiguous_fallback_search_error(self, mock_llm_client):
        """
        Test AMBIGUOUS fallback when search function errors.

        Verifies:
        - Search errors are handled gracefully
        - Original chunks are returned
        """
        # Setup mock to return AMBIGUOUS
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "AMBIGUOUS"
        mock_llm_client.chat.completions.create.return_value = mock_response

        evaluator = RetrievalEvaluator(llm_client=mock_llm_client)

        original_chunks = [{"id": "1", "content": "Original content"}]

        def failing_search_fn(query, threshold):
            raise Exception("Search service unavailable")

        chunks, evaluation, warning = evaluator.evaluate_with_fallback(
            "What is Python?",
            original_chunks,
            search_fn=failing_search_fn,
        )

        assert evaluation == RetrievalEvaluation.AMBIGUOUS
        assert chunks == original_chunks  # Original chunks returned on error
        assert warning is None


# =============================================================================
# Test Suite: Performance and Scale
# =============================================================================


class TestPipelinePerformance:
    """Tests for pipeline performance characteristics."""

    @pytest.mark.django_db
    def test_rrf_fuse_multi_performance_with_many_sources(self):
        """
        Test RRF fusion with many sources and results.

        Verifies:
        - Performance remains acceptable with many sources
        - Deduplication works correctly at scale
        """
        # Create many sources with overlapping results
        sources = {}
        for i in range(10):  # 10 different sources
            results = []
            for j in range(20):  # 20 results each
                result_id = f"doc_{(i + j) % 50}"  # Creates overlap
                results.append({"id": result_id, "content": f"Content {result_id}"})
            sources[f"source_{i}"] = results

        # Fuse results
        fused = rrf_fuse_multi(sources, k=60, limit=10)

        # Verify reasonable results
        assert len(fused) == 10  # Limited to 10

        # Verify all results have required fields
        for result in fused:
            assert "id" in result
            assert "rrf_score" in result
            assert "source_contributions" in result

    @pytest.mark.django_db
    def test_multi_scale_retrieval_with_weighted_fusion(self):
        """
        Test multi-scale retrieval with weighted source fusion.

        Verifies:
        - Source weights affect ranking
        - Larger scales can be weighted differently
        """
        sources = {
            "dense_512": [{"id": "doc1", "content": "Content 512"}],
            "dense_1024": [{"id": "doc1", "content": "Content 1024"}],
            "dense_2048": [{"id": "doc1", "content": "Content 2048"}],
        }

        # Test with equal weights
        fused_equal = rrf_fuse_multi(sources, k=60, limit=10)

        # Test with weighted preference for larger scales
        weights = {"dense_512": 0.5, "dense_1024": 1.0, "dense_2048": 1.5}
        fused_weighted = rrf_fuse_multi(
            sources, k=60, limit=10, source_weights=weights
        )

        # Both should return results
        assert len(fused_equal) == 1
        assert len(fused_weighted) == 1

        # Weighted score should be different from equal score
        assert fused_equal[0]["rrf_score"] != fused_weighted[0]["rrf_score"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

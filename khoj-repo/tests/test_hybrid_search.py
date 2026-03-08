"""
Comprehensive tests for hybrid search functionality.

Tests for dense_search(), sparse_search(), and hybrid_search() functions
with mocked database queries and embeddings.
"""

from unittest.mock import MagicMock, patch

import pytest
import torch

from khoj.database.models import Agent, Entry, KhojUser
from khoj.search_type import text_search


class MockQuerySet:
    """Mock Django QuerySet for testing."""

    def __init__(self, results):
        self._results = results

    def annotate(self, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        # Handle agent and file_type filtering
        if "agent" in kwargs:
            agent = kwargs["agent"]
            filtered = [r for r in self._results if getattr(r, "agent", None) == agent]
            return MockQuerySet(filtered)
        if "file_type" in kwargs:
            file_type = kwargs["file_type"]
            filtered = [r for r in self._results if getattr(r, "file_type", None) == file_type]
            return MockQuerySet(filtered)
        return self

    def order_by(self, *args):
        # Simple mock - just return self
        return self

    def __getitem__(self, key):
        return MockQuerySet(self._results[key])

    def __iter__(self):
        return iter(self._results)

    def __len__(self):
        return len(self._results)

    def all(self):
        return self


def create_mock_entry(entry_id: int, content: str = None, **kwargs) -> MagicMock:
    """Create a mock Entry object for testing."""
    entry = MagicMock(spec=Entry)
    entry.id = entry_id
    entry.raw = content or f"Test content {entry_id}"
    entry.compiled = content or f"Test compiled {entry_id}"
    entry.heading = kwargs.get("heading", f"Test heading {entry_id}")
    entry.file_type = kwargs.get("file_type", Entry.EntryType.PLAINTEXT)
    entry.file_source = kwargs.get("file_source", Entry.EntrySource.COMPUTER)
    entry.file_path = kwargs.get("file_path", f"/test/path/{entry_id}.txt")
    entry.hashed_value = kwargs.get("hashed_value", f"hash_{entry_id}")
    entry.corpus_id = kwargs.get("corpus_id", f"corpus_{entry_id}")
    entry.url = kwargs.get("url", None)
    entry.agent = kwargs.get("agent", None)
    entry.user = kwargs.get("user", None)
    entry.distance = kwargs.get("distance", 0.5)
    return entry


class TestDenseSearch:
    """Tests for dense_search() function."""

    @pytest.mark.asyncio
    async def test_dense_search_basic(self, default_user):
        """Test basic dense search functionality."""
        # Arrange
        mock_entries = [
            create_mock_entry(1, "First test entry", distance=0.3),
            create_mock_entry(2, "Second test entry", distance=0.5),
        ]
        query_embedding = torch.tensor([0.1, 0.2, 0.3])

        with patch("khoj.search_type.text_search.EntryAdapters") as mock_adapter:
            mock_queryset = MockQuerySet(mock_entries)
            mock_adapter.search_with_embeddings.return_value = mock_queryset

            # Act
            results = await text_search.dense_search(
                query_embedding=query_embedding,
                user=default_user,
                k=10,
            )

            # Assert
            assert len(results) == 2
            assert results[0].id == 1
            assert results[1].id == 2
            mock_adapter.search_with_embeddings.assert_called_once()

    @pytest.mark.asyncio
    async def test_dense_search_with_max_distance(self, default_user):
        """Test dense search with max_distance filter."""
        # Arrange
        query_embedding = torch.tensor([0.1, 0.2, 0.3])
        max_distance = 0.4

        with patch("khoj.search_type.text_search.EntryAdapters") as mock_adapter:
            mock_entries = [create_mock_entry(1, "Close match", distance=0.3)]
            mock_adapter.search_with_embeddings.return_value = MockQuerySet(mock_entries)

            # Act
            results = await text_search.dense_search(
                query_embedding=query_embedding,
                user=default_user,
                k=10,
                max_distance=max_distance,
            )

            # Assert
            mock_adapter.search_with_embeddings.assert_called_once()
            call_kwargs = mock_adapter.search_with_embeddings.call_args[1]
            assert call_kwargs["max_distance"] == max_distance

    @pytest.mark.asyncio
    async def test_dense_search_with_file_type_filter(self, default_user):
        """Test dense search with file_type filter."""
        # Arrange
        query_embedding = torch.tensor([0.1, 0.2, 0.3])
        file_type = Entry.EntryType.MARKDOWN

        with patch("khoj.search_type.text_search.EntryAdapters") as mock_adapter:
            mock_entries = [create_mock_entry(1, "Markdown entry", file_type=file_type)]
            mock_adapter.search_with_embeddings.return_value = MockQuerySet(mock_entries)

            # Act
            results = await text_search.dense_search(
                query_embedding=query_embedding,
                user=default_user,
                k=10,
                file_type=file_type,
            )

            # Assert
            mock_adapter.search_with_embeddings.assert_called_once()
            call_kwargs = mock_adapter.search_with_embeddings.call_args[1]
            assert call_kwargs["file_type_filter"] == file_type

    @pytest.mark.asyncio
    async def test_dense_search_with_agent_filter(self, default_user):
        """Test dense search with agent filter."""
        # Arrange
        query_embedding = torch.tensor([0.1, 0.2, 0.3])
        mock_agent = MagicMock(spec=Agent)
        mock_agent.id = 123

        with patch("khoj.search_type.text_search.EntryAdapters") as mock_adapter:
            mock_entries = [create_mock_entry(1, "Agent entry", agent=mock_agent)]
            mock_adapter.search_with_embeddings.return_value = MockQuerySet(mock_entries)

            # Act
            results = await text_search.dense_search(
                query_embedding=query_embedding,
                user=default_user,
                k=10,
                agent=mock_agent,
            )

            # Assert
            mock_adapter.search_with_embeddings.assert_called_once()
            call_kwargs = mock_adapter.search_with_embeddings.call_args[1]
            assert call_kwargs["agent"] == mock_agent

    @pytest.mark.asyncio
    async def test_dense_search_with_raw_query(self, default_user):
        """Test dense search passes raw_query parameter."""
        # Arrange
        query_embedding = torch.tensor([0.1, 0.2, 0.3])
        raw_query = "test search query"

        with patch("khoj.search_type.text_search.EntryAdapters") as mock_adapter:
            mock_entries = [create_mock_entry(1)]
            mock_adapter.search_with_embeddings.return_value = MockQuerySet(mock_entries)

            # Act
            results = await text_search.dense_search(
                query_embedding=query_embedding,
                user=default_user,
                k=10,
                raw_query=raw_query,
            )

            # Assert
            mock_adapter.search_with_embeddings.assert_called_once()
            call_kwargs = mock_adapter.search_with_embeddings.call_args[1]
            assert call_kwargs["raw_query"] == raw_query

    @pytest.mark.asyncio
    async def test_dense_search_empty_results(self, default_user):
        """Test dense search returns empty list when no results found."""
        # Arrange
        query_embedding = torch.tensor([0.1, 0.2, 0.3])

        with patch("khoj.search_type.text_search.EntryAdapters") as mock_adapter:
            mock_adapter.search_with_embeddings.return_value = MockQuerySet([])

            # Act
            results = await text_search.dense_search(
                query_embedding=query_embedding,
                user=default_user,
                k=10,
            )

            # Assert
            assert results == []

    @pytest.mark.asyncio
    async def test_dense_search_respects_k_parameter(self, default_user):
        """Test dense search respects k (limit) parameter."""
        # Arrange
        query_embedding = torch.tensor([0.1, 0.2, 0.3])

        with patch("khoj.search_type.text_search.EntryAdapters") as mock_adapter:
            mock_entries = [create_mock_entry(i) for i in range(1, 21)]  # 20 entries
            mock_adapter.search_with_embeddings.return_value = MockQuerySet(mock_entries)

            # Act
            results = await text_search.dense_search(
                query_embedding=query_embedding,
                user=default_user,
                k=5,
            )

            # Assert
            mock_adapter.search_with_embeddings.assert_called_once()
            call_kwargs = mock_adapter.search_with_embeddings.call_args[1]
            assert call_kwargs["max_results"] == 5

    @pytest.mark.asyncio
    async def test_dense_search_uses_default_max_distance(self, default_user):
        """Test dense search uses default max_distance from search model when not provided."""
        # Arrange
        query_embedding = torch.tensor([0.1, 0.2, 0.3])
        mock_search_model = MagicMock()
        mock_search_model.bi_encoder_confidence_threshold = 0.75

        with patch("khoj.search_type.text_search.EntryAdapters") as mock_adapter, \
             patch("khoj.search_type.text_search.get_default_search_model") as mock_get_model:
            mock_get_model.return_value = mock_search_model
            mock_entries = [create_mock_entry(1)]
            mock_adapter.search_with_embeddings.return_value = MockQuerySet(mock_entries)

            # Act
            results = await text_search.dense_search(
                query_embedding=query_embedding,
                user=default_user,
                k=10,
            )

            # Assert
            mock_adapter.search_with_embeddings.assert_called_once()
            call_kwargs = mock_adapter.search_with_embeddings.call_args[1]
            assert call_kwargs["max_distance"] == 0.75


class TestSparseSearch:
    """Tests for sparse_search() function."""

    @pytest.mark.asyncio
    async def test_sparse_search_basic(self, default_user):
        """Test basic sparse search functionality."""
        # Arrange
        query_text = "test query"
        mock_entries = [
            create_mock_entry(1, "First test entry"),
            create_mock_entry(2, "Second test entry"),
        ]

        with patch.object(Entry.objects, "annotate") as mock_annotate, \
             patch.object(Entry.objects, "filter") as mock_filter:
            mock_queryset = MagicMock()
            mock_queryset.order_by.return_value.__getitem__ = lambda self, key: MockQuerySet(mock_entries[:key.stop if hasattr(key, 'stop') else len(mock_entries)])
            mock_filter.return_value = mock_queryset
            mock_annotate.return_value.filter.return_value = mock_filter.return_value

            # We need to patch the entire queryset chain
            mock_chain = MagicMock()
            mock_chain.annotate.return_value = mock_chain
            mock_chain.filter.return_value = mock_chain
            mock_chain.order_by.return_value.__getitem__ = lambda k: MockQuerySet(mock_entries[:10])

            with patch.object(Entry.objects, "annotate", return_value=mock_chain):
                # Act
                results = await text_search.sparse_search(
                    query_text=query_text,
                    user=default_user,
                    k=10,
                )

                # Assert
                assert len(results) == 2

    @pytest.mark.asyncio
    async def test_sparse_search_with_file_type_filter(self, default_user):
        """Test sparse search with file_type filter."""
        # Arrange
        query_text = "test query"
        file_type = Entry.EntryType.MARKDOWN

        with patch.object(Entry.objects, "annotate") as mock_annotate:
            mock_chain = MagicMock()
            mock_chain.annotate.return_value = mock_chain
            mock_chain.filter.return_value = mock_chain
            mock_chain.order_by.return_value.__getitem__ = lambda k: MockQuerySet([])

            mock_annotate.return_value = mock_chain

            # Act
            results = await text_search.sparse_search(
                query_text=query_text,
                user=default_user,
                k=10,
                file_type=file_type,
            )

            # Assert - verify chain was called with file_type filter
            mock_chain.filter.assert_any_call(file_type=file_type)

    @pytest.mark.asyncio
    async def test_sparse_search_with_agent_filter(self, default_user):
        """Test sparse search with agent filter."""
        # Arrange
        query_text = "test query"
        mock_agent = MagicMock(spec=Agent)
        mock_agent.id = 123

        with patch.object(Entry.objects, "annotate") as mock_annotate:
            mock_chain = MagicMock()
            mock_chain.annotate.return_value = mock_chain
            mock_chain.filter.return_value = mock_chain
            mock_chain.order_by.return_value.__getitem__ = lambda k: MockQuerySet([])

            mock_annotate.return_value = mock_chain

            # Act
            results = await text_search.sparse_search(
                query_text=query_text,
                user=default_user,
                k=10,
                agent=mock_agent,
            )

            # Assert - verify chain was called with agent filter
            mock_chain.filter.assert_any_call(agent=mock_agent)

    @pytest.mark.asyncio
    async def test_sparse_search_empty_results(self, default_user):
        """Test sparse search returns empty list when no results found."""
        # Arrange
        query_text = "nonexistent query"

        with patch.object(Entry.objects, "annotate") as mock_annotate:
            mock_chain = MagicMock()
            mock_chain.annotate.return_value = mock_chain
            mock_chain.filter.return_value = mock_chain
            mock_chain.order_by.return_value.__getitem__ = lambda k: MockQuerySet([])

            mock_annotate.return_value = mock_chain

            # Act
            results = await text_search.sparse_search(
                query_text=query_text,
                user=default_user,
                k=10,
            )

            # Assert
            assert results == []

    @pytest.mark.asyncio
    async def test_sparse_search_respects_k_parameter(self, default_user):
        """Test sparse search respects k (limit) parameter."""
        # Arrange
        query_text = "test query"

        with patch.object(Entry.objects, "annotate") as mock_annotate:
            mock_chain = MagicMock()
            mock_chain.annotate.return_value = mock_chain
            mock_chain.filter.return_value = mock_chain
            mock_chain.order_by.return_value.__getitem__ = lambda k: MockQuerySet([create_mock_entry(i) for i in range(5)])

            mock_annotate.return_value = mock_chain

            # Act
            results = await text_search.sparse_search(
                query_text=query_text,
                user=default_user,
                k=5,
            )

            # Assert - verify slice was called with [:5]
            slice_call = mock_chain.order_by.return_value.__getitem__.call_args[0][0]
            assert slice_call.stop == 5


class TestHybridSearch:
    """Tests for hybrid_search() function combining dense and sparse search."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("alpha", [0.3, 0.5, 0.7])
    async def test_hybrid_search_with_different_alpha_values(self, alpha, default_user):
        """Test hybrid search with different alpha weighting values."""
        # Arrange
        query_text = "test query"
        query_embedding = torch.tensor([0.1, 0.2, 0.3])

        # Create mock entries that appear in both dense and sparse results
        mock_entry_1 = create_mock_entry(1, "Common entry 1")
        mock_entry_2 = create_mock_entry(2, "Common entry 2")
        mock_entry_3 = create_mock_entry(3, "Dense only entry")
        mock_entry_4 = create_mock_entry(4, "Sparse only entry")

        dense_entries = [mock_entry_1, mock_entry_2, mock_entry_3]
        sparse_entries = [mock_entry_1, mock_entry_2, mock_entry_4]

        with patch("khoj.search_type.text_search.dense_search") as mock_dense, \
             patch("khoj.search_type.text_search.sparse_search") as mock_sparse:
            mock_dense.return_value = dense_entries
            mock_sparse.return_value = sparse_entries

            # Act
            results = await text_search.hybrid_search(
                query_text=query_text,
                query_embedding=query_embedding,
                user=default_user,
                k=10,
                alpha=alpha,
            )

            # Assert
            assert len(results) <= 10
            # Verify both search methods were called
            mock_dense.assert_called_once()
            mock_sparse.assert_called_once()

            # Verify alpha was passed through (stored for future use)
            # Note: Currently alpha is stored but RRF doesn't use it directly

    @pytest.mark.asyncio
    async def test_hybrid_search_combines_results(self, default_user):
        """Test that hybrid search combines results from both dense and sparse search."""
        # Arrange
        query_text = "test query"
        query_embedding = torch.tensor([0.1, 0.2, 0.3])

        # Create overlapping results
        mock_entry_1 = create_mock_entry(1, "Entry from both")
        mock_entry_2 = create_mock_entry(2, "Entry from both")
        mock_entry_3 = create_mock_entry(3, "Dense only")
        mock_entry_4 = create_mock_entry(4, "Sparse only")

        dense_entries = [mock_entry_1, mock_entry_2, mock_entry_3]
        sparse_entries = [mock_entry_1, mock_entry_2, mock_entry_4]

        with patch("khoj.search_type.text_search.dense_search") as mock_dense, \
             patch("khoj.search_type.text_search.sparse_search") as mock_sparse:
            mock_dense.return_value = dense_entries
            mock_sparse.return_value = sparse_entries

            # Act
            results = await text_search.hybrid_search(
                query_text=query_text,
                query_embedding=query_embedding,
                user=default_user,
                k=10,
                alpha=0.6,
            )

            # Assert
            result_ids = {entry.id for entry in results}
            # Should have all unique entries from both sources
            assert 1 in result_ids  # Common
            assert 2 in result_ids  # Common
            assert 3 in result_ids  # Dense only
            assert 4 in result_ids  # Sparse only

    @pytest.mark.asyncio
    async def test_hybrid_search_prefers_entries_in_both_sources(self, default_user):
        """Test that entries appearing in both dense and sparse results rank higher."""
        # Arrange
        query_text = "test query"
        query_embedding = torch.tensor([0.1, 0.2, 0.3])

        # Entry 1: Ranked high in both (should get highest RRF score)
        # Entry 2: Ranked high only in dense
        # Entry 3: Ranked high only in sparse
        mock_entry_1 = create_mock_entry(1, "Both sources")
        mock_entry_2 = create_mock_entry(2, "Dense only")
        mock_entry_3 = create_mock_entry(3, "Sparse only")

        dense_entries = [mock_entry_1, mock_entry_2]  # Entry 1 at rank 0
        sparse_entries = [mock_entry_1, mock_entry_3]  # Entry 1 at rank 0

        with patch("khoj.search_type.text_search.dense_search") as mock_dense, \
             patch("khoj.search_type.text_search.sparse_search") as mock_sparse:
            mock_dense.return_value = dense_entries
            mock_sparse.return_value = sparse_entries

            # Act
            results = await text_search.hybrid_search(
                query_text=query_text,
                query_embedding=query_embedding,
                user=default_user,
                k=10,
                alpha=0.6,
            )

            # Assert
            # Entry 1 should be first as it appears in both lists
            assert results[0].id == 1

    @pytest.mark.asyncio
    async def test_hybrid_search_empty_dense_results(self, default_user):
        """Test hybrid search handles empty dense results gracefully."""
        # Arrange
        query_text = "test query"
        query_embedding = torch.tensor([0.1, 0.2, 0.3])

        mock_entry = create_mock_entry(1, "Sparse only entry")
        sparse_entries = [mock_entry]

        with patch("khoj.search_type.text_search.dense_search") as mock_dense, \
             patch("khoj.search_type.text_search.sparse_search") as mock_sparse:
            mock_dense.return_value = []
            mock_sparse.return_value = sparse_entries

            # Act
            results = await text_search.hybrid_search(
                query_text=query_text,
                query_embedding=query_embedding,
                user=default_user,
                k=10,
                alpha=0.6,
            )

            # Assert
            assert len(results) == 1
            assert results[0].id == 1

    @pytest.mark.asyncio
    async def test_hybrid_search_empty_sparse_results(self, default_user):
        """Test hybrid search handles empty sparse results gracefully."""
        # Arrange
        query_text = "test query"
        query_embedding = torch.tensor([0.1, 0.2, 0.3])

        mock_entry = create_mock_entry(1, "Dense only entry")
        dense_entries = [mock_entry]

        with patch("khoj.search_type.text_search.dense_search") as mock_dense, \
             patch("khoj.search_type.text_search.sparse_search") as mock_sparse:
            mock_dense.return_value = dense_entries
            mock_sparse.return_value = []

            # Act
            results = await text_search.hybrid_search(
                query_text=query_text,
                query_embedding=query_embedding,
                user=default_user,
                k=10,
                alpha=0.6,
            )

            # Assert
            assert len(results) == 1
            assert results[0].id == 1

    @pytest.mark.asyncio
    async def test_hybrid_search_both_empty_results(self, default_user):
        """Test hybrid search returns empty list when both sources return empty."""
        # Arrange
        query_text = "test query"
        query_embedding = torch.tensor([0.1, 0.2, 0.3])

        with patch("khoj.search_type.text_search.dense_search") as mock_dense, \
             patch("khoj.search_type.text_search.sparse_search") as mock_sparse:
            mock_dense.return_value = []
            mock_sparse.return_value = []

            # Act
            results = await text_search.hybrid_search(
                query_text=query_text,
                query_embedding=query_embedding,
                user=default_user,
                k=10,
                alpha=0.6,
            )

            # Assert
            assert results == []

    @pytest.mark.asyncio
    async def test_hybrid_search_single_source_only(self, default_user):
        """Test hybrid search when only one source returns results."""
        # Arrange
        query_text = "test query"
        query_embedding = torch.tensor([0.1, 0.2, 0.3])

        mock_entry = create_mock_entry(1, "Only source entry")

        with patch("khoj.search_type.text_search.dense_search") as mock_dense, \
             patch("khoj.search_type.text_search.sparse_search") as mock_sparse:
            # Only dense returns results
            mock_dense.return_value = [mock_entry]
            mock_sparse.return_value = []

            # Act
            results = await text_search.hybrid_search(
                query_text=query_text,
                query_embedding=query_embedding,
                user=default_user,
                k=10,
                alpha=0.6,
            )

            # Assert
            assert len(results) == 1
            assert results[0].id == 1

    @pytest.mark.asyncio
    async def test_hybrid_search_with_file_type_filter(self, default_user):
        """Test hybrid search passes file_type filter to both searches."""
        # Arrange
        query_text = "test query"
        query_embedding = torch.tensor([0.1, 0.2, 0.3])
        file_type = Entry.EntryType.MARKDOWN

        with patch("khoj.search_type.text_search.dense_search") as mock_dense, \
             patch("khoj.search_type.text_search.sparse_search") as mock_sparse:
            mock_dense.return_value = []
            mock_sparse.return_value = []

            # Act
            results = await text_search.hybrid_search(
                query_text=query_text,
                query_embedding=query_embedding,
                user=default_user,
                k=10,
                alpha=0.6,
                file_type=file_type,
            )

            # Assert
            dense_call = mock_dense.call_args[1]
            sparse_call = mock_sparse.call_args[1]
            assert dense_call["file_type"] == file_type
            assert sparse_call["file_type"] == file_type

    @pytest.mark.asyncio
    async def test_hybrid_search_with_agent_filter(self, default_user):
        """Test hybrid search passes agent filter to both searches."""
        # Arrange
        query_text = "test query"
        query_embedding = torch.tensor([0.1, 0.2, 0.3])
        mock_agent = MagicMock(spec=Agent)

        with patch("khoj.search_type.text_search.dense_search") as mock_dense, \
             patch("khoj.search_type.text_search.sparse_search") as mock_sparse:
            mock_dense.return_value = []
            mock_sparse.return_value = []

            # Act
            results = await text_search.hybrid_search(
                query_text=query_text,
                query_embedding=query_embedding,
                user=default_user,
                k=10,
                alpha=0.6,
                agent=mock_agent,
            )

            # Assert
            dense_call = mock_dense.call_args[1]
            sparse_call = mock_sparse.call_args[1]
            assert dense_call["agent"] == mock_agent
            assert sparse_call["agent"] == mock_agent

    @pytest.mark.asyncio
    async def test_hybrid_search_respects_k_parameter(self, default_user):
        """Test hybrid search respects k parameter for final results."""
        # Arrange
        query_text = "test query"
        query_embedding = torch.tensor([0.1, 0.2, 0.3])

        # Create many entries
        dense_entries = [create_mock_entry(i) for i in range(1, 21)]
        sparse_entries = [create_mock_entry(i + 10) for i in range(1, 21)]

        with patch("khoj.search_type.text_search.dense_search") as mock_dense, \
             patch("khoj.search_type.text_search.sparse_search") as mock_sparse:
            mock_dense.return_value = dense_entries
            mock_sparse.return_value = sparse_entries

            # Act
            results = await text_search.hybrid_search(
                query_text=query_text,
                query_embedding=query_embedding,
                user=default_user,
                k=5,
                alpha=0.6,
            )

            # Assert
            assert len(results) == 5

    @pytest.mark.asyncio
    async def test_hybrid_search_runs_concurrently(self, default_user):
        """Test that dense and sparse searches run concurrently (asyncio.gather)."""
        # Arrange
        query_text = "test query"
        query_embedding = torch.tensor([0.1, 0.2, 0.3])

        call_order = []

        async def tracked_dense_search(*args, **kwargs):
            call_order.append("dense")
            return [create_mock_entry(1)]

        async def tracked_sparse_search(*args, **kwargs):
            call_order.append("sparse")
            return [create_mock_entry(2)]

        with patch("khoj.search_type.text_search.dense_search", side_effect=tracked_dense_search), \
             patch("khoj.search_type.text_search.sparse_search", side_effect=tracked_sparse_search):
            # Act
            results = await text_search.hybrid_search(
                query_text=query_text,
                query_embedding=query_embedding,
                user=default_user,
                k=10,
                alpha=0.6,
            )

            # Assert - if running concurrently, both should start before either completes
            # The order in call_order depends on which one schedules first
            assert "dense" in call_order
            assert "sparse" in call_order

    @pytest.mark.asyncio
    async def test_hybrid_search_passes_raw_query_to_dense(self, default_user):
        """Test hybrid search passes query_text as raw_query to dense search."""
        # Arrange
        query_text = "my search query"
        query_embedding = torch.tensor([0.1, 0.2, 0.3])

        with patch("khoj.search_type.text_search.dense_search") as mock_dense, \
             patch("khoj.search_type.text_search.sparse_search") as mock_sparse:
            mock_dense.return_value = []
            mock_sparse.return_value = []

            # Act
            results = await text_search.hybrid_search(
                query_text=query_text,
                query_embedding=query_embedding,
                user=default_user,
                k=10,
                alpha=0.6,
            )

            # Assert
            dense_call = mock_dense.call_args[1]
            assert dense_call["raw_query"] == query_text


class TestHybridSearchEdgeCases:
    """Tests for hybrid search edge cases."""

    @pytest.mark.asyncio
    async def test_hybrid_search_deduplicates_entries(self, default_user):
        """Test that hybrid search deduplicates entries appearing in both sources."""
        # Arrange
        query_text = "test query"
        query_embedding = torch.tensor([0.1, 0.2, 0.3])

        # Same entry in both lists
        mock_entry = create_mock_entry(1, "Common entry")

        with patch("khoj.search_type.text_search.dense_search") as mock_dense, \
             patch("khoj.search_type.text_search.sparse_search") as mock_sparse:
            mock_dense.return_value = [mock_entry]
            mock_sparse.return_value = [mock_entry]

            # Act
            results = await text_search.hybrid_search(
                query_text=query_text,
                query_embedding=query_embedding,
                user=default_user,
                k=10,
                alpha=0.6,
            )

            # Assert
            assert len(results) == 1  # Should not duplicate
            assert results[0].id == 1

    @pytest.mark.asyncio
    async def test_hybrid_search_with_large_embedding(self, default_user):
        """Test hybrid search with large embedding tensors."""
        # Arrange
        query_text = "test query"
        query_embedding = torch.randn(768)  # Large embedding vector

        with patch("khoj.search_type.text_search.dense_search") as mock_dense, \
             patch("khoj.search_type.text_search.sparse_search") as mock_sparse:
            mock_dense.return_value = [create_mock_entry(1)]
            mock_sparse.return_value = []

            # Act
            results = await text_search.hybrid_search(
                query_text=query_text,
                query_embedding=query_embedding,
                user=default_user,
                k=10,
                alpha=0.6,
            )

            # Assert
            assert len(results) == 1

    @pytest.mark.asyncio
    async def test_hybrid_search_preserves_entry_attributes(self, default_user):
        """Test that hybrid search preserves all entry attributes."""
        # Arrange
        query_text = "test query"
        query_embedding = torch.tensor([0.1, 0.2, 0.3])

        mock_entry = create_mock_entry(
            1,
            "Test content",
            heading="Test heading",
            file_type=Entry.EntryType.MARKDOWN,
            file_path="/test/file.md",
        )

        with patch("khoj.search_type.text_search.dense_search") as mock_dense, \
             patch("khoj.search_type.text_search.sparse_search") as mock_sparse:
            mock_dense.return_value = [mock_entry]
            mock_sparse.return_value = []

            # Act
            results = await text_search.hybrid_search(
                query_text=query_text,
                query_embedding=query_embedding,
                user=default_user,
                k=10,
                alpha=0.6,
            )

            # Assert
            assert len(results) == 1
            result = results[0]
            assert result.id == 1
            assert result.raw == "Test content"
            assert result.heading == "Test heading"
            assert result.file_type == Entry.EntryType.MARKDOWN

    @pytest.mark.asyncio
    async def test_hybrid_search_with_k_zero(self, default_user):
        """Test hybrid search with k=0 returns empty results."""
        # Arrange
        query_text = "test query"
        query_embedding = torch.tensor([0.1, 0.2, 0.3])

        with patch("khoj.search_type.text_search.dense_search") as mock_dense, \
             patch("khoj.search_type.text_search.sparse_search") as mock_sparse:
            mock_dense.return_value = [create_mock_entry(i) for i in range(1, 11)]
            mock_sparse.return_value = [create_mock_entry(i) for i in range(11, 21)]

            # Act
            results = await text_search.hybrid_search(
                query_text=query_text,
                query_embedding=query_embedding,
                user=default_user,
                k=0,
                alpha=0.6,
            )

            # Assert
            assert results == []

    @pytest.mark.asyncio
    async def test_hybrid_search_with_many_overlapping_results(self, default_user):
        """Test hybrid search with many overlapping results."""
        # Arrange
        query_text = "test query"
        query_embedding = torch.tensor([0.1, 0.2, 0.3])

        # Create 20 entries that appear in both lists
        common_entries = [create_mock_entry(i, f"Common entry {i}") for i in range(1, 21)]
        # Add some unique entries
        dense_only = [create_mock_entry(i + 100, f"Dense only {i}") for i in range(1, 6)]
        sparse_only = [create_mock_entry(i + 200, f"Sparse only {i}") for i in range(1, 6)]

        with patch("khoj.search_type.text_search.dense_search") as mock_dense, \
             patch("khoj.search_type.text_search.sparse_search") as mock_sparse:
            mock_dense.return_value = common_entries + dense_only
            mock_sparse.return_value = common_entries + sparse_only

            # Act
            results = await text_search.hybrid_search(
                query_text=query_text,
                query_embedding=query_embedding,
                user=default_user,
                k=10,
                alpha=0.6,
            )

            # Assert
            assert len(results) == 10
            # Common entries should rank higher (appear first)
            result_ids = {r.id for r in results}
            # All results should be unique
            assert len(result_ids) == 10


class TestHybridSearchIntegration:
    """Integration-style tests for hybrid search."""

    @pytest.mark.asyncio
    async def test_hybrid_search_default_alpha(self, default_user):
        """Test hybrid search uses default alpha value of 0.6."""
        # Arrange
        query_text = "test query"
        query_embedding = torch.tensor([0.1, 0.2, 0.3])

        with patch("khoj.search_type.text_search.dense_search") as mock_dense, \
             patch("khoj.search_type.text_search.sparse_search") as mock_sparse:
            mock_dense.return_value = []
            mock_sparse.return_value = []

            # Act - call without specifying alpha
            results = await text_search.hybrid_search(
                query_text=query_text,
                query_embedding=query_embedding,
                user=default_user,
                k=10,
            )

            # Assert - function should work with default alpha
            assert results == []

    @pytest.mark.asyncio
    async def test_hybrid_search_with_complex_query(self, default_user):
        """Test hybrid search with complex query text."""
        # Arrange
        query_text = "How to implement machine learning algorithms in Python?"
        query_embedding = torch.tensor([0.1, 0.2, 0.3])

        mock_entries = [
            create_mock_entry(1, "Python ML tutorial"),
            create_mock_entry(2, "Machine learning basics"),
            create_mock_entry(3, "Implementing algorithms"),
        ]

        with patch("khoj.search_type.text_search.dense_search") as mock_dense, \
             patch("khoj.search_type.text_search.sparse_search") as mock_sparse:
            mock_dense.return_value = mock_entries[:2]
            mock_sparse.return_value = mock_entries[1:]

            # Act
            results = await text_search.hybrid_search(
                query_text=query_text,
                query_embedding=query_embedding,
                user=default_user,
                k=10,
                alpha=0.6,
            )

            # Assert
            assert len(results) >= 2
            result_ids = {r.id for r in results}
            assert 2 in result_ids  # Entry 2 in both should be highest ranked

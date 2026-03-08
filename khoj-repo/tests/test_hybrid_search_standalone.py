"""
Comprehensive tests for hybrid search functionality.

Tests for dense_search(), sparse_search(), and hybrid_search() functions
with mocked database queries and embeddings.
"""

import sys
import os
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
import torch


# Mock Django models before importing them
class MockEntryType:
    PLAINTEXT = "plaintext"
    MARKDOWN = "markdown"
    ORG = "org"
    PDF = "pdf"

class MockEntrySource:
    COMPUTER = "computer"

class MockEntry:
    EntryType = MockEntryType
    EntrySource = MockEntrySource
    
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class MockAgent:
    pass

class MockKhojUser:
    pass

# Mock the entire database module
mock_models = MagicMock()
mock_models.Entry = MockEntry
mock_models.Agent = MockAgent
mock_models.KhojUser = MockKhojUser

sys.modules['khoj'] = MagicMock()
sys.modules['khoj.database'] = MagicMock()
sys.modules['khoj.database.models'] = mock_models

# Mock other dependencies
sys.modules['khoj.database.adapters'] = MagicMock()
sys.modules['khoj.search_filter'] = MagicMock()
sys.modules['khoj.search_filter.date_filter'] = MagicMock()
sys.modules['khoj.utils'] = MagicMock()
sys.modules['khoj.utils.state'] = MagicMock()
sys.modules['khoj.utils.helpers'] = MagicMock()

# Now import the module under test
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
    entry = MagicMock(spec=MockEntry)
    entry.id = entry_id
    entry.raw = content or f"Test content {entry_id}"
    entry.compiled = content or f"Test compiled {entry_id}"
    entry.heading = kwargs.get("heading", f"Test heading {entry_id}")
    entry.file_type = kwargs.get("file_type", MockEntry.EntryType.PLAINTEXT)
    entry.file_source = kwargs.get("file_source", MockEntry.EntrySource.COMPUTER)
    entry.file_path = kwargs.get("file_path", f"/test/path/{entry_id}.txt")
    entry.hashed_value = kwargs.get("hashed_value", f"hash_{entry_id}")
    entry.corpus_id = kwargs.get("corpus_id", f"corpus_{entry_id}")
    entry.url = kwargs.get("url", None)
    entry.agent = kwargs.get("agent", None)
    entry.user = kwargs.get("user", None)
    entry.distance = kwargs.get("distance", 0.5)
    return entry


@pytest.fixture
def default_user():
    """Return a mock user for testing."""
    user = MagicMock()
    user.id = 1
    user.username = "test_user"
    user.email = "test@example.com"
    return user


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
        file_type = MockEntry.EntryType.MARKDOWN

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
        mock_agent = MagicMock(spec=MockAgent)
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

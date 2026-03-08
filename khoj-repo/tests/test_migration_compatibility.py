"""
Migration Compatibility Tests

This module tests compatibility after database migrations for:
1. Entry.objects.filter(user=user) - Basic ORM operations work after migrations
2. search_with_embeddings() - Vector search still works
3. FTS search - Full-text search works with search_vector field
4. Agent isolation - User data remains isolated after migrations

Test coverage for migrations:
- 0100_add_search_vector.py - Adds search_vector field and GIN index
- 0101_add_context_summary.py - Adds context_summary field
- 0102_add_chunk_scale.py - Adds chunk_scale field
"""

import math
from unittest.mock import patch

import pytest
import torch
from asgiref.sync import sync_to_async
from django.contrib.postgres.search import SearchQuery, SearchVector
from django.db.models import Q

from khoj.database.adapters import EntryAdapters
from khoj.database.models import Agent, Entry, KhojUser, SearchModelConfig
from tests.helpers import ChatModelFactory, SearchModelFactory, UserFactory


@pytest.fixture
def test_users(db):
    """Create test users for multi-user tests."""
    user1 = UserFactory(username="test_user_1", email="user1@test.com")
    user2 = UserFactory(username="test_user_2", email="user2@test.com")
    user3 = UserFactory(username="test_user_3", email="user3@test.com")
    return user1, user2, user3


@pytest.fixture
def search_model(db):
    """Create a search model configuration."""
    return SearchModelFactory()


@pytest.fixture
def test_agent(db):
    """Create a test agent."""
    chat_model = ChatModelFactory()
    return Agent.objects.create(
        name="Test Agent",
        chat_model=chat_model,
        personality="Test personality",
    )


@pytest.fixture
def sample_embeddings():
    """Generate sample embeddings for testing."""
    # Create a 384-dimensional embedding vector (common size for sentence-transformers)
    return torch.randn(384).tolist()


@pytest.fixture
def sample_embeddings_list():
    """Generate multiple sample embeddings for testing."""
    return [torch.randn(384).tolist() for _ in range(5)]


class TestEntryOrmOperationsAfterMigrations:
    """Test basic ORM operations on Entry model after migrations."""

    @pytest.mark.django_db
    def test_create_entry_with_all_new_fields(self, test_users, search_model, sample_embeddings):
        """Create Entry with all new fields and verify data integrity."""
        user = test_users[0]

        entry = Entry.objects.create(
            user=user,
            embeddings=sample_embeddings,
            raw="Test raw content",
            compiled="Test compiled content",
            heading="Test Heading",
            file_type=Entry.EntryType.PLAINTEXT,
            file_path="/test/path/file.txt",
            file_name="file.txt",
            hashed_value="test_hash_123",
            search_model=search_model,
            # New fields from migrations 0100-0102
            search_vector=SearchVector("compiled"),
            context_summary="Test context summary",
            chunk_scale="1024",
        )

        # Verify entry was created
        assert entry.id is not None
        assert entry.user == user
        assert entry.compiled == "Test compiled content"

        # Verify new fields are set
        assert entry.context_summary == "Test context summary"
        assert entry.chunk_scale == "1024"

    @pytest.mark.django_db
    def test_filter_by_user(self, test_users, search_model, sample_embeddings_list):
        """Filter entries by user and verify data integrity."""
        user1, user2, _ = test_users

        # Create entries for user1
        for i, emb in enumerate(sample_embeddings_list[:3]):
            Entry.objects.create(
                user=user1,
                embeddings=emb,
                raw=f"User1 content {i}",
                compiled=f"User1 compiled {i}",
                hashed_value=f"hash_user1_{i}",
                search_model=search_model,
                chunk_scale="512",
            )

        # Create entries for user2
        for i, emb in enumerate(sample_embeddings_list[3:]):
            Entry.objects.create(
                user=user2,
                embeddings=emb,
                raw=f"User2 content {i}",
                compiled=f"User2 compiled {i}",
                hashed_value=f"hash_user2_{i}",
                search_model=search_model,
                chunk_scale="1024",
            )

        # Filter by user1
        user1_entries = Entry.objects.filter(user=user1)
        assert user1_entries.count() == 3

        # Filter by user2
        user2_entries = Entry.objects.filter(user=user2)
        assert user2_entries.count() == 2

        # Verify content integrity
        for entry in user1_entries:
            assert entry.user == user1
            assert "User1" in entry.raw

        for entry in user2_entries:
            assert entry.user == user2
            assert "User2" in entry.raw

    @pytest.mark.django_db
    def test_entry_queryset_chaining(self, test_users, search_model, sample_embeddings_list):
        """Test that ORM queryset chaining works correctly after migrations."""
        user = test_users[0]

        # Create entries with different file types
        file_types = [
            Entry.EntryType.PLAINTEXT,
            Entry.EntryType.MARKDOWN,
            Entry.EntryType.ORG,
        ]

        for i, (emb, file_type) in enumerate(zip(sample_embeddings_list[:3], file_types)):
            Entry.objects.create(
                user=user,
                embeddings=emb,
                raw=f"Content {i}",
                compiled=f"Compiled {i}",
                file_type=file_type,
                hashed_value=f"hash_{i}",
                search_model=search_model,
                chunk_scale=str(512 * (i + 1)),
            )

        # Test queryset chaining with new fields
        results = (
            Entry.objects.filter(user=user)
            .exclude(file_type=Entry.EntryType.IMAGE)
            .filter(chunk_scale__in=["512", "1024"])
            .order_by("-created_at")
        )

        assert results.count() == 2


class TestSearchWithEmbeddingsAfterMigrations:
    """Test vector similarity search after migrations."""

    @pytest.mark.django_db
    def test_search_with_embeddings_basic(self, test_users, search_model, sample_embeddings_list):
        """Perform vector similarity search and verify search works."""
        user = test_users[0]

        # Create entries with different embeddings
        for i, emb in enumerate(sample_embeddings_list):
            Entry.objects.create(
                user=user,
                embeddings=emb,
                raw=f"Test content about topic {i}",
                compiled=f"Compiled content about topic {i}",
                hashed_value=f"hash_{i}",
                search_model=search_model,
                chunk_scale="1024",
            )

        # Create a query embedding
        query_embedding = torch.randn(384)

        # Perform search
        results = EntryAdapters.search_with_embeddings(
            raw_query="topic",
            embeddings=query_embedding,
            user=user,
            max_results=3,
        )

        # Verify search returns results
        assert results is not None
        # Note: Actual similarity values depend on random embeddings
        assert len(list(results)) <= 3

    @pytest.mark.django_db
    def test_search_with_embeddings_with_agent(self, test_users, test_agent, search_model, sample_embeddings_list):
        """Test vector search with agent filter."""
        user = test_users[0]

        # Create entries for user
        for i, emb in enumerate(sample_embeddings_list[:2]):
            Entry.objects.create(
                user=user,
                embeddings=emb,
                raw=f"User content {i}",
                compiled=f"User compiled {i}",
                hashed_value=f"user_hash_{i}",
                search_model=search_model,
            )

        # Create entries for agent
        for i, emb in enumerate(sample_embeddings_list[2:]):
            Entry.objects.create(
                agent=test_agent,
                embeddings=emb,
                raw=f"Agent content {i}",
                compiled=f"Agent compiled {i}",
                hashed_value=f"agent_hash_{i}",
                search_model=search_model,
            )

        # Search with user and agent
        query_embedding = torch.randn(384)
        results = EntryAdapters.search_with_embeddings(
            raw_query="content",
            embeddings=query_embedding,
            user=user,
            agent=test_agent,
            max_results=10,
        )

        # Should find both user and agent entries
        assert results is not None

    @pytest.mark.django_db
    def test_search_with_file_type_filter(self, test_users, search_model, sample_embeddings_list):
        """Test vector search with file type filter after migrations."""
        user = test_users[0]

        # Create entries with different file types
        for i, emb in enumerate(sample_embeddings_list):
            file_type = Entry.EntryType.PLAINTEXT if i % 2 == 0 else Entry.EntryType.MARKDOWN
            Entry.objects.create(
                user=user,
                embeddings=emb,
                raw=f"Content {i}",
                compiled=f"Compiled {i}",
                file_type=file_type,
                hashed_value=f"hash_{i}",
                search_model=search_model,
                chunk_scale="512" if i % 2 == 0 else "1024",
            )

        # Search with file type filter
        query_embedding = torch.randn(384)
        results = EntryAdapters.search_with_embeddings(
            raw_query="content",
            embeddings=query_embedding,
            user=user,
            file_type_filter=Entry.EntryType.PLAINTEXT,
            max_results=10,
        )

        # Verify only plaintext results
        for result in results:
            assert result.file_type == Entry.EntryType.PLAINTEXT


class TestFtsSearchAfterMigrations:
    """Test full-text search with search_vector field after migrations."""

    @pytest.mark.django_db
    def test_search_vector_field_operations(self, test_users, search_model, sample_embeddings):
        """Test search_vector field operations and GIN index usage."""
        user = test_users[0]

        # Create entry with search_vector
        entry = Entry.objects.create(
            user=user,
            embeddings=sample_embeddings,
            raw="PostgreSQL full-text search testing",
            compiled="Testing PostgreSQL full-text search capabilities",
            hashed_value="hash_fts_1",
            search_model=search_model,
        )

        # Update search_vector
        Entry.objects.filter(id=entry.id).update(
            search_vector=SearchVector("compiled", "raw")
        )

        # Retrieve and verify
        entry.refresh_from_db()
        assert entry.search_vector is not None

    @pytest.mark.django_db
    def test_fts_query_with_search_vector(self, test_users, search_model, sample_embeddings_list):
        """Perform FTS query and verify results."""
        user = test_users[0]

        # Create entries with different content
        contents = [
            "Python programming tutorial",
            "Django web framework guide",
            "PostgreSQL database administration",
            "Machine learning with Python",
        ]

        for i, (emb, content) in enumerate(zip(sample_embeddings_list, contents)):
            entry = Entry.objects.create(
                user=user,
                embeddings=emb,
                raw=content,
                compiled=f"Compiled: {content}",
                hashed_value=f"hash_fts_{i}",
                search_model=search_model,
            )
            # Set search_vector
            Entry.objects.filter(id=entry.id).update(
                search_vector=SearchVector("raw", "compiled")
            )

        # Search using search_vector
        results = Entry.objects.filter(
            user=user,
            search_vector=SearchQuery("Python"),
        )

        # Should find entries containing "Python"
        found_titles = [r.raw for r in results]
        assert any("Python" in title for title in found_titles)

    @pytest.mark.django_db
    def test_gin_index_exists(self, test_users, search_model, sample_embeddings):
        """Verify GIN index on search_vector field is being used."""
        from django.db import connection

        user = test_users[0]

        # Create an entry
        entry = Entry.objects.create(
            user=user,
            embeddings=sample_embeddings,
            raw="Test content for GIN index",
            compiled="Compiled test content",
            hashed_value="hash_gin",
            search_model=search_model,
        )

        # Update search_vector
        Entry.objects.filter(id=entry.id).update(
            search_vector=SearchVector("raw")
        )

        # Check if GIN index exists by querying pg_indexes
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'database_entry'
                AND indexname LIKE '%search_vector%gin%'
            """)
            result = cursor.fetchone()

        # The GIN index should exist (added in migration 0100)
        assert result is not None, "GIN index on search_vector not found"


class TestUserIsolationAfterMigrations:
    """Test that user data remains isolated after migrations."""

    @pytest.mark.django_db
    def test_user_entry_isolation(self, test_users, search_model, sample_embeddings_list):
        """Verify users can only access their own entries."""
        user1, user2, user3 = test_users

        # Create entries for each user with new fields
        for i, emb in enumerate(sample_embeddings_list):
            Entry.objects.create(
                user=user1,
                embeddings=emb,
                raw=f"User1 private content {i}",
                compiled=f"User1 compiled {i}",
                hashed_value=f"hash_u1_{i}",
                search_model=search_model,
                context_summary=f"User1 summary {i}",
                chunk_scale="512",
            )

        for i, emb in enumerate(sample_embeddings_list):
            Entry.objects.create(
                user=user2,
                embeddings=emb,
                raw=f"User2 private content {i}",
                compiled=f"User2 compiled {i}",
                hashed_value=f"hash_u2_{i}",
                search_model=search_model,
                context_summary=f"User2 summary {i}",
                chunk_scale="1024",
            )

        # Verify user1 can only see their own entries
        user1_entries = Entry.objects.filter(user=user1)
        assert user1_entries.count() == 5
        for entry in user1_entries:
            assert entry.user == user1
            assert "User1" in entry.raw

        # Verify user2 can only see their own entries
        user2_entries = Entry.objects.filter(user=user2)
        assert user2_entries.count() == 5
        for entry in user2_entries:
            assert entry.user == user2
            assert "User2" in entry.raw

        # Verify user3 has no entries
        user3_entries = Entry.objects.filter(user=user3)
        assert user3_entries.count() == 0

    @pytest.mark.django_db
    def test_cross_user_search_isolation(self, test_users, search_model, sample_embeddings_list):
        """Test that search respects user boundaries with new fields."""
        user1, user2, _ = test_users

        # Create entries for both users
        for i, emb in enumerate(sample_embeddings_list[:2]):
            Entry.objects.create(
                user=user1,
                embeddings=emb,
                raw=f"Shared keyword content for user1",
                compiled=f"User1 compiled",
                hashed_value=f"hash_iso1_{i}",
                search_model=search_model,
                chunk_scale="512",
            )

        for i, emb in enumerate(sample_embeddings_list[2:4]):
            Entry.objects.create(
                user=user2,
                embeddings=emb,
                raw=f"Shared keyword content for user2",
                compiled=f"User2 compiled",
                hashed_value=f"hash_iso2_{i}",
                search_model=search_model,
                chunk_scale="1024",
            )

        # Search as user1
        query_embedding = torch.randn(384)
        user1_results = EntryAdapters.search_with_embeddings(
            raw_query="Shared keyword",
            embeddings=query_embedding,
            user=user1,
            max_results=10,
        )

        # Verify all results belong to user1
        for result in user1_results:
            assert result.user == user1

        # Search as user2
        user2_results = EntryAdapters.search_with_embeddings(
            raw_query="Shared keyword",
            embeddings=query_embedding,
            user=user2,
            max_results=10,
        )

        # Verify all results belong to user2
        for result in user2_results:
            assert result.user == user2


class TestNewFieldsNullable:
    """Test that new fields allow NULL values as specified."""

    @pytest.mark.django_db
    def test_context_summary_nullable(self, test_users, search_model, sample_embeddings):
        """Verify context_summary allows NULL."""
        user = test_users[0]

        entry = Entry.objects.create(
            user=user,
            embeddings=sample_embeddings,
            raw="Test content",
            compiled="Test compiled",
            hashed_value="hash_null_ctx",
            search_model=search_model,
            # context_summary is not set - should be NULL
        )

        entry.refresh_from_db()
        assert entry.context_summary is None or entry.context_summary == ""

    @pytest.mark.django_db
    def test_chunk_scale_nullable(self, test_users, search_model, sample_embeddings):
        """Verify chunk_scale allows NULL."""
        user = test_users[0]

        entry = Entry.objects.create(
            user=user,
            embeddings=sample_embeddings,
            raw="Test content",
            compiled="Test compiled",
            hashed_value="hash_null_chunk",
            search_model=search_model,
            # chunk_scale is not set - should use default or be NULL
        )

        entry.refresh_from_db()
        # chunk_scale has default="default" so it shouldn't be None
        assert entry.chunk_scale is not None

    @pytest.mark.django_db
    def test_search_vector_nullable(self, test_users, search_model, sample_embeddings):
        """Verify search_vector allows NULL."""
        user = test_users[0]

        entry = Entry.objects.create(
            user=user,
            embeddings=sample_embeddings,
            raw="Test content",
            compiled="Test compiled",
            hashed_value="hash_null_sv",
            search_model=search_model,
            # search_vector is not set - should be NULL
        )

        entry.refresh_from_db()
        assert entry.search_vector is None


class TestBackwardCompatibility:
    """Test backward compatibility with entries without new fields."""

    @pytest.mark.django_db
    def test_create_entry_without_new_fields(self, test_users, search_model, sample_embeddings):
        """Create entries without new fields (as if old code) and verify defaults."""
        user = test_users[0]

        # Simulate old code creating entry without new fields
        entry = Entry.objects.create(
            user=user,
            embeddings=sample_embeddings,
            raw="Old style entry",
            compiled="Old style compiled",
            hashed_value="hash_old",
            search_model=search_model,
            # Not setting: search_vector, context_summary, chunk_scale
        )

        entry.refresh_from_db()

        # Verify entry exists
        assert entry.id is not None

        # Verify new fields have appropriate default values
        assert entry.search_vector is None  # NULL is allowed
        assert entry.context_summary is None  # NULL is allowed
        assert entry.chunk_scale == "default"  # Has default value

    @pytest.mark.django_db
    def test_query_entries_mixed_new_and_old(self, test_users, search_model, sample_embeddings_list):
        """Query entries with mixed presence of new fields."""
        user = test_users[0]

        # Create old-style entry
        old_entry = Entry.objects.create(
            user=user,
            embeddings=sample_embeddings_list[0],
            raw="Old entry",
            compiled="Old compiled",
            hashed_value="hash_old_mixed",
            search_model=search_model,
        )

        # Create new-style entry
        new_entry = Entry.objects.create(
            user=user,
            embeddings=sample_embeddings_list[1],
            raw="New entry",
            compiled="New compiled",
            hashed_value="hash_new_mixed",
            search_model=search_model,
            context_summary="New context summary",
            chunk_scale="2048",
        )

        # Query all entries - should work
        all_entries = Entry.objects.filter(user=user)
        assert all_entries.count() == 2

        # Verify both entries are accessible
        entry_ids = set(e.id for e in all_entries)
        assert old_entry.id in entry_ids
        assert new_entry.id in entry_ids

    @pytest.mark.django_db
    def test_filter_by_new_fields_with_nulls(self, test_users, search_model, sample_embeddings_list):
        """Filter by new fields when some entries have NULL values."""
        user = test_users[0]

        # Create entries with and without context_summary
        Entry.objects.create(
            user=user,
            embeddings=sample_embeddings_list[0],
            raw="Entry without summary",
            compiled="Compiled without summary",
            hashed_value="hash_no_summary",
            search_model=search_model,
        )

        Entry.objects.create(
            user=user,
            embeddings=sample_embeddings_list[1],
            raw="Entry with summary",
            compiled="Compiled with summary",
            hashed_value="hash_with_summary",
            search_model=search_model,
            context_summary="This entry has a summary",
        )

        # Filter for entries with context_summary
        with_summary = Entry.objects.filter(
            user=user,
            context_summary__isnull=False,
        )
        assert with_summary.count() == 1
        assert with_summary.first().context_summary == "This entry has a summary"

        # Filter for entries without context_summary
        without_summary = Entry.objects.filter(
            user=user,
            context_summary__isnull=True,
        )
        assert without_summary.count() == 1


class TestMigration0100SearchVectorOperations:
    """Test search_vector field operations from migration 0100."""

    @pytest.mark.django_db
    def test_search_vector_creation(self, test_users, search_model, sample_embeddings):
        """Test search_vector field creation and updates."""
        user = test_users[0]

        entry = Entry.objects.create(
            user=user,
            embeddings=sample_embeddings,
            raw="PostgreSQL search test",
            compiled="Testing PostgreSQL full-text search",
            hashed_value="hash_sv_create",
            search_model=search_model,
        )

        # Update search_vector
        Entry.objects.filter(id=entry.id).update(
            search_vector=SearchVector("raw", "compiled")
        )

        entry.refresh_from_db()
        assert entry.search_vector is not None

    @pytest.mark.django_db
    def test_search_vector_weighted(self, test_users, search_model, sample_embeddings):
        """Test weighted search vectors."""
        user = test_users[0]

        entry = Entry.objects.create(
            user=user,
            embeddings=sample_embeddings,
            raw="Important raw content",
            compiled="Compiled content",
            heading="Very Important Heading",
            hashed_value="hash_sv_weight",
            search_model=search_model,
        )

        # Create weighted search vector
        Entry.objects.filter(id=entry.id).update(
            search_vector=(
                SearchVector("heading", weight="A")
                + SearchVector("compiled", weight="B")
                + SearchVector("raw", weight="C")
            )
        )

        entry.refresh_from_db()
        assert entry.search_vector is not None

    @pytest.mark.django_db
    def test_gin_index_usage_in_query(self, test_users, search_model, sample_embeddings):
        """Test that GIN index is usable in queries."""
        from django.db import connection
        from django.test.utils import override_settings

        user = test_users[0]

        # Create entries with search_vector
        for i in range(5):
            entry = Entry.objects.create(
                user=user,
                embeddings=sample_embeddings,
                raw=f"Content for search test {i}",
                compiled=f"Compiled content {i}",
                hashed_value=f"hash_gin_{i}",
                search_model=search_model,
            )
            Entry.objects.filter(id=entry.id).update(
                search_vector=SearchVector("raw")
            )

        # Query using search_vector - should work with GIN index
        results = Entry.objects.filter(
            user=user,
            search_vector=SearchQuery("content"),
        )

        # Results should be returned
        assert results.count() > 0  # Should find entries with 'content' in raw field


class TestMigration0101ContextSummaryOperations:
    """Test context_summary field operations from migration 0101."""

    @pytest.mark.django_db
    def test_context_summary_read_write(self, test_users, search_model, sample_embeddings):
        """Test context_summary field read/write operations."""
        user = test_users[0]

        # Create entry with context_summary
        entry = Entry.objects.create(
            user=user,
            embeddings=sample_embeddings,
            raw="Test content",
            compiled="Test compiled",
            hashed_value="hash_cs_rw",
            search_model=search_model,
            context_summary="Initial summary",
        )

        assert entry.context_summary == "Initial summary"

        # Update context_summary
        Entry.objects.filter(id=entry.id).update(context_summary="Updated summary")

        entry.refresh_from_db()
        assert entry.context_summary == "Updated summary"

    @pytest.mark.django_db
    def test_context_summary_long_text(self, test_users, search_model, sample_embeddings):
        """Test context_summary with long text content."""
        user = test_users[0]

        long_summary = "This is a very long context summary. " * 100  # ~3700 chars

        entry = Entry.objects.create(
            user=user,
            embeddings=sample_embeddings,
            raw="Test content",
            compiled="Test compiled",
            hashed_value="hash_cs_long",
            search_model=search_model,
            context_summary=long_summary,
        )

        entry.refresh_from_db()
        assert entry.context_summary == long_summary
        assert len(entry.context_summary) > 3000

    @pytest.mark.django_db
    def test_context_summary_unicode(self, test_users, search_model, sample_embeddings):
        """Test context_summary with unicode content."""
        user = test_users[0]

        unicode_summary = "Context with unicode: 🚀 émojis 中文 العربية"

        entry = Entry.objects.create(
            user=user,
            embeddings=sample_embeddings,
            raw="Test content",
            compiled="Test compiled",
            hashed_value="hash_cs_unicode",
            search_model=search_model,
            context_summary=unicode_summary,
        )

        entry.refresh_from_db()
        assert entry.context_summary == unicode_summary


class TestMigration0102ChunkScaleOperations:
    """Test chunk_scale field operations from migration 0102."""

    @pytest.mark.django_db
    def test_chunk_scale_read_write(self, test_users, search_model, sample_embeddings):
        """Test chunk_scale field read/write operations."""
        user = test_users[0]

        # Create entry with chunk_scale
        entry = Entry.objects.create(
            user=user,
            embeddings=sample_embeddings,
            raw="Test content",
            compiled="Test compiled",
            hashed_value="hash_cs_rw",
            search_model=search_model,
            chunk_scale="1024",
        )

        assert entry.chunk_scale == "1024"

        # Update chunk_scale
        Entry.objects.filter(id=entry.id).update(chunk_scale="2048")

        entry.refresh_from_db()
        assert entry.chunk_scale == "2048"

    @pytest.mark.django_db
    def test_chunk_scale_default_value(self, test_users, search_model, sample_embeddings):
        """Test chunk_scale default value."""
        user = test_users[0]

        # Create entry without specifying chunk_scale
        entry = Entry.objects.create(
            user=user,
            embeddings=sample_embeddings,
            raw="Test content",
            compiled="Test compiled",
            hashed_value="hash_cs_default",
            search_model=search_model,
        )

        entry.refresh_from_db()
        # Default value should be "default"
        assert entry.chunk_scale == "default"

    @pytest.mark.django_db
    def test_chunk_scale_filtering(self, test_users, search_model, sample_embeddings_list):
        """Test filtering entries by chunk_scale values."""
        user = test_users[0]

        # Create entries with different chunk scales
        scales = ["512", "1024", "2048", "default"]
        for i, (emb, scale) in enumerate(zip(sample_embeddings_list, scales)):
            Entry.objects.create(
                user=user,
                embeddings=emb,
                raw=f"Content with scale {scale}",
                compiled=f"Compiled {scale}",
                hashed_value=f"hash_scale_{i}",
                search_model=search_model,
                chunk_scale=scale,
            )

        # Filter by specific chunk scales
        small_chunks = Entry.objects.filter(user=user, chunk_scale__in=["512", "1024"])
        assert small_chunks.count() == 2

        default_chunks = Entry.objects.filter(user=user, chunk_scale="default")
        assert default_chunks.count() == 1

    @pytest.mark.django_db
    def test_chunk_scale_max_length(self, test_users, search_model, sample_embeddings):
        """Test chunk_scale respects max_length constraint."""
        user = test_users[0]

        # chunk_scale has max_length=16, so this should work
        valid_scale = "x" * 16

        entry = Entry.objects.create(
            user=user,
            embeddings=sample_embeddings,
            raw="Test content",
            compiled="Test compiled",
            hashed_value="hash_cs_max",
            search_model=search_model,
            chunk_scale=valid_scale,
        )

        entry.refresh_from_db()
        assert entry.chunk_scale == valid_scale


class TestMultiScaleChunkingIntegration:
    """Test multi-scale chunking integration with new fields."""

    @pytest.mark.django_db
    def test_multi_scale_entries_coexist(self, test_users, search_model, sample_embeddings_list):
        """Test that entries with different chunk scales can coexist."""
        user = test_users[0]

        # Create entries representing different chunk scales of the same content
        base_content = "This is a test document for multi-scale chunking."

        scales = ["512", "1024", "2048"]
        entries = []

        for i, (emb, scale) in enumerate(zip(sample_embeddings_list[:3], scales)):
            entry = Entry.objects.create(
                user=user,
                embeddings=emb,
                raw=f"{base_content} Scale: {scale}",
                compiled=f"Compiled scale {scale}",
                hashed_value=f"hash_multiscale_{i}",
                search_model=search_model,
                chunk_scale=scale,
                context_summary=f"Summary for {scale} chunk",
            )
            entries.append(entry)

        # Verify all entries exist
        assert len(entries) == 3

        # Verify each has correct scale
        for entry in entries:
            assert entry.chunk_scale in scales
            assert entry.context_summary.startswith("Summary for")

    @pytest.mark.django_db
    def test_search_across_chunk_scales(self, test_users, search_model, sample_embeddings_list):
        """Test search works across entries with different chunk scales."""
        user = test_users[0]

        # Create entries with different chunk scales
        for i, emb in enumerate(sample_embeddings_list):
            Entry.objects.create(
                user=user,
                embeddings=emb,
                raw=f"Multi-scale content test",
                compiled=f"Compiled content for scale",
                hashed_value=f"hash_search_ms_{i}",
                search_model=search_model,
                chunk_scale=["512", "1024", "2048"][i % 3],
            )

        # Search across all scales
        query_embedding = torch.randn(384)
        results = EntryAdapters.search_with_embeddings(
            raw_query="multi-scale content",
            embeddings=query_embedding,
            user=user,
            max_results=10,
        )

        # Should find results regardless of chunk scale
        assert results is not None


# ============================================================================
# Async versions of key tests for async compatibility
# ============================================================================

@pytest.mark.asyncio
class TestAsyncEntryOperations:
    """Test async operations on Entry model after migrations."""

    @pytest.mark.django_db
    async def test_async_filter_by_user(self, test_users, search_model, sample_embeddings_list):
        """Test async filtering of entries by user."""
        user = test_users[0]

        # Create entries
        for i, emb in enumerate(sample_embeddings_list[:3]):
            await sync_to_async(Entry.objects.create)(
                user=user,
                embeddings=emb,
                raw=f"Async content {i}",
                compiled=f"Async compiled {i}",
                hashed_value=f"hash_async_{i}",
                search_model=search_model,
                chunk_scale="1024",
            )

        # Async filter
        entries = await sync_to_async(list)(Entry.objects.filter(user=user))
        assert len(entries) == 3

    @pytest.mark.django_db
    async def test_async_context_summary_update(self, test_users, search_model, sample_embeddings):
        """Test async update of context_summary."""
        user = test_users[0]

        entry = await sync_to_async(Entry.objects.create)(
            user=user,
            embeddings=sample_embeddings,
            raw="Async test",
            compiled="Async compiled",
            hashed_value="hash_async_update",
            search_model=search_model,
        )

        # Async update
        await sync_to_async(Entry.objects.filter(id=entry.id).update)(
            context_summary="Async updated summary"
        )

        # Refresh and verify
        entry = await sync_to_async(Entry.objects.get)(id=entry.id)
        assert entry.context_summary == "Async updated summary"

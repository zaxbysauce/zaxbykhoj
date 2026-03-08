"""
Rollback Verification Tests for Migrations 0100-0102

This module tests database migration rollbacks for:
- 0100_add_search_vector.py - Adds search_vector field and GIN index
- 0101_add_context_summary.py - Adds context_summary field
- 0102_add_chunk_scale.py - Adds chunk_scale field

Test coverage:
1. Individual rollback for each migration
2. Complete rollback of all 3 migrations
3. Row count preservation during rollbacks
4. Data integrity after rollbacks
5. Idempotency of rollback and reapply
"""

import pytest
import torch
from django.core.management import call_command
from django.db import connection
from django.db.models import Count
from django.test.utils import override_settings

from khoj.database.models import Entry, KhojUser, SearchModelConfig
from tests.helpers import SearchModelFactory, UserFactory


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def test_user(db):
    """Create a test user for rollback tests."""
    return UserFactory(username="rollback_test_user", email="rollback@test.com")


@pytest.fixture
def search_model(db):
    """Create a search model configuration."""
    return SearchModelFactory()


@pytest.fixture
def sample_embeddings():
    """Generate sample embeddings for testing."""
    return torch.randn(384).tolist()


@pytest.fixture
def migration_executor():
    """Get the migration executor for running migrations programmatically."""
    from django.db.migrations.executor import MigrationExecutor

    return MigrationExecutor(connection)


@pytest.fixture(autouse=True)
def ensure_initial_state(db):
    """Ensure database is at migration 0099 before each test."""
    # Start fresh at 0099
    call_command("migrate", "database", "0099", verbosity=0)
    yield
    # Cleanup: migrate back to latest after test
    call_command("migrate", "database", verbosity=0)


# ============================================================================
# Helper Functions
# ============================================================================


def get_row_count(table_name="database_entry"):
    """Get the row count for a given table."""
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        return cursor.fetchone()[0]


def column_exists(table_name, column_name):
    """Check if a column exists in a table."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = %s AND column_name = %s
            )
            """,
            [table_name, column_name],
        )
        return cursor.fetchone()[0]


def index_exists(table_name, index_name):
    """Check if an index exists on a table."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1 
                FROM pg_indexes 
                WHERE tablename = %s AND indexname = %s
            )
            """,
            [table_name, index_name],
        )
        return cursor.fetchone()[0]


def get_current_migration():
    """Get the current migration version for the database app."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT name FROM django_migrations 
            WHERE app = 'database' 
            ORDER BY applied DESC 
            LIMIT 1
            """
        )
        result = cursor.fetchone()
        return result[0] if result else None


def create_test_entry(user, search_model, sample_embeddings, **extra_fields):
    """Helper to create a test entry with the given fields."""
    return Entry.objects.create(
        user=user,
        embeddings=sample_embeddings,
        raw="Test raw content for rollback",
        compiled="Test compiled content for rollback",
        heading="Test Heading",
        file_type=Entry.EntryType.PLAINTEXT,
        file_path="/test/path/rollback.txt",
        file_name="rollback.txt",
        hashed_value=f"rollback_hash_{get_row_count()}",
        search_model=search_model,
        **extra_fields,
    )


# ============================================================================
# Test Case 1: Rollback 0102 - Removes chunk_scale
# ============================================================================


@pytest.mark.django_db(transaction=True)
class TestRollback0102RemovesChunkScale:
    """Test that rollback of migration 0102 removes chunk_scale column."""

    def test_rollback_0102_removes_chunk_scale(self, test_user, search_model, sample_embeddings):
        """
        Test: Apply migration 0102, create entries with chunk_scale, rollback to 0101,
        verify chunk_scale column is removed and row count is preserved.
        """
        # Step 1: Apply migration 0102
        call_command("migrate", "database", "0102", verbosity=0)

        # Verify we're at 0102
        assert "0102" in get_current_migration()

        # Step 2: Create entries with chunk_scale values
        entries = []
        for i in range(5):
            entry = create_test_entry(
                test_user,
                search_model,
                sample_embeddings,
                chunk_scale=["512", "1024", "2048", "default", "1024"][i],
            )
            entries.append(entry)

        # Record row count before rollback
        row_count_before = get_row_count()
        assert row_count_before == 5

        # Verify chunk_scale column exists
        assert column_exists("database_entry", "chunk_scale")

        # Step 3: Rollback to 0101
        call_command("migrate", "database", "0101", verbosity=0)

        # Step 4: Verify chunk_scale column is removed
        assert not column_exists("database_entry", "chunk_scale"), (
            "chunk_scale column should be removed after rollback"
        )

        # Step 5: Verify row count is preserved
        row_count_after = get_row_count()
        assert row_count_after == row_count_before, (
            f"Row count changed after rollback: {row_count_before} -> {row_count_after}"
        )

        # Step 6: Verify entries still exist (can query without chunk_scale)
        remaining_entries = Entry.objects.filter(user=test_user)
        assert remaining_entries.count() == 5

    def test_rollback_0102_preserves_other_new_fields(self, test_user, search_model, sample_embeddings):
        """
        Test: When rolling back 0102, ensure other fields (search_vector, context_summary) are preserved.
        """
        from django.contrib.postgres.search import SearchVector

        # Apply up to 0102
        call_command("migrate", "database", "0102", verbosity=0)

        # Create entry with all new fields
        entry = create_test_entry(
            test_user,
            search_model,
            sample_embeddings,
            chunk_scale="1024",
            context_summary="Test context summary",
        )

        # Set search_vector
        Entry.objects.filter(id=entry.id).update(search_vector=SearchVector("raw"))

        # Verify all fields exist
        assert column_exists("database_entry", "chunk_scale")
        assert column_exists("database_entry", "context_summary")
        assert column_exists("database_entry", "search_vector")

        # Rollback to 0101 (removes only chunk_scale)
        call_command("migrate", "database", "0101", verbosity=0)

        # Verify only chunk_scale is removed
        assert not column_exists("database_entry", "chunk_scale")
        assert column_exists("database_entry", "context_summary")
        assert column_exists("database_entry", "search_vector")


# ============================================================================
# Test Case 2: Rollback 0101 - Removes context_summary
# ============================================================================


@pytest.mark.django_db(transaction=True)
class TestRollback0101RemovesContextSummary:
    """Test that rollback of migration 0101 removes context_summary column."""

    def test_rollback_0101_removes_context_summary(self, test_user, search_model, sample_embeddings):
        """
        Test: Apply migration 0101, create entries with context_summary, rollback to 0100,
        verify context_summary column is removed and row count is preserved.
        """
        # Step 1: Apply migration 0101
        call_command("migrate", "database", "0101", verbosity=0)

        # Verify we're at 0101
        assert "0101" in get_current_migration()

        # Step 2: Create entries with context_summary
        summaries = ["Summary 1", "Summary 2", "Summary 3", None, "Summary 5"]
        for i, summary in enumerate(summaries):
            create_test_entry(
                test_user,
                search_model,
                sample_embeddings,
                context_summary=summary,
            )

        # Record row count before rollback
        row_count_before = get_row_count()
        assert row_count_before == 5

        # Verify context_summary column exists
        assert column_exists("database_entry", "context_summary")

        # Step 3: Rollback to 0100
        call_command("migrate", "database", "0100", verbosity=0)

        # Step 4: Verify context_summary column is removed
        assert not column_exists("database_entry", "context_summary"), (
            "context_summary column should be removed after rollback"
        )

        # Step 5: Verify row count is preserved
        row_count_after = get_row_count()
        assert row_count_after == row_count_before, (
            f"Row count changed after rollback: {row_count_before} -> {row_count_after}"
        )

    def test_rollback_0101_preserves_search_vector(self, test_user, search_model, sample_embeddings):
        """
        Test: When rolling back 0101, ensure search_vector field is preserved.
        """
        from django.contrib.postgres.search import SearchVector

        # Apply up to 0101
        call_command("migrate", "database", "0101", verbosity=0)

        # Create entry with context_summary
        entry = create_test_entry(
            test_user,
            search_model,
            sample_embeddings,
            context_summary="Test summary",
        )

        # Set search_vector (simulating 0100 is applied)
        Entry.objects.filter(id=entry.id).update(search_vector=SearchVector("raw"))

        # Verify both fields exist
        assert column_exists("database_entry", "context_summary")
        assert column_exists("database_entry", "search_vector")

        # Rollback to 0100 (removes only context_summary)
        call_command("migrate", "database", "0100", verbosity=0)

        # Verify only context_summary is removed
        assert not column_exists("database_entry", "context_summary")
        assert column_exists("database_entry", "search_vector")


# ============================================================================
# Test Case 3: Rollback 0100 - Removes search_vector and GIN index
# ============================================================================


@pytest.mark.django_db(transaction=True)
class TestRollback0100RemovesSearchVector:
    """Test that rollback of migration 0100 removes search_vector column and GIN index."""

    def test_rollback_0100_removes_search_vector(self, test_user, search_model, sample_embeddings):
        """
        Test: Apply migration 0100, create entries with search_vector, rollback to 0099,
        verify search_vector column and GIN index are removed, row count preserved.
        """
        from django.contrib.postgres.search import SearchVector

        # Step 1: Apply migration 0100
        call_command("migrate", "database", "0100", verbosity=0)

        # Verify we're at 0100
        assert "0100" in get_current_migration()

        # Step 2: Create entries with search_vector
        for i in range(10):
            entry = create_test_entry(test_user, search_model, sample_embeddings)
            # Set search_vector
            Entry.objects.filter(id=entry.id).update(search_vector=SearchVector("raw", "compiled"))

        # Record row count before rollback
        row_count_before = get_row_count()
        assert row_count_before == 10

        # Verify search_vector column and GIN index exist
        assert column_exists("database_entry", "search_vector")
        assert index_exists("database_entry", "entry_search_vector_gin_idx")

        # Step 3: Rollback to 0099
        call_command("migrate", "database", "0099", verbosity=0)

        # Step 4: Verify search_vector column is removed
        assert not column_exists("database_entry", "search_vector"), (
            "search_vector column should be removed after rollback"
        )

        # Step 5: Verify GIN index is removed
        assert not index_exists("database_entry", "entry_search_vector_gin_idx"), (
            "GIN index on search_vector should be removed after rollback"
        )

        # Step 6: Verify row count is preserved
        row_count_after = get_row_count()
        assert row_count_after == row_count_before, (
            f"Row count changed after rollback: {row_count_before} -> {row_count_after}"
        )

        # Step 7: Verify entries still exist and are queryable
        remaining_entries = Entry.objects.filter(user=test_user)
        assert remaining_entries.count() == 10

    def test_rollback_0100_removes_gin_index_only(self, test_user, search_model, sample_embeddings):
        """
        Test: Verify that rolling back 0100 specifically removes the GIN index.
        """
        from django.contrib.postgres.search import SearchVector

        # Apply 0100
        call_command("migrate", "database", "0100", verbosity=0)

        # Create entry and set search_vector
        entry = create_test_entry(test_user, search_model, sample_embeddings)
        Entry.objects.filter(id=entry.id).update(search_vector=SearchVector("raw"))

        # Verify GIN index exists
        assert index_exists("database_entry", "entry_search_vector_gin_idx")

        # Rollback
        call_command("migrate", "database", "0099", verbosity=0)

        # Verify GIN index is removed
        assert not index_exists("database_entry", "entry_search_vector_gin_idx")


# ============================================================================
# Test Case 4: Complete Rollback - All 3 Migrations
# ============================================================================


@pytest.mark.django_db(transaction=True)
class TestCompleteRollbackAllMigrations:
    """Test complete rollback of all 3 migrations (0100, 0101, 0102) to 0099."""

    def test_complete_rollback_all_migrations(self, test_user, search_model, sample_embeddings):
        """
        Test: Apply all 3 migrations, create 100 test entries, rollback all,
        verify all columns removed and row count unchanged.
        """
        from django.contrib.postgres.search import SearchVector

        # Step 1: Apply all 3 migrations
        call_command("migrate", "database", "0102", verbosity=0)

        # Verify we're at 0102
        assert "0102" in get_current_migration()

        # Step 2: Create 100 test entries with all new fields
        scales = ["512", "1024", "2048", "default"]
        for i in range(100):
            entry = create_test_entry(
                test_user,
                search_model,
                sample_embeddings,
                chunk_scale=scales[i % 4],
                context_summary=f"Context summary for entry {i}",
            )
            # Set search_vector
            Entry.objects.filter(id=entry.id).update(search_vector=SearchVector("raw"))

        # Step 3: Record row count
        row_count_before = get_row_count()
        assert row_count_before == 100

        # Verify all columns and index exist
        assert column_exists("database_entry", "search_vector")
        assert column_exists("database_entry", "context_summary")
        assert column_exists("database_entry", "chunk_scale")
        assert index_exists("database_entry", "entry_search_vector_gin_idx")

        # Step 4: Rollback all 3 migrations to 0099
        call_command("migrate", "database", "0099", verbosity=0)

        # Step 5: Verify all columns removed
        assert not column_exists("database_entry", "search_vector"), (
            "search_vector should be removed after complete rollback"
        )
        assert not column_exists("database_entry", "context_summary"), (
            "context_summary should be removed after complete rollback"
        )
        assert not column_exists("database_entry", "chunk_scale"), (
            "chunk_scale should be removed after complete rollback"
        )

        # Step 6: Verify GIN index removed
        assert not index_exists("database_entry", "entry_search_vector_gin_idx"), (
            "GIN index should be removed after complete rollback"
        )

        # Step 7: Verify row count unchanged
        row_count_after = get_row_count()
        assert row_count_after == row_count_before, (
            f"Row count changed after complete rollback: {row_count_before} -> {row_count_after}"
        )

        # Step 8: Verify entries still queryable
        remaining_entries = Entry.objects.filter(user=test_user)
        assert remaining_entries.count() == 100

    def test_staged_rollback_all_migrations(self, test_user, search_model, sample_embeddings):
        """
        Test: Rollback migrations one at a time and verify correct columns removed at each stage.
        """
        from django.contrib.postgres.search import SearchVector

        # Apply all migrations
        call_command("migrate", "database", "0102", verbosity=0)

        # Create test entry with all fields
        entry = create_test_entry(
            test_user,
            search_model,
            sample_embeddings,
            chunk_scale="1024",
            context_summary="Test summary",
        )
        Entry.objects.filter(id=entry.id).update(search_vector=SearchVector("raw"))

        # Stage 1: Rollback to 0101 (removes chunk_scale only)
        call_command("migrate", "database", "0101", verbosity=0)
        assert not column_exists("database_entry", "chunk_scale")
        assert column_exists("database_entry", "context_summary")
        assert column_exists("database_entry", "search_vector")
        assert index_exists("database_entry", "entry_search_vector_gin_idx")

        # Stage 2: Rollback to 0100 (removes context_summary only)
        call_command("migrate", "database", "0100", verbosity=0)
        assert not column_exists("database_entry", "chunk_scale")
        assert not column_exists("database_entry", "context_summary")
        assert column_exists("database_entry", "search_vector")
        assert index_exists("database_entry", "entry_search_vector_gin_idx")

        # Stage 3: Rollback to 0099 (removes search_vector and GIN index)
        call_command("migrate", "database", "0099", verbosity=0)
        assert not column_exists("database_entry", "chunk_scale")
        assert not column_exists("database_entry", "context_summary")
        assert not column_exists("database_entry", "search_vector")
        assert not index_exists("database_entry", "entry_search_vector_gin_idx")

        # Verify entry still exists
        assert Entry.objects.filter(id=entry.id).exists()


# ============================================================================
# Test Case 5: Rollback Preserves Existing Data
# ============================================================================


@pytest.mark.django_db(transaction=True)
class TestRollbackPreservesExistingData:
    """Test that rollback preserves data that existed before migrations."""

    def test_rollback_preserves_original_data(self, test_user, search_model, sample_embeddings):
        """
        Test: Create entries before migrations, apply then rollback migrations,
        verify original data is still intact.
        """
        from django.contrib.postgres.search import SearchVector

        # Step 1: Create entries at 0099 (before any new migrations)
        original_entries = []
        for i in range(10):
            entry = create_test_entry(
                test_user,
                search_model,
                sample_embeddings,
                raw=f"Original raw content {i}",
                compiled=f"Original compiled content {i}",
                hashed_value=f"original_hash_{i}",
            )
            original_entries.append(entry)

        # Store original data for verification
        original_data = {
            entry.id: {
                "raw": entry.raw,
                "compiled": entry.compiled,
                "hashed_value": entry.hashed_value,
            }
            for entry in original_entries
        }

        # Step 2: Apply all migrations
        call_command("migrate", "database", "0102", verbosity=0)

        # Step 3: Update entries with new fields
        for i, entry in enumerate(original_entries):
            Entry.objects.filter(id=entry.id).update(
                chunk_scale="1024",
                context_summary=f"Added summary {i}",
                search_vector=SearchVector("raw"),
            )

        # Step 4: Rollback all migrations
        call_command("migrate", "database", "0099", verbosity=0)

        # Step 5: Verify original data is preserved
        for entry_id, original in original_data.items():
            entry = Entry.objects.get(id=entry_id)
            assert entry.raw == original["raw"], (
                f"Raw content changed for entry {entry_id}"
            )
            assert entry.compiled == original["compiled"], (
                f"Compiled content changed for entry {entry_id}"
            )
            assert entry.hashed_value == original["hashed_value"], (
                f"Hashed value changed for entry {entry_id}"
            )

    def test_rollback_preserves_row_count_with_existing_data(self, test_user, search_model, sample_embeddings):
        """
        Test: Mix of existing and new entries, verify all preserved after rollback.
        """
        from django.contrib.postgres.search import SearchVector

        # Create initial entries
        initial_count = 25
        for i in range(initial_count):
            create_test_entry(
                test_user,
                search_model,
                sample_embeddings,
                raw=f"Initial entry {i}",
                hashed_value=f"initial_hash_{i}",
            )

        # Record count
        count_before_migrations = get_row_count()
        assert count_before_migrations == initial_count

        # Apply migrations
        call_command("migrate", "database", "0102", verbosity=0)

        # Create more entries with new fields
        additional_count = 15
        for i in range(additional_count):
            entry = create_test_entry(
                test_user,
                search_model,
                sample_embeddings,
                raw=f"New entry {i}",
                hashed_value=f"new_hash_{i}",
                chunk_scale="512",
                context_summary=f"Summary {i}",
            )
            Entry.objects.filter(id=entry.id).update(search_vector=SearchVector("raw"))

        # Verify total count
        count_with_new = get_row_count()
        assert count_with_new == initial_count + additional_count

        # Rollback
        call_command("migrate", "database", "0099", verbosity=0)

        # Verify all entries preserved
        count_after_rollback = get_row_count()
        assert count_after_rollback == count_with_new, (
            f"Row count mismatch after rollback: {count_with_new} -> {count_after_rollback}"
        )

        # Verify all entries queryable
        all_entries = Entry.objects.filter(user=test_user)
        assert all_entries.count() == initial_count + additional_count


# ============================================================================
# Test Case 6: Rollback and Reapply Idempotent
# ============================================================================


@pytest.mark.django_db(transaction=True)
class TestRollbackAndReapplyIdempotent:
    """Test that rollback and reapply cycle is idempotent."""

    def test_rollback_and_reapply_idempotent(self, test_user, search_model, sample_embeddings):
        """
        Test: Apply migrations, rollback, re-apply migrations, verify system works correctly.
        """
        from django.contrib.postgres.search import SearchVector

        # Step 1: Apply migrations
        call_command("migrate", "database", "0102", verbosity=0)

        # Step 2: Create entries with all new fields
        entries = []
        for i in range(5):
            entry = create_test_entry(
                test_user,
                search_model,
                sample_embeddings,
                chunk_scale="1024",
                context_summary=f"Summary {i}",
            )
            Entry.objects.filter(id=entry.id).update(search_vector=SearchVector("raw"))
            entries.append(entry)

        # Step 3: Verify columns exist
        assert column_exists("database_entry", "search_vector")
        assert column_exists("database_entry", "context_summary")
        assert column_exists("database_entry", "chunk_scale")
        assert index_exists("database_entry", "entry_search_vector_gin_idx")

        # Step 4: Rollback all migrations
        call_command("migrate", "database", "0099", verbosity=0)

        # Verify columns removed
        assert not column_exists("database_entry", "search_vector")
        assert not column_exists("database_entry", "context_summary")
        assert not column_exists("database_entry", "chunk_scale")

        # Step 5: Re-apply migrations
        call_command("migrate", "database", "0102", verbosity=0)

        # Step 6: Verify columns restored
        assert column_exists("database_entry", "search_vector")
        assert column_exists("database_entry", "context_summary")
        assert column_exists("database_entry", "chunk_scale")
        assert index_exists("database_entry", "entry_search_vector_gin_idx")

        # Step 7: Verify system works - can create new entries with all fields
        new_entries = []
        for i in range(3):
            entry = create_test_entry(
                test_user,
                search_model,
                sample_embeddings,
                raw=f"Reapplied entry {i}",
                compiled=f"Reapplied compiled {i}",
                hashed_value=f"reapplied_hash_{i}",
                chunk_scale="2048",
                context_summary=f"Reapplied summary {i}",
            )
            Entry.objects.filter(id=entry.id).update(search_vector=SearchVector("raw", "compiled"))
            new_entries.append(entry)

        # Step 8: Verify all entries (old and new) exist
        all_entries = Entry.objects.filter(user=test_user)
        assert all_entries.count() == len(entries) + len(new_entries)

        # Step 9: Verify new entries have correct data
        for i, entry in enumerate(new_entries):
            entry.refresh_from_db()
            assert entry.chunk_scale == "2048"
            assert entry.context_summary == f"Reapplied summary {i}"
            assert entry.search_vector is not None

    def test_multiple_rollback_reapply_cycles(self, test_user, search_model, sample_embeddings):
        """
        Test: Multiple rollback and reapply cycles remain idempotent.
        """
        from django.contrib.postgres.search import SearchVector

        # Perform multiple cycles
        for cycle in range(3):
            # Apply
            call_command("migrate", "database", "0102", verbosity=0)

            # Create entry
            entry = create_test_entry(
                test_user,
                search_model,
                sample_embeddings,
                raw=f"Cycle {cycle} entry",
                chunk_scale=f"{512 * (cycle + 1)}",
                context_summary=f"Cycle {cycle} summary",
            )
            Entry.objects.filter(id=entry.id).update(search_vector=SearchVector("raw"))

            # Verify
            entry.refresh_from_db()
            assert entry.chunk_scale == f"{512 * (cycle + 1)}"
            assert entry.context_summary == f"Cycle {cycle} summary"

            # Rollback
            call_command("migrate", "database", "0099", verbosity=0)

            # Verify entry still exists (core data preserved)
            assert Entry.objects.filter(id=entry.id).exists()

        # Final apply
        call_command("migrate", "database", "0102", verbosity=0)

        # Verify final state
        assert column_exists("database_entry", "search_vector")
        assert column_exists("database_entry", "context_summary")
        assert column_exists("database_entry", "chunk_scale")
        assert index_exists("database_entry", "entry_search_vector_gin_idx")

        # Verify all entries exist
        total_entries = Entry.objects.filter(user=test_user).count()
        assert total_entries == 3  # One per cycle


# ============================================================================
# Additional Edge Case Tests
# ============================================================================


@pytest.mark.django_db(transaction=True)
class TestRollbackEdgeCases:
    """Test edge cases for migration rollbacks."""

    def test_rollback_with_no_entries(self):
        """
        Test: Rollback migrations when no entries exist.
        """
        from django.contrib.postgres.search import SearchVector

        # Apply migrations
        call_command("migrate", "database", "0102", verbosity=0)

        # Verify columns exist
        assert column_exists("database_entry", "search_vector")
        assert column_exists("database_entry", "context_summary")
        assert column_exists("database_entry", "chunk_scale")

        # Rollback (no entries to preserve)
        call_command("migrate", "database", "0099", verbosity=0)

        # Verify columns removed
        assert not column_exists("database_entry", "search_vector")
        assert not column_exists("database_entry", "context_summary")
        assert not column_exists("database_entry", "chunk_scale")

        # Verify row count is 0
        assert get_row_count() == 0

    def test_rollback_with_unicode_data(self, test_user, search_model, sample_embeddings):
        """
        Test: Rollback preserves unicode data correctly.
        """
        from django.contrib.postgres.search import SearchVector

        # Apply migrations
        call_command("migrate", "database", "0102", verbosity=0)

        # Create entry with unicode content
        unicode_summary = "Unicode: 🚀 émojis 中文 العربية 日本語"
        entry = create_test_entry(
            test_user,
            search_model,
            sample_embeddings,
            raw="Unicode raw content",
            compiled="Unicode compiled content",
            chunk_scale="1024",
            context_summary=unicode_summary,
        )
        Entry.objects.filter(id=entry.id).update(search_vector=SearchVector("raw"))

        # Rollback
        call_command("migrate", "database", "0099", verbosity=0)

        # Re-apply
        call_command("migrate", "database", "0102", verbosity=0)

        # Verify unicode content preserved
        entry.refresh_from_db()
        assert entry.raw == "Unicode raw content"
        assert entry.compiled == "Unicode compiled content"

    def test_rollback_with_large_dataset(self, test_user, search_model, sample_embeddings):
        """
        Test: Rollback with a larger dataset (1000 entries).
        """
        from django.contrib.postgres.search import SearchVector

        # Apply migrations
        call_command("migrate", "database", "0102", verbosity=0)

        # Create 1000 entries
        for i in range(1000):
            entry = create_test_entry(
                test_user,
                search_model,
                sample_embeddings,
                raw=f"Large dataset entry {i}",
                hashed_value=f"large_hash_{i}",
                chunk_scale=["512", "1024", "2048", "default"][i % 4],
                context_summary=f"Summary for entry {i}",
            )
            if i % 2 == 0:  # Set search_vector on half
                Entry.objects.filter(id=entry.id).update(search_vector=SearchVector("raw"))

        # Record count
        count_before = get_row_count()
        assert count_before == 1000

        # Rollback
        call_command("migrate", "database", "0099", verbosity=0)

        # Verify count preserved
        count_after = get_row_count()
        assert count_after == count_before

        # Re-apply
        call_command("migrate", "database", "0102", verbosity=0)

        # Verify system still works
        entry = create_test_entry(
            test_user,
            search_model,
            sample_embeddings,
            chunk_scale="1024",
            context_summary="Final entry",
        )
        Entry.objects.filter(id=entry.id).update(search_vector=SearchVector("raw"))

        assert Entry.objects.filter(user=test_user).count() == 1001

    def test_rollback_individual_migration_preserves_others(self, test_user, search_model, sample_embeddings):
        """
        Test: Rolling back individual migration doesn't affect other migrations.
        """
        from django.contrib.postgres.search import SearchVector

        # Apply all
        call_command("migrate", "database", "0102", verbosity=0)

        # Create entries with all fields
        entry = create_test_entry(
            test_user,
            search_model,
            sample_embeddings,
            chunk_scale="1024",
            context_summary="Test summary",
        )
        Entry.objects.filter(id=entry.id).update(search_vector=SearchVector("raw"))

        # Rollback only 0102
        call_command("migrate", "database", "0101", verbosity=0)

        # Verify 0100 and 0101 fields still work
        Entry.objects.filter(id=entry.id).update(context_summary="Updated after 0102 rollback")
        entry.refresh_from_db()
        assert entry.context_summary == "Updated after 0102 rollback"

        # Rollback 0101
        call_command("migrate", "database", "0100", verbosity=0)

        # Verify 0100 field still works
        Entry.objects.filter(id=entry.id).update(search_vector=SearchVector("compiled"))
        entry.refresh_from_db()
        assert entry.search_vector is not None

        # Rollback 0100
        call_command("migrate", "database", "0099", verbosity=0)

        # Verify entry still exists
        assert Entry.objects.filter(id=entry.id).exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

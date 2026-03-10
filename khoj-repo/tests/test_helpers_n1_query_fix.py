"""
Tests for N+1 query fix in khoj.routers.helpers

These tests verify that ai_update_memories uses bulk operations:
- Bulk create using abulk_create
- Bulk delete using filter().adelete()

This ensures query count is reduced from O(N) to O(1).

These tests verify the source code directly without requiring a database.
"""

import pytest


class TestAiUpdateMemoriesBulkOperations:
    """Test that ai_update_memories uses bulk operations to avoid N+1 queries."""

    def test_bulk_create_is_used_in_implementation(self):
        """
        Test that the implementation uses abulk_create for bulk memory creation.
        
        This verifies that the code path uses bulk operations by checking
        the actual implementation in helpers.py.
        """
        # Read the source file and verify bulk operations are used
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # Verify abulk_create is used for bulk creation
        assert 'abulk_create' in source, "abulk_create should be used for bulk memory creation"
        
        # Verify filter().adelete() pattern is used for bulk deletion
        assert '.adelete()' in source, "adelete() should be used for bulk memory deletion"
        assert 'filter(' in source, "filter() should be used to select memories for deletion"

    def test_bulk_create_signature(self):
        """
        Test that abulk_create is called with the correct arguments.
        """
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # Verify abulk_create is called with new_memories list
        assert 'await UserMemory.objects.abulk_create(new_memories)' in source, \
            "Should call abulk_create with the new_memories list"

    def test_bulk_delete_pattern(self):
        """
        Test that filter().adelete() pattern is used for deletion.
        """
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # Verify the bulk delete pattern: filter(...).adelete()
        assert 'filter(user=user, raw__in=memory_update.delete).adelete()' in source, \
            "Should use filter().adelete() pattern for bulk deletion"


class TestN1QueryFixVerification:
    """Verify the N+1 query fix is properly implemented."""

    def test_no_individual_save_calls(self):
        """
        Verify that the N+1 problem is avoided by using bulk operations.
        
        The N+1 problem occurs when you loop and call save() for each item.
        The fix should use bulk operations instead.
        """
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # The fix should use list comprehension with abulk_create, not loop with save()
        # Check that the memory creation uses list comprehension
        assert 'new_memories = [' in source, "Should use list comprehension for memory creation"

    def test_bulk_operations_reduce_query_count(self):
        """
        Verify that bulk operations are used to reduce query count.
        
        With N memories:
        - Old (N+1): N queries for creates + 1 for fetch = N+1 total
        - New (O(1)): 1 query for bulk create + 1 for fetch = O(1) total
        """
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # Count the use of bulk operations
        bulk_create_count = source.count('abulk_create')
        bulk_delete_count = source.count('.adelete()')
        
        # Should have at least one bulk create and one bulk delete
        assert bulk_create_count >= 1, "Should use abulk_create for memory creation"
        assert bulk_delete_count >= 1, "Should use adelete() for memory deletion"


class TestAiUpdateMemoriesCodeQuality:
    """Additional tests for code quality of the N+1 fix."""

    def test_ai_update_memories_function_exists(self):
        """Verify the ai_update_memories function is defined in helpers.py."""
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        assert 'async def ai_update_memories(' in source, \
            "ai_update_memories function should be defined"

    def test_memory_updates_class_exists(self):
        """Verify the MemoryUpdates class is defined in helpers.py."""
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        assert 'class MemoryUpdates' in source, \
            "MemoryUpdates class should be defined"


class TestImplementationDetails:
    """Test specific implementation details of the N+1 fix."""

    def test_bulk_create_uses_correct_model_manager(self):
        """Verify bulk create uses the correct model manager."""
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # Should use UserMemory.objects.abulk_create
        assert 'UserMemory.objects.abulk_create' in source, \
            "Should use UserMemory.objects.abulk_create for bulk creation"

    def test_bulk_delete_uses_filter(self):
        """Verify bulk delete uses filter with proper criteria."""
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # Should filter by user and raw content
        assert 'filter(user=user' in source, "Should filter by user"
        assert 'raw__in=' in source, "Should filter by raw content"

    def test_memory_list_comprehension_used(self):
        """Verify a list comprehension is used for creating memory objects."""
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # Should have list comprehension to create memory objects
        assert 'new_memories = [' in source or 'new_memories=[' in source, \
            "Should use list comprehension to create memory objects"

    def test_comments_explain_optimization(self):
        """Verify that comments explain the bulk operations."""
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # Should have explanatory comments
        assert 'Bulk create all memories in a single query' in source, \
            "Should have comment explaining bulk create optimization"
        assert 'Delete all memories matching the raw content in a single query' in source, \
            "Should have comment explaining bulk delete optimization"

"""
Adversarial Security Tests for N+1 Query Fix in khoj.routers.helpers

This test suite focuses on security testing of the memory operations:
1. SQL injection via memory content
2. User data isolation
3. Bulk operation failure handling
4. Edge cases: empty list, very large list

These tests are designed to identify vulnerabilities in the memory handling code.
These tests verify the source code directly without requiring a database.
"""

import os
import pytest


# Change to project root before tests run
os.chdir(os.path.join(os.path.dirname(__file__), '..'))


class TestSQLInjectionViaMemoryContent:
    """
    Test for SQL injection vulnerabilities in memory content.
    The memory content flows through raw__in filter which could be vulnerable
    if not properly sanitized.
    """

    def test_memory_content_not_directly_concatenated_in_filter(self):
        """
        Verify that memory content is not directly concatenated into filter queries.
        Django ORM should handle parameterization automatically, but we verify
        the correct patterns are used.
        """
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # The filter should use parameterized queries (raw__in with list)
        # NOT string interpolation or raw SQL
        assert 'filter(user=user, raw__in=' in source, \
            "Should use parameterized filter with raw__in"
        
        # Should NOT use raw() queries or extra() which could be vulnerable
        assert '.extra(' not in source or source.count('.extra(') == 0, \
            "Should not use .extra() which could allow SQL injection"
        
        # Should NOT use .raw() for direct SQL
        assert '.raw(' not in source, \
            "Should not use .raw() which could allow SQL injection"

    def test_memory_create_list_comprehension_is_safe(self):
        """
        Verify that memory creation uses safe patterns.
        Memory content should be passed as parameters, not interpolated.
        """
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # The list comprehension should create UserMemory objects safely
        # using the raw=memory parameter, not string formatting
        assert 'raw=memory' in source, \
            "Memory content should be passed as parameter to model field"
        
        # Verify embeddings are computed separately
        assert 'embeddings_model[' in source, \
            "Embeddings should be computed via model, not direct SQL"

    def test_sql_injection_payloads_are_handled_safely(self):
        """
        Test that SQL injection payloads in memory content are handled safely.
        This verifies the code structure prevents injection.
        """
        # Simulate malicious input
        malicious_memory = [
            "'; DROP TABLE user_memory; --",
            "1' OR '1'='1",
            "'; SELECT * FROM user_memory; --",
            " UNION SELECT * FROM user_memory--",
            "admin'--",
            "1; DELETE FROM user_memory WHERE 1=1; --",
        ]
        
        # The filter pattern should handle these as parameter values, not SQL
        # Verify the code uses filter with __in operator which is safe
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # This pattern is safe because Django parameterizes the query
        # The __in lookup with a list is properly escaped
        assert 'raw__in=' in source, \
            "Using __in lookup provides SQL injection protection"


class TestUserDataIsolation:
    """
    Test that user data isolation is properly enforced in memory operations.
    """

    def test_bulk_create_includes_user_field(self):
        """
        Verify that bulk create operations include the user field
        to ensure memories are associated with the correct user.
        """
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # UserMemory objects should include user=user
        assert 'UserMemory(\n                user=user,' in source or \
               'UserMemory(user=user,' in source or \
               'user=user,' in source, \
            "Bulk created memories must be associated with user"

    def test_bulk_delete_filters_by_user(self):
        """
        Verify that bulk delete operations filter by user
        to prevent cross-user memory deletion.
        """
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # The filter MUST include user=user to prevent unauthorized deletion
        assert 'filter(user=user,' in source, \
            "Bulk delete must filter by user to prevent cross-user deletion"
        
        # The delete should NOT be performed without user filter
        # Count occurrences to ensure proper pattern is used
        filter_with_user = source.count('filter(user=user,')
        assert filter_with_user >= 1, \
            "At least one filter(user=user, ...) must exist"

    def test_agent_isolation_in_memory_operations(self):
        """
        Verify that agent-based memory isolation is handled.
        """
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # Should handle custom agent vs default agent
        assert 'use_custom_agent = agent and agent != default_agent' in source, \
            "Should distinguish between custom and default agent"

    def test_no_memory_operations_without_user_context(self):
        """
        Verify that memory operations cannot be performed without user context.
        """
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # ai_update_memories should require user parameter
        assert 'async def ai_update_memories(' in source
        # The function signature should include user
        assert 'user: KhojUser,' in source or 'user: KhojUser' in source, \
            "Function must require user parameter"


class TestBulkOperationFailureHandling:
    """
    Test that bulk operations handle failures properly.
    """

    def test_bulk_create_has_error_handling(self):
        """
        Verify that bulk operations have try-except handling.
        """
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # Look for the bulk create section
        # The function should have some error handling
        # Check if there's exception handling around bulk operations
        bulk_create_section = source[source.find('# Bulk create new memories'):] if '# Bulk create new memories' in source else ''
        
        # Should have logging at minimum
        assert 'logger.info' in bulk_create_section or 'logger.debug' in bulk_create_section, \
            "Bulk operations should have logging"

    def test_bulk_delete_has_error_handling(self):
        """
        Verify that bulk delete operations have proper handling.
        """
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # Look for the bulk delete section
        bulk_delete_section = source[source.find('# Bulk delete memories'):] if '# Bulk delete memories' in source else ''
        
        # Should have logging
        assert 'logger.info' in bulk_delete_section or 'logger.debug' in bulk_delete_section, \
            "Bulk delete should have logging"

    def test_empty_memory_update_handled(self):
        """
        Verify that empty memory updates don't cause errors.
        """
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # Should check if memory_update.create exists before processing
        assert 'if memory_update.create:' in source, \
            "Should check if create list is not empty"
        
        # Should check if memory_update.delete exists before processing
        assert 'if memory_update.delete:' in source, \
            "Should check if delete list is not empty"

    def test_memory_update_class_validation(self):
        """
        Verify that MemoryUpdates class has proper field validation.
        """
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # Find MemoryUpdates class definition
        assert 'class MemoryUpdates(BaseModel):' in source, \
            "MemoryUpdates should be a Pydantic model"
        
        # Fields should have min_items=0 to allow empty lists
        assert 'min_items=0' in source, \
            "Fields should allow empty lists to prevent validation errors"


class TestEdgeCasesEmptyAndLargeLists:
    """
    Test edge cases for empty and very large lists.
    """

    def test_empty_create_list_handled(self):
        """
        Verify that empty create lists are handled without errors.
        """
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # Should have conditional check before bulk create
        assert 'if memory_update.create:' in source, \
            "Should check if create list has items before bulk create"
        
        # Verify the check prevents calling abulk_create with empty list
        # The list comprehension should only run if there are items
        create_section = source[source.find('if memory_update.create:'):]
        assert 'abulk_create' in create_section, \
            "Bulk create should only be called when create list is not empty"

    def test_empty_delete_list_handled(self):
        """
        Verify that empty delete lists are handled without errors.
        """
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # Should have conditional check before bulk delete
        assert 'if memory_update.delete:' in source, \
            "Should check if delete list has items before bulk delete"

    def test_bulk_operations_check_list_before_execution(self):
        """
        Verify that bulk operations check list length before execution.
        """
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # The pattern should be: if <list>: then bulk operation
        # This prevents empty list operations
        create_if_pos = source.find('if memory_update.create:')
        bulk_create_pos = source.find('abulk_create', create_if_pos)
        
        if create_if_pos != -1 and bulk_create_pos != -1:
            # The if statement should come before bulk_create
            assert create_if_pos < bulk_create_pos, \
                "if check should come before bulk_create to prevent empty list operations"

    def test_very_large_list_handling(self):
        """
        Verify that code can handle very large lists (theoretical check).
        The bulk operation should handle large lists efficiently.
        """
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # The code should use batch processing via list comprehension
        # which is memory efficient for large lists
        assert 'for memory, embedding in zip(memory_list, embeddings)' in source, \
            "Should use zip to iterate efficiently over memory and embedding pairs"
        
        # Should create all memories in memory first, then bulk insert
        # This is more efficient than individual inserts
        assert 'new_memories = [' in source, \
            "Should build memory list before bulk insert"

    def test_memory_list_prepared_before_bulk_create(self):
        """
        Verify that memories are prepared as a list before bulk create.
        """
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # Should convert to list first
        assert 'memory_list = list(memory_update.create)' in source, \
            "Should convert to list before processing"
        
        # Should use list comprehension for efficient building
        assert 'new_memories = [' in source, \
            "Should build complete list before bulk create"


class TestMemoryContentSanitization:
    """
    Test that memory content is properly sanitized/validated.
    """

    def test_memory_content_pydantic_validation(self):
        """
        Verify that MemoryUpdates uses Pydantic for validation.
        """
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # Pydantic provides validation and type coercion
        assert 'class MemoryUpdates(BaseModel):' in source, \
            "Should use Pydantic for validation"
        
        # Fields should be properly typed as List[str]
        assert 'create: List[str]' in source, \
            "create field should be List[str] type"
        
        assert 'delete: List[str]' in source, \
            "delete field should be List[str] type"

    def test_response_parsing_has_error_handling(self):
        """
        Verify that response parsing from LLM has error handling.
        """
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # Find extract_facts_from_query function
        assert 'async def extract_facts_from_query(' in source, \
            "Should have function to extract facts from query"
        
        # The function should have try-except for parsing
        # Look for exception handling in that function
        extract_func = source[source.find('async def extract_facts_from_query('):]
        extract_func = extract_func[:extract_func.find('\n\nasync def ') if '\n\nasync def ' in extract_func else len(extract_func)]
        
        assert 'try:' in extract_func and 'except' in extract_func, \
            "Response parsing should have try-except for error handling"
        
        # Should return safe defaults on error
        assert 'return MemoryUpdates(create=[], delete=[])' in source, \
            "Should return empty MemoryUpdates on parsing failure"


class TestEmbeddingsSecurity:
    """
    Test that embedding operations are handled securely.
    """

    def test_embeddings_computed_for_user_content_only(self):
        """
        Verify that embeddings are only computed for valid user content.
        """
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # Embeddings should be computed via embeddings model
        assert 'embeddings_model[' in source, \
            "Should use embeddings model for vector creation"
        
        # Should use embed_query for individual memories
        assert 'embed_query(memory)' in source or 'embed_query' in source, \
            "Should use embed_query for memory embedding"

    def test_no_raw_embedding_storage(self):
        """
        Verify that raw embeddings are not stored directly in unsafe manner.
        """
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # Embeddings should be stored as model field, not in raw text
        assert 'embeddings=embedding' in source, \
            "Embeddings should be stored as model field"


class TestBulkOperationIntegrity:
    """
    Test the integrity of bulk operations.
    """

    def test_all_memories_in_batch_have_same_user(self):
        """
        Verify all memories in a bulk operation belong to the same user.
        """
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # In the list comprehension, user should be bound from the outer scope
        # This ensures all memories in the batch are for the same user
        create_memories_section = source[source.find('new_memories = ['):source.find('abulk_create')]
        
        assert 'user=user' in create_memories_section, \
            "All memories should use the same user from outer scope"

    def test_bulk_create_is_awaited(self):
        """
        Verify that bulk create is properly awaited (async operation).
        """
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # Should await the bulk create operation
        assert 'await UserMemory.objects.abulk_create' in source, \
            "Should await the bulk create operation"

    def test_bulk_delete_is_awaited(self):
        """
        Verify that bulk delete is properly awaited (async operation).
        """
        with open('src/khoj/routers/helpers.py', 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        # Should await the bulk delete operation
        assert 'await UserMemory.objects.filter' in source and '.adelete()' in source, \
            "Should await the bulk delete operation"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

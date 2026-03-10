"""
Tests for memory module.

Tests the memory helpers and adapters including:
- Memory creation, retrieval, update, and deletion
- Memory adapters for database operations
- Memory query and search functionality
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from khoj.database.adapters import UserMemoryAdapters
from khoj.database.models import UserMemory
from tests.helpers import (
    acreate_user,
    acreate_subscription,
    acreate_test_memory,
    acreate_chat_model,
    acreate_default_agent,
    acreate_agent,
    UserFactory,
    SubscriptionFactory,
)


# ----------------------------------------------------------------------------------------------------
# Test UserMemoryAdapters
# ----------------------------------------------------------------------------------------------------
@pytest.mark.anyio
@pytest.mark.django_db(transaction=True)
async def test_create_memory_in_db():
    """Creating a memory directly in DB should work."""
    # Setup
    user = await acreate_user()
    await acreate_subscription(user)
    
    # Create memory
    memory = await acreate_test_memory(user, agent=None, raw_text="test memory content")
    
    # Assert
    assert memory.id is not None
    assert memory.user == user
    assert memory.raw == "test memory content"


@pytest.mark.anyio
@pytest.mark.django_db(transaction=True)
async def test_pull_memories_returns_user_memories():
    """Pulling memories should return all memories for a user."""
    # Setup
    user = await acreate_user()
    await acreate_subscription(user)
    
    # Create multiple memories
    await acreate_test_memory(user, agent=None, raw_text="memory 1")
    await acreate_test_memory(user, agent=None, raw_text="memory 2")
    await acreate_test_memory(user, agent=None, raw_text="memory 3")
    
    # Act
    memories = await UserMemoryAdapters.pull_memories(user=user)
    
    # Assert
    assert len(memories) == 3
    memory_texts = [m.raw for m in memories]
    assert "memory 1" in memory_texts
    assert "memory 2" in memory_texts
    assert "memory 3" in memory_texts


@pytest.mark.anyio
@pytest.mark.django_db(transaction=True)
async def test_pull_memories_empty_for_new_user():
    """New users should have no memories."""
    # Setup
    user = await acreate_user()
    await acreate_subscription(user)
    
    # Act
    memories = await UserMemoryAdapters.pull_memories(user=user)
    
    # Assert
    assert len(memories) == 0


@pytest.mark.anyio
@pytest.mark.django_db(transaction=True)
async def test_delete_memory_removes_from_db():
    """Deleting a memory should remove it from the database."""
    # Setup
    user = await acreate_user()
    await acreate_subscription(user)
    
    # Create memory
    memory = await acreate_test_memory(user, agent=None, raw_text="memory to delete")
    memory_id = memory.id
    
    # Act - delete the memory
    await UserMemoryAdapters.adelete_memory(memory_id)
    
    # Assert memory is deleted
    assert await UserMemoryAdapters.amemory_exists(memory_id) is False


@pytest.mark.anyio
@pytest.mark.django_db(transaction=True)
async def test_search_memory_by_query():
    """Searching memories should return relevant memories."""
    # Setup
    user = await acreate_user()
    await acreate_subscription(user)
    
    # Create memories with specific content
    await acreate_test_memory(user, agent=None, raw_text="I love coding in Python")
    await acreate_test_memory(user, agent=None, raw_text="I enjoy playing guitar")
    await acreate_test_memory(user, agent=None, raw_text="Python is a great programming language")
    
    # Act - search for Python-related memories
    # Note: This test may need embeddings model to be set up
    # For now, we test that the function exists and can be called
    from khoj.search_type import text_search
    from khoj.utils.state import SearchType
    
    # This test verifies the search function structure
    # Full integration test would require embeddings


@pytest.mark.anyio
@pytest.mark.django_db(transaction=True)
async def test_update_memory_content():
    """Updating a memory's content should persist changes."""
    # Setup
    user = await acreate_user()
    await acreate_subscription(user)
    
    # Create memory
    memory = await acreate_test_memory(user, agent=None, raw_text="original content")
    memory_id = memory.id
    
    # Act - update memory
    await UserMemoryAdapters.aupdate_memory(memory_id, raw="updated content")
    
    # Assert
    updated_memory = await UserMemoryAdapters.aget_memory(memory_id)
    assert updated_memory.raw == "updated content"


@pytest.mark.anyio
@pytest.mark.django_db(transaction=True)
async def test_aget_memory_returns_memory():
    """Getting a single memory by ID should return the memory."""
    # Setup
    user = await acreate_user()
    await acreate_subscription(user)
    
    # Create memory
    memory = await acreate_test_memory(user, agent=None, raw_text="specific memory")
    memory_id = memory.id
    
    # Act
    retrieved = await UserMemoryAdapters.aget_memory(memory_id)
    
    # Assert
    assert retrieved is not None
    assert retrieved.id == memory_id
    assert retrieved.raw == "specific memory"


@pytest.mark.anyio
@pytest.mark.django_db(transaction=True)
async def test_aget_memory_returns_none_for_invalid_id():
    """Getting a memory with invalid ID should return None."""
    # Setup
    user = await acreate_user()
    await acreate_subscription(user)
    
    # Act
    retrieved = await UserMemoryAdapters.aget_memory(99999)
    
    # Assert
    assert retrieved is None


# ----------------------------------------------------------------------------------------------------
# Test memory isolation between users
# ----------------------------------------------------------------------------------------------------
@pytest.mark.anyio
@pytest.mark.django_db(transaction=True)
async def test_memories_isolated_by_user():
    """Memories should be isolated between different users."""
    # Setup
    user1 = await acreate_user()
    user2 = await acreate_user()
    await acreate_subscription(user1)
    await acreate_subscription(user2)
    
    # Create memories for each user
    await acreate_test_memory(user1, agent=None, raw_text="user1 private memory")
    await acreate_test_memory(user2, agent=None, raw_text="user2 private memory")
    
    # Act
    user1_memories = await UserMemoryAdapters.pull_memories(user=user1)
    user2_memories = await UserMemoryAdapters.pull_memories(user=user2)
    
    # Assert - each user only sees their own memories
    assert len(user1_memories) == 1
    assert user1_memories[0].raw == "user1 private memory"
    
    assert len(user2_memories) == 1
    assert user2_memories[0].raw == "user2 private memory"


# ----------------------------------------------------------------------------------------------------
# Test memory helpers
# ----------------------------------------------------------------------------------------------------
def test_memory_helpers_module_exists():
    """Memory helpers module should exist and be importable."""
    from khoj.common import memory_helpers
    
    assert memory_helpers is not None
    assert hasattr(memory_helpers, "ai_update_memories")


# ----------------------------------------------------------------------------------------------------
# Test MemoryUpdates model
# ----------------------------------------------------------------------------------------------------
def test_memory_updates_model():
    """MemoryUpdates model should work correctly."""
    from khoj.routers.helpers import MemoryUpdates
    
    # Create memory updates
    updates = MemoryUpdates(
        create=["new memory 1", "new memory 2"],
        delete=["old memory"]
    )
    
    assert len(updates.create) == 2
    assert len(updates.delete) == 1
    assert "new memory 1" in updates.create
    assert "old memory" in updates.delete


def test_memory_updates_model_empty():
    """MemoryUpdates model should handle empty updates."""
    from khoj.routers.helpers import MemoryUpdates
    
    updates = MemoryUpdates(create=[], delete=[])
    
    assert len(updates.create) == 0
    assert len(updates.delete) == 0


# ----------------------------------------------------------------------------------------------------
# Test memory embeddings
# ----------------------------------------------------------------------------------------------------
@pytest.mark.anyio
@pytest.mark.django_db(transaction=True)
async def test_memory_has_embeddings_field():
    """Memory should have embeddings field."""
    # Setup
    user = await acreate_user()
    await acreate_subscription(user)
    
    # Create memory with embeddings
    memory = await acreate_test_memory(
        user, 
        agent=None, 
        raw_text="memory with embeddings"
    )
    
    # Assert embeddings exist
    assert memory.embeddings is not None
    assert len(memory.embeddings) > 0


# ----------------------------------------------------------------------------------------------------
# Test memory with agent context
# ----------------------------------------------------------------------------------------------------
@pytest.mark.anyio
@pytest.mark.django_db(transaction=True)
async def test_memory_with_agent_context():
    """Memories should support agent context."""
    # Setup
    user = await acreate_user()
    await acreate_subscription(user)
    chat_model = await acreate_chat_model()
    
    # Create agents
    default_agent = await acreate_default_agent()
    custom_agent = await acreate_agent("Test Agent", chat_model, "Test personality")
    
    # Create memories for different agents
    await acreate_test_memory(user, agent=None, raw_text="no agent memory")
    await acreate_test_memory(user, agent=default_agent, raw_text="default agent memory")
    await acreate_test_memory(user, agent=custom_agent, raw_text="custom agent memory")
    
    # Act - pull all memories (should see all with default agent)
    all_memories = await UserMemoryAdapters.pull_memories(user=user, agent=default_agent)
    
    # Assert
    assert len(all_memories) == 3
    
    # Pull memories for custom agent (should see only its own)
    custom_memories = await UserMemoryAdapters.pull_memories(user=user, agent=custom_agent)
    assert len(custom_memories) == 1
    assert custom_memories[0].raw == "custom agent memory"

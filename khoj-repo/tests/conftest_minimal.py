"""
Minimal conftest for running hybrid search tests without database.
This provides mock fixtures that don't require PostgreSQL.
"""

import pytest
from unittest.mock import MagicMock


@pytest.fixture
def default_user():
    """Return a mock user for testing."""
    user = MagicMock()
    user.id = 1
    user.username = "test_user"
    user.email = "test@example.com"
    return user

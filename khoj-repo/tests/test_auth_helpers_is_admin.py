"""
Tests for is_admin field in get_user_config function.

Tests the is_admin field logic in auth_helpers.py:
- Line 62: Non-detailed response
- Line 150: Detailed response (uses same logic as line 62)

Test cases:
1. is_admin=True when user.is_staff=True
2. is_admin=True when user.is_superuser=True
3. is_admin=True when both is_staff=True and is_superuser=True
4. is_admin=False when user is regular (no staff/superuser)
5. is_admin=False when user is None (edge case)

Note: These tests use mocking to avoid requiring database access.
"""

import pytest
from unittest.mock import MagicMock, patch

from khoj.routers.auth_helpers import get_user_config


def create_mock_request():
    """Create a mock request object for testing."""
    request = MagicMock()
    request.url = MagicMock()
    request.url.path = "/api/config"
    request.session = {}
    return request


def create_mock_user(is_staff=False, is_superuser=False):
    """Create a mock user object with specified attributes."""
    user = MagicMock()
    user.is_staff = is_staff
    user.is_superuser = is_superuser
    user.username = "testuser"
    user.email = "test@example.com"
    return user


# ----------------------------------------------------------------------------------------------------
# Test is_admin field - Non-detailed response (is_detailed=False)
# Tests both line 62 and line 150 since they use identical logic
# ----------------------------------------------------------------------------------------------------
def test_is_admin_true_when_is_staff_true():
    """is_admin should be True when user.is_staff=True."""
    user = create_mock_user(is_staff=True, is_superuser=False)
    request = create_mock_request()

    with patch('khoj.routers.auth_helpers.has_required_scope', return_value=False):
        with patch('khoj.routers.auth_helpers.EntryAdapters.user_has_entries', return_value=False):
            config = get_user_config(user, request, is_detailed=False)

    assert config["is_admin"] is True


def test_is_admin_true_when_is_superuser_true():
    """is_admin should be True when user.is_superuser=True."""
    user = create_mock_user(is_staff=False, is_superuser=True)
    request = create_mock_request()

    with patch('khoj.routers.auth_helpers.has_required_scope', return_value=False):
        with patch('khoj.routers.auth_helpers.EntryAdapters.user_has_entries', return_value=False):
            config = get_user_config(user, request, is_detailed=False)

    assert config["is_admin"] is True


def test_is_admin_true_when_both_is_staff_and_is_superuser():
    """is_admin should be True when both is_staff=True and is_superuser=True."""
    user = create_mock_user(is_staff=True, is_superuser=True)
    request = create_mock_request()

    with patch('khoj.routers.auth_helpers.has_required_scope', return_value=False):
        with patch('khoj.routers.auth_helpers.EntryAdapters.user_has_entries', return_value=False):
            config = get_user_config(user, request, is_detailed=False)

    assert config["is_admin"] is True


def test_is_admin_false_when_regular_user():
    """is_admin should be False when user is regular (no staff/superuser)."""
    user = create_mock_user(is_staff=False, is_superuser=False)
    request = create_mock_request()

    with patch('khoj.routers.auth_helpers.has_required_scope', return_value=False):
        with patch('khoj.routers.auth_helpers.EntryAdapters.user_has_entries', return_value=False):
            config = get_user_config(user, request, is_detailed=False)

    assert config["is_admin"] is False


def test_is_admin_false_when_user_is_none():
    """is_admin should be False when user is None."""
    request = create_mock_request()

    with patch('khoj.routers.auth_helpers.has_required_scope', return_value=False):
        config = get_user_config(None, request, is_detailed=False)

    assert config["is_admin"] is False

"""
Tests for authentication module.

Tests the auth router endpoints including:
- Login/Logout functionality
- Token generation and management
- Magic link authentication
- OAuth redirect handling
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from starlette.requests import Request
from starlette.responses import Response

from khoj.database.models import KhojUser, KhojApiUser
from tests.helpers import UserFactory, SubscriptionFactory


# ----------------------------------------------------------------------------------------------------
# Test logout endpoint
# ----------------------------------------------------------------------------------------------------
@pytest.mark.django_db
def test_logout_clears_session():
    """Logout should clear the user session."""
    from khoj.routers.auth import logout
    
    # Create mock request with session
    mock_request = MagicMock()
    mock_request.session = {"user": {"email": "test@example.com"}}
    
    # Call logout
    response = logout(mock_request)
    
    # Assert session is cleared
    mock_request.session.pop.assert_called_once_with("user", None)
    assert isinstance(response, Response)


# ----------------------------------------------------------------------------------------------------
# Test token generation
# ----------------------------------------------------------------------------------------------------
@pytest.mark.django_db
@pytest.mark.anyio
async def test_generate_token_creates_new_token():
    """Token generation should create a new API token for the user."""
    from khoj.routers.auth import generate_token
    
    # Setup
    user = UserFactory()
    SubscriptionFactory(user=user)
    
    mock_request = MagicMock()
    mock_request.user = MagicMock()
    mock_request.user.object = user
    mock_request.user.is_authenticated = True
    
    # Call generate_token
    response = await generate_token(mock_request, token_name="test-token")
    
    # Assert token was created
    assert "token" in response
    assert "name" in response
    assert response["name"] == "test-token"
    
    # Verify token exists in database
    tokens = KhojApiUser.objects.filter(user=user)
    assert tokens.count() == 1


@pytest.mark.django_db
@pytest.mark.anyio
async def test_generate_token_without_name_uses_default():
    """Token generation without a name should use default naming."""
    from khoj.routers.auth import generate_token
    
    # Setup
    user = UserFactory()
    SubscriptionFactory(user=user)
    
    mock_request = MagicMock()
    mock_request.user = MagicMock()
    mock_request.user.object = user
    mock_request.user.is_authenticated = True
    
    # Call generate_token without name
    response = await generate_token(mock_request, token_name=None)
    
    # Assert token was created
    assert "token" in response
    assert "name" in response


# ----------------------------------------------------------------------------------------------------
# Test get tokens
# ----------------------------------------------------------------------------------------------------
@pytest.mark.django_db
@pytest.mark.anyio
async def test_get_tokens_returns_user_tokens():
    """Get tokens should return all API tokens for the user."""
    from khoj.routers.auth import get_tokens
    
    # Setup
    user = UserFactory()
    SubscriptionFactory(user=user)
    
    # Create API tokens
    api_token1 = KhojApiUser.objects.create(user=user, name="token1", token="secret1")
    api_token2 = KhojApiUser.objects.create(user=user, name="token2", token="secret2")
    
    mock_request = MagicMock()
    mock_request.user = MagicMock()
    mock_request.user.object = user
    mock_request.user.is_authenticated = True
    
    # Call get_tokens
    response = get_tokens(mock_request)
    
    # Assert tokens are returned
    assert len(response) == 2
    token_names = [t["name"] for t in response]
    assert "token1" in token_names
    assert "token2" in token_names


# ----------------------------------------------------------------------------------------------------
# Test delete token
# ----------------------------------------------------------------------------------------------------
@pytest.mark.django_db
@pytest.mark.anyio
async def test_delete_token_removes_token():
    """Delete token should remove the specified API token."""
    from khoj.routers.auth import delete_token
    
    # Setup
    user = UserFactory()
    SubscriptionFactory(user=user)
    
    # Create API token
    api_token = KhojApiUser.objects.create(user=user, name="token1", token="secret1")
    
    mock_request = MagicMock()
    mock_request.user = MagicMock()
    mock_request.user.object = user
    mock_request.user.is_authenticated = True
    
    # Call delete_token
    response = await delete_token(mock_request, token="secret1")
    
    # Assert token was deleted
    assert KhojApiUser.objects.filter(user=user, token="secret1").count() == 0


# ----------------------------------------------------------------------------------------------------
# Test OAuth metadata endpoint
# ----------------------------------------------------------------------------------------------------
@pytest.mark.django_db
def test_oauth_metadata_returns_google_config():
    """OAuth metadata should return Google OAuth configuration."""
    from khoj.routers.auth import oauth_metadata
    
    mock_request = MagicMock()
    mock_request.app = MagicMock()
    mock_request.app.url_path_for = MagicMock(return_value="/auth/redirect")
    
    with patch.dict("os.environ", {"GOOGLE_CLIENT_ID": "test-client-id"}):
        response = oauth_metadata(mock_request)
    
    assert "google" in response
    assert response["google"]["client_id"] == "test-client-id"


# ----------------------------------------------------------------------------------------------------
# Test auth router is properly configured
# ----------------------------------------------------------------------------------------------------
def test_auth_router_exists():
    """Auth router should be properly configured."""
    from khoj.routers.auth import auth_router
    
    assert auth_router is not None
    assert hasattr(auth_router, "routes")


def test_auth_router_has_login_endpoint():
    """Auth router should have login endpoint."""
    from khoj.routers.auth import auth_router
    
    # Check routes exist
    route_paths = [route.path for route in auth_router.routes]
    assert "/login" in route_paths or any("login" in path for path in route_paths)


def test_auth_router_has_logout_endpoint():
    """Auth router should have logout endpoint."""
    from khoj.routers.auth import auth_router
    
    # Check routes exist
    route_paths = [route.path for route in auth_router.routes]
    assert "/logout" in route_paths or any("logout" in path for path in route_paths)

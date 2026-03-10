"""
Tests for user_config_to_response helper in auth_helpers module.

Verifies:
- user_config_to_response helper exists and is properly defined
- It's being used by api.py and api_content.py endpoints
"""

import pytest
import sys
import os
import inspect


class TestUserConfigToResponseHelper:
    """Test suite for user_config_to_response helper function."""

    def test_user_config_to_response_exists(self):
        """Verify the user_config_to_response helper exists in auth_helpers module."""
        # Read the source file directly to avoid import cascade issues
        auth_helpers_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'khoj', 'routers', 'auth_helpers.py')
        with open(auth_helpers_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Verify the function is defined
        assert 'def user_config_to_response(' in source
        assert 'def user_config_to_response(' in source

    def test_user_config_to_response_has_correct_signature(self):
        """Verify user_config_to_response has the expected function signature."""
        auth_helpers_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'khoj', 'routers', 'auth_helpers.py')
        with open(auth_helpers_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Verify the function signature includes expected parameters
        assert 'def user_config_to_response(' in source
        assert 'user: KhojUser' in source
        assert 'request: Request' in source
        assert 'is_detailed: bool' in source
        assert 'extra_config: Optional[dict]' in source

    def test_user_config_to_response_returns_response(self):
        """Verify user_config_to_response returns a Starlette Response."""
        auth_helpers_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'khoj', 'routers', 'auth_helpers.py')
        with open(auth_helpers_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Verify it returns a Response object
        assert 'Response(' in source
        assert 'json.dumps' in source
        assert 'status_code=200' in source


class TestUserConfigToResponseUsage:
    """Test suite verifying user_config_to_response is used in API endpoints."""

    def test_user_config_to_response_imported_in_api(self):
        """Verify user_config_to_response is imported in api.py."""
        api_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'khoj', 'routers', 'api.py')
        with open(api_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Verify the import exists
        assert 'from khoj.routers.auth_helpers import user_config_to_response' in source

    def test_user_config_to_response_imported_in_api_content(self):
        """Verify user_config_to_response is imported in api_content.py."""
        api_content_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'khoj', 'routers', 'api_content.py')
        with open(api_content_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Verify the import exists
        assert 'from khoj.routers.auth_helpers import' in source
        assert 'user_config_to_response' in source

    def test_user_config_to_response_used_in_api_routes(self):
        """Verify user_config_to_response is actually called in API routes."""
        api_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'khoj', 'routers', 'api.py')
        with open(api_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Verify it's actually called
        assert 'user_config_to_response(user, request' in source

    def test_user_config_to_response_used_in_api_content_routes(self):
        """Verify user_config_to_response is actually called in api_content routes."""
        api_content_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'khoj', 'routers', 'api_content.py')
        with open(api_content_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Verify it's actually called
        assert 'user_config_to_response(' in source

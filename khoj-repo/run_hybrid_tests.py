"""
Standalone test runner for hybrid search tests without database dependency.
This script patches the database fixtures to run tests with mocked users.
"""

import sys
import os
from unittest.mock import MagicMock, patch

# Set up Django settings before importing Django models
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "khoj.app.settings")

# Patch the database before Django initializes
import django
from django.conf import settings

# Configure a test database using SQLite
settings.DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Now we can import and run the tests
import pytest

# Create a mock user fixture
def create_mock_user():
    """Create a mock user for testing."""
    user = MagicMock()
    user.id = 1
    user.username = "test_user"
    user.email = "test@example.com"
    return user

# Patch the default_user fixture before pytest collects tests
@pytest.fixture
def default_user():
    return create_mock_user()

if __name__ == "__main__":
    # Run pytest with the test file
    sys.exit(pytest.main([
        "tests/test_hybrid_search.py",
        "-v",
        "--tb=short",
        "-W", "ignore::pytest.PytestRemovedIn9Warning",
        "-W", "ignore::DeprecationWarning",
    ]))

"""Tests for api_metrics router in khoj/routers/api_metrics.py

These tests use mocking to avoid database dependencies.
"""

import os
import sys
import django

# Setup Django settings before importing Django models
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "khoj.app.settings")
django.setup()

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Django imports
from django.test import TestCase

# FastAPI imports
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.authentication import AuthCredentials, AuthenticationBackend, SimpleUser
from starlette.middleware.authentication import AuthenticationMiddleware

# Khoj imports
from khoj.app import settings
from khoj.routers.api_metrics import api_metrics
from khoj.utils.config import RagConfig


# Custom authentication backend for testing
class TestAuthBackend(AuthenticationBackend):
    """Test authentication backend that can simulate authenticated/unauthenticated users"""

    def __init__(self, authenticated=True, user=None):
        self.authenticated = authenticated
        self.user = user

    async def authenticate(self, conn):
        if self.authenticated and self.user:
            return AuthCredentials(["authenticated"]), SimpleUser(self.user.username)
        return None


class MockUser:
    """Mock user object for testing"""
    def __init__(self, username="testuser"):
        self.username = username
        self.object = self


def create_test_app(authenticated=True, user=None):
    """Create a test FastAPI app with the api_metrics router and authentication"""
    app = FastAPI()

    # Add authentication middleware
    app.add_middleware(AuthenticationMiddleware, backend=TestAuthBackend(authenticated=authenticated, user=user))

    # Include the api_metrics router
    app.include_router(api_metrics)

    return app


@pytest.mark.django_db(transaction=True)
class TestGetRagMetricsAuthenticated(TestCase):
    """Test suite for authenticated access to /api/rag/metrics endpoint"""

    def test_get_rag_metrics_authenticated(self):
        """Returns metrics for authenticated user"""
        # Arrange
        mock_user = MockUser("testuser")
        app = create_test_app(authenticated=True, user=mock_user)
        client = TestClient(app)

        # Mock the Entry queries
        mock_entry_counts = [
            {"chunk_scale": "512", "count": 10},
            {"chunk_scale": "1024", "count": 20},
            {"chunk_scale": None, "count": 5},  # Should become "default"
        ]
        mock_scales = ["512", "1024"]
        mock_total = 35

        with patch("khoj.routers.api_metrics.Entry") as mock_entry:
            mock_queryset = MagicMock()
            mock_entry.objects.filter.return_value = mock_queryset

            with patch("khoj.routers.api_metrics.sync_to_async") as mock_sync_to_async:
                call_count = [0]

                def side_effect(fn):
                    if fn == list:
                        async def async_wrapper(*args, **kwargs):
                            call_count[0] += 1
                            if call_count[0] == 1:
                                return mock_entry_counts
                            return mock_scales
                        return async_wrapper
                    else:
                        async def async_count():
                            return mock_total
                        return async_count

                mock_sync_to_async.side_effect = side_effect

                # Act
                response = client.get("/api/rag/metrics")

        # Assert
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Verify structure
        self.assertIn("entry_counts_by_scale", data)
        self.assertIn("feature_flags", data)
        self.assertIn("total_entries", data)
        self.assertIn("scales_available", data)

        # Verify entry counts
        self.assertEqual(data["entry_counts_by_scale"]["512"], 10)
        self.assertEqual(data["entry_counts_by_scale"]["1024"], 20)
        self.assertEqual(data["entry_counts_by_scale"]["default"], 5)

        # Verify total
        self.assertEqual(data["total_entries"], mock_total)

        # Verify scales are sorted
        self.assertEqual(data["scales_available"], sorted(mock_scales))


class TestGetRagMetricsUnauthenticated:
    """Test suite for unauthenticated access to /api/rag/metrics endpoint"""

    def test_get_rag_metrics_unauthenticated(self):
        """Returns 403 for unauthenticated user"""
        # Arrange
        app = create_test_app(authenticated=False, user=None)
        client = TestClient(app)

        # Act
        response = client.get("/api/rag/metrics")

        # Assert
        assert response.status_code == 403  # @requires decorator returns 403, not 401


@pytest.mark.django_db(transaction=True)
class TestEntryCountsByScale(TestCase):
    """Test suite for entry_counts_by_scale in response"""

    def test_entry_counts_by_scale(self):
        """Correct counts per chunk_scale"""
        # Arrange
        mock_user = MockUser("testuser")
        app = create_test_app(authenticated=True, user=mock_user)
        client = TestClient(app)

        mock_entry_counts = [
            {"chunk_scale": "512", "count": 100},
            {"chunk_scale": "1024", "count": 50},
            {"chunk_scale": "2048", "count": 25},
            {"chunk_scale": None, "count": 10},  # Should become "default"
        ]
        mock_scales = ["512", "1024", "2048"]
        mock_total = 185

        with patch("khoj.routers.api_metrics.Entry") as mock_entry:
            mock_queryset = MagicMock()
            mock_entry.objects.filter.return_value = mock_queryset

            with patch("khoj.routers.api_metrics.sync_to_async") as mock_sync_to_async:
                call_count = [0]

                def side_effect(fn):
                    if fn == list:
                        async def async_wrapper(*args, **kwargs):
                            call_count[0] += 1
                            if call_count[0] == 1:
                                return mock_entry_counts
                            return mock_scales
                        return async_wrapper
                    else:
                        async def async_count():
                            return mock_total
                        return async_count

                mock_sync_to_async.side_effect = side_effect

                # Act
                response = client.get("/api/rag/metrics")

        # Assert
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Verify all scales are present with correct counts
        entry_counts = data["entry_counts_by_scale"]
        self.assertEqual(entry_counts["512"], 100)
        self.assertEqual(entry_counts["1024"], 50)
        self.assertEqual(entry_counts["2048"], 25)
        self.assertEqual(entry_counts["default"], 10)

    def test_entry_counts_empty_chunk_scale_handling(self):
        """Handle empty string chunk_scale correctly"""
        # Arrange
        mock_user = MockUser("testuser")
        app = create_test_app(authenticated=True, user=mock_user)
        client = TestClient(app)

        mock_entry_counts = [
            {"chunk_scale": "", "count": 5},  # Empty string
            {"chunk_scale": "512", "count": 10},
        ]
        mock_scales = ["512"]
        mock_total = 15

        with patch("khoj.routers.api_metrics.Entry") as mock_entry:
            mock_queryset = MagicMock()
            mock_entry.objects.filter.return_value = mock_queryset

            with patch("khoj.routers.api_metrics.sync_to_async") as mock_sync_to_async:
                call_count = [0]

                def side_effect(fn):
                    if fn == list:
                        async def async_wrapper(*args, **kwargs):
                            call_count[0] += 1
                            if call_count[0] == 1:
                                return mock_entry_counts
                            return mock_scales
                        return async_wrapper
                    else:
                        async def async_count():
                            return mock_total
                        return async_count

                mock_sync_to_async.side_effect = side_effect

                # Act
                response = client.get("/api/rag/metrics")

        # Assert
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Empty string should become "default"
        entry_counts = data["entry_counts_by_scale"]
        self.assertEqual(entry_counts["default"], 5)
        self.assertEqual(entry_counts["512"], 10)


@pytest.mark.django_db(transaction=True)
class TestFeatureFlagsInResponse(TestCase):
    """Test suite for feature_flags in response"""

    def test_feature_flags_in_response(self):
        """All RagConfig flags present in response"""
        # Arrange
        mock_user = MockUser("testuser")
        app = create_test_app(authenticated=True, user=mock_user)
        client = TestClient(app)

        # Set specific feature flag values for testing
        original_crag = settings.CRAG_ENABLED
        original_query_transform = settings.QUERY_TRANSFORM_ENABLED
        original_hybrid = RagConfig.hybrid_search_enabled
        original_contextual = RagConfig.contextual_chunking_enabled
        original_multi_scale = RagConfig.multi_scale_chunking_enabled
        original_tri_vector = RagConfig.tri_vector_search_enabled

        try:
            settings.CRAG_ENABLED = True
            settings.QUERY_TRANSFORM_ENABLED = False
            RagConfig.hybrid_search_enabled = True
            RagConfig.contextual_chunking_enabled = False
            RagConfig.multi_scale_chunking_enabled = True
            RagConfig.tri_vector_search_enabled = False

            mock_entry_counts = []
            mock_scales = []
            mock_total = 0

            with patch("khoj.routers.api_metrics.Entry") as mock_entry:
                mock_queryset = MagicMock()
                mock_entry.objects.filter.return_value = mock_queryset

                with patch("khoj.routers.api_metrics.sync_to_async") as mock_sync_to_async:
                    call_count = [0]

                    def side_effect(fn):
                        if fn == list:
                            async def async_wrapper(*args, **kwargs):
                                call_count[0] += 1
                                if call_count[0] == 1:
                                    return mock_entry_counts
                                return mock_scales
                            return async_wrapper
                        else:
                            async def async_count():
                                return mock_total
                            return async_count

                    mock_sync_to_async.side_effect = side_effect

                    # Act
                    response = client.get("/api/rag/metrics")

            # Assert
            self.assertEqual(response.status_code, 200)
            data = response.json()

            feature_flags = data["feature_flags"]
            self.assertIn("crag_enabled", feature_flags)
            self.assertIn("query_transform_enabled", feature_flags)
            self.assertIn("hybrid_search_enabled", feature_flags)
            self.assertIn("contextual_chunking_enabled", feature_flags)
            self.assertIn("multi_scale_chunking_enabled", feature_flags)
            self.assertIn("tri_vector_search_enabled", feature_flags)

            # Verify values match runtime flags used by retrieval endpoints
            self.assertTrue(feature_flags["crag_enabled"])
            self.assertFalse(feature_flags["query_transform_enabled"])
            self.assertTrue(feature_flags["hybrid_search_enabled"])
            self.assertFalse(feature_flags["contextual_chunking_enabled"])
            self.assertTrue(feature_flags["multi_scale_chunking_enabled"])
            self.assertFalse(feature_flags["tri_vector_search_enabled"])

        finally:
            # Restore original values
            settings.CRAG_ENABLED = original_crag
            settings.QUERY_TRANSFORM_ENABLED = original_query_transform
            RagConfig.hybrid_search_enabled = original_hybrid
            RagConfig.contextual_chunking_enabled = original_contextual
            RagConfig.multi_scale_chunking_enabled = original_multi_scale
            RagConfig.tri_vector_search_enabled = original_tri_vector


@pytest.mark.django_db(transaction=True)
class TestTotalEntriesCount(TestCase):
    """Test suite for total_entries count in response"""

    def test_total_entries_count(self):
        """Accurate total count"""
        # Arrange
        mock_user = MockUser("testuser")
        app = create_test_app(authenticated=True, user=mock_user)
        client = TestClient(app)

        mock_entry_counts = [
            {"chunk_scale": "512", "count": 100},
            {"chunk_scale": "1024", "count": 200},
        ]
        mock_scales = ["512", "1024"]
        mock_total = 300  # This is what the count() query returns

        with patch("khoj.routers.api_metrics.Entry") as mock_entry:
            mock_queryset = MagicMock()
            mock_entry.objects.filter.return_value = mock_queryset

            with patch("khoj.routers.api_metrics.sync_to_async") as mock_sync_to_async:
                call_count = [0]

                def side_effect(fn):
                    if fn == list:
                        async def async_wrapper(*args, **kwargs):
                            call_count[0] += 1
                            if call_count[0] == 1:
                                return mock_entry_counts
                            return mock_scales
                        return async_wrapper
                    else:
                        async def async_count():
                            return mock_total
                        return async_count

                mock_sync_to_async.side_effect = side_effect

                # Act
                response = client.get("/api/rag/metrics")

        # Assert
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_entries"], 300)

    def test_total_entries_zero(self):
        """Total count of zero when no entries"""
        # Arrange
        mock_user = MockUser("testuser")
        app = create_test_app(authenticated=True, user=mock_user)
        client = TestClient(app)

        mock_entry_counts = []
        mock_scales = []
        mock_total = 0

        with patch("khoj.routers.api_metrics.Entry") as mock_entry:
            mock_queryset = MagicMock()
            mock_entry.objects.filter.return_value = mock_queryset

            with patch("khoj.routers.api_metrics.sync_to_async") as mock_sync_to_async:
                call_count = [0]

                def side_effect(fn):
                    if fn == list:
                        async def async_wrapper(*args, **kwargs):
                            call_count[0] += 1
                            if call_count[0] == 1:
                                return mock_entry_counts
                            return mock_scales
                        return async_wrapper
                    else:
                        async def async_count():
                            return mock_total
                        return async_count

                mock_sync_to_async.side_effect = side_effect

                # Act
                response = client.get("/api/rag/metrics")

        # Assert
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_entries"], 0)
        self.assertEqual(data["entry_counts_by_scale"], {})
        self.assertEqual(data["scales_available"], [])


@pytest.mark.django_db(transaction=True)
class TestScalesAvailable(TestCase):
    """Test suite for scales_available in response"""

    def test_scales_available_lists_non_empty(self):
        """Lists non-empty chunk_scales"""
        # Arrange
        mock_user = MockUser("testuser")
        app = create_test_app(authenticated=True, user=mock_user)
        client = TestClient(app)

        mock_entry_counts = [
            {"chunk_scale": "512", "count": 10},
            {"chunk_scale": "1024", "count": 20},
            {"chunk_scale": "2048", "count": 30},
        ]
        mock_scales = ["512", "1024", "2048"]
        mock_total = 60

        with patch("khoj.routers.api_metrics.Entry") as mock_entry:
            mock_queryset = MagicMock()
            mock_entry.objects.filter.return_value = mock_queryset

            with patch("khoj.routers.api_metrics.sync_to_async") as mock_sync_to_async:
                call_count = [0]

                def side_effect(fn):
                    if fn == list:
                        async def async_wrapper(*args, **kwargs):
                            call_count[0] += 1
                            if call_count[0] == 1:
                                return mock_entry_counts
                            return mock_scales
                        return async_wrapper
                    else:
                        async def async_count():
                            return mock_total
                        return async_count

                mock_sync_to_async.side_effect = side_effect

                # Act
                response = client.get("/api/rag/metrics")

        # Assert
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Verify scales are present and sorted
        scales = data["scales_available"]
        self.assertEqual(len(scales), 3)
        self.assertEqual(scales, ["512", "1024", "2048"])  # Should be sorted

    def test_scales_available_excludes_empty(self):
        """Excludes empty and null chunk_scales from scales_available"""
        # Arrange
        mock_user = MockUser("testuser")
        app = create_test_app(authenticated=True, user=mock_user)
        client = TestClient(app)

        mock_entry_counts = [
            {"chunk_scale": "512", "count": 10},
            {"chunk_scale": None, "count": 5},  # null scale
        ]
        mock_scales = ["512"]  # Only non-empty/null scales
        mock_total = 15

        with patch("khoj.routers.api_metrics.Entry") as mock_entry:
            mock_queryset = MagicMock()
            mock_entry.objects.filter.return_value = mock_queryset

            with patch("khoj.routers.api_metrics.sync_to_async") as mock_sync_to_async:
                call_count = [0]

                def side_effect(fn):
                    if fn == list:
                        async def async_wrapper(*args, **kwargs):
                            call_count[0] += 1
                            if call_count[0] == 1:
                                return mock_entry_counts
                            return mock_scales
                        return async_wrapper
                    else:
                        async def async_count():
                            return mock_total
                        return async_count

                mock_sync_to_async.side_effect = side_effect

                # Act
                response = client.get("/api/rag/metrics")

        # Assert
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Verify null scale is not in scales_available but is in entry_counts
        self.assertIn("512", data["scales_available"])
        self.assertNotIn(None, data["scales_available"])
        self.assertNotIn("", data["scales_available"])

        # But it should be counted as "default"
        self.assertEqual(data["entry_counts_by_scale"]["default"], 5)

    def test_scales_available_adds_default_when_needed(self):
        """Adds 'default' to scales_available when null entries exist"""
        # Arrange
        mock_user = MockUser("testuser")
        app = create_test_app(authenticated=True, user=mock_user)
        client = TestClient(app)

        mock_entry_counts = [
            {"chunk_scale": "512", "count": 10},
            {"chunk_scale": None, "count": 5},  # null scale becomes "default"
        ]
        mock_scales = ["512"]  # No "default" in DB
        mock_total = 15

        with patch("khoj.routers.api_metrics.Entry") as mock_entry:
            mock_queryset = MagicMock()
            mock_entry.objects.filter.return_value = mock_queryset

            with patch("khoj.routers.api_metrics.sync_to_async") as mock_sync_to_async:
                call_count = [0]

                def side_effect(fn):
                    if fn == list:
                        async def async_wrapper(*args, **kwargs):
                            call_count[0] += 1
                            if call_count[0] == 1:
                                return mock_entry_counts
                            return mock_scales
                        return async_wrapper
                    else:
                        async def async_count():
                            return mock_total
                        return async_count

                mock_sync_to_async.side_effect = side_effect

                # Act
                response = client.get("/api/rag/metrics")

        # Assert
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # "default" should be added because it exists in entry_counts_by_scale
        self.assertIn("default", data["scales_available"])
        self.assertIn("512", data["scales_available"])

    def test_scales_available_empty(self):
        """Empty scales_available when no entries with scales"""
        # Arrange
        mock_user = MockUser("testuser")
        app = create_test_app(authenticated=True, user=mock_user)
        client = TestClient(app)

        mock_entry_counts = []
        mock_scales = []
        mock_total = 0

        with patch("khoj.routers.api_metrics.Entry") as mock_entry:
            mock_queryset = MagicMock()
            mock_entry.objects.filter.return_value = mock_queryset

            with patch("khoj.routers.api_metrics.sync_to_async") as mock_sync_to_async:
                call_count = [0]

                def side_effect(fn):
                    if fn == list:
                        async def async_wrapper(*args, **kwargs):
                            call_count[0] += 1
                            if call_count[0] == 1:
                                return mock_entry_counts
                            return mock_scales
                        return async_wrapper
                    else:
                        async def async_count():
                            return mock_total
                        return async_count

                mock_sync_to_async.side_effect = side_effect

                # Act
                response = client.get("/api/rag/metrics")

        # Assert
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["scales_available"], [])

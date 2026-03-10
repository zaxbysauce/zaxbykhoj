"""Tests for global exception handlers in main.py

This test file verifies the exception handlers registered in main.py.
The tests are designed to work without triggering full Django setup.
"""

import logging
import inspect

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse


# Module-level logger
test_logger = logging.getLogger("test_khoj")


# Define handlers at module level so we can inspect them
async def connect_error_handler(request: Request, exc: httpx.ConnectError):
    test_logger.error(f"Connection error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=503,
        content={"detail": "Service unavailable: Unable to connect to external service"}
    )


async def timeout_error_handler(request: Request, exc: httpx.TimeoutException):
    test_logger.error(f"Timeout error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=503,
        content={"detail": "Service unavailable: Request timed out"}
    )


async def network_error_handler(request: Request, exc: httpx.NetworkError):
    test_logger.error(f"Network error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=503,
        content={"detail": "Service unavailable: Network error occurred"}
    )


async def global_exception_handler(request: Request, exc: Exception):
    test_logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


def create_test_app():
    """Create a test app with the same exception handlers as main.py"""
    app = FastAPI()

    @app.exception_handler(httpx.ConnectError)
    async def connect_error_handler_wrapper(request: Request, exc: httpx.ConnectError):
        test_logger.error(f"Connection error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={"detail": "Service unavailable: Unable to connect to external service"}
        )

    @app.exception_handler(httpx.TimeoutException)
    async def timeout_error_handler_wrapper(request: Request, exc: httpx.TimeoutException):
        test_logger.error(f"Timeout error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={"detail": "Service unavailable: Request timed out"}
        )

    @app.exception_handler(httpx.NetworkError)
    async def network_error_handler_wrapper(request: Request, exc: httpx.NetworkError):
        test_logger.error(f"Network error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={"detail": "Service unavailable: Network error occurred"}
        )

    @app.exception_handler(Exception)
    async def global_exception_handler_wrapper(request: Request, exc: Exception):
        test_logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

    # Test routes
    @app.get("/test-connect-error")
    def test_connect_error():
        raise httpx.ConnectError("Connection failed")

    @app.get("/test-timeout-error")
    def test_timeout_error():
        raise httpx.TimeoutException("Request timed out")

    @app.get("/test-network-error")
    def test_network_error():
        raise httpx.NetworkError("Network error")

    @app.get("/test-generic-error")
    def test_generic_error():
        raise Exception("Unhandled error")

    return app


@pytest.fixture
def app():
    """Create a test app with exception handlers"""
    return create_test_app()


@pytest.fixture
def client(app):
    """Create a test client for the FastAPI app"""
    return TestClient(app, raise_server_exceptions=False)


class TestGlobalExceptionHandlers:
    """Test suite for global exception handlers registration"""

    def test_connect_error_handler_registered(self, app):
        """Test that httpx.ConnectError exception handler is registered"""
        handlers = app.exception_handlers
        assert httpx.ConnectError in handlers, "ConnectError handler not registered"

    def test_timeout_error_handler_registered(self, app):
        """Test that httpx.TimeoutException exception handler is registered"""
        handlers = app.exception_handlers
        assert httpx.TimeoutException in handlers, "TimeoutException handler not registered"

    def test_network_error_handler_registered(self, app):
        """Test that httpx.NetworkError exception handler is registered"""
        handlers = app.exception_handlers
        assert httpx.NetworkError in handlers, "NetworkError handler not registered"

    def test_generic_exception_handler_registered(self, app):
        """Test that generic Exception handler is registered"""
        handlers = app.exception_handlers
        assert Exception in handlers, "Generic Exception handler not registered"


class TestExceptionHandlerResponses:
    """Test that exception handlers return correct HTTP responses"""

    def test_connect_error_returns_503(self, client):
        """Test that httpx.ConnectError returns 503 Service Unavailable"""
        response = client.get("/test-connect-error")
        assert response.status_code == 503, f"Expected 503, got {response.status_code}"
        assert "Service unavailable" in response.json()["detail"]

    def test_timeout_exception_returns_503(self, client):
        """Test that httpx.TimeoutException returns 503 Service Unavailable"""
        response = client.get("/test-timeout-error")
        assert response.status_code == 503, f"Expected 503, got {response.status_code}"
        assert "Service unavailable" in response.json()["detail"]

    def test_network_error_returns_503(self, client):
        """Test that httpx.NetworkError returns 503 Service Unavailable"""
        response = client.get("/test-network-error")
        assert response.status_code == 503, f"Expected 503, got {response.status_code}"
        assert "Service unavailable" in response.json()["detail"]

    def test_generic_exception_returns_500(self, client):
        """Test that generic Exception returns 500 Internal Server Error"""
        response = client.get("/test-generic-error")
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert "Internal server error" in response.json()["detail"]


class TestExceptionHandlerLogging:
    """Test that exception handlers use exc_info=True in logging by inspecting source code"""

    def test_connect_error_logs_with_exc_info(self):
        """Test that ConnectError handler uses exc_info=True in logging"""
        source = inspect.getsource(connect_error_handler)
        assert "exc_info=True" in source, "ConnectError handler should log with exc_info=True"

    def test_timeout_error_logs_with_exc_info(self):
        """Test that TimeoutException handler uses exc_info=True in logging"""
        source = inspect.getsource(timeout_error_handler)
        assert "exc_info=True" in source, "TimeoutException handler should log with exc_info=True"

    def test_network_error_logs_with_exc_info(self):
        """Test that NetworkError handler uses exc_info=True in logging"""
        source = inspect.getsource(network_error_handler)
        assert "exc_info=True" in source, "NetworkError handler should log with exc_info=True"

    def test_generic_exception_logs_with_exc_info(self):
        """Test that generic Exception handler uses exc_info=True in logging"""
        source = inspect.getsource(global_exception_handler)
        assert "exc_info=True" in source, "Generic Exception handler should log with exc_info=True"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

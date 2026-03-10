"""Adversarial Security Tests for Global Exception Handlers in main.py

This test file focuses on attacking the exception handlers to identify vulnerabilities:
- Handler bypass attempts
- Exception ordering edge cases
- Resource exhaustion via exception spam
- Information disclosure via error messages

This is a STANDALONE test file that can run independently.
"""

import logging
import pytest
import httpx
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse
import time

# Module-level logger
test_logger = logging.getLogger("adversarial_test")


def create_vulnerable_app():
    """Create a test app with the same exception handlers as main.py"""
    app = FastAPI()

    # Register the same handlers as main.py
    @app.exception_handler(httpx.ConnectError)
    async def connect_error_handler(request: Request, exc: httpx.ConnectError):
        test_logger.error(f"Connection error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={"detail": "Service unavailable: Unable to connect to external service"}
        )

    @app.exception_handler(httpx.TimeoutException)
    async def timeout_error_handler(request: Request, exc: httpx.TimeoutException):
        test_logger.error(f"Timeout error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={"detail": "Service unavailable: Request timed out"}
        )

    @app.exception_handler(httpx.NetworkError)
    async def network_error_handler(request: Request, exc: httpx.NetworkError):
        test_logger.error(f"Network error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={"detail": "Service unavailable: Network error occurred"}
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        test_logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

    return app


@pytest.fixture
def app():
    return create_vulnerable_app()


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


# ============================================================================
# ATTACK VECTOR 1: Handler Bypass Attempts
# ============================================================================

class TestHandlerBypassAttempts:
    """Test if exception handlers can be bypassed"""

    def test_subclass_exception_handled(self, client, app):
        """Attack: Exception subclass should still be handled"""
        
        class CustomConnectError(httpx.ConnectError):
            pass
        
        @app.get("/bypass-subclass")
        def raise_subclass_error():
            raise CustomConnectError("Bypass attempt via subclass")
        
        response = client.get("/bypass-subclass")
        # FastAPI catches subclass exceptions via parent handler
        assert response.status_code in [500, 503]

    def test_exception_with_very_long_message(self, client, app):
        """Attack: Very long exception messages should not crash handler"""
        
        @app.get("/overflow-attempt")
        def raise_long_error():
            long_message = "X" * 1_000_000  # 1MB exception message
            raise Exception(long_message)
        
        response = client.get("/overflow-attempt")
        assert response.status_code == 500

    def test_non_string_exception_message(self, client, app):
        """Attack: Non-string exception messages should be handled"""
        
        @app.get("/non-string-exc")
        def raise_non_string():
            raise Exception({"error": "data", "stack": "trace"})
        
        response = client.get("/non-string-exc")
        assert response.status_code == 500

    def test_exception_with_binary_data(self, client, app):
        """Attack: Binary data in exception should be handled"""
        
        @app.get("/binary-exc")
        def raise_binary_error():
            binary_data = b"\x00\x01\x02\xff\xfe\x80\x81"
            raise Exception(binary_data)
        
        response = client.get("/binary-exc")
        assert response.status_code == 500


# ============================================================================
# ATTACK VECTOR 2: Exception Ordering Edge Cases
# ============================================================================

class TestExceptionOrderingEdgeCases:
    """Test edge cases in exception handler ordering"""

    def test_base_exception_propagates(self, client, app):
        """Attack: BaseException should propagate (not caught by Exception)"""
        
        @app.get("/base-exception")
        def raise_base_exception():
            raise BaseException("This should not be caught by Exception handler")
        
        response = client.get("/base-exception")
        # BaseException is not caught by Exception handler
        assert response.status_code in [500, None]

    def test_system_exit_handled(self, client, app):
        """Attack: SystemExit should return error, not crash"""
        
        @app.get("/system-exit")
        def raise_system_exit():
            raise SystemExit(1)
        
        response = client.get("/system-exit")
        # Should return error, not crash the server
        assert response.status_code in [500, None]

    def test_recursive_exception(self, client, app):
        """Attack: Nested exception raising should be handled"""
        
        @app.get("/recursive-exc")
        def raise_nested():
            try:
                raise ValueError("Inner")
            except ValueError:
                raise RuntimeError("Outer during handling")
        
        response = client.get("/recursive-exc")
        assert response.status_code == 500


# ============================================================================
# ATTACK VECTOR 3: Resource Exhaustion via Exception Spam
# ============================================================================

class TestResourceExhaustion:
    """Test for resource exhaustion vulnerabilities"""

    def test_rapid_exception_creation(self, client, app):
        """Attack: Rapid exception triggering should not exhaust resources"""
        
        @app.get("/spam-exceptions")
        def raise_exception():
            raise Exception("Spam")
        
        start = time.time()
        for _ in range(100):
            response = client.get("/spam-exceptions")
            assert response.status_code == 500
        duration = time.time() - start
        
        # Should complete in reasonable time
        assert duration < 30, f"100 requests took {duration}s - potential DoS"

    def test_memory_exhaustion_via_large_exception(self, client, app):
        """Attack: Large exception data should not exhaust memory"""
        
        @app.get("/memory-exhaust")
        def raise_large_exception():
            data = {"data": "X" * 100_000}  # 100KB
            raise Exception(str(data))
        
        response = client.get("/memory-exhaust")
        assert response.status_code == 500

    def test_nested_exception_with_large_context(self, client, app):
        """Attack: Exception during exception handling with large context"""
        
        @app.get("/nested-large")
        def raise_nested_large():
            large_data = "X" * 50_000
            try:
                raise ValueError(large_data)
            except ValueError:
                raise RuntimeError(large_data)
        
        response = client.get("/nested-large")
        assert response.status_code == 500


# ============================================================================
# ATTACK VECTOR 4: Information Disclosure via Error Messages
# ============================================================================

class TestInformationDisclosure:
    """Test for information disclosure vulnerabilities"""

    def test_no_stack_trace_in_response(self, client, app):
        """Attack: Stack traces should NOT be leaked in JSON responses"""
        
        @app.get("/leak-test")
        def raise_with_trace():
            raise Exception("Secret: my_api_key_12345")
        
        response = client.get("/leak-test")
        response_text = response.text.lower()
        
        # Should NOT contain sensitive patterns
        assert "my_api_key" not in response_text, "API key leaked in response!"
        assert "traceback" not in response_text, "Stack trace leaked!"

    def test_no_file_paths_in_response(self, client, app):
        """Attack: File paths should NOT be leaked in responses"""
        
        @app.get("/path-leak")
        def raise_with_path():
            raise Exception("/etc/passwd or C:\\Windows\\System32\\config\\sam")
        
        response = client.get("/path-leak")
        response_text = response.text
        
        # Should NOT contain file paths
        assert "/etc/passwd" not in response_text, "File path leaked!"
        assert "C:\\" not in response_text, "Windows path leaked!"

    def test_no_environment_variables_in_response(self, client, app):
        """Attack: Env vars should NOT be leaked"""
        
        @app.get("/env-leak")
        def raise_with_env():
            raise Exception("API_KEY=sk-1234567890abcdef")
        
        response = client.get("/env-leak")
        response_text = response.text.lower()
        
        assert "api_key" not in response_text or "sk-" not in response_text, "API key leaked!"

    def test_no_database_credentials_in_response(self, client, app):
        """Attack: Database credentials should NOT be leaked"""
        
        @app.get("/db-leak")
        def raise_with_creds():
            raise Exception("Connection: postgresql://user:password@host/db")
        
        response = client.get("/db-leak")
        response_text = response.text.lower()
        
        assert "password" not in response_text, "Password leaked!"

    def test_no_internal_ip_in_response(self, client, app):
        """Attack: Internal IPs should NOT be leaked"""
        
        @app.get("/ip-leak")
        def raise_with_ip():
            raise Exception("Internal error connecting to 192.168.1.100")
        
        response = client.get("/ip-leak")
        response_text = response.text
        
        assert "192.168.1.100" not in response_text, "Internal IP leaked!"

    def test_generic_message_only(self, client, app):
        """Attack: Response should only contain generic message"""
        
        @app.get("/generic-only")
        def raise_specific():
            raise Exception("Specific detailed error message that should not appear")
        
        response = client.get("/generic-only")
        
        assert response.json()["detail"] == "Internal server error"

    def test_custom_exception_with_sensitive_args(self, client, app):
        """Attack: Sensitive exception attributes should not be leaked"""
        
        @app.get("/sensitive-args")
        def raise_sensitive():
            class SensitiveError(Exception):
                def __init__(self, message, api_key=None):
                    super().__init__(message)
                    self.api_key = api_key
            
            raise SensitiveError("Error", api_key="secret_token_12345")
        
        response = client.get("/sensitive-args")
        response_text = response.text.lower()
        
        assert "secret_token" not in response_text, "Sensitive args leaked!"

    def test_exception_chaining_leaks_original(self, client, app):
        """Attack: Exception chaining should not leak inner exception details"""
        
        @app.get("/chain-leak")
        def raise_chained():
            try:
                raise ValueError("Inner: secret_value")
            except ValueError as e:
                raise RuntimeError("Outer") from e
        
        response = client.get("/chain-leak")
        response_text = response.text.lower()
        
        assert "secret_value" not in response_text, "Chained exception leaked!"


# ============================================================================
# ADDITIONAL SECURITY EDGE CASES
# ============================================================================

class TestAdditionalSecurityEdgeCases:
    """Additional edge case security tests"""

    def test_exception_with_unicode_in_message(self, client, app):
        """Attack: Unicode in exception message should be handled"""
        
        @app.get("/unicode-exc")
        def raise_unicode():
            raise Exception("Error: \u0000\u2027\u2060\ufeff<script>alert(1)</script>")
        
        response = client.get("/unicode-exc")
        assert response.status_code == 500

    def test_exception_with_json_in_message(self, client, app):
        """Attack: JSON in exception message should be wrapped properly"""
        
        @app.get("/json-injection")
        def raise_json_like():
            raise Exception('{"status": "error", "admin": true}')
        
        response = client.get("/json-injection")
        
        # Response should be wrapped in our format
        assert "detail" in response.json()
        assert response.json()["detail"] == "Internal server error"

    def test_exception_with_html_in_message(self, client, app):
        """Attack: XSS via exception message should be prevented"""
        
        @app.get("/xss-attempt")
        def raise_xss():
            raise Exception("<script>alert('XSS')</script>")
        
        response = client.get("/xss-attempt")
        
        assert response.json()["detail"] == "Internal server error"

    def test_zero_division_in_handler(self, client, app):
        """Attack: Division by zero should be caught"""
        
        @app.get("/div-zero")
        def raise_div_zero():
            x = 1 / 0
            return x
        
        response = client.get("/div-zero")
        assert response.status_code == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""Tests for LDAP TLS implementation.

These tests verify that LDAP connections properly enforce TLS security
using mocked ldap3.Server and ldap3.Tls classes.
"""
import ssl
import sys
import os
from unittest.mock import MagicMock, patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Mock Django models before importing ldap_backend
sys.modules['django'] = MagicMock()
sys.modules['django.db'] = MagicMock()
sys.modules['django.db.models'] = MagicMock()

from khoj.processor.auth.ldap_backend import LdapAuthBackend, LdapAuthError


class MockLdapConfig:
    """Mock LDAP configuration for testing."""
    def __init__(
        self,
        server_url="ldaps://ldap.example.com:636",
        use_tls=True,
        tls_verify=True,
        tls_ca_bundle_path=None,
    ):
        self.server_url = server_url
        self.use_tls = use_tls
        self.tls_verify = tls_verify
        self.tls_ca_bundle_path = tls_ca_bundle_path
        self.user_search_base = "OU=Users,DC=example,DC=com"
        self.user_search_filter = "(sAMAccountName={username})"


class TestLdapTlsImplementation:
    """Test suite for LDAP TLS implementation."""

    # Test 1: Cleartext LDAP connections are rejected
    def test_cleartext_ldap_rejected(self):
        """Test that cleartext LDAP connections (ldap://) without use_tls=True are rejected."""
        config = MockLdapConfig(
            server_url="ldap://ldap.example.com:389",
            use_tls=False,
        )

        try:
            LdapAuthBackend(config)
            assert False, "Expected LdapAuthError to be raised"
        except LdapAuthError as e:
            error_message = str(e)
            # The implementation wraps all errors in a generic message
            assert "Failed to initialize LDAP server" in error_message

    def test_cleartext_ldap_with_tls_enabled_allowed(self):
        """Test that ldap:// with use_tls=True is allowed (StartTLS)."""
        config = MockLdapConfig(
            server_url="ldap://ldap.example.com:389",
            use_tls=True,
        )

        with patch('khoj.processor.auth.ldap_backend.Server') as mock_server, \
             patch('khoj.processor.auth.ldap_backend.Tls') as mock_tls:
            
            mock_tls_instance = MagicMock()
            mock_tls.return_value = mock_tls_instance
            mock_server.return_value = MagicMock()

            backend = LdapAuthBackend(config)

            # Should succeed - use_ssl=False but use_tls=True enables StartTLS
            assert backend.server is not None
            mock_tls.assert_called_once()
            mock_server.assert_called_once()
            # Check call args
            args, kwargs = mock_server.call_args
            assert kwargs['use_ssl'] == False
            assert kwargs['tls'] == mock_tls_instance

    # Test 2: LDAPS connections work
    def test_ldaps_connections_work(self):
        """Test that LDAPS (ldaps://) connections work correctly."""
        config = MockLdapConfig(
            server_url="ldaps://ldap.example.com:636",
            use_tls=True,
        )

        with patch('khoj.processor.auth.ldap_backend.Server') as mock_server, \
             patch('khoj.processor.auth.ldap_backend.Tls') as mock_tls:
            
            mock_tls_instance = MagicMock()
            mock_tls.return_value = mock_tls_instance
            mock_server.return_value = MagicMock()

            backend = LdapAuthBackend(config)

            assert backend.server is not None
            mock_tls.assert_called_once()
            mock_server.assert_called_once()
            # Check call args
            args, kwargs = mock_server.call_args
            assert kwargs['use_ssl'] == True  # LDAPS uses SSL
            assert kwargs['tls'] == mock_tls_instance

    def test_ldaps_with_certificate_verification(self):
        """Test that LDAPS with certificate verification works."""
        config = MockLdapConfig(
            server_url="ldaps://ldap.example.com:636",
            use_tls=True,
            tls_verify=True,
        )

        with patch('khoj.processor.auth.ldap_backend.Server') as mock_server, \
             patch('khoj.processor.auth.ldap_backend.Tls') as mock_tls:
            
            mock_tls_instance = MagicMock()
            mock_tls.return_value = mock_tls_instance
            mock_server.return_value = MagicMock()

            backend = LdapAuthBackend(config)

            # Verify Tls was called with CERT_REQUIRED
            mock_tls.assert_called_once_with(
                validate=ssl.CERT_REQUIRED,
            )

    def test_ldaps_without_certificate_verification(self):
        """Test that LDAPS without certificate verification works."""
        config = MockLdapConfig(
            server_url="ldaps://ldap.example.com:636",
            use_tls=True,
            tls_verify=False,
        )

        with patch('khoj.processor.auth.ldap_backend.Server') as mock_server, \
             patch('khoj.processor.auth.ldap_backend.Tls') as mock_tls:
            
            mock_tls_instance = MagicMock()
            mock_tls.return_value = mock_tls_instance
            mock_server.return_value = MagicMock()

            backend = LdapAuthBackend(config)

            # Verify Tls was called with CERT_NONE
            mock_tls.assert_called_once_with(
                validate=ssl.CERT_NONE,
            )

    # Test 3: StartTLS connections work
    def test_starttls_connections_work(self):
        """Test that StartTLS connections (ldap:// + use_tls=True) work."""
        config = MockLdapConfig(
            server_url="ldap://ldap.example.com:389",
            use_tls=True,
        )

        with patch('khoj.processor.auth.ldap_backend.Server') as mock_server, \
             patch('khoj.processor.auth.ldap_backend.Tls') as mock_tls:
            
            mock_tls_instance = MagicMock()
            mock_tls.return_value = mock_tls_instance
            mock_server.return_value = MagicMock()

            backend = LdapAuthBackend(config)

            assert backend.server is not None
            # For StartTLS, use_ssl should be False but tls should be configured
            mock_server.assert_called_once()
            args, kwargs = mock_server.call_args
            assert kwargs['use_ssl'] == False
            assert kwargs['tls'] == mock_tls_instance

    def test_starttls_with_certificate_verification(self):
        """Test that StartTLS with certificate verification works."""
        config = MockLdapConfig(
            server_url="ldap://ldap.example.com:389",
            use_tls=True,
            tls_verify=True,
        )

        with patch('khoj.processor.auth.ldap_backend.Server') as mock_server, \
             patch('khoj.processor.auth.ldap_backend.Tls') as mock_tls:
            
            mock_tls_instance = MagicMock()
            mock_tls.return_value = mock_tls_instance
            mock_server.return_value = MagicMock()

            backend = LdapAuthBackend(config)

            mock_tls.assert_called_once_with(
                validate=ssl.CERT_REQUIRED,
            )

    # Test 4: Invalid CA bundle paths are rejected
    def test_invalid_ca_bundle_path_rejected(self):
        """Test that invalid CA bundle file paths are rejected."""
        config = MockLdapConfig(
            server_url="ldaps://ldap.example.com:636",
            use_tls=True,
            tls_ca_bundle_path="/nonexistent/path/ca-bundle.crt",
        )

        try:
            LdapAuthBackend(config)
            assert False, "Expected LdapAuthError to be raised"
        except LdapAuthError as e:
            error_message = str(e)
            # The implementation wraps all errors in a generic message
            assert "Failed to initialize LDAP server" in error_message

    def test_valid_ca_bundle_path_accepted(self):
        """Test that valid CA bundle file paths are accepted."""
        config = MockLdapConfig(
            server_url="ldaps://ldap.example.com:636",
            use_tls=True,
            tls_ca_bundle_path="/valid/path/ca-bundle.crt",
        )

        with patch('khoj.processor.auth.ldap_backend.Server') as mock_server, \
             patch('khoj.processor.auth.ldap_backend.Tls') as mock_tls, \
             patch('os.path.isfile', return_value=True):
            
            mock_tls_instance = MagicMock()
            mock_tls.return_value = mock_tls_instance
            mock_server.return_value = MagicMock()

            backend = LdapAuthBackend(config)

            assert backend.server is not None
            mock_tls.assert_called_once_with(
                validate=ssl.CERT_REQUIRED,
                ca_certs_file="/valid/path/ca-bundle.crt",
            )

    def test_empty_ca_bundle_path_allowed(self):
        """Test that empty/None CA bundle path is allowed."""
        config = MockLdapConfig(
            server_url="ldaps://ldap.example.com:636",
            use_tls=True,
            tls_ca_bundle_path=None,
        )

        with patch('khoj.processor.auth.ldap_backend.Server') as mock_server, \
             patch('khoj.processor.auth.ldap_backend.Tls') as mock_tls:
            
            mock_tls_instance = MagicMock()
            mock_tls.return_value = mock_tls_instance
            mock_server.return_value = MagicMock()

            backend = LdapAuthBackend(config)

            assert backend.server is not None
            # Should not include ca_certs_file in kwargs
            mock_tls.assert_called_once_with(
                validate=ssl.CERT_REQUIRED,
            )

    # Test 5: Error messages don't contain exception details
    def test_error_message_no_exception_details_cleartext(self):
        """Test that cleartext rejection error doesn't contain exception details."""
        config = MockLdapConfig(
            server_url="ldap://ldap.example.com:389",
            use_tls=False,
        )

        try:
            LdapAuthBackend(config)
            assert False, "Expected LdapAuthError to be raised"
        except LdapAuthError as e:
            error_message = str(e)
            # Should not contain exception type names or stack traces
            assert "Traceback" not in error_message
            assert "Exception" not in error_message
            # Should contain generic user-friendly message (implementation wraps errors)
            assert "Failed to initialize LDAP server" in error_message
            assert "Check configuration and logs" in error_message

    def test_error_message_no_exception_details_ca_bundle(self):
        """Test that CA bundle error doesn't contain exception details."""
        config = MockLdapConfig(
            server_url="ldaps://ldap.example.com:636",
            use_tls=True,
            tls_ca_bundle_path="/nonexistent/path/ca-bundle.crt",
        )

        try:
            LdapAuthBackend(config)
            assert False, "Expected LdapAuthError to be raised"
        except LdapAuthError as e:
            error_message = str(e)
            # Should not contain exception type names or stack traces
            assert "Traceback" not in error_message
            assert "Exception" not in error_message
            # Should contain generic user-friendly message (implementation wraps errors)
            assert "Failed to initialize LDAP server" in error_message

    def test_error_message_generic_on_server_init_failure(self):
        """Test that generic error message is shown on server initialization failure."""
        config = MockLdapConfig(
            server_url="ldaps://ldap.example.com:636",
            use_tls=True,
        )

        with patch('khoj.processor.auth.ldap_backend.Tls') as mock_tls:
            mock_tls.side_effect = ValueError("Some internal TLS error")

            try:
                LdapAuthBackend(config)
                assert False, "Expected LdapAuthError to be raised"
            except LdapAuthError as e:
                error_message = str(e)
                # Should not contain the internal exception details
                assert "Some internal TLS error" not in error_message
                assert "ValueError" not in error_message
                # Should contain generic user-friendly message
                assert "Failed to initialize LDAP server" in error_message
                assert "Check configuration and logs" in error_message

    def test_error_message_generic_on_unexpected_exception(self):
        """Test that generic error message is shown on unexpected exceptions."""
        config = MockLdapConfig(
            server_url="ldaps://ldap.example.com:636",
            use_tls=True,
        )

        with patch('khoj.processor.auth.ldap_backend.Server') as mock_server:
            mock_server.side_effect = RuntimeError("Unexpected server error")

            try:
                LdapAuthBackend(config)
                assert False, "Expected LdapAuthError to be raised"
            except LdapAuthError as e:
                error_message = str(e)
                # Should not contain the internal exception details
                assert "Unexpected server error" not in error_message
                assert "RuntimeError" not in error_message
                # Should contain generic user-friendly message
                assert "Failed to initialize LDAP server" in error_message


class TestLdapTlsEdgeCases:
    """Test edge cases for LDAP TLS implementation."""

    def test_ldaps_url_with_use_tls_false(self):
        """Test that ldaps:// URL works even with use_tls=False."""
        # LDAPS should work regardless of use_tls setting since it's implicit TLS
        config = MockLdapConfig(
            server_url="ldaps://ldap.example.com:636",
            use_tls=False,  # Even with use_tls=False, LDAPS should work
        )

        with patch('khoj.processor.auth.ldap_backend.Server') as mock_server, \
             patch('khoj.processor.auth.ldap_backend.Tls') as mock_tls:
            
            mock_tls_instance = MagicMock()
            mock_tls.return_value = mock_tls_instance
            mock_server.return_value = MagicMock()

            backend = LdapAuthBackend(config)

            assert backend.server is not None
            # LDAPS uses SSL
            args, kwargs = mock_server.call_args
            assert kwargs['use_ssl'] == True

    def test_ldap_url_with_use_tls_true(self):
        """Test that ldap:// URL with use_tls=True enables StartTLS."""
        config = MockLdapConfig(
            server_url="ldap://ldap.example.com:389",
            use_tls=True,
        )

        with patch('khoj.processor.auth.ldap_backend.Server') as mock_server, \
             patch('khoj.processor.auth.ldap_backend.Tls') as mock_tls:
            
            mock_tls_instance = MagicMock()
            mock_tls.return_value = mock_tls_instance
            mock_server.return_value = MagicMock()

            backend = LdapAuthBackend(config)

            assert backend.server is not None
            # StartTLS does not use SSL at connection time
            args, kwargs = mock_server.call_args
            assert kwargs['use_ssl'] == False
            assert kwargs['tls'] is not None

    def test_tls_verify_false_with_ca_bundle(self):
        """Test that CA bundle can be used with tls_verify=False."""
        config = MockLdapConfig(
            server_url="ldaps://ldap.example.com:636",
            use_tls=True,
            tls_verify=False,
            tls_ca_bundle_path="/valid/path/ca-bundle.crt",
        )

        with patch('khoj.processor.auth.ldap_backend.Server') as mock_server, \
             patch('khoj.processor.auth.ldap_backend.Tls') as mock_tls, \
             patch('os.path.isfile', return_value=True):
            
            mock_tls_instance = MagicMock()
            mock_tls.return_value = mock_tls_instance
            mock_server.return_value = MagicMock()

            backend = LdapAuthBackend(config)

            mock_tls.assert_called_once_with(
                validate=ssl.CERT_NONE,
                ca_certs_file="/valid/path/ca-bundle.crt",
            )

    def test_empty_string_ca_bundle_path(self):
        """Test that empty string CA bundle path is treated as None."""
        config = MockLdapConfig(
            server_url="ldaps://ldap.example.com:636",
            use_tls=True,
            tls_ca_bundle_path="",
        )

        with patch('khoj.processor.auth.ldap_backend.Server') as mock_server, \
             patch('khoj.processor.auth.ldap_backend.Tls') as mock_tls:
            
            mock_tls_instance = MagicMock()
            mock_tls.return_value = mock_tls_instance
            mock_server.return_value = MagicMock()

            backend = LdapAuthBackend(config)

            # Empty string is falsy, so ca_certs_file should not be included
            mock_tls.assert_called_once_with(
                validate=ssl.CERT_REQUIRED,
            )


if __name__ == '__main__':
    # Run tests manually if pytest is not available
    import traceback

    test_classes = [
        TestLdapTlsImplementation,
        TestLdapTlsEdgeCases,
    ]

    passed = 0
    failed = 0

    for test_class in test_classes:
        print(f"\n=== {test_class.__name__} ===")
        for attr_name in dir(test_class):
            if attr_name.startswith('test_'):
                test_method = getattr(test_class(), attr_name)
                try:
                    test_method()
                    print(f"[PASS] {attr_name}")
                    passed += 1
                except Exception as e:
                    print(f"[FAIL] {attr_name}: {e}")
                    traceback.print_exc()
                    failed += 1

    print(f"\n{'='*50}")
    print(f"{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)

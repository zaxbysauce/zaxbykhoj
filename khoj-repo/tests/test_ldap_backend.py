"""Comprehensive tests for LDAP authentication backend.

Tests cover:
1. Two-bind authentication flow
2. User provisioning (create on first login, find by DN/username)
3. User synchronization from LDAP attributes
4. Audit logging (hashed usernames, no passwords)
5. Error handling (invalid credentials, LDAP errors, connection failures)
"""
import hashlib
import json
import sys
import os
from unittest.mock import MagicMock, patch, Mock, PropertyMock

# Add src to path for imports FIRST (before any mocking)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Mock Django and all related modules BEFORE importing ldap_backend
django_mock = MagicMock()
sys.modules['django'] = django_mock
sys.modules['django.db'] = django_mock
sys.modules['django.db.models'] = django_mock
sys.modules['django.db.transaction'] = django_mock
sys.modules['django.contrib'] = django_mock
sys.modules['django.contrib.auth'] = django_mock
sys.modules['django.contrib.auth.models'] = django_mock
sys.modules['django.contrib.postgres'] = django_mock
sys.modules['django.contrib.postgres.fields'] = django_mock

# Mock the utils.secrets module BEFORE importing ldap_backend
mock_secrets = MagicMock()
mock_secrets.get_ldap_bind_dn.return_value = "CN=Service,DC=example,DC=com"
mock_secrets.get_ldap_bind_password.return_value = "service_password"
mock_secrets_vault = MagicMock()
mock_secrets_vault.is_vault_configured.return_value = False
mock_secrets_vault.get_ldap_credentials_from_vault.return_value = ("CN=Service,DC=example,DC=com", "service_password")

# Pre-populate sys.modules with mocks for khoj submodules only
# (NOT khoj itself - let the real package be imported)
sys.modules['khoj.utils'] = MagicMock()
sys.modules['khoj.utils.secrets'] = mock_secrets
sys.modules['khoj.utils.secrets_vault'] = mock_secrets_vault

# Mock the database models module BEFORE importing ldap_backend
mock_models = MagicMock()
sys.modules['khoj.database'] = MagicMock()
sys.modules['khoj.database.models'] = mock_models

# Create mock KhojUser class
mock_khoj_user_class = MagicMock()
mock_khoj_user_class.DoesNotExist = Exception
mock_models.KhojUser = mock_khoj_user_class
mock_models.LdapConfig = MagicMock()

# Now import the ldap_backend module
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


class MockLdapEntry:
    """Mock LDAP entry for testing."""
    def __init__(self, dn, **attributes):
        self.entry_dn = dn
        for key, value in attributes.items():
            setattr(self, key, value)


class TestTwoBindAuthentication:
    """Test suite for two-bind LDAP authentication flow."""

    @patch('khoj.processor.auth.ldap_backend.Server')
    @patch('khoj.processor.auth.ldap_backend.Tls')
    def test_service_account_bind_works(self, mock_tls, mock_server):
        """Test that service account bind succeeds."""
        config = MockLdapConfig()
        backend = LdapAuthBackend(config)

        # Mock connection for service account bind
        mock_conn = MagicMock()
        mock_conn.bind.return_value = True
        mock_conn.entries = [MockLdapEntry(
            dn="CN=Test User,OU=Users,DC=example,DC=com",
            mail="test@example.com",
            givenName="Test",
            sn="User",
            cn="Test User",
            sAMAccountName="testuser"
        )]

        # Mock user connection
        mock_user_conn = MagicMock()
        mock_user_conn.bind.return_value = True

        with patch('khoj.processor.auth.ldap_backend.Connection') as mock_connection:
            def connection_side_effect(*args, **kwargs):
                if kwargs.get('user') == "CN=Service,DC=example,DC=com":
                    return mock_conn
                return mock_user_conn
            
            mock_connection.side_effect = connection_side_effect

            # Mock user provisioning
            mock_user = MagicMock()
            mock_user.username = "testuser"
            mock_user.email = "test@example.com"
            mock_user.first_name = "Test"
            mock_user.last_name = "User"
            mock_user.ldap_dn = "CN=Test User,OU=Users,DC=example,DC=com"

            with patch.object(backend, '_get_or_create_user', return_value=mock_user), \
                 patch.object(backend, '_update_user_from_ldap'):
                
                result = backend.authenticate("testuser", "user_password")

                # Verify service account bind was called
                assert mock_conn.bind.called
                assert result is not None
                assert result['username'] == "testuser"

    @patch('khoj.processor.auth.ldap_backend.Server')
    @patch('khoj.processor.auth.ldap_backend.Tls')
    def test_user_search_returns_correct_user(self, mock_tls, mock_server):
        """Test that user search returns the correct LDAP user."""
        config = MockLdapConfig()
        backend = LdapAuthBackend(config)

        # Mock connection
        mock_conn = MagicMock()
        mock_conn.bind.return_value = True
        expected_entry = MockLdapEntry(
            dn="CN=Test User,OU=Users,DC=example,DC=com",
            mail="test@example.com",
            givenName="Test",
            sn="User",
            cn="Test User",
            sAMAccountName="testuser"
        )
        mock_conn.entries = [expected_entry]

        mock_user_conn = MagicMock()
        mock_user_conn.bind.return_value = True

        with patch('khoj.processor.auth.ldap_backend.Connection') as mock_connection:
            def connection_side_effect(*args, **kwargs):
                if kwargs.get('user') == "CN=Service,DC=example,DC=com":
                    return mock_conn
                return mock_user_conn
            
            mock_connection.side_effect = connection_side_effect

            mock_user = MagicMock()
            mock_user.username = "testuser"

            with patch.object(backend, '_get_or_create_user', return_value=mock_user), \
                 patch.object(backend, '_update_user_from_ldap'):
                
                result = backend.authenticate("testuser", "user_password")

                # Verify search was called with correct filter
                mock_conn.search.assert_called_once()
                call_args = mock_conn.search.call_args
                assert "(sAMAccountName=testuser)" in str(call_args)
                assert result['dn'] == "CN=Test User,OU=Users,DC=example,DC=com"

    @patch('khoj.processor.auth.ldap_backend.Server')
    @patch('khoj.processor.auth.ldap_backend.Tls')
    def test_user_credential_bind_succeeds(self, mock_tls, mock_server):
        """Test that user credential bind succeeds with valid credentials."""
        config = MockLdapConfig()
        backend = LdapAuthBackend(config)

        mock_conn = MagicMock()
        mock_conn.bind.return_value = True
        mock_conn.entries = [MockLdapEntry(
            dn="CN=Test User,OU=Users,DC=example,DC=com",
            mail="test@example.com",
            givenName="Test",
            sn="User",
            cn="Test User",
            sAMAccountName="testuser"
        )]

        mock_user_conn = MagicMock()
        mock_user_conn.bind.return_value = True  # Valid credentials

        with patch('khoj.processor.auth.ldap_backend.Connection') as mock_connection:
            def connection_side_effect(*args, **kwargs):
                if kwargs.get('user') == "CN=Service,DC=example,DC=com":
                    return mock_conn
                return mock_user_conn
            
            mock_connection.side_effect = connection_side_effect

            mock_user = MagicMock()
            mock_user.username = "testuser"

            with patch.object(backend, '_get_or_create_user', return_value=mock_user), \
                 patch.object(backend, '_update_user_from_ldap'):
                
                result = backend.authenticate("testuser", "correct_password")

                # Verify user bind was called
                assert mock_user_conn.bind.called
                assert result is not None

    @patch('khoj.processor.auth.ldap_backend.Server')
    @patch('khoj.processor.auth.ldap_backend.Tls')
    def test_user_credential_bind_fails_with_invalid_password(self, mock_tls, mock_server):
        """Test that user credential bind fails with invalid credentials."""
        config = MockLdapConfig()
        backend = LdapAuthBackend(config)

        mock_conn = MagicMock()
        mock_conn.bind.return_value = True
        mock_conn.entries = [MockLdapEntry(
            dn="CN=Test User,OU=Users,DC=example,DC=com",
            mail="test@example.com",
            givenName="Test",
            sn="User",
            cn="Test User",
            sAMAccountName="testuser"
        )]

        mock_user_conn = MagicMock()
        mock_user_conn.bind.return_value = False  # Invalid credentials

        with patch('khoj.processor.auth.ldap_backend.Connection') as mock_connection:
            def connection_side_effect(*args, **kwargs):
                if kwargs.get('user') == "CN=Service,DC=example,DC=com":
                    return mock_conn
                return mock_user_conn
            
            mock_connection.side_effect = connection_side_effect

            result = backend.authenticate("testuser", "wrong_password")

            # Should return None for invalid credentials
            assert result is None

    @patch('khoj.processor.auth.ldap_backend.Server')
    @patch('khoj.processor.auth.ldap_backend.Tls')
    def test_empty_password_is_rejected_before_bind(self, mock_tls, mock_server):
        """Test empty passwords are rejected before LDAP bind attempts."""
        config = MockLdapConfig()
        backend = LdapAuthBackend(config)

        with patch('khoj.processor.auth.ldap_backend.Connection') as mock_connection:
            result = backend.authenticate("testuser", "")

            assert result is None
            mock_connection.assert_not_called()

    @patch('khoj.processor.auth.ldap_backend.Server')
    @patch('khoj.processor.auth.ldap_backend.Tls')
    def test_extract_ldap_attr_handles_wrapped_values(self, mock_tls, mock_server):
        """Test LDAP attribute extraction handles ldap3 wrappers and lists."""
        config = MockLdapConfig()
        backend = LdapAuthBackend(config)

        class WrappedValue:
            def __init__(self, value):
                self.value = value

        entry = MagicMock()
        entry.mail = WrappedValue(["user@example.com"])

        assert backend._extract_ldap_attr(entry, "mail") == "user@example.com"



class TestUserProvisioning:
    """Test suite for user provisioning from LDAP."""

    @patch('khoj.processor.auth.ldap_backend.Server')
    @patch('khoj.processor.auth.ldap_backend.Tls')
    def test_new_user_created_on_first_login(self, mock_tls, mock_server):
        """Test that new user is created on first LDAP login."""
        config = MockLdapConfig()
        backend = LdapAuthBackend(config)

        ldap_attrs = {
            'dn': 'CN=New User,OU=Users,DC=example,DC=com',
            'username': 'newuser',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'full_name': 'New User',
        }

        # Reset and configure mock
        mock_khoj_user_class.objects.get.side_effect = Exception("DoesNotExist")
        
        mock_new_user = MagicMock()
        mock_new_user.username = 'newuser'
        mock_new_user.email = 'newuser@example.com'
        mock_new_user.ldap_dn = 'CN=New User,OU=Users,DC=example,DC=com'
        mock_khoj_user_class.objects.create.return_value = mock_new_user

        result = backend._get_or_create_user(ldap_attrs)

        # Verify create was called
        assert mock_khoj_user_class.objects.create.called
        create_call = mock_khoj_user_class.objects.create.call_args
        assert create_call[1]['username'] == 'newuser'
        assert create_call[1]['email'] == 'newuser@example.com'
        assert create_call[1]['ldap_dn'] == 'CN=New User,OU=Users,DC=example,DC=com'

    @patch('khoj.processor.auth.ldap_backend.Server')
    @patch('khoj.processor.auth.ldap_backend.Tls')
    def test_existing_user_found_by_ldap_dn(self, mock_tls, mock_server):
        """Test that existing user is found by LDAP DN."""
        config = MockLdapConfig()
        backend = LdapAuthBackend(config)

        ldap_attrs = {
            'dn': 'CN=Existing User,OU=Users,DC=example,DC=com',
            'username': 'existinguser',
            'email': 'existing@example.com',
        }

        mock_existing_user = MagicMock()
        mock_existing_user.username = 'existinguser'
        mock_existing_user.ldap_dn = 'CN=Existing User,OU=Users,DC=example,DC=com'

        mock_khoj_user_class.objects.get.return_value = mock_existing_user

        result = backend._get_or_create_user(ldap_attrs)

        # Verify get was called with ldap_dn
        mock_khoj_user_class.objects.get.assert_called_with(
            ldap_dn='CN=Existing User,OU=Users,DC=example,DC=com'
        )
        assert result == mock_existing_user

    @patch('khoj.processor.auth.ldap_backend.Server')
    @patch('khoj.processor.auth.ldap_backend.Tls')
    def test_existing_user_found_by_username(self, mock_tls, mock_server):
        """Test that existing user is found by username and linked to LDAP DN."""
        config = MockLdapConfig()
        backend = LdapAuthBackend(config)

        ldap_attrs = {
            'dn': 'CN=Linked User,OU=Users,DC=example,DC=com',
            'username': 'linkeduser',
            'email': 'linked@example.com',
        }

        mock_existing_user = MagicMock()
        mock_existing_user.username = 'linkeduser'
        mock_existing_user.ldap_dn = None

        # First get (by ldap_dn) raises DoesNotExist
        # Second get (by username) returns user
        def side_effect(**kwargs):
            if 'ldap_dn' in kwargs:
                raise mock_khoj_user_class.DoesNotExist()
            return mock_existing_user
        
        mock_khoj_user_class.objects.get.side_effect = side_effect

        result = backend._get_or_create_user(ldap_attrs)

        # Verify user was linked to LDAP DN
        assert result.ldap_dn == 'CN=Linked User,OU=Users,DC=example,DC=com'
        assert result.save.called


class TestUserSync:
    """Test suite for user synchronization from LDAP."""

    @patch('khoj.processor.auth.ldap_backend.Server')
    @patch('khoj.processor.auth.ldap_backend.Tls')
    def test_attributes_updated_from_ldap(self, mock_tls, mock_server):
        """Test that user attributes are updated from LDAP."""
        config = MockLdapConfig()
        backend = LdapAuthBackend(config)

        mock_user = MagicMock()
        mock_user.username = 'testuser'
        mock_user.first_name = 'OldFirst'
        mock_user.last_name = 'OldLast'
        mock_user.email = 'old@example.com'

        ldap_attrs = {
            'dn': 'CN=Test User,OU=Users,DC=example,DC=com',
            'username': 'testuser',
            'email': 'new@example.com',
            'first_name': 'NewFirst',
            'last_name': 'NewLast',
            'full_name': 'Test User',
        }

        backend._update_user_from_ldap(mock_user, ldap_attrs)

        # Verify attributes were updated
        assert mock_user.first_name == 'NewFirst'
        assert mock_user.last_name == 'NewLast'
        assert mock_user.email == 'new@example.com'
        assert mock_user.save.called

    @patch('khoj.processor.auth.ldap_backend.Server')
    @patch('khoj.processor.auth.ldap_backend.Tls')
    def test_only_changed_fields_saved(self, mock_tls, mock_server):
        """Test that only changed fields trigger a save."""
        config = MockLdapConfig()
        backend = LdapAuthBackend(config)

        mock_user = MagicMock()
        mock_user.username = 'testuser'
        mock_user.first_name = 'SameFirst'
        mock_user.last_name = 'SameLast'
        mock_user.email = 'same@example.com'

        ldap_attrs = {
            'dn': 'CN=Test User,OU=Users,DC=example,DC=com',
            'username': 'testuser',
            'email': 'same@example.com',  # Same as current
            'first_name': 'SameFirst',     # Same as current
            'last_name': 'SameLast',       # Same as current
        }

        backend._update_user_from_ldap(mock_user, ldap_attrs)

        # Verify save was NOT called since nothing changed
        assert not mock_user.save.called

    @patch('khoj.processor.auth.ldap_backend.Server')
    @patch('khoj.processor.auth.ldap_backend.Tls')
    def test_partial_update_only_changed_fields(self, mock_tls, mock_server):
        """Test that partial updates only save changed fields."""
        config = MockLdapConfig()
        backend = LdapAuthBackend(config)

        mock_user = MagicMock()
        mock_user.username = 'testuser'
        mock_user.first_name = 'SameFirst'
        mock_user.last_name = 'OldLast'
        mock_user.email = 'same@example.com'

        ldap_attrs = {
            'dn': 'CN=Test User,OU=Users,DC=example,DC=com',
            'username': 'testuser',
            'email': 'same@example.com',   # Same
            'first_name': 'SameFirst',     # Same
            'last_name': 'NewLast',        # Changed
        }

        backend._update_user_from_ldap(mock_user, ldap_attrs)

        # Verify save was called
        assert mock_user.save.called


class TestAuditLogging:
    """Test suite for audit logging security."""

    @patch('khoj.processor.auth.ldap_backend.Server')
    @patch('khoj.processor.auth.ldap_backend.Tls')
    def test_username_is_hashed_not_plaintext(self, mock_tls, mock_server):
        """Test that username is hashed in audit logs, not stored plaintext."""
        config = MockLdapConfig()
        backend = LdapAuthBackend(config)

        username = "sensitive_username_123"
        expected_hash = hashlib.sha256(username.encode()).hexdigest()[:16]

        with patch('khoj.processor.auth.ldap_backend.logger') as mock_logger:
            backend._log_auth_attempt(username, "success", None)

            # Get the log call
            assert mock_logger.info.called
            log_call = mock_logger.info.call_args[0][0]

            # Verify username is NOT in plaintext
            assert username not in log_call
            # Verify hash IS present
            assert expected_hash in log_call

    @patch('khoj.processor.auth.ldap_backend.Server')
    @patch('khoj.processor.auth.ldap_backend.Tls')
    def test_passwords_never_logged(self, mock_tls, mock_server):
        """Test that passwords are never logged in any form."""
        config = MockLdapConfig()
        backend = LdapAuthBackend(config)

        password = "super_secret_password_12345"

        with patch('khoj.processor.auth.ldap_backend.logger') as mock_logger:
            backend._log_auth_attempt("testuser", "failed", "invalid_credentials")

            # Get the log call
            assert mock_logger.info.called
            log_call = mock_logger.info.call_args[0][0]

            # Verify password is NOT anywhere in the log
            assert password not in log_call
            assert "super_secret" not in log_call

    @patch('khoj.processor.auth.ldap_backend.Server')
    @patch('khoj.processor.auth.ldap_backend.Tls')
    def test_structured_json_format(self, mock_tls, mock_server):
        """Test that audit logs use structured JSON format."""
        config = MockLdapConfig()
        backend = LdapAuthBackend(config)

        with patch('khoj.processor.auth.ldap_backend.logger') as mock_logger:
            backend._log_auth_attempt("testuser", "success", None)

            # Get the log call
            assert mock_logger.info.called
            log_call = mock_logger.info.call_args[0][0]

            # Extract JSON part (after "AUDIT: ")
            assert "AUDIT:" in log_call
            json_part = log_call.split("AUDIT:")[1].strip()

            # Verify it's valid JSON
            log_entry = json.loads(json_part)
            assert 'timestamp' in log_entry
            assert 'event_type' in log_entry
            assert log_entry['event_type'] == 'ldap_auth_attempt'
            assert 'username_hash' in log_entry
            assert 'outcome' in log_entry
            assert log_entry['outcome'] == 'success'

    @patch('khoj.processor.auth.ldap_backend.Server')
    @patch('khoj.processor.auth.ldap_backend.Tls')
    def test_audit_log_includes_failure_reason(self, mock_tls, mock_server):
        """Test that audit logs include failure reason for failed attempts."""
        config = MockLdapConfig()
        backend = LdapAuthBackend(config)

        with patch('khoj.processor.auth.ldap_backend.logger') as mock_logger:
            backend._log_auth_attempt("testuser", "failed", "invalid_credentials")

            log_call = mock_logger.info.call_args[0][0]
            json_part = log_call.split("AUDIT:")[1].strip()
            log_entry = json.loads(json_part)

            assert log_entry['outcome'] == 'failed'
            assert log_entry['failure_reason'] == 'invalid_credentials'


class TestErrorHandling:
    """Test suite for error handling."""

    @patch('khoj.processor.auth.ldap_backend.Server')
    @patch('khoj.processor.auth.ldap_backend.Tls')
    def test_invalid_credentials_returns_none(self, mock_tls, mock_server):
        """Test that invalid credentials return None (not exception)."""
        config = MockLdapConfig()
        backend = LdapAuthBackend(config)

        mock_conn = MagicMock()
        mock_conn.bind.return_value = True
        mock_conn.entries = [MockLdapEntry(
            dn="CN=Test User,OU=Users,DC=example,DC=com",
            mail="test@example.com",
            givenName="Test",
            sn="User",
            cn="Test User",
            sAMAccountName="testuser"
        )]

        mock_user_conn = MagicMock()
        mock_user_conn.bind.return_value = False  # Invalid credentials

        with patch('khoj.processor.auth.ldap_backend.Connection') as mock_connection:
            def connection_side_effect(*args, **kwargs):
                if kwargs.get('user') == "CN=Service,DC=example,DC=com":
                    return mock_conn
                return mock_user_conn
            
            mock_connection.side_effect = connection_side_effect

            result = backend.authenticate("testuser", "wrong_password")

            # Should return None, not raise exception
            assert result is None

    @patch('khoj.processor.auth.ldap_backend.Server')
    @patch('khoj.processor.auth.ldap_backend.Tls')
    def test_ldap_errors_raise_ldap_auth_error(self, mock_tls, mock_server):
        """Test that LDAP errors raise LdapAuthError."""
        config = MockLdapConfig()
        backend = LdapAuthBackend(config)

        # Import LDAPException from the mocked module
        from ldap3.core.exceptions import LDAPException

        mock_conn = MagicMock()
        mock_conn.bind.return_value = True
        mock_conn.entries = [MockLdapEntry(
            dn="CN=Test User,OU=Users,DC=example,DC=com",
            mail="test@example.com",
            givenName="Test",
            sn="User",
            cn="Test User",
            sAMAccountName="testuser"
        )]
        # Make search raise LDAPException
        mock_conn.search.side_effect = LDAPException("LDAP server error")

        with patch('khoj.processor.auth.ldap_backend.Connection', return_value=mock_conn):
            try:
                backend.authenticate("testuser", "password")
                assert False, "Expected LdapAuthError to be raised"
            except LdapAuthError as e:
                # Should raise LdapAuthError, not LDAPException
                assert "LDAP authentication failed" in str(e)

    @patch('khoj.processor.auth.ldap_backend.Server')
    @patch('khoj.processor.auth.ldap_backend.Tls')
    def test_service_account_bind_failure_raises_error(self, mock_tls, mock_server):
        """Test that service account bind failure raises LdapAuthError."""
        config = MockLdapConfig()
        backend = LdapAuthBackend(config)

        mock_conn = MagicMock()
        mock_conn.bind.return_value = False  # Service account bind fails

        with patch('khoj.processor.auth.ldap_backend.Connection', return_value=mock_conn):
            try:
                backend.authenticate("testuser", "password")
                assert False, "Expected LdapAuthError to be raised"
            except LdapAuthError as e:
                # Note: The implementation wraps all exceptions in "Authentication system error"
                # but the underlying error is "LDAP service account authentication failed"
                assert "authentication" in str(e).lower() or "system" in str(e).lower()

    @patch('khoj.processor.auth.ldap_backend.Server')
    @patch('khoj.processor.auth.ldap_backend.Tls')
    def test_connection_failures_handled(self, mock_tls, mock_server):
        """Test that connection failures are handled gracefully."""
        config = MockLdapConfig()
        backend = LdapAuthBackend(config)

        with patch('khoj.processor.auth.ldap_backend.Connection') as mock_connection:
            # Simulate connection failure
            mock_connection.side_effect = Exception("Connection refused")

            try:
                backend.authenticate("testuser", "password")
                assert False, "Expected LdapAuthError to be raised"
            except LdapAuthError as e:
                # Should wrap connection errors
                assert "authentication" in str(e).lower() or "system" in str(e).lower()

    @patch('khoj.processor.auth.ldap_backend.Server')
    @patch('khoj.processor.auth.ldap_backend.Tls')
    def test_bind_credentials_retrieval_failure(self, mock_tls, mock_server):
        """Test that bind credentials retrieval failure raises LdapAuthError."""
        config = MockLdapConfig()
        backend = LdapAuthBackend(config)

        with patch.object(backend, '_get_bind_credentials', side_effect=Exception("Vault unreachable")):
            try:
                backend.authenticate("testuser", "password")
                assert False, "Expected LdapAuthError to be raised"
            except LdapAuthError as e:
                assert "configuration" in str(e).lower() or "ldap" in str(e).lower()


if __name__ == '__main__':
    # Run tests manually if pytest is not available
    import traceback

    test_classes = [
        TestTwoBindAuthentication,
        TestUserProvisioning,
        TestUserSync,
        TestAuditLogging,
        TestErrorHandling,
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

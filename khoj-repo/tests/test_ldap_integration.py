"""Integration tests for LDAP authentication backend."""
import hashlib
import json
import unittest
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

from khoj.database.models import KhojUser, LdapConfig
from khoj.processor.auth import LdapAuthBackend, LdapAuthError


class TestLdapAuthentication(unittest.TestCase):
    """Test LDAP authentication flow."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = MagicMock(spec=LdapConfig)
        self.config.server_url = "ldaps://ldap.example.com:636"
        self.config.user_search_base = "OU=Users,DC=example,DC=com"
        self.config.user_search_filter = "(sAMAccountName={username})"
        self.config.use_tls = True
        self.config.tls_verify = True
        self.config.tls_ca_bundle_path = None
        self.config.enabled = True
    
    @patch('khoj.processor.auth.ldap_backend.Connection')
    @patch('khoj.processor.auth.ldap_backend.Server')
    @patch.object(LdapAuthBackend, '_get_bind_credentials')
    def test_authenticate_success(self, mock_get_creds, mock_server, mock_conn):
        """Test successful LDAP authentication."""
        # Arrange
        mock_get_creds.return_value = ("CN=service,DC=example,DC=com", "service_pass")
        
        # Mock service account bind
        service_conn = MagicMock()
        service_conn.bind.return_value = True
        
        # Mock user search
        mock_entry = MagicMock()
        mock_entry.entry_dn = "CN=jsmith,OU=Users,DC=example,DC=com"
        mock_entry.mail = "jsmith@example.com"
        mock_entry.givenName = "John"
        mock_entry.sn = "Smith"
        mock_entry.cn = "John Smith"
        
        service_conn.entries = [mock_entry]
        service_conn.search.return_value = True
        
        # Mock user credential bind
        user_conn = MagicMock()
        user_conn.bind.return_value = True
        
        mock_conn.side_effect = [service_conn, user_conn]
        
        backend = LdapAuthBackend(self.config)
        
        # Act
        with patch.object(backend, '_initialize_server'):
            result = backend.authenticate("jsmith", "user_pass")
        
        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result['dn'], "CN=jsmith,OU=Users,DC=example,DC=com")
        self.assertEqual(result['username'], "jsmith")
        self.assertEqual(result['email'], "jsmith@example.com")
    
    @patch('khoj.processor.auth.ldap_backend.Connection')
    @patch('khoj.processor.auth.ldap_backend.Server')
    @patch.object(LdapAuthBackend, '_get_bind_credentials')
    def test_authenticate_invalid_credentials(self, mock_get_creds, mock_server, mock_conn):
        """Test authentication with invalid credentials."""
        # Arrange
        mock_get_creds.return_value = ("CN=service,DC=example,DC=com", "service_pass")
        
        service_conn = MagicMock()
        service_conn.bind.return_value = True
        
        mock_entry = MagicMock()
        mock_entry.entry_dn = "CN=jsmith,OU=Users,DC=example,DC=com"
        service_conn.entries = [mock_entry]
        
        user_conn = MagicMock()
        user_conn.bind.return_value = False  # Invalid credentials
        
        mock_conn.side_effect = [service_conn, user_conn]
        
        backend = LdapAuthBackend(self.config)
        
        # Act
        with patch.object(backend, '_initialize_server'):
            result = backend.authenticate("jsmith", "wrong_pass")
        
        # Assert
        self.assertIsNone(result)
    
    @patch('khoj.processor.auth.ldap_backend.Connection')
    @patch('khoj.processor.auth.ldap_backend.Server')
    @patch.object(LdapAuthBackend, '_get_bind_credentials')
    def test_authenticate_user_not_found(self, mock_get_creds, mock_server, mock_conn):
        """Test authentication when user not found in LDAP."""
        # Arrange
        mock_get_creds.return_value = ("CN=service,DC=example,DC=com", "service_pass")
        
        service_conn = MagicMock()
        service_conn.bind.return_value = True
        service_conn.entries = []  # No user found
        
        mock_conn.return_value = service_conn
        
        backend = LdapAuthBackend(self.config)
        
        # Act
        with patch.object(backend, '_initialize_server'):
            result = backend.authenticate("unknownuser", "pass")
        
        # Assert
        self.assertIsNone(result)


class TestLdapInjectionPrevention(unittest.TestCase):
    """Test LDAP injection prevention."""
    
    def setUp(self):
        self.config = MagicMock(spec=LdapConfig)
        self.config.server_url = "ldaps://ldap.example.com:636"
        self.config.user_search_base = "OU=Users,DC=example,DC=com"
        self.config.user_search_filter = "(sAMAccountName={username})"
        self.config.use_tls = True
        self.config.tls_verify = True
        self.config.tls_ca_bundle_path = None
    
    def test_sanitize_username_escapes_special_chars(self):
        """Test that special LDAP characters are escaped."""
        backend = LdapAuthBackend(self.config)
        
        # Test wildcards
        result = backend._sanitize_username("admin*")
        self.assertEqual(result, "admin\\2a")
        
        # Test parentheses
        result = backend._sanitize_username("admin)(uid=*")
        self.assertIn("\\28", result)
        self.assertIn("\\29", result)
        
        # Test backslash
        result = backend._sanitize_username("domain\\user")
        self.assertEqual(result, "domain\\5cuser")
    
    def test_sanitize_username_preserves_valid_chars(self):
        """Test that valid characters are preserved."""
        backend = LdapAuthBackend(self.config)
        
        result = backend._sanitize_username("jsmith")
        self.assertEqual(result, "jsmith")
        
        result = backend._sanitize_username("john.doe")
        self.assertEqual(result, "john.doe")
        
        result = backend._sanitize_username("user123")
        self.assertEqual(result, "user123")
    
    def test_sanitize_username_rejects_empty(self):
        """Test that empty username raises ValueError."""
        backend = LdapAuthBackend(self.config)
        
        with self.assertRaises(ValueError):
            backend._sanitize_username("")
        
        with self.assertRaises(ValueError):
            backend._sanitize_username(None)


class TestUserProvisioning(unittest.TestCase):
    """Test user provisioning from LDAP."""
    
    def setUp(self):
        self.config = MagicMock(spec=LdapConfig)
        self.config.server_url = "ldaps://ldap.example.com"
    
    @patch('khoj.processor.auth.ldap_backend.KhojUser')
    def test_get_or_create_user_creates_new(self, mock_user_model):
        """Test that new user is created when not found."""
        backend = LdapAuthBackend(self.config)
        
        # Mock user not existing
        mock_user_model.objects.get.side_effect = KhojUser.DoesNotExist
        mock_user_model.objects.create.return_value = MagicMock(
            username="jsmith",
            email="jsmith@example.com"
        )
        
        ldap_attrs = {
            'dn': 'CN=jsmith,OU=Users,DC=example,DC=com',
            'username': 'jsmith',
            'email': 'jsmith@example.com'
        }
        
        # Act
        with patch.object(backend, '_initialize_server'):
            user = backend._get_or_create_user(ldap_attrs)
        
        # Assert
        mock_user_model.objects.create.assert_called_once()
    
    @patch('khoj.processor.auth.ldap_backend.KhojUser')
    def test_update_user_from_ldap_updates_fields(self, mock_user_model):
        """Test that user fields are updated from LDAP."""
        backend = LdapAuthBackend(self.config)
        
        mock_user = MagicMock()
        mock_user.first_name = ""
        mock_user.last_name = ""
        mock_user.email = "old@example.com"
        
        ldap_attrs = {
            'first_name': 'John',
            'last_name': 'Smith',
            'email': 'jsmith@example.com'
        }
        
        # Act
        with patch.object(backend, '_initialize_server'):
            backend._update_user_from_ldap(mock_user, ldap_attrs)
        
        # Assert
        self.assertEqual(mock_user.first_name, 'John')
        self.assertEqual(mock_user.last_name, 'Smith')
        self.assertEqual(mock_user.email, 'jsmith@example.com')
        mock_user.save.assert_called_once()


class TestAuditLogging(unittest.TestCase):
    """Test audit logging functionality."""
    
    def setUp(self):
        self.config = MagicMock(spec=LdapConfig)
        self.config.server_url = "ldaps://ldap.example.com"
    
    @patch('khoj.processor.auth.ldap_backend.logger')
    def test_log_auth_attempt_hashes_username(self, mock_logger):
        """Test that username is hashed in logs."""
        backend = LdapAuthBackend(self.config)
        
        # Act
        with patch.object(backend, '_initialize_server'):
            backend._log_auth_attempt("jsmith", "success", None)
        
        # Assert
        log_call = mock_logger.info.call_args[0][0]
        self.assertIn("AUDIT:", log_call)
        
        # Verify username is hashed (should be 16 char hex)
        log_data = json.loads(log_call.replace("AUDIT: ", ""))
        self.assertEqual(len(log_data['username_hash']), 16)
        self.assertNotEqual(log_data['username_hash'], "jsmith")
    
    @patch('khoj.processor.auth.ldap_backend.logger')
    def test_log_auth_attempt_includes_failure_reason(self, mock_logger):
        """Test that failure reason is included in logs."""
        backend = LdapAuthBackend(self.config)
        
        # Act
        with patch.object(backend, '_initialize_server'):
            backend._log_auth_attempt("jsmith", "failed", "invalid_credentials")
        
        # Assert
        log_call = mock_logger.info.call_args[0][0]
        log_data = json.loads(log_call.replace("AUDIT: ", ""))
        self.assertEqual(log_data['outcome'], "failed")
        self.assertEqual(log_data['failure_reason'], "invalid_credentials")


if __name__ == "__main__":
    unittest.main()

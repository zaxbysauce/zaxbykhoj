"""Tests for the secrets_vault module - HashiCorp Vault adapter.

These tests use mocks to avoid requiring a real Vault server.
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock, Mock

# Mock hvac before any imports
sys.modules['hvac'] = MagicMock()

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import after mocking hvac
from khoj.utils.secrets import LdapSecretError
from khoj.utils.secrets_vault import (
    VaultAdapter,
    is_vault_configured,
    get_ldap_credentials_from_vault,
    HVAC_AVAILABLE,
)


class TestModuleImport(unittest.TestCase):
    """Test that the module imports without errors."""

    def test_module_has_required_attributes(self):
        """Verify the secrets_vault module has all required attributes."""
        import khoj.utils.secrets_vault as vault_module
        self.assertTrue(hasattr(vault_module, 'VaultAdapter'))
        self.assertTrue(hasattr(vault_module, 'is_vault_configured'))
        self.assertTrue(hasattr(vault_module, 'get_ldap_credentials_from_vault'))
        self.assertTrue(hasattr(vault_module, 'LdapSecretError'))
        self.assertTrue(hasattr(vault_module, 'HVAC_AVAILABLE'))

    def test_hvac_available_is_true_when_mocked(self):
        """Verify HVAC_AVAILABLE is True when hvac is mocked."""
        self.assertTrue(HVAC_AVAILABLE)


class TestIsVaultConfigured(unittest.TestCase):
    """Test is_vault_configured function."""

    @patch.dict(os.environ, {}, clear=True)
    def test_returns_false_when_no_env_vars_set(self):
        """Test that False is returned when no Vault env vars are set."""
        result = is_vault_configured()
        self.assertFalse(result)

    @patch.dict(os.environ, {"KHOJ_VAULT_ADDR": "http://vault:8200"}, clear=True)
    def test_returns_false_when_only_addr_set(self):
        """Test that False is returned when only KHOJ_VAULT_ADDR is set."""
        result = is_vault_configured()
        self.assertFalse(result)

    @patch.dict(os.environ, {"KHOJ_VAULT_TOKEN": "test-token"}, clear=True)
    def test_returns_false_when_only_token_set(self):
        """Test that False is returned when only KHOJ_VAULT_TOKEN is set."""
        result = is_vault_configured()
        self.assertFalse(result)

    @patch.dict(os.environ, {"KHOJ_VAULT_PATH": "secret/data/khoj/ldap"}, clear=True)
    def test_returns_false_when_only_path_set(self):
        """Test that False is returned when only KHOJ_VAULT_PATH is set."""
        result = is_vault_configured()
        self.assertFalse(result)

    @patch.dict(os.environ, {
        "KHOJ_VAULT_ADDR": "http://vault:8200",
        "KHOJ_VAULT_TOKEN": "test-token"
    }, clear=True)
    def test_returns_false_when_only_addr_and_token_set(self):
        """Test that False is returned when only addr and token are set."""
        result = is_vault_configured()
        self.assertFalse(result)

    @patch.dict(os.environ, {
        "KHOJ_VAULT_ADDR": "http://vault:8200",
        "KHOJ_VAULT_TOKEN": "test-token",
        "KHOJ_VAULT_PATH": "secret/data/khoj/ldap"
    }, clear=True)
    def test_returns_true_when_all_required_env_vars_set(self):
        """Test that True is returned when all required Vault env vars are set."""
        result = is_vault_configured()
        self.assertTrue(result)

    @patch.dict(os.environ, {
        "KHOJ_VAULT_ADDR": "",
        "KHOJ_VAULT_TOKEN": "test-token",
        "KHOJ_VAULT_PATH": "secret/data/khoj/ldap"
    }, clear=True)
    def test_returns_false_when_addr_is_empty(self):
        """Test that False is returned when KHOJ_VAULT_ADDR is empty string."""
        result = is_vault_configured()
        self.assertFalse(result)

    @patch.dict(os.environ, {
        "KHOJ_VAULT_ADDR": "http://vault:8200",
        "KHOJ_VAULT_TOKEN": "",
        "KHOJ_VAULT_PATH": "secret/data/khoj/ldap"
    }, clear=True)
    def test_returns_false_when_token_is_empty(self):
        """Test that False is returned when KHOJ_VAULT_TOKEN is empty string."""
        result = is_vault_configured()
        self.assertFalse(result)

    @patch.dict(os.environ, {
        "KHOJ_VAULT_ADDR": "http://vault:8200",
        "KHOJ_VAULT_TOKEN": "test-token",
        "KHOJ_VAULT_PATH": ""
    }, clear=True)
    def test_returns_false_when_path_is_empty(self):
        """Test that False is returned when KHOJ_VAULT_PATH is empty string."""
        result = is_vault_configured()
        self.assertFalse(result)


class TestVaultAdapterInit(unittest.TestCase):
    """Test VaultAdapter initialization."""

    @patch.dict(os.environ, {}, clear=True)
    def test_raises_error_when_env_vars_not_set(self):
        """Test that LdapSecretError is raised when Vault env vars are not set."""
        with self.assertRaises(LdapSecretError) as context:
            VaultAdapter()
        self.assertIn("vault configuration incomplete", str(context.exception).lower())

    @patch.dict(os.environ, {"KHOJ_VAULT_ADDR": "http://vault:8200"}, clear=True)
    def test_raises_error_when_vault_token_not_set(self):
        """Test that LdapSecretError is raised when KHOJ_VAULT_TOKEN is not set."""
        with self.assertRaises(LdapSecretError) as context:
            VaultAdapter()
        self.assertIn("vault configuration incomplete", str(context.exception).lower())

    @patch.dict(os.environ, {
        "KHOJ_VAULT_ADDR": "http://vault:8200",
        "KHOJ_VAULT_TOKEN": "test-token"
    }, clear=True)
    @patch('khoj.utils.secrets_vault.hvac.Client')
    def test_initializes_client_when_env_vars_set(self, mock_client_class):
        """Test that Vault client is initialized when env vars are set."""
        mock_client = MagicMock()
        mock_client.is_authenticated.return_value = True
        mock_client_class.return_value = mock_client
        
        adapter = VaultAdapter()
        
        mock_client_class.assert_called_once_with(
            url="http://vault:8200",
            token="test-token"
        )
        self.assertEqual(adapter.client, mock_client)

    @patch.dict(os.environ, {
        "KHOJ_VAULT_ADDR": "http://vault:8200",
        "KHOJ_VAULT_TOKEN": "test-token"
    }, clear=True)
    @patch('khoj.utils.secrets_vault.hvac.Client')
    def test_raises_error_when_authentication_fails(self, mock_client_class):
        """Test that LdapSecretError is raised when Vault authentication fails."""
        mock_client = MagicMock()
        mock_client.is_authenticated.return_value = False
        mock_client_class.return_value = mock_client
        
        with self.assertRaises(LdapSecretError) as context:
            VaultAdapter()
        self.assertIn("authentication failed", str(context.exception).lower())

    @patch.dict(os.environ, {
        "KHOJ_VAULT_ADDR": "http://vault:8200",
        "KHOJ_VAULT_TOKEN": "test-token"
    }, clear=True)
    @patch('khoj.utils.secrets_vault.hvac.Client')
    def test_raises_error_when_client_creation_fails(self, mock_client_class):
        """Test that LdapSecretError is raised when client creation fails."""
        mock_client_class.side_effect = Exception("Connection refused")
        
        with self.assertRaises(LdapSecretError) as context:
            VaultAdapter()
        self.assertIn("failed to connect", str(context.exception).lower())

    @patch.dict(os.environ, {
        "KHOJ_VAULT_ADDR": "http://vault:8200",
        "KHOJ_VAULT_TOKEN": "test-token",
        "KHOJ_VAULT_CACHE_TTL": "600"
    }, clear=True)
    @patch('khoj.utils.secrets_vault.hvac.Client')
    def test_uses_custom_cache_ttl_from_env(self, mock_client_class):
        """Test that custom cache TTL is read from environment."""
        mock_client = MagicMock()
        mock_client.is_authenticated.return_value = True
        mock_client_class.return_value = mock_client
        
        adapter = VaultAdapter()
        
        self.assertEqual(adapter._cache_ttl, 600)


class TestVaultAdapterGetLdapCredentials(unittest.TestCase):
    """Test VaultAdapter.get_ldap_credentials method."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.mock_response = {
            "data": {
                "data": {
                    "bind_dn": "CN=service,DC=example,DC=com",
                    "bind_password": "secret_password_123"
                }
            }
        }
        self.mock_client.secrets.kv.v2.read_secret_version.return_value = self.mock_response
        self.mock_client.is_authenticated.return_value = True

    @patch.dict(os.environ, {
        "KHOJ_VAULT_ADDR": "http://vault:8200",
        "KHOJ_VAULT_TOKEN": "test-token",
        "KHOJ_VAULT_PATH": "secret/data/khoj/ldap"
    }, clear=True)
    @patch('khoj.utils.secrets_vault.hvac.Client')
    def test_returns_credentials_from_vault(self, mock_client_class):
        """Test that credentials are retrieved from Vault."""
        mock_client_class.return_value = self.mock_client
        
        adapter = VaultAdapter()
        bind_dn, bind_password = adapter.get_ldap_credentials()
        
        self.assertEqual(bind_dn, "CN=service,DC=example,DC=com")
        self.assertEqual(bind_password, "secret_password_123")

    @patch.dict(os.environ, {
        "KHOJ_VAULT_ADDR": "http://vault:8200",
        "KHOJ_VAULT_TOKEN": "test-token",
        "KHOJ_VAULT_PATH": "secret/data/khoj/ldap"
    }, clear=True)
    @patch('khoj.utils.secrets_vault.hvac.Client')
    def test_uses_correct_vault_path(self, mock_client_class):
        """Test that the correct Vault path is used."""
        mock_client_class.return_value = self.mock_client
        
        adapter = VaultAdapter()
        adapter.get_ldap_credentials()
        
        self.mock_client.secrets.kv.v2.read_secret_version.assert_called_once_with(
            path="khoj/ldap",
            mount_point="secret"
        )

    @patch.dict(os.environ, {
        "KHOJ_VAULT_ADDR": "http://vault:8200",
        "KHOJ_VAULT_TOKEN": "test-token",
        "KHOJ_VAULT_PATH": "custom/data/app/secrets"
    }, clear=True)
    @patch('khoj.utils.secrets_vault.hvac.Client')
    def test_uses_custom_vault_path(self, mock_client_class):
        """Test that custom Vault path is used when set."""
        mock_client_class.return_value = self.mock_client
        
        adapter = VaultAdapter()
        adapter.get_ldap_credentials()
        
        self.mock_client.secrets.kv.v2.read_secret_version.assert_called_once_with(
            path="app/secrets",
            mount_point="custom"
        )

    @patch.dict(os.environ, {
        "KHOJ_VAULT_ADDR": "http://vault:8200",
        "KHOJ_VAULT_TOKEN": "test-token",
        "KHOJ_VAULT_PATH": "secret/data/khoj/ldap"
    }, clear=True)
    @patch('khoj.utils.secrets_vault.hvac.Client')
    def test_raises_error_when_bind_dn_missing(self, mock_client_class):
        """Test that LdapSecretError is raised when bind_dn is missing."""
        mock_response = {
            "data": {
                "data": {
                    "bind_password": "secret_password_123"
                }
            }
        }
        self.mock_client.secrets.kv.v2.read_secret_version.return_value = mock_response
        mock_client_class.return_value = self.mock_client
        
        adapter = VaultAdapter()
        with self.assertRaises(LdapSecretError) as context:
            adapter.get_ldap_credentials()
        self.assertIn("missing required fields", str(context.exception).lower())

    @patch.dict(os.environ, {
        "KHOJ_VAULT_ADDR": "http://vault:8200",
        "KHOJ_VAULT_TOKEN": "test-token",
        "KHOJ_VAULT_PATH": "secret/data/khoj/ldap"
    }, clear=True)
    @patch('khoj.utils.secrets_vault.hvac.Client')
    def test_raises_error_when_bind_password_missing(self, mock_client_class):
        """Test that LdapSecretError is raised when bind_password is missing."""
        mock_response = {
            "data": {
                "data": {
                    "bind_dn": "CN=service,DC=example,DC=com"
                }
            }
        }
        self.mock_client.secrets.kv.v2.read_secret_version.return_value = mock_response
        mock_client_class.return_value = self.mock_client
        
        adapter = VaultAdapter()
        with self.assertRaises(LdapSecretError) as context:
            adapter.get_ldap_credentials()
        self.assertIn("missing required fields", str(context.exception).lower())

    @patch.dict(os.environ, {
        "KHOJ_VAULT_ADDR": "http://vault:8200",
        "KHOJ_VAULT_TOKEN": "test-token",
        "KHOJ_VAULT_PATH": "secret/data/khoj/ldap"
    }, clear=True)
    @patch('khoj.utils.secrets_vault.hvac.Client')
    def test_raises_error_when_vault_read_fails(self, mock_client_class):
        """Test that LdapSecretError is raised when Vault read fails."""
        self.mock_client.secrets.kv.v2.read_secret_version.side_effect = Exception("Permission denied")
        mock_client_class.return_value = self.mock_client
        
        adapter = VaultAdapter()
        with self.assertRaises(LdapSecretError) as context:
            adapter.get_ldap_credentials()
        self.assertIn("failed to retrieve secrets", str(context.exception).lower())


class TestVaultAdapterCaching(unittest.TestCase):
    """Test VaultAdapter caching behavior."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.mock_response = {
            "data": {
                "data": {
                    "bind_dn": "CN=service,DC=example,DC=com",
                    "bind_password": "secret_password_123"
                }
            }
        }
        self.mock_client.secrets.kv.v2.read_secret_version.return_value = self.mock_response
        self.mock_client.is_authenticated.return_value = True

    @patch.dict(os.environ, {
        "KHOJ_VAULT_ADDR": "http://vault:8200",
        "KHOJ_VAULT_TOKEN": "test-token",
        "KHOJ_VAULT_PATH": "secret/data/khoj/ldap"
    }, clear=True)
    @patch('khoj.utils.secrets_vault.hvac.Client')
    @patch('khoj.utils.secrets_vault.time.time')
    def test_uses_cache_when_valid(self, mock_time, mock_client_class):
        """Test that cached credentials are returned when cache is valid."""
        mock_client_class.return_value = self.mock_client
        mock_time.return_value = 1000.0
        
        adapter = VaultAdapter()
        
        # First call - should read from Vault
        adapter.get_ldap_credentials()
        self.assertEqual(self.mock_client.secrets.kv.v2.read_secret_version.call_count, 1)
        
        # Second call - should use cache
        mock_time.return_value = 1100.0  # 100 seconds later (within default 300s TTL)
        adapter.get_ldap_credentials()
        self.assertEqual(self.mock_client.secrets.kv.v2.read_secret_version.call_count, 1)

    @patch.dict(os.environ, {
        "KHOJ_VAULT_ADDR": "http://vault:8200",
        "KHOJ_VAULT_TOKEN": "test-token",
        "KHOJ_VAULT_PATH": "secret/data/khoj/ldap"
    }, clear=True)
    @patch('khoj.utils.secrets_vault.hvac.Client')
    @patch('khoj.utils.secrets_vault.time.time')
    def test_refreshes_cache_when_expired(self, mock_time, mock_client_class):
        """Test that Vault is called again when cache is expired."""
        mock_client_class.return_value = self.mock_client
        mock_time.return_value = 1000.0
        
        adapter = VaultAdapter()
        
        # First call - should read from Vault
        adapter.get_ldap_credentials()
        self.assertEqual(self.mock_client.secrets.kv.v2.read_secret_version.call_count, 1)
        
        # Second call after cache expiry - should read from Vault again
        mock_time.return_value = 1500.0  # 500 seconds later (beyond default 300s TTL)
        adapter.get_ldap_credentials()
        self.assertEqual(self.mock_client.secrets.kv.v2.read_secret_version.call_count, 2)

    @patch.dict(os.environ, {
        "KHOJ_VAULT_ADDR": "http://vault:8200",
        "KHOJ_VAULT_TOKEN": "test-token",
        "KHOJ_VAULT_PATH": "secret/data/khoj/ldap"
    }, clear=True)
    @patch('khoj.utils.secrets_vault.hvac.Client')
    def test_clear_cache_empties_cache(self, mock_client_class):
        """Test that clear_cache empties the cache."""
        mock_client_class.return_value = self.mock_client
        
        adapter = VaultAdapter()
        
        # First call to populate cache
        adapter.get_ldap_credentials()
        self.assertTrue(adapter._cache)
        
        # Clear cache
        adapter.clear_cache()
        self.assertFalse(adapter._cache)
        self.assertEqual(adapter._cache_timestamp, 0)


class TestVaultAdapterLogging(unittest.TestCase):
    """Test that no secrets are logged by VaultAdapter."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.mock_response = {
            "data": {
                "data": {
                    "bind_dn": "CN=service,DC=example,DC=com",
                    "bind_password": "secret_password_123"
                }
            }
        }
        self.mock_client.secrets.kv.v2.read_secret_version.return_value = self.mock_response
        self.mock_client.is_authenticated.return_value = True

    @patch.dict(os.environ, {
        "KHOJ_VAULT_ADDR": "http://vault:8200",
        "KHOJ_VAULT_TOKEN": "test-token",
        "KHOJ_VAULT_PATH": "secret/data/khoj/ldap"
    }, clear=True)
    @patch('khoj.utils.secrets_vault.hvac.Client')
    @patch('khoj.utils.secrets_vault.logger')
    def test_debug_logs_do_not_contain_password(self, mock_logger, mock_client_class):
        """Test that debug log messages don't contain the password."""
        mock_client_class.return_value = self.mock_client
        
        adapter = VaultAdapter()
        adapter.get_ldap_credentials()
        
        # Check that debug logs were called
        debug_calls = [call for call in mock_logger.debug.call_args_list]
        self.assertTrue(len(debug_calls) > 0)
        
        # Verify no log message contains the actual password
        for call in mock_logger.debug.call_args_list:
            log_message = str(call)
            self.assertNotIn("secret_password_123", log_message)

    @patch.dict(os.environ, {
        "KHOJ_VAULT_ADDR": "http://vault:8200",
        "KHOJ_VAULT_TOKEN": "test-token",
        "KHOJ_VAULT_PATH": "secret/data/khoj/ldap"
    }, clear=True)
    @patch('khoj.utils.secrets_vault.hvac.Client')
    @patch('khoj.utils.secrets_vault.logger')
    def test_error_logs_do_not_contain_password(self, mock_logger, mock_client_class):
        """Test that error log messages don't contain the password."""
        self.mock_client.secrets.kv.v2.read_secret_version.side_effect = Exception("Permission denied")
        mock_client_class.return_value = self.mock_client
        
        adapter = VaultAdapter()
        with self.assertRaises(LdapSecretError):
            adapter.get_ldap_credentials()
        
        # Check that exception was logged (using logger.exception)
        mock_logger.exception.assert_called()

        # Verify no log message contains the password
        for call in mock_logger.exception.call_args_list:
            log_message = str(call)
            self.assertNotIn("secret_password_123", log_message)


class TestGetLdapCredentialsFromVault(unittest.TestCase):
    """Test get_ldap_credentials_from_vault convenience function."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.mock_response = {
            "data": {
                "data": {
                    "bind_dn": "CN=service,DC=example,DC=com",
                    "bind_password": "secret_password_123"
                }
            }
        }
        self.mock_client.secrets.kv.v2.read_secret_version.return_value = self.mock_response
        self.mock_client.is_authenticated.return_value = True

    @patch.dict(os.environ, {
        "KHOJ_VAULT_ADDR": "http://vault:8200",
        "KHOJ_VAULT_TOKEN": "test-token",
        "KHOJ_VAULT_PATH": "secret/data/khoj/ldap"
    }, clear=True)
    @patch('khoj.utils.secrets_vault.hvac.Client')
    def test_returns_credentials(self, mock_client_class):
        """Test that the convenience function returns credentials."""
        mock_client_class.return_value = self.mock_client
        
        bind_dn, bind_password = get_ldap_credentials_from_vault()
        
        self.assertEqual(bind_dn, "CN=service,DC=example,DC=com")
        self.assertEqual(bind_password, "secret_password_123")

    @patch.dict(os.environ, {}, clear=True)
    def test_raises_error_when_not_configured(self):
        """Test that LdapSecretError is raised when Vault is not configured."""
        with self.assertRaises(LdapSecretError):
            get_ldap_credentials_from_vault()


class TestVaultPathParsing(unittest.TestCase):
    """Test Vault path parsing for different formats."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.mock_response = {
            "data": {
                "data": {
                    "bind_dn": "CN=service,DC=example,DC=com",
                    "bind_password": "secret_password_123"
                }
            }
        }
        self.mock_client.secrets.kv.v2.read_secret_version.return_value = self.mock_response
        self.mock_client.is_authenticated.return_value = True

    @patch.dict(os.environ, {
        "KHOJ_VAULT_ADDR": "http://vault:8200",
        "KHOJ_VAULT_TOKEN": "test-token",
        "KHOJ_VAULT_PATH": "secret/data/khoj/ldap"
    }, clear=True)
    @patch('khoj.utils.secrets_vault.hvac.Client')
    def test_parses_standard_kv_v2_path(self, mock_client_class):
        """Test parsing of standard KV v2 path format."""
        mock_client_class.return_value = self.mock_client
        
        adapter = VaultAdapter()
        adapter.get_ldap_credentials()
        
        self.mock_client.secrets.kv.v2.read_secret_version.assert_called_once_with(
            path="khoj/ldap",
            mount_point="secret"
        )

    @patch.dict(os.environ, {
        "KHOJ_VAULT_ADDR": "http://vault:8200",
        "KHOJ_VAULT_TOKEN": "test-token",
        "KHOJ_VAULT_PATH": "secret/data/deep/nested/path"
    }, clear=True)
    @patch('khoj.utils.secrets_vault.hvac.Client')
    def test_parses_deeply_nested_path(self, mock_client_class):
        """Test parsing of deeply nested path."""
        mock_client_class.return_value = self.mock_client
        
        adapter = VaultAdapter()
        adapter.get_ldap_credentials()
        
        self.mock_client.secrets.kv.v2.read_secret_version.assert_called_once_with(
            path="deep/nested/path",
            mount_point="secret"
        )

    @patch.dict(os.environ, {
        "KHOJ_VAULT_ADDR": "http://vault:8200",
        "KHOJ_VAULT_TOKEN": "test-token",
        "KHOJ_VAULT_PATH": "kv/secret/path"
    }, clear=True)
    @patch('khoj.utils.secrets_vault.hvac.Client')
    def test_handles_path_without_data_prefix(self, mock_client_class):
        """Test handling of path without /data/ prefix."""
        mock_client_class.return_value = self.mock_client
        
        adapter = VaultAdapter()
        adapter.get_ldap_credentials()
        
        self.mock_client.secrets.kv.v2.read_secret_version.assert_called_once_with(
            path="secret/path",
            mount_point="kv"
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)

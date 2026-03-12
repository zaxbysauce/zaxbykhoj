"""Standalone tests for the secrets module - no Django dependencies."""
import os
import sys
import unittest
from unittest.mock import patch

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import the module directly without Django setup
import importlib.util
spec = importlib.util.spec_from_file_location("secrets", os.path.join(os.path.dirname(__file__), '..', 'src', 'khoj', 'utils', 'secrets.py'))
secrets_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(secrets_module)

LdapSecretError = secrets_module.LdapSecretError
get_ldap_bind_dn = secrets_module.get_ldap_bind_dn
get_ldap_bind_password = secrets_module.get_ldap_bind_password
get_ldap_credentials = secrets_module.get_ldap_credentials
has_ldap_credentials = secrets_module.has_ldap_credentials
set_ldap_credentials = secrets_module.set_ldap_credentials


class TestModuleImport(unittest.TestCase):
    """Test that the module imports without errors."""

    def test_module_has_required_attributes(self):
        """Verify the secrets module has all required attributes."""
        self.assertTrue(hasattr(secrets_module, 'LdapSecretError'))
        self.assertTrue(hasattr(secrets_module, 'get_ldap_bind_dn'))
        self.assertTrue(hasattr(secrets_module, 'get_ldap_bind_password'))
        self.assertTrue(hasattr(secrets_module, 'get_ldap_credentials'))
        self.assertTrue(hasattr(secrets_module, 'has_ldap_credentials'))
        self.assertTrue(hasattr(secrets_module, 'set_ldap_credentials'))


class TestGetLdapBindDn(unittest.TestCase):
    """Test get_ldap_bind_dn function."""

    @patch.dict(os.environ, {}, clear=True)
    def test_raises_error_when_env_var_not_set(self):
        """Test that LdapSecretError is raised when KHOJ_LDAP_BIND_DN is not set."""
        with self.assertRaises(LdapSecretError) as context:
            get_ldap_bind_dn()
        self.assertIn("KHOJ_LDAP_BIND_DN environment variable not set", str(context.exception))

    @patch.dict(os.environ, {"KHOJ_LDAP_BIND_DN": "CN=service,DC=example,DC=com"})
    def test_returns_value_when_env_var_set(self):
        """Test that the correct value is returned when KHOJ_LDAP_BIND_DN is set."""
        expected_dn = "CN=service,DC=example,DC=com"
        result = get_ldap_bind_dn()
        self.assertEqual(result, expected_dn)

    @patch.dict(os.environ, {"KHOJ_LDAP_BIND_DN": ""})
    def test_raises_error_when_env_var_empty(self):
        """Test that LdapSecretError is raised when KHOJ_LDAP_BIND_DN is empty string."""
        with self.assertRaises(LdapSecretError) as context:
            get_ldap_bind_dn()
        self.assertIn("KHOJ_LDAP_BIND_DN environment variable not set", str(context.exception))


class TestGetLdapBindPassword(unittest.TestCase):
    """Test get_ldap_bind_password function."""

    @patch.dict(os.environ, {}, clear=True)
    def test_raises_error_when_env_var_not_set(self):
        """Test that LdapSecretError is raised when KHOJ_LDAP_BIND_PASSWORD is not set."""
        with self.assertRaises(LdapSecretError) as context:
            get_ldap_bind_password()
        self.assertIn("KHOJ_LDAP_BIND_PASSWORD environment variable not set", str(context.exception))

    @patch.dict(os.environ, {"KHOJ_LDAP_BIND_PASSWORD": "secret_password_123"})
    def test_returns_value_when_env_var_set(self):
        """Test that the correct value is returned when KHOJ_LDAP_BIND_PASSWORD is set."""
        expected_password = "secret_password_123"
        result = get_ldap_bind_password()
        self.assertEqual(result, expected_password)

    @patch.dict(os.environ, {"KHOJ_LDAP_BIND_PASSWORD": ""})
    def test_raises_error_when_env_var_empty(self):
        """Test that LdapSecretError is raised when KHOJ_LDAP_BIND_PASSWORD is empty string."""
        with self.assertRaises(LdapSecretError) as context:
            get_ldap_bind_password()
        self.assertIn("KHOJ_LDAP_BIND_PASSWORD environment variable not set", str(context.exception))


class TestGetLdapCredentials(unittest.TestCase):
    """Test get_ldap_credentials function."""

    @patch.dict(os.environ, {"KHOJ_LDAP_BIND_PASSWORD": "password123"}, clear=True)
    def test_raises_error_when_bind_dn_not_set(self):
        """Test that LdapSecretError is raised when KHOJ_LDAP_BIND_DN is not set."""
        with self.assertRaises(LdapSecretError) as context:
            get_ldap_credentials()
        self.assertIn("KHOJ_LDAP_BIND_DN environment variable not set", str(context.exception))

    @patch.dict(os.environ, {"KHOJ_LDAP_BIND_DN": "CN=service,DC=example,DC=com"}, clear=True)
    def test_raises_error_when_password_not_set(self):
        """Test that LdapSecretError is raised when KHOJ_LDAP_BIND_PASSWORD is not set."""
        with self.assertRaises(LdapSecretError) as context:
            get_ldap_credentials()
        self.assertIn("KHOJ_LDAP_BIND_PASSWORD environment variable not set", str(context.exception))

    @patch.dict(os.environ, {}, clear=True)
    def test_raises_error_when_neither_set(self):
        """Test that LdapSecretError is raised when neither credential is set."""
        with self.assertRaises(LdapSecretError) as context:
            get_ldap_credentials()
        # Should fail on bind DN first
        self.assertIn("KHOJ_LDAP_BIND_DN environment variable not set", str(context.exception))

    @patch.dict(os.environ, {
        "KHOJ_LDAP_BIND_DN": "CN=service,DC=example,DC=com",
        "KHOJ_LDAP_BIND_PASSWORD": "secret_password_123"
    })
    def test_returns_tuple_when_both_set(self):
        """Test that a tuple is returned when both credentials are set."""
        expected_dn = "CN=service,DC=example,DC=com"
        expected_password = "secret_password_123"
        result = get_ldap_credentials()
        self.assertIsInstance(result, tuple)
        self.assertEqual(result, (expected_dn, expected_password))


class TestHasLdapCredentials(unittest.TestCase):
    """Test has_ldap_credentials function."""

    @patch.dict(os.environ, {}, clear=True)
    def test_returns_false_when_neither_set(self):
        """Test that False is returned when neither credential is set."""
        result = has_ldap_credentials()
        self.assertFalse(result)

    @patch.dict(os.environ, {"KHOJ_LDAP_BIND_DN": "CN=service,DC=example,DC=com"}, clear=True)
    def test_returns_false_when_only_bind_dn_set(self):
        """Test that False is returned when only KHOJ_LDAP_BIND_DN is set."""
        result = has_ldap_credentials()
        self.assertFalse(result)

    @patch.dict(os.environ, {"KHOJ_LDAP_BIND_PASSWORD": "password123"}, clear=True)
    def test_returns_false_when_only_password_set(self):
        """Test that False is returned when only KHOJ_LDAP_BIND_PASSWORD is set."""
        result = has_ldap_credentials()
        self.assertFalse(result)

    @patch.dict(os.environ, {
        "KHOJ_LDAP_BIND_DN": "CN=service,DC=example,DC=com",
        "KHOJ_LDAP_BIND_PASSWORD": "password123"
    })
    def test_returns_true_when_both_set(self):
        """Test that True is returned when both credentials are set."""
        result = has_ldap_credentials()
        self.assertTrue(result)

    @patch.dict(os.environ, {
        "KHOJ_LDAP_BIND_DN": "",
        "KHOJ_LDAP_BIND_PASSWORD": "password123"
    })
    def test_returns_false_when_bind_dn_is_empty(self):
        """Test that False is returned when KHOJ_LDAP_BIND_DN is empty string."""
        result = has_ldap_credentials()
        self.assertFalse(result)

    @patch.dict(os.environ, {
        "KHOJ_LDAP_BIND_DN": "CN=service,DC=example,DC=com",
        "KHOJ_LDAP_BIND_PASSWORD": ""
    })
    def test_returns_false_when_password_is_empty(self):
        """Test that False is returned when KHOJ_LDAP_BIND_PASSWORD is empty string."""
        result = has_ldap_credentials()
        self.assertFalse(result)

    @patch.dict(os.environ, {
        "KHOJ_LDAP_BIND_DN": "",
        "KHOJ_LDAP_BIND_PASSWORD": ""
    })
    def test_returns_false_when_both_empty(self):
        """Test that False is returned when both credentials are empty strings."""
        result = has_ldap_credentials()
        self.assertFalse(result)



class TestSetLdapCredentials(unittest.TestCase):
    """Test set_ldap_credentials function."""

    @patch.dict(os.environ, {}, clear=True)
    def test_sets_credentials_in_environment(self):
        set_ldap_credentials("CN=svc,DC=example,DC=com", "secret")
        self.assertEqual(os.environ.get("KHOJ_LDAP_BIND_DN"), "CN=svc,DC=example,DC=com")
        self.assertEqual(os.environ.get("KHOJ_LDAP_BIND_PASSWORD"), "secret")

    @patch.dict(os.environ, {}, clear=True)
    def test_rejects_empty_dn(self):
        with self.assertRaises(LdapSecretError):
            set_ldap_credentials("", "secret")

    @patch.dict(os.environ, {}, clear=True)
    def test_rejects_empty_password(self):
        with self.assertRaises(LdapSecretError):
            set_ldap_credentials("CN=svc,DC=example,DC=com", "")


if __name__ == '__main__':
    unittest.main(verbosity=2)

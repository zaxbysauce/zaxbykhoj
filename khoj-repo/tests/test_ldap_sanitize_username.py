"""Tests for LdapAuthBackend._sanitize_username() method.

These tests verify LDAP injection prevention, edge cases, DoS prevention,
and valid input handling for the username sanitization method.
"""
import sys
import os
import logging

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from khoj.processor.auth.ldap_backend import LdapAuthBackend


# Mock the config class for testing
class MockLdapConfig:
    """Mock LDAP configuration for testing."""
    def __init__(self):
        self.server_url = "ldaps://ldap.example.com"
        self.use_tls = True
        self.tls_verify = True
        self.tls_ca_bundle_path = None
        self.user_search_base = "dc=example,dc=com"
        self.user_search_filter = "(sAMAccountName={username})"


def get_backend():
    """Create a LdapAuthBackend instance with mocked config."""
    return LdapAuthBackend(MockLdapConfig())


class TestLdapInjectionPrevention:
    """Test LDAP injection prevention - special characters should be escaped."""
    
    def test_wildcard_injection_pattern(self):
        """Test input: *)(uid=* should be escaped."""
        backend = get_backend()
        result = backend._sanitize_username('*)(uid=*')
        # ldap3 escape_filter_chars escapes * as \2a and ( as \28 and ) as \29
        assert '*(' not in result, f"Injection pattern still present: {repr(result)}"
        assert ')*' not in result, f"Injection pattern still present: {repr(result)}"
    
    def test_admin_wildcard_injection(self):
        """Test input: admin*)(uid=* should be escaped."""
        backend = get_backend()
        result = backend._sanitize_username('admin*)(uid=*')
        # The injection pattern should be escaped
        assert '*(' not in result, f"Injection pattern still present: {repr(result)}"
        assert ')*' not in result, f"Injection pattern still present: {repr(result)}"
        # admin should be preserved (escaped)
        assert 'admin' in result, f"Admin text not preserved: {repr(result)}"
    
    def test_single_wildcard(self):
        """Test input: * (wildcard) should be escaped."""
        backend = get_backend()
        result = backend._sanitize_username('*')
        assert result != '*', f"Wildcard not escaped: {repr(result)}"
        assert '2a' in result, f"Escaped wildcard not found: {repr(result)}"
    
    def test_cn_admin_injection(self):
        """Test input: (cn=admin) should be escaped."""
        backend = get_backend()
        result = backend._sanitize_username('(cn=admin)')
        assert '28' in result, f"Opening paren not escaped: {repr(result)}"
        assert '29' in result, f"Closing paren not escaped: {repr(result)}"
        # cn=admin should be preserved but escaped
        assert 'cn=admin' in result, f"cn=admin text not preserved: {repr(result)}"


class TestEdgeCases:
    """Test edge cases for username sanitization."""
    
    def test_empty_string_raises_valueerror(self):
        """Test empty string raises ValueError."""
        backend = get_backend()
        try:
            backend._sanitize_username('')
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "Username cannot be empty or None" in str(e)
    
    def test_none_raises_valueerror(self):
        """Test None raises ValueError."""
        backend = get_backend()
        try:
            backend._sanitize_username(None)
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "Username cannot be empty or None" in str(e)
    
    def test_unicode_username(self):
        """Test Unicode: josé should work."""
        backend = get_backend()
        result = backend._sanitize_username('josé')
        assert 'josé' in result, f"Unicode not preserved: {repr(result)}"
    
    def test_very_long_input_gets_truncated(self):
        """Test very long input gets truncated to 256 characters."""
        backend = get_backend()
        long_username = 'a' * 500
        result = backend._sanitize_username(long_username)
        # After escaping, length might be longer due to escape sequences
        # But the base username should be truncated to 256 before escaping
        assert len(result) <= 256 * 3, f"Result too long: {len(result)}"


class TestDoSPrevention:
    """Test DoS prevention through input length limits."""
    
    def test_1000_character_input_truncated(self):
        """Test 1000 character input gets truncated to 256."""
        backend = get_backend()
        long_username = 'x' * 1000
        result = backend._sanitize_username(long_username)
        # The result should not contain all 1000 characters
        assert 'x' * 257 not in result, "Input not truncated"
    
    def test_truncation_warning_logged(self, caplog=None):
        """Verify truncation warning is logged."""
        backend = get_backend()
        
        # Set log level to capture warnings
        if caplog:
            # Running under pytest with caplog fixture
            with caplog.at_level(logging.WARNING):
                long_username = 'a' * 300
                backend._sanitize_username(long_username)
            
            # Check for truncation warning
            assert any("truncat" in record.message.lower() for record in caplog.records), \
                "No truncation warning logged"
        else:
            # Running standalone - verify logger is called via mock
            import unittest.mock
            with unittest.mock.patch('khoj.processor.auth.ldap_backend.logger') as mock_logger:
                long_username = 'a' * 300
                backend._sanitize_username(long_username)
                
                # Verify warning was called
                assert mock_logger.warning.called, "No truncation warning logged"
                # Check the warning message contains "truncat"
                call_args = mock_logger.warning.call_args
                assert call_args and "truncat" in str(call_args).lower(), \
                    f"Warning message doesn't mention truncation: {call_args}"


class TestValidInput:
    """Test valid username inputs pass through correctly."""
    
    def test_normal_username(self):
        """Test normal username: jsmith passes unchanged."""
        backend = get_backend()
        result = backend._sanitize_username('jsmith')
        assert result == 'jsmith', f"Got: {repr(result)}"
    
    def test_username_with_dots(self):
        """Test username with dots: john.doe passes unchanged."""
        backend = get_backend()
        result = backend._sanitize_username('john.doe')
        assert result == 'john.doe', f"Got: {repr(result)}"
    
    def test_username_with_numbers(self):
        """Test username with numbers: user123 passes unchanged."""
        backend = get_backend()
        result = backend._sanitize_username('user123')
        assert result == 'user123', f"Got: {repr(result)}"
    
    def test_username_with_underscore(self):
        """Test username with underscore: john_doe passes unchanged."""
        backend = get_backend()
        result = backend._sanitize_username('john_doe')
        assert result == 'john_doe', f"Got: {repr(result)}"
    
    def test_username_with_hyphen(self):
        """Test username with hyphen: john-doe passes unchanged."""
        backend = get_backend()
        result = backend._sanitize_username('john-doe')
        assert result == 'john-doe', f"Got: {repr(result)}"


class TestBackslashEscaping:
    """Test backslash escaping for LDAP injection prevention."""
    
    def test_backslash_in_username(self):
        """Test backslash is escaped properly."""
        backend = get_backend()
        result = backend._sanitize_username(r'domain\user')
        # Backslash should be escaped as \5c
        assert '5c' in result, f"Backslash not escaped: {repr(result)}"
    
    def test_null_byte_in_username(self):
        """Test null byte is escaped properly."""
        backend = get_backend()
        result = backend._sanitize_username('user\x00name')
        # Null byte should be escaped as \00
        assert '00' in result, f"Null byte not escaped: {repr(result)}"


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])

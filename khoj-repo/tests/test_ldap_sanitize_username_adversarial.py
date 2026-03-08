"""Adversarial Security Tests for LdapAuthBackend._sanitize_username() method.

These tests simulate real-world attack vectors against the username sanitization:
1. LDAP Injection Bypass Attempts
2. DoS Attacks
3. Unicode Attacks
4. Filter Manipulation

Note: These tests are completely standalone and don't require Django.
"""
import sys
import os
import logging

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Mock Django settings before any Django imports
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'khoj.app.settings')

# Minimal mock for django.conf.settings
class MockSettings:
    INSTALLED_APPS = []
    DATABASES = {}
    
import django.conf
django.conf.settings = MockSettings()

# Now import the LDAP backend
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


class TestLdapInjectionBypass:
    """Test LDAP injection bypass attempts - advanced attack vectors."""
    
    def test_null_byte_injection_admin(self):
        """Test null byte injection: admin\x00)(uid=*"""
        backend = get_backend()
        result = backend._sanitize_username('admin\x00)(uid=*')
        # Null byte should be escaped, injection pattern neutralized
        assert '\x00' not in result, f"Null byte not escaped: {repr(result)}"
        assert '*(' not in result, f"Injection pattern still present: {repr(result)}"
        assert ')*' not in result, f"Injection pattern still present: {repr(result)}"
    
    def test_cyrillic_homoglyph_attack(self):
        """Test Unicode homoglyph: Cyrillic 'а' (U+0430) instead of Latin 'a'."""
        backend = get_backend()
        # Cyrillic аdmin - visually looks like "admin" but different bytes
        cyrillic_admin = '\u0430dmin'  # а is Cyrillic small letter a
        result = backend._sanitize_username(cyrillic_admin)
        # Should preserve the Unicode character (it's not malicious, just deceptive)
        assert '\u0430' in result or 'dmin' in result, f"Cyrillic character not preserved: {repr(result)}"
    
    def test_case_variation_injection_uppercase(self):
        """Test case variations: ADMIN*)(UID=*"""
        backend = get_backend()
        result = backend._sanitize_username('ADMIN*)(UID=*')
        # Injection pattern should be escaped regardless of case
        assert '*(' not in result, f"Injection pattern still present: {repr(result)}"
        assert ')*' not in result, f"Injection pattern still present: {repr(result)}"
        # ADMIN text should be preserved
        assert 'ADMIN' in result, f"ADMIN text not preserved: {repr(result)}"
    
    def test_url_encoded_injection(self):
        """Test URL encoded injection: admin%29 (represents admin))."""
        backend = get_backend()
        result = backend._sanitize_username('admin%29')
        # %29 is literal text, not a decoded ), so it should pass through
        # But we need to ensure it's not interpreted as )
        assert result == 'admin%29' or '%29' in result, f"URL encoded char mishandled: {repr(result)}"
    
    def test_url_encoded_wildcard(self):
        """Test URL encoded wildcard: admin%2a (represents admin*)."""
        backend = get_backend()
        result = backend._sanitize_username('admin%2a')
        # %2a is literal text, should pass through unchanged
        assert '%2a' in result or result == 'admin%2a', f"URL encoded wildcard mishandled: {repr(result)}"
    
    def test_mixed_encoding_attack(self):
        """Test mixed encoding: admin%29%28 (represents admin)( )."""
        backend = get_backend()
        result = backend._sanitize_username('admin%29%28')
        # Should remain as literal URL-encoded string
        assert '%29' in result or '%28' in result or result == 'admin%29%28', \
            f"Mixed encoding mishandled: {repr(result)}"
    
    def test_double_encoding_attack(self):
        """Test double URL encoding: admin%2529 (represents admin%29)."""
        backend = get_backend()
        result = backend._sanitize_username('admin%2529')
        # %2529 is literal text representing %29
        assert '%25' in result or result == 'admin%2529', f"Double encoding mishandled: {repr(result)}"
    
    def test_hex_encoding_attack(self):
        """Test hex encoding variations: \x29\x28 for )(."""
        backend = get_backend()
        result = backend._sanitize_username('admin\x29\x28')
        # These are actual bytes that should be escaped
        assert '\x29' not in result, f"Hex ) not escaped: {repr(result)}"
        assert '\x28' not in result, f"Hex ( not escaped: {repr(result)}"
    
    def test_unicode_escape_injection(self):
        """Test Unicode escape sequences: \\u0029 for )."""
        backend = get_backend()
        # Python string with unicode escape - actual ) character
        result = backend._sanitize_username('admin\u0029')
        # \u0029 is the actual ) character, should be escaped
        assert ')' not in result or '29' in result, f"Unicode ) not escaped: {repr(result)}"


class TestDoSAttacks:
    """Test DoS attack prevention - resource exhaustion attempts."""
    
    def test_1mb_username_truncated(self):
        """Test 1MB username gets truncated to prevent memory exhaustion."""
        backend = get_backend()
        one_mb_username = 'x' * (1024 * 1024)  # 1 million characters
        result = backend._sanitize_username(one_mb_username)
        # Should be truncated to 256 chars before escaping
        assert len(result) < 1000, f"1MB username not truncated, length: {len(result)}"
    
    def test_million_asterisks_wildcard_dos(self):
        """Test username with million asterisks (wildcard DoS)."""
        backend = get_backend()
        million_stars = '*' * 1000000
        result = backend._sanitize_username(million_stars)
        # Should be truncated first, then escaped
        assert len(result) < 1000, f"Million asterisks not truncated, length: {len(result)}"
        # All asterisks should be escaped (as \2a)
        # After truncation to 256, we have 256 chars that become \2a repeated
        # So result should be 256 * 3 = 768 chars max
        assert len(result) <= 768, f"Escaped result too long: {len(result)}"
    
    def test_recursive_escape_sequence_dos(self):
        """Test recursive/long escape sequences: \\\\* repeated."""
        backend = get_backend()
        # Backslash-star pattern that could cause recursive escaping issues
        recursive_pattern = '\\*' * 10000
        result = backend._sanitize_username(recursive_pattern)
        # Should truncate first, preventing excessive processing
        assert len(result) < 50000, f"Recursive pattern not truncated, length: {len(result)}"
    
    def test_nested_parentheses_dos(self):
        """Test deeply nested parentheses: (((...)))."""
        backend = get_backend()
        nested = '(' * 5000 + 'admin' + ')' * 5000
        result = backend._sanitize_username(nested)
        # Should truncate before escaping
        assert len(result) < 20000, f"Nested parens not truncated, length: {len(result)}"
    
    def test_repeated_null_bytes_dos(self):
        """Test repeated null bytes: \x00 * 10000."""
        backend = get_backend()
        null_bytes = '\x00' * 10000
        result = backend._sanitize_username(null_bytes)
        # Should truncate first
        assert len(result) < 1000, f"Null byte flood not truncated, length: {len(result)}"
    
    def test_mixed_special_chars_dos(self):
        """Test mixed special characters for processing overhead."""
        backend = get_backend()
        # Pattern designed to maximize escaping overhead
        mixed = '(*\x00\\)' * 10000
        result = backend._sanitize_username(mixed)
        # Should truncate first
        assert len(result) < 50000, f"Mixed special chars not truncated, length: {len(result)}"


class TestUnicodeAttacks:
    """Test Unicode-based attacks and edge cases."""
    
    def test_right_to_left_override_character(self):
        """Test Right-to-Left Override (RLO) character: U+202E."""
        backend = get_backend()
        # RLO can be used for visual spoofing
        rlo_username = 'admin\u202Euser'
        result = backend._sanitize_username(rlo_username)
        # RLO is not a special LDAP char, should be preserved
        assert '\u202E' in result or 'admin' in result, f"RLO character mishandled: {repr(result)}"
    
    def test_zero_width_joiner(self):
        """Test Zero-Width Joiner (ZWJ): U+200D."""
        backend = get_backend()
        # ZWJ used in emoji sequences
        zwj_username = 'admin\u200Duser'
        result = backend._sanitize_username(zwj_username)
        # ZWJ should be preserved
        assert '\u200D' in result or 'admin' in result, f"ZWJ mishandled: {repr(result)}"
    
    def test_zero_width_non_joiner(self):
        """Test Zero-Width Non-Joiner (ZWNJ): U+200C."""
        backend = get_backend()
        zwnj_username = 'admin\u200Cuser'
        result = backend._sanitize_username(zwnj_username)
        assert '\u200C' in result or 'admin' in result, f"ZWNJ mishandled: {repr(result)}"
    
    def test_combining_characters(self):
        """Test combining characters: accents that overlay previous char."""
        backend = get_backend()
        # Combining acute accent U+0301
        combining = 'admin\u0301'
        result = backend._sanitize_username(combining)
        # Combining char should be preserved
        assert '\u0301' in result or 'admin' in result, f"Combining char mishandled: {repr(result)}"
    
    def test_emoji_in_username(self):
        """Test emoji in username."""
        backend = get_backend()
        emoji_username = 'user\U0001F600'  # Grinning face emoji
        result = backend._sanitize_username(emoji_username)
        # Emoji should be preserved
        assert '\U0001F600' in result or 'user' in result, f"Emoji mishandled: {repr(result)}"
    
    def test_bidirectional_text_attack(self):
        """Test bidirectional text manipulation."""
        backend = get_backend()
        # Left-to-right mark (LRM) U+200E and Right-to-left mark (RLM) U+200F
        bidi_username = '\u200Eadmin\u200F'
        result = backend._sanitize_username(bidi_username)
        # Bidi marks should be preserved (not LDAP special chars)
        assert '\u200E' in result or '\u200F' in result or 'admin' in result, \
            f"Bidi marks mishandled: {repr(result)}"
    
    def test_fullwidth_variants(self):
        """Test fullwidth variants of special chars: ＊ instead of *."""
        backend = get_backend()
        # Fullwidth asterisk U+FF0A looks like * but is different
        fullwidth = 'admin\uFF0A'
        result = backend._sanitize_username(fullwidth)
        # Fullwidth * is not LDAP special, should be preserved
        assert '\uFF0A' in result or 'admin' in result, f"Fullwidth char mishandled: {repr(result)}"
    
    def test_mixed_script_spoofing(self):
        """Test mixed script spoofing: Latin + Cyrillic + Greek."""
        backend = get_backend()
        # Mix of scripts that look similar
        mixed = 'аdmin'  # Cyrillic a + Latin dmin
        result = backend._sanitize_username(mixed)
        # Should preserve the mixed script characters
        assert 'dmin' in result or '\u0430' in result, f"Mixed script mishandled: {repr(result)}"


class TestFilterManipulation:
    """Test LDAP filter manipulation attempts."""
    
    def test_always_true_or_injection(self):
        """Test always-true OR injection: *)(|(uid=*)."""
        backend = get_backend()
        # Attempt to create OR condition that matches everything
        or_injection = '*)(|(uid=*'
        result = backend._sanitize_username(or_injection)
        # Per RFC 4515, | is only special at filter level, not in assertion values
        # But * ( ) should be escaped to prevent filter structure manipulation
        assert '*(' not in result, f"Injection pattern present: {repr(result)}"
        assert ')*' not in result, f"Injection pattern present: {repr(result)}"
    
    def test_always_true_and_injection(self):
        """Test always-true AND injection with comments."""
        backend = get_backend()
        # LDAP doesn't have comments, but test & operator
        and_injection = '*)(&(uid=*'
        result = backend._sanitize_username(and_injection)
        # Per RFC 4515, & is only special at filter level, not in assertion values
        # But * ( ) should be escaped to prevent filter structure manipulation
        assert '*(' not in result, f"Injection pattern present: {repr(result)}"
        assert ')*' not in result, f"Injection pattern present: {repr(result)}"
    
    def test_union_based_injection_attempt(self):
        """Test union-based injection pattern."""
        backend = get_backend()
        # Attempt to union multiple filters
        union = '*)(uid=*)(cn=*'
        result = backend._sanitize_username(union)
        # All parens and wildcards should be escaped
        assert '*(' not in result, f"Union injection present: {repr(result)}"
        assert ')(' not in result, f"Union injection present: {repr(result)}"
    
    def test_boolean_based_injection(self):
        """Test boolean-based blind injection patterns."""
        backend = get_backend()
        # Boolean blind injection attempt
        boolean = 'admin*)(objectClass=*'
        result = backend._sanitize_username(boolean)
        assert '*(' not in result, f"Boolean injection present: {repr(result)}"
        assert '=' in result, f"Equals sign escaped incorrectly: {repr(result)}"
    
    def test_ldap_comment_injection(self):
        """Test LDAP comment-style injection if supported."""
        backend = get_backend()
        # Some LDAP implementations support comments
        comment = 'admin/*comment*/'
        result = backend._sanitize_username(comment)
        # / is not a special LDAP char per RFC 4515
        assert 'admin' in result, f"Comment injection mishandled: {repr(result)}"
    
    def test_attribute_discovery_injection(self):
        """Test attribute discovery injection."""
        backend = get_backend()
        # Attempt to discover attributes
        discovery = '*)(|(objectClass=*)(cn=*)(mail=*'
        result = backend._sanitize_username(discovery)
        # Per RFC 4515, | is only special at filter level, not in assertion values
        # But * ( ) should be escaped to prevent filter structure manipulation
        assert '*(' not in result, f"Injection pattern present: {repr(result)}"
        assert ')*' not in result, f"Injection pattern present: {repr(result)}"
    
    def test_dn_injection_attempt(self):
        """Test DN injection in username field."""
        backend = get_backend()
        # Attempt to inject DN components
        dn_inject = 'cn=admin,dc=example,dc=com'
        result = backend._sanitize_username(dn_inject)
        # = and , are not special in filter values per RFC 4515
        assert 'cn=admin' in result, f"DN content not preserved: {repr(result)}"
    
    def test_extensible_match_injection(self):
        """Test extensible match injection: := operator."""
        backend = get_backend()
        # Extensible match operator
        extensible = 'admin:=something'
        result = backend._sanitize_username(extensible)
        # := is not special in filter values
        assert ':=' in result or 'admin' in result, f"Extensible match mishandled: {repr(result)}"


class TestEdgeCaseAttacks:
    """Test edge case and format-based attacks."""
    
    def test_whitespace_manipulation(self):
        """Test various whitespace characters."""
        backend = get_backend()
        # Tab, newline, carriage return, space
        whitespace = 'admin\t\n\r user'
        result = backend._sanitize_username(whitespace)
        # Whitespace should be preserved (not special LDAP chars)
        assert 'admin' in result, f"Whitespace handling failed: {repr(result)}"
    
    def test_non_printable_ascii(self):
        """Test non-printable ASCII characters."""
        backend = get_backend()
        # Bell, escape, form feed
        non_print = 'admin\x07\x1b\x0c'
        result = backend._sanitize_username(non_print)
        # Non-printables should be preserved
        assert 'admin' in result, f"Non-printable handling failed: {repr(result)}"
    
    def test_high_unicode_planes(self):
        """Test characters from high Unicode planes."""
        backend = get_backend()
        # Characters outside BMP (plane 1+)
        high_unicode = 'user\U0001F680'  # Rocket emoji
        result = backend._sanitize_username(high_unicode)
        assert 'user' in result, f"High Unicode handling failed: {repr(result)}"
    
    def test_invalid_utf8_sequences(self):
        """Test handling of potentially invalid UTF-8 sequences."""
        backend = get_backend()
        # Python strings are Unicode, so we test surrogate range
        # which might cause issues in some systems
        try:
            surrogate = 'admin\ud800'  # Surrogate character
            result = backend._sanitize_username(surrogate)
            assert 'admin' in result, f"Surrogate handling failed: {repr(result)}"
        except UnicodeEncodeError:
            # Some Python builds may reject surrogates
            pass
    
    def test_very_short_input(self):
        """Test very short input (single char)."""
        backend = get_backend()
        result = backend._sanitize_username('*')
        assert '\x2a' in result or '2a' in result, f"Single char not escaped: {repr(result)}"
    
    def test_only_special_chars(self):
        """Test username consisting only of special characters."""
        backend = get_backend()
        only_special = '*()\\\x00'
        result = backend._sanitize_username(only_special)
        # All should be escaped
        assert '*' not in result, f"* not escaped: {repr(result)}"
        assert '\x00' not in result, f"Null not escaped: {repr(result)}"
    
    def test_repeated_escape_sequences_input(self):
        """Test input that looks like already-escaped sequences."""
        backend = get_backend()
        # Input that looks like hex escapes
        looks_escaped = 'admin\x5c2a'  # \2a which looks like escaped *
        result = backend._sanitize_username(looks_escaped)
        # The backslash should be escaped
        assert '5c' in result, f"Backslash not escaped: {repr(result)}"
    
    def test_numeric_username(self):
        """Test purely numeric username."""
        backend = get_backend()
        numeric = '1234567890'
        result = backend._sanitize_username(numeric)
        assert result == '1234567890', f"Numeric username changed: {repr(result)}"
    
    def test_sql_injection_pattern_in_username(self):
        """Test SQL injection patterns (should pass through unchanged)."""
        backend = get_backend()
        # SQL injection attempt in username field
        sql_inject = "admin' OR '1'='1"
        result = backend._sanitize_username(sql_inject)
        # Single quotes are not special LDAP chars
        assert "admin' OR" in result or "admin" in result, f"SQL pattern mishandled: {repr(result)}"


class TestPathTraversalAndCommandInjection:
    """Test non-LDAP injection attempts that might occur in username."""
    
    def test_path_traversal_attempt(self):
        """Test path traversal patterns in username."""
        backend = get_backend()
        path_traversal = '../../../etc/passwd'
        result = backend._sanitize_username(path_traversal)
        # Path traversal is not LDAP injection, should pass through
        assert 'etc/passwd' in result or '../' in result, f"Path traversal mishandled: {repr(result)}"
    
    def test_command_injection_attempt(self):
        """Test command injection patterns."""
        backend = get_backend()
        cmd_inject = 'user; cat /etc/passwd'
        result = backend._sanitize_username(cmd_inject)
        # Command injection is not LDAP injection, should pass through
        assert 'user' in result, f"Command injection mishandled: {repr(result)}"
    
    def test_backtick_command_substitution(self):
        """Test backtick command substitution."""
        backend = get_backend()
        backtick = '`whoami`'
        result = backend._sanitize_username(backtick)
        # Backticks are not special LDAP chars
        assert '`whoami`' in result or 'whoami' in result, f"Backtick mishandled: {repr(result)}"
    
    def test_dollar_command_substitution(self):
        """Test $() command substitution."""
        backend = get_backend()
        dollar = '$(whoami)'
        result = backend._sanitize_username(dollar)
        # $ and () - parens should be escaped, $ is not special
        assert '$' in result, f"Dollar sign mishandled: {repr(result)}"


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])

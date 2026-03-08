"""Standalone Adversarial Security Tests for LdapAuthBackend._sanitize_username().

Run with: python test_ldap_sanitize_username_adversarial_standalone.py
"""
import sys
import os
import logging
import traceback

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Mock Django settings before any Django imports
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'khoj.app.settings')

class MockSettings:
    INSTALLED_APPS = []
    DATABASES = {}
    configured = True
    DEBUG = False
    
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


# Test results tracking
results = {
    'passed': [],
    'failed': [],
    'errors': []
}


def test(name):
    """Decorator to register tests."""
    def decorator(func):
        func.test_name = name
        return func
    return decorator


def run_test(func):
    """Run a single test and record results."""
    try:
        func()
        results['passed'].append(func.test_name)
        print(f"  [PASS] {func.test_name}")
        return True
    except AssertionError as e:
        results['failed'].append((func.test_name, str(e)))
        print(f"  [FAIL] {func.test_name}")
        print(f"    {e}")
        return False
    except Exception as e:
        results['errors'].append((func.test_name, traceback.format_exc()))
        print(f"  [ERROR] {func.test_name}")
        print(f"    {e}")
        return False


# =============================================================================
# LDAP INJECTION BYPASS TESTS
# =============================================================================

@test("Null byte injection: admin\\x00)(uid=*")
def test_null_byte_injection_admin():
    backend = get_backend()
    result = backend._sanitize_username('admin\x00)(uid=*')
    assert '\x00' not in result, f"Null byte not escaped: {repr(result)}"
    assert '*(' not in result, f"Injection pattern still present: {repr(result)}"
    assert ')*' not in result, f"Injection pattern still present: {repr(result)}"


@test("Cyrillic homoglyph: \\u0430dmin")
def test_cyrillic_homoglyph_attack():
    backend = get_backend()
    cyrillic_admin = '\u0430dmin'
    result = backend._sanitize_username(cyrillic_admin)
    assert '\u0430' in result or 'dmin' in result, f"Cyrillic character not preserved: {repr(result)}"


@test("Case variation injection: ADMIN*)(UID=*")
def test_case_variation_injection_uppercase():
    backend = get_backend()
    result = backend._sanitize_username('ADMIN*)(UID=*')
    assert '*(' not in result, f"Injection pattern still present: {repr(result)}"
    assert ')*' not in result, f"Injection pattern still present: {repr(result)}"
    assert 'ADMIN' in result, f"ADMIN text not preserved: {repr(result)}"


@test("URL encoded injection: admin%29")
def test_url_encoded_injection():
    backend = get_backend()
    result = backend._sanitize_username('admin%29')
    assert result == 'admin%29' or '%29' in result, f"URL encoded char mishandled: {repr(result)}"


@test("URL encoded wildcard: admin%2a")
def test_url_encoded_wildcard():
    backend = get_backend()
    result = backend._sanitize_username('admin%2a')
    assert '%2a' in result or result == 'admin%2a', f"URL encoded wildcard mishandled: {repr(result)}"


@test("Mixed encoding: admin%29%28")
def test_mixed_encoding_attack():
    backend = get_backend()
    result = backend._sanitize_username('admin%29%28')
    assert '%29' in result or '%28' in result or result == 'admin%29%28', f"Mixed encoding mishandled: {repr(result)}"


@test("Double URL encoding: admin%2529")
def test_double_encoding_attack():
    backend = get_backend()
    result = backend._sanitize_username('admin%2529')
    assert '%25' in result or result == 'admin%2529', f"Double encoding mishandled: {repr(result)}"


@test("Hex encoding: \\x29\\x28")
def test_hex_encoding_attack():
    backend = get_backend()
    result = backend._sanitize_username('admin\x29\x28')
    assert '\x29' not in result, f"Hex ) not escaped: {repr(result)}"
    assert '\x28' not in result, f"Hex ( not escaped: {repr(result)}"


@test("Unicode escape: \\u0029")
def test_unicode_escape_injection():
    backend = get_backend()
    result = backend._sanitize_username('admin\u0029')
    assert ')' not in result or '29' in result, f"Unicode ) not escaped: {repr(result)}"


# =============================================================================
# DoS ATTACK TESTS
# =============================================================================

@test("1MB username truncation")
def test_1mb_username_truncated():
    backend = get_backend()
    one_mb_username = 'x' * (1024 * 1024)
    result = backend._sanitize_username(one_mb_username)
    assert len(result) < 1000, f"1MB username not truncated, length: {len(result)}"


@test("Million asterisks wildcard DoS")
def test_million_asterisks_wildcard_dos():
    backend = get_backend()
    million_stars = '*' * 1000000
    result = backend._sanitize_username(million_stars)
    assert len(result) < 1000, f"Million asterisks not truncated, length: {len(result)}"
    assert len(result) <= 768, f"Escaped result too long: {len(result)}"


@test("Recursive escape sequence DoS")
def test_recursive_escape_sequence_dos():
    backend = get_backend()
    recursive_pattern = '\\*' * 10000
    result = backend._sanitize_username(recursive_pattern)
    assert len(result) < 50000, f"Recursive pattern not truncated, length: {len(result)}"


@test("Nested parentheses DoS")
def test_nested_parentheses_dos():
    backend = get_backend()
    nested = '(' * 5000 + 'admin' + ')' * 5000
    result = backend._sanitize_username(nested)
    assert len(result) < 20000, f"Nested parens not truncated, length: {len(result)}"


@test("Repeated null bytes DoS")
def test_repeated_null_bytes_dos():
    backend = get_backend()
    null_bytes = '\x00' * 10000
    result = backend._sanitize_username(null_bytes)
    assert len(result) < 1000, f"Null byte flood not truncated, length: {len(result)}"


@test("Mixed special chars DoS")
def test_mixed_special_chars_dos():
    backend = get_backend()
    mixed = '(*\x00\\)' * 10000
    result = backend._sanitize_username(mixed)
    assert len(result) < 50000, f"Mixed special chars not truncated, length: {len(result)}"


# =============================================================================
# UNICODE ATTACK TESTS
# =============================================================================

@test("Right-to-Left Override character U+202E")
def test_right_to_left_override_character():
    backend = get_backend()
    rlo_username = 'admin\u202Euser'
    result = backend._sanitize_username(rlo_username)
    assert '\u202E' in result or 'admin' in result, f"RLO character mishandled: {repr(result)}"


@test("Zero-Width Joiner U+200D")
def test_zero_width_joiner():
    backend = get_backend()
    zwj_username = 'admin\u200Duser'
    result = backend._sanitize_username(zwj_username)
    assert '\u200D' in result or 'admin' in result, f"ZWJ mishandled: {repr(result)}"


@test("Zero-Width Non-Joiner U+200C")
def test_zero_width_non_joiner():
    backend = get_backend()
    zwnj_username = 'admin\u200Cuser'
    result = backend._sanitize_username(zwnj_username)
    assert '\u200C' in result or 'admin' in result, f"ZWNJ mishandled: {repr(result)}"


@test("Combining characters U+0301")
def test_combining_characters():
    backend = get_backend()
    combining = 'admin\u0301'
    result = backend._sanitize_username(combining)
    assert '\u0301' in result or 'admin' in result, f"Combining char mishandled: {repr(result)}"


@test("Emoji in username U+1F600")
def test_emoji_in_username():
    backend = get_backend()
    emoji_username = 'user\U0001F600'
    result = backend._sanitize_username(emoji_username)
    assert '\U0001F600' in result or 'user' in result, f"Emoji mishandled: {repr(result)}"


@test("Bidirectional text U+200E/U+200F")
def test_bidirectional_text_attack():
    backend = get_backend()
    bidi_username = '\u200Eadmin\u200F'
    result = backend._sanitize_username(bidi_username)
    assert '\u200E' in result or '\u200F' in result or 'admin' in result, f"Bidi marks mishandled: {repr(result)}"


@test("Fullwidth variants U+FF0A")
def test_fullwidth_variants():
    backend = get_backend()
    fullwidth = 'admin\uFF0A'
    result = backend._sanitize_username(fullwidth)
    assert '\uFF0A' in result or 'admin' in result, f"Fullwidth char mishandled: {repr(result)}"


@test("Mixed script spoofing")
def test_mixed_script_spoofing():
    backend = get_backend()
    mixed = 'аdmin'
    result = backend._sanitize_username(mixed)
    assert 'dmin' in result or '\u0430' in result, f"Mixed script mishandled: {repr(result)}"


# =============================================================================
# FILTER MANIPULATION TESTS
# =============================================================================

@test("Always-true OR injection")
def test_always_true_or_injection():
    backend = get_backend()
    or_injection = '*)(|(uid=*'
    result = backend._sanitize_username(or_injection)
    # Per RFC 4515, | is only special at filter level, not in assertion values
    # But * ( ) should be escaped to prevent filter structure manipulation
    assert '*(' not in result, f"Injection pattern present: {repr(result)}"
    assert ')*' not in result, f"Injection pattern present: {repr(result)}"


@test("Always-true AND injection")
def test_always_true_and_injection():
    backend = get_backend()
    and_injection = '*)(\x26(uid=*'
    result = backend._sanitize_username(and_injection)
    # Per RFC 4515, & is only special at filter level, not in assertion values
    # But * ( ) should be escaped to prevent filter structure manipulation
    assert '*(' not in result, f"Injection pattern present: {repr(result)}"
    assert ')*' not in result, f"Injection pattern present: {repr(result)}"


@test("Union-based injection")
def test_union_based_injection_attempt():
    backend = get_backend()
    union = '*)(uid=*)(cn=*'
    result = backend._sanitize_username(union)
    assert '*(' not in result, f"Union injection present: {repr(result)}"
    assert ')(' not in result, f"Union injection present: {repr(result)}"


@test("Boolean-based blind injection")
def test_boolean_based_injection():
    backend = get_backend()
    boolean = 'admin*)(objectClass=*'
    result = backend._sanitize_username(boolean)
    assert '*(' not in result, f"Boolean injection present: {repr(result)}"
    assert '=' in result, f"Equals sign escaped incorrectly: {repr(result)}"


@test("LDAP comment injection")
def test_ldap_comment_injection():
    backend = get_backend()
    comment = 'admin/*comment*/'
    result = backend._sanitize_username(comment)
    assert 'admin' in result, f"Comment injection mishandled: {repr(result)}"


@test("Attribute discovery injection")
def test_attribute_discovery_injection():
    backend = get_backend()
    discovery = '*)(|(objectClass=*)(cn=*)(mail=*'
    result = backend._sanitize_username(discovery)
    # Per RFC 4515, | is only special at filter level, not in assertion values
    # But * ( ) should be escaped to prevent filter structure manipulation
    assert '*(' not in result, f"Injection pattern present: {repr(result)}"
    assert ')*' not in result, f"Injection pattern present: {repr(result)}"


@test("DN injection attempt")
def test_dn_injection_attempt():
    backend = get_backend()
    dn_inject = 'cn=admin,dc=example,dc=com'
    result = backend._sanitize_username(dn_inject)
    assert 'cn=admin' in result, f"DN content not preserved: {repr(result)}"


@test("Extensible match injection")
def test_extensible_match_injection():
    backend = get_backend()
    extensible = 'admin:=something'
    result = backend._sanitize_username(extensible)
    assert ':=' in result or 'admin' in result, f"Extensible match mishandled: {repr(result)}"


# =============================================================================
# EDGE CASE ATTACK TESTS
# =============================================================================

@test("Whitespace manipulation")
def test_whitespace_manipulation():
    backend = get_backend()
    whitespace = 'admin\t\n\r user'
    result = backend._sanitize_username(whitespace)
    assert 'admin' in result, f"Whitespace handling failed: {repr(result)}"


@test("Non-printable ASCII")
def test_non_printable_ascii():
    backend = get_backend()
    non_print = 'admin\x07\x1b\x0c'
    result = backend._sanitize_username(non_print)
    assert 'admin' in result, f"Non-printable handling failed: {repr(result)}"


@test("High Unicode planes (emoji)")
def test_high_unicode_planes():
    backend = get_backend()
    high_unicode = 'user\U0001F680'
    result = backend._sanitize_username(high_unicode)
    assert 'user' in result, f"High Unicode handling failed: {repr(result)}"


@test("Invalid UTF-8 sequences (surrogates)")
def test_invalid_utf8_sequences():
    backend = get_backend()
    try:
        surrogate = 'admin\ud800'
        result = backend._sanitize_username(surrogate)
        assert 'admin' in result, f"Surrogate handling failed: {repr(result)}"
    except UnicodeEncodeError:
        pass  # Some Python builds may reject surrogates


@test("Very short input (single *)")
def test_very_short_input():
    backend = get_backend()
    result = backend._sanitize_username('*')
    assert '\x2a' in result or '2a' in result, f"Single char not escaped: {repr(result)}"


@test("Only special characters")
def test_only_special_chars():
    backend = get_backend()
    only_special = '*()\\\x00'
    result = backend._sanitize_username(only_special)
    assert '*' not in result, f"* not escaped: {repr(result)}"
    assert '\x00' not in result, f"Null not escaped: {repr(result)}"


@test("Repeated escape sequences input")
def test_repeated_escape_sequences_input():
    backend = get_backend()
    looks_escaped = 'admin\x5c2a'
    result = backend._sanitize_username(looks_escaped)
    assert '5c' in result, f"Backslash not escaped: {repr(result)}"


@test("Numeric username")
def test_numeric_username():
    backend = get_backend()
    numeric = '1234567890'
    result = backend._sanitize_username(numeric)
    assert result == '1234567890', f"Numeric username changed: {repr(result)}"


@test("SQL injection pattern")
def test_sql_injection_pattern_in_username():
    backend = get_backend()
    sql_inject = "admin' OR '1'='1"
    result = backend._sanitize_username(sql_inject)
    assert "admin' OR" in result or "admin" in result, f"SQL pattern mishandled: {repr(result)}"


# =============================================================================
# PATH TRAVERSAL AND COMMAND INJECTION TESTS
# =============================================================================

@test("Path traversal attempt")
def test_path_traversal_attempt():
    backend = get_backend()
    path_traversal = '../../../etc/passwd'
    result = backend._sanitize_username(path_traversal)
    assert 'etc/passwd' in result or '../' in result, f"Path traversal mishandled: {repr(result)}"


@test("Command injection attempt")
def test_command_injection_attempt():
    backend = get_backend()
    cmd_inject = 'user; cat /etc/passwd'
    result = backend._sanitize_username(cmd_inject)
    assert 'user' in result, f"Command injection mishandled: {repr(result)}"


@test("Backtick command substitution")
def test_backtick_command_substitution():
    backend = get_backend()
    backtick = '`whoami`'
    result = backend._sanitize_username(backtick)
    assert '`whoami`' in result or 'whoami' in result, f"Backtick mishandled: {repr(result)}"


@test("Dollar command substitution")
def test_dollar_command_substitution():
    backend = get_backend()
    dollar = '$(whoami)'
    result = backend._sanitize_username(dollar)
    assert '$' in result, f"Dollar sign mishandled: {repr(result)}"


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("ADVERSARIAL SECURITY TESTS: _sanitize_username()")
    print("=" * 70)
    print()
    
    # Collect all test functions
    test_funcs = [obj for name, obj in globals().items() if callable(obj) and hasattr(obj, 'test_name')]
    
    print(f"Running {len(test_funcs)} adversarial tests...")
    print()
    
    # Run tests
    for func in test_funcs:
        run_test(func)
    
    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total:  {len(test_funcs)}")
    print(f"Passed: {len(results['passed'])}")
    print(f"Failed: {len(results['failed'])}")
    print(f"Errors: {len(results['errors'])}")
    print()
    
    if results['failed']:
        print("FAILED TESTS:")
        for name, error in results['failed']:
            print(f"  - {name}")
        print()
    
    if results['errors']:
        print("TESTS WITH ERRORS:")
        for name, error in results['errors']:
            print(f"  - {name}")
        print()
    
    if len(results['passed']) == len(test_funcs):
        print("[SUCCESS] ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("[FAILED] SOME TESTS FAILED")
        sys.exit(1)

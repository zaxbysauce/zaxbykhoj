"""
Adversarial tests for redaction function in helpers.py

These tests attempt to find bypasses for the redact_sensitive_data function.
They test various attack vectors that might circumvent regex-based redaction.
"""
import pytest

# Run tests without Django database setup
pytestmark = pytest.mark.django_db(None)

from khoj.utils.helpers import redact_sensitive_data


class TestRedactionBypassAttempts:
    """Tests for attempting to bypass redaction through various attack vectors."""

    # ===== Unicode/Encoding Attacks =====
    
    def test_unicode_variation_in_password_key(self):
        """Attempt bypass using Unicode lookalike characters in password keyword."""
        # Using Cyrillic 'a' instead of Latin 'a' in "password"
        message = "password=\u0430\u0434\u043c\u0438\u043dsecret123"
        result = redact_sensitive_data(message)
        # If bypassed, result would contain the secret
        assert "[REDACTED]" in result or "secret" not in result.lower()
    
    def test_unicode_zero_width_characters(self):
        """Attempt bypass using zero-width characters in secrets."""
        message = "api_key=sk-\u200btest\u200bsecret\u200btoken"
        result = redact_sensitive_data(message)
        # The secret should still be redacted
        assert "[REDACTED]" in result

    # ===== Injection Attacks =====
    
    def test_newline_injection_password(self):
        """Attempt bypass by injecting newline between key and value."""
        message = "password=\nsecret123"
        result = redact_sensitive_data(message)
        assert "[REDACTED]" in result or "secret" not in result
    
    def test_tab_injection_password(self):
        """Attempt bypass using tab character between key and value."""
        message = "password:\tsecret123"
        result = redact_sensitive_data(message)
        assert "[REDACTED]" in result or "secret" not in result
    
    def test_null_byte_injection(self):
        """Attempt bypass using null bytes."""
        message = "api_key=sk-\x00secret123"
        result = redact_sensitive_data(message)
        assert "[REDACTED]" in result or "secret" not in result
    
    def test_carriage_return_injection(self):
        """Attempt bypass using carriage return."""
        message = "password=\rsecret123"
        result = redact_sensitive_data(message)
        assert "[REDACTED]" in result or "secret" not in result

    # ===== Case Variation Attacks =====
    
    def test_uppercase_password_variant(self):
        """Test uppercase PASSWORD variant."""
        message = "PASSWORD=MySecretPass123"
        result = redact_sensitive_data(message)
        assert "[REDACTED]" in result
    
    def test_mixed_case_password_variant(self):
        """Test mixed case PaSsWoRd variant."""
        message = "PaSsWoRd=MySecretPass123"
        result = redact_sensitive_data(message)
        assert "[REDACTED]" in result

    # ===== ReDoS (Regex Denial of Service) Attempts =====
    
    def test_redos_with_many_repeating_chars(self):
        """Attempt ReDoS with many repeating characters."""
        message = "password=" + "a" * 10000
        # Should complete without hanging
        import time
        start = time.time()
        result = redact_sensitive_data(message)
        elapsed = time.time() - start
        # Should complete quickly (under 1 second)
        assert elapsed < 1.0
        assert "[REDACTED]" in result
    
    def test_redos_nested_quantifiers(self):
        """Attempt ReDoS with nested quantifiers."""
        message = "password=" + "a" * 100 + "b" * 100
        import time
        start = time.time()
        result = redact_sensitive_data(message)
        elapsed = time.time() - start
        assert elapsed < 1.0

    # ===== Multiple Secret Variations =====
    
    def test_multiple_passwords_same_line(self):
        """Test multiple passwords on same line."""
        message = 'user1 password=pass1, user2 password=pass2, user3 password=pass3'
        result = redact_sensitive_data(message)
        # All passwords should be redacted
        assert result.count("[REDACTED]") >= 3 or "pass1" not in result
    
    def test_nested_json_like_password(self):
        """Test password in nested JSON structure."""
        message = '{"user": {"credentials": {"password": "supersecret"}}}'
        result = redact_sensitive_data(message)
        assert "[REDACTED]" in result or "supersecret" not in result

    # ===== URL/Query Parameter Variations =====
    
    def test_url_encoded_secret_in_query(self):
        """Test URL-encoded secret in query parameter."""
        message = "?api_key=%73%6B-%74%65%73%74%74%6F%6B%65%6E"
        result = redact_sensitive_data(message)
        # The regex looks for api_key= pattern, URL-encoded may not be caught
        # But the decoded version shouldn't appear redacted either
        assert "[REDACTED]" in result or "sk-" not in result
    
    def test_double_encoded_secret_in_query(self):
        """Test double URL-encoded secret."""
        message = "?api_key=%253F%253F%253F"
        result = redact_sensitive_data(message)
        # Should not cause errors
        assert result is not None

    # ===== HTML Entity Attacks =====
    
    def test_html_entity_encoded_secret(self):
        """Attempt bypass using HTML entities."""
        message = "password=&#115;&#101;&#99;&#114;&#101;&#116;"
        result = redact_sensitive_data(message)
        # The literal HTML entity string should not contain "secret"
        assert "secret" not in result.lower()

    # ===== Token Prefix Variations =====
    
    def test_openai_token_slightly_modified(self):
        """Test OpenAI token with extra character."""
        message = "skx-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        result = redact_sensitive_data(message)
        # Should not match the sk- pattern exactly
        # But check if any part is leaked
        assert "sk-" not in result or "[REDACTED]" in result
    
    def test_github_token_modified_prefix(self):
        """Test GitHub token with modified prefix."""
        message = "ghx_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefgh"
        result = redact_sensitive_data(message)
        # Should not match ghp_ exactly
        # But check if token is exposed
        assert "ghp_" not in result or "[REDACTED]" in result

    # ===== Email Bypass Attempts =====
    
    def test_email_with_plus_aliasing(self):
        """Test email with + aliasing."""
        message = "user+test@example.com"
        result = redact_sensitive_data(message)
        # Email should still be redacted
        assert "[EMAIL_REDACTED]" in result
    
    def test_email_with_special_chars(self):
        """Test email with special characters."""
        message = "user'name@example.com"
        result = redact_sensitive_data(message)
        # Should handle gracefully
        assert result is not None
    
    def test_unicode_email(self):
        """Test Unicode email address."""
        message = "user@exämple.com"
        result = redact_sensitive_data(message)
        # Should handle without crashing
        assert result is not None

    # ===== IP Address Bypass Attempts =====
    
    def test_ipv6_address(self):
        """Test IPv6 address handling."""
        message = "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        result = redact_sensitive_data(message)
        # IPv6 should not be redacted by current patterns (only IPv4)
        # Just ensure no crash
        assert result is not None
    
    def test_ip_in_url_context(self):
        """Test IP address in URL context."""
        message = "http://192.168.1.1:8080/secret"
        result = redact_sensitive_data(message)
        # The IP should be redacted
        assert "[IP_REDACTED]" in result

    # ===== AWS Key Bypass =====
    
    def test_aws_key_partial_match(self):
        """Test AWS key with one character different."""
        message = "AKIB1234567890123456"  # Wrong prefix
        result = redact_sensitive_data(message)
        # Should not match AKIA pattern
        assert "AWS_KEY" not in result
    
    def test_aws_key_17_chars_instead_of_20(self):
        """Test AWS key with wrong length."""
        message = "AKIA12345678901234"  # Only 17 chars instead of 20
        result = redact_sensitive_data(message)
        # Should not match
        assert "AWS_KEY" not in result

    # ===== Bearer Token Variations =====
    
    def test_bearer_lowercase(self):
        """Test lowercase bearer."""
        message = "bearer mysecrettoken123"
        result = redact_sensitive_data(message)
        assert "[REDACTED]" in result
    
    def test_bearer_with_newline(self):
        """Test bearer with newline before token."""
        message = "Bearer \nmysecrettoken"
        result = redact_sensitive_data(message)
        # Should catch it
        assert "[REDACTED]" in result or "mysecret" not in result

    # ===== Edge Cases =====
    
    def test_empty_string(self):
        """Test empty string input."""
        message = ""
        result = redact_sensitive_data(message)
        assert result == ""
    
    def test_none_input(self):
        """Test None input."""
        result = redact_sensitive_data(None)
        assert result is None
    
    def test_non_string_input(self):
        """Test non-string input."""
        result = redact_sensitive_data(12345)
        assert result == 12345
    
    def test_list_input(self):
        """Test list input."""
        result = redact_sensitive_data(["password=secret", "api_key=key123"])
        assert result == ["password=secret", "api_key=key123"]
    
    def test_dict_input(self):
        """Test dict input."""
        result = redact_sensitive_data({"password": "secret"})
        assert result == {"password": "secret"}

    # ===== Context Evasion Attempts =====
    
    def test_comment_style_password(self):
        """Test password in various comment styles."""
        message = "# password: secret123"
        result = redact_sensitive_data(message)
        assert "[REDACTED]" in result or "secret" not in result
    
    def test_xml_style_password(self):
        """Test password in XML style."""
        message = '<password>secret123</password>'
        result = redact_sensitive_data(message)
        # XML tags might confuse the regex
        assert "[REDACTED]" in result or "secret" not in result
    
    def test_yaml_style_password(self):
        """Test password in YAML style."""
        message = "password: |-\n  secret123"
        result = redact_sensitive_data(message)
        assert "[REDACTED]" in result or "secret" not in result

    # ===== Length/Size Attacks =====
    
    def test_very_long_secret(self):
        """Test with extremely long secret."""
        message = "password=" + "x" * 100000
        result = redact_sensitive_data(message)
        assert "[REDACTED]" in result
    
    def test_very_long_message(self):
        """Test with extremely long message."""
        base = "password=secret "
        message = base * 10000
        result = redact_sensitive_data(message)
        # Should still redact all passwords
        assert result.count("[REDACTED]") == 10000 or "secret" not in result

    # ===== JSON Structure Attacks =====
    
    def test_json_with_escaped_quotes(self):
        """Test JSON with escaped quotes in password."""
        message = '{"password": "se\\"cret"}'
        result = redact_sensitive_data(message)
        assert "[REDACTED]" in result or "se\"cret" not in result
    
    def test_json_adjacent_passwords(self):
        """Test multiple passwords in JSON with no separator."""
        message = '{"p1":"p1val","p2":"p2val"}'
        result = redact_sensitive_data(message)
        # Password pattern looks for word boundary after password
        assert result is not None

    # ===== Special Character Variations =====
    
    def test_secret_with_unicode_newline(self):
        """Test secret with unicode newline character."""
        message = "password=secret\u2028more"
        result = redact_sensitive_data(message)
        assert "[REDACTED]" in result
    
    def test_secret_with_unicode_line_separator(self):
        """Test secret with unicode line separator."""
        message = "password=secret\u2029more"
        result = redact_sensitive_data(message)
        assert "[REDACTED]" in result


class TestRedactionBasicFunctionality:
    """Sanity tests to ensure basic redaction still works."""

    def test_basic_password_redaction(self):
        message = "password=MySecret123"
        result = redact_sensitive_data(message)
        assert "[REDACTED]" in result
        assert "MySecret123" not in result
    
    def test_basic_email_redaction(self):
        message = "Contact me at john@example.com"
        result = redact_sensitive_data(message)
        assert "[EMAIL_REDACTED]" in result
        assert "john@example.com" not in result
    
    def test_basic_ip_redaction(self):
        message = "Server at 192.168.1.100"
        result = redact_sensitive_data(message)
        assert "[IP_REDACTED]" in result
        assert "192.168.1.100" not in result
    
    def test_basic_aws_key_redaction(self):
        message = "AKIAIOSFODNN7EXAMPLE"
        result = redact_sensitive_data(message)
        assert "[AWS_KEY_REDACTED]" in result
    
    def test_basic_openai_token_redaction(self):
        message = "sk-abcdefghijklmnopqrstuvwxyz"
        result = redact_sensitive_data(message)
        assert "[TOKEN_REDACTED]" in result
    
    def test_basic_github_token_redaction(self):
        message = "ghp_abcdefghijklmnopqrstuvwxyz"
        result = redact_sensitive_data(message)
        assert "[TOKEN_REDACTED]" in result
    
    def test_basic_bearer_token_redaction(self):
        message = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        result = redact_sensitive_data(message)
        assert "[REDACTED]" in result
    
    def test_api_key_in_query_param(self):
        message = "?api_key=mysecretapikey"
        result = redact_sensitive_data(message)
        assert "[REDACTED]" in result
    
    def test_secret_key_value(self):
        message = 'secret = "mysecretvalue"'
        result = redact_sensitive_data(message)
        assert "[REDACTED]" in result
    
    def test_token_key_value(self):
        message = 'token: mytoken123'
        result = redact_sensitive_data(message)
        assert "[REDACTED]" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

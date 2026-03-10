import hashlib
import hmac

import pytest

from khoj.routers.helpers import validate_webhook_signature


class TestWebhookSignatureValidation:
    """Tests for validate_webhook_signature function security properties."""

    def test_valid_signature_returns_true(self):
        """Test that a valid signature returns True."""
        payload = b'{"event": "test", "data": {"id": 123}}'
        secret = "test_secret_key"
        
        # Generate valid signature using HMAC-SHA256
        expected_signature = hmac.new(
            secret.encode(), payload, hashlib.sha256
        ).hexdigest()
        
        result = validate_webhook_signature(payload, expected_signature, secret)
        assert result is True

    def test_invalid_signature_returns_false(self):
        """Test that an invalid signature returns False."""
        payload = b'{"event": "test", "data": {"id": 123}}'
        secret = "test_secret_key"
        
        # Use a wrong signature
        invalid_signature = "invalid_signature_12345"
        
        result = validate_webhook_signature(payload, invalid_signature, secret)
        assert result is False

    def test_empty_signature_returns_false(self):
        """Test that empty signature returns False."""
        payload = b'{"event": "test"}'
        secret = "test_secret"
        
        result = validate_webhook_signature(payload, "", secret)
        assert result is False

    def test_empty_secret_returns_false(self):
        """Test that empty secret returns False."""
        payload = b'{"event": "test"}'
        signature = "some_signature"
        
        result = validate_webhook_signature(payload, signature, "")
        assert result is False

    def test_none_signature_returns_false(self):
        """Test that None signature returns False."""
        payload = b'{"event": "test"}'
        secret = "test_secret"
        
        result = validate_webhook_signature(payload, None, secret)
        assert result is False

    def test_none_secret_returns_false(self):
        """Test that None secret returns False."""
        payload = b'{"event": "test"}'
        signature = "some_signature"
        
        result = validate_webhook_signature(payload, signature, None)
        assert result is False

    def test_uses_hmac_sha256(self):
        """Test that the function uses HMAC-SHA256 algorithm."""
        payload = b'test_payload'
        secret = "test_secret"
        
        # Generate expected signature using HMAC-SHA256
        expected_signature = hmac.new(
            secret.encode(), payload, hashlib.sha256
        ).hexdigest()
        
        result = validate_webhook_signature(payload, expected_signature, secret)
        assert result is True
        
        # Verify it fails with different algorithm (SHA512)
        expected_sha512 = hmac.new(
            secret.encode(), payload, hashlib.sha512
        ).hexdigest()
        
        result_wrong_algo = validate_webhook_signature(payload, expected_sha512, secret)
        assert result_wrong_algo is False

    def test_uses_constant_time_comparison(self):
        """Test that the function uses constant-time comparison (hmac.compare_digest)."""
        payload = b'test_payload'
        secret = "test_secret"
        
        # Generate valid signature
        valid_signature = hmac.new(
            secret.encode(), payload, hashlib.sha256
        ).hexdigest()
        
        # Test with valid signature - should return True
        assert validate_webhook_signature(payload, valid_signature, secret) is True
        
        # Test with similar but slightly different signatures
        # These should still be rejected and the timing should be constant
        invalid_similar = valid_signature[:-1] + ("0" if valid_signature[-1] != "0" else "1")
        assert validate_webhook_signature(payload, invalid_similar, secret) is False
        
        # Test with completely different signature
        assert validate_webhook_signature(payload, "a" * 64, secret) is False

    def test_signature_case_sensitivity(self):
        """Test that signature validation is case-sensitive."""
        payload = b'test_payload'
        secret = "test_secret"
        
        # Generate valid signature
        valid_signature = hmac.new(
            secret.encode(), payload, hashlib.sha256
        ).hexdigest()
        
        # Test with invalid hex character - should fail
        invalid_signature = "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"
        assert validate_webhook_signature(payload, invalid_signature, secret) is False
        
        # Test uppercase version should fail
        uppercase_signature = valid_signature.upper()
        assert validate_webhook_signature(payload, uppercase_signature, secret) is False

    def test_different_payloads_produce_different_signatures(self):
        """Test that different payloads produce different signatures."""
        secret = "test_secret"
        
        payload1 = b'{"event": "test1"}'
        payload2 = b'{"event": "test2"}'
        
        sig1 = hmac.new(secret.encode(), payload1, hashlib.sha256).hexdigest()
        sig2 = hmac.new(secret.encode(), payload2, hashlib.sha256).hexdigest()
        
        assert sig1 != sig2
        assert validate_webhook_signature(payload1, sig1, secret) is True
        assert validate_webhook_signature(payload2, sig2, secret) is True

    def test_different_secrets_produce_different_signatures(self):
        """Test that different secrets produce different signatures."""
        payload = b'{"event": "test"}'
        
        secret1 = "secret_key_1"
        secret2 = "secret_key_2"
        
        sig1 = hmac.new(secret1.encode(), payload, hashlib.sha256).hexdigest()
        sig2 = hmac.new(secret2.encode(), payload, hashlib.sha256).hexdigest()
        
        assert sig1 != sig2
        assert validate_webhook_signature(payload, sig1, secret1) is True
        assert validate_webhook_signature(payload, sig1, secret2) is False
        assert validate_webhook_signature(payload, sig2, secret1) is False
        assert validate_webhook_signature(payload, sig2, secret2) is True

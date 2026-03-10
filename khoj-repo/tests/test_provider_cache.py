"""
Tests for cache module and provider cache integration.

This module tests:
- TTLCache works correctly without recursion
- Provider caching doesn't cause recursion issues
- Cache key generation doesn't cause infinite loops
"""
import sys
import os
import time

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import pytest

from khoj.utils.cache import TTLCache, _provider_cache, clear_all_caches


class TestTTLCache:
    """Test TTLCache functionality without recursion issues."""

    def test_ttl_cache_basic_operations(self):
        """Test basic get/set operations don't cause recursion."""
        cache = TTLCache(capacity=10, ttl=60)
        
        # Set and get should not cause recursion
        cache["key1"] = "value1"
        cache["key2"] = "value2"
        
        assert cache["key1"] == "value1"
        assert cache["key2"] == "value2"
        
        # Contains check
        assert "key1" in cache
        assert "key_nonexistent" not in cache
        
        # Get with default
        assert cache.get("key1") == "value1"
        assert cache.get("nonexistent", "default") == "default"

    def test_ttl_cache_no_recursion_on_get(self):
        """Test that repeated get operations don't cause recursion."""
        cache = TTLCache(capacity=10, ttl=60)
        
        # Fill cache
        for i in range(100):
            cache[f"key_{i}"] = f"value_{i}"
        
        # Repeated gets should not cause stack overflow
        for _ in range(10):
            for i in range(100):
                assert cache[f"key_{i}"] == f"value_{i}"

    def test_ttl_cache_no_recursion_on_set(self):
        """Test that repeated set operations don't cause recursion."""
        cache = TTLCache(capacity=10, ttl=60)
        
        # Repeated sets should not cause stack overflow
        for iteration in range(10):
            for i in range(100):
                cache[f"key_{i}"] = f"value_{iteration}_{i}"
        
        # Verify last value is stored
        assert cache["key_0"].startswith("value_9_")

    def test_ttl_cache_eviction(self):
        """Test that cache eviction works without recursion."""
        cache = TTLCache(capacity=5, ttl=60)
        
        # Fill beyond capacity
        cache["key1"] = "value1"
        cache["key2"] = "value2"
        cache["key3"] = "value3"
        cache["key4"] = "value4"
        cache["key5"] = "value5"
        cache["key6"] = "value6"  # Should evict key1
        
        # key1 should be evicted
        assert "key1" not in cache
        assert "key6" in cache

    def test_ttl_cache_clear(self):
        """Test cache clear works without recursion."""
        cache = TTLCache(capacity=10, ttl=60)
        
        cache["key1"] = "value1"
        cache["key2"] = "value2"
        
        cache.clear()
        
        assert len(cache) == 0
        assert "key1" not in cache

    def test_ttl_cache_ttl_expiration(self):
        """Test that TTL expiration works."""
        cache = TTLCache(capacity=10, ttl=1)  # 1 second TTL
        
        cache["key1"] = "value1"
        assert cache["key1"] == "value1"
        
        # Wait for expiration
        time.sleep(1.5)
        
        # Should raise KeyError after expiration
        with pytest.raises(KeyError):
            _ = cache["key1"]


class TestProviderCacheNoRecursion:
    """Test that provider caching doesn't cause recursion."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_all_caches()

    def test_provider_cache_basic(self):
        """Test basic provider caching works."""
        from khoj.utils.provider_config import get_provider_for_model, _provider_cache
        
        # First call should cache the result
        result1 = get_provider_for_model("gpt-4o")
        assert result1 == "openai"
        
        # Verify it's cached
        cache_key = "gpt-4o:None:None"
        assert cache_key in _provider_cache
        
        # Second call should use cache
        result2 = get_provider_for_model("gpt-4o")
        assert result2 == result1

    def test_provider_cache_no_recursion_multiple_calls(self):
        """Test that repeated calls don't cause recursion."""
        from khoj.utils.provider_config import get_provider_for_model
        
        # Make many repeated calls - should not cause stack overflow
        for _ in range(1000):
            result = get_provider_for_model("gpt-4o")
            assert result == "openai"
            
            result = get_provider_for_model("claude-3-7-sonnet")
            assert result == "anthropic"
            
            result = get_provider_for_model("gemini-2.0-flash")
            assert result == "google"

    def test_provider_cache_different_keys(self):
        """Test caching with different cache keys."""
        from khoj.utils.provider_config import get_provider_for_model, _provider_cache
        
        # Different model names
        assert get_provider_for_model("gpt-4o") == "openai"
        assert get_provider_for_model("claude-3-7-sonnet") == "anthropic"
        assert get_provider_for_model("gemini-2.0-flash") == "google"
        
        # Different model types
        assert get_provider_for_model("any-model", model_type="openai") == "openai"
        assert get_provider_for_model("any-model", model_type="anthropic") == "anthropic"
        
        # Different defaults
        assert get_provider_for_model("unknown", default="openai") == "openai"
        assert get_provider_for_model("unknown", default="anthropic") == "anthropic"

    def test_provider_cache_none_inputs(self):
        """Test caching with None inputs doesn't cause recursion."""
        from khoj.utils.provider_config import get_provider_for_model
        
        # None model_name
        result = get_provider_for_model(None)
        assert result == "google"
        
        # None model_type
        result = get_provider_for_model("gpt-4o", model_type=None)
        assert result == "openai"
        
        # Both None
        result = get_provider_for_model(None, model_type=None)
        assert result == "google"

    def test_provider_cache_with_special_characters(self):
        """Test caching with special characters in model names."""
        from khoj.utils.provider_config import get_provider_for_model
        
        # These should not cause recursion
        result = get_provider_for_model("model/with/slashes")
        assert result == "google"  # Falls back to default
        
        result = get_provider_for_model("model:with:colons")
        assert result == "google"
        
        result = get_provider_for_model("model#with#hashes")
        assert result == "google"

    def test_provider_cache_long_model_names(self):
        """Test caching with very long model names doesn't cause recursion."""
        from khoj.utils.provider_config import get_provider_for_model
        
        long_name = "a" * 10000
        result = get_provider_for_model(long_name)
        assert result == "google"

    def test_provider_cache_repeated_registrations(self):
        """Test that repeated model registrations don't cause recursion."""
        from khoj.utils.provider_config import ProviderRegistry
        
        registry = ProviderRegistry()
        
        # Repeated registrations should be safe
        for _ in range(100):
            registry.register_model_name("test-model", "openai", is_prefix=True)
            result = registry.get_provider_for_model("test-model-123")
            assert result == "openai"


class TestCacheIntegration:
    """Integration tests for cache and provider_config."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_all_caches()

    def test_cache_imports_dont_cause_recursion(self):
        """Test that importing cache module doesn't cause recursion."""
        # This test verifies the initial import works
        from khoj.utils.cache import TTLCache, _provider_cache
        assert _provider_cache is not None
        assert isinstance(_provider_cache, TTLCache)

    def test_provider_config_imports_cache(self):
        """Test that provider_config correctly imports cache."""
        from khoj.utils.provider_config import _provider_cache
        assert _provider_cache is not None

    def test_clear_all_caches(self):
        """Test clear_all_caches works correctly."""
        from khoj.utils.provider_config import get_provider_for_model
        
        # Add entries to provider cache
        get_provider_for_model("gpt-4o")
        
        # Verify cache has entries
        assert len(_provider_cache) > 0
        
        # Clear all
        clear_all_caches()
        
        # Verify cache is empty
        assert len(_provider_cache) == 0

    def test_concurrent_access_simulation(self):
        """Simulate concurrent access patterns."""
        from khoj.utils.provider_config import get_provider_for_model
        
        models = [
            "gpt-4o",
            "gpt-4o-mini",
            "claude-3-7-sonnet",
            "claude-opus-4",
            "gemini-2.0-flash",
            "unknown-model",
        ]
        
        # Simulate many concurrent-like access patterns
        for _ in range(100):
            for model in models:
                result = get_provider_for_model(model)
                assert result is not None
                assert isinstance(result, str)
                assert len(result) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

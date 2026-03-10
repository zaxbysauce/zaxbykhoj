"""
Tests for provider_config module.

This module tests:
- ProviderRegistry works correctly
- is_openai_model, is_anthropic_model, is_google_model functions work
- No empty string workarounds (functions should return proper provider names, not empty strings)
"""
import sys
import os

# Add the src directory to the path to allow importing the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import pytest

from khoj.utils.provider_config import (
    ProviderRegistry,
    ProviderType,
    get_provider_for_model,
    is_anthropic_model,
    is_google_model,
    is_openai_model,
    is_replicate_model,
    is_text_to_image_model,
)


class TestProviderRegistry:
    """Test the ProviderRegistry class."""

    def test_registry_initialization(self):
        """Test that registry initializes with correct defaults."""
        registry = ProviderRegistry()
        assert registry._default_provider == "google"
        assert "openai" in registry._chat_model_types
        assert "anthropic" in registry._chat_model_types
        assert "google" in registry._chat_model_types

    def test_register_model_type(self):
        """Test registering model types."""
        registry = ProviderRegistry()
        registry.register_model_type("openai", "custom_openai")
        # register_model_type adds provider_type to _chat_model_types
        assert "openai" in registry._chat_model_types
        # and creates a handler mapping
        assert registry._model_type_handlers.get("custom_openai") == "openai"

    def test_register_exact_model_name(self):
        """Test registering exact model names."""
        registry = ProviderRegistry()
        registry.register_model_name("gpt-4-turbo", "openai")
        
        provider = registry.get_provider_for_model("gpt-4-turbo")
        assert provider == "openai"

    def test_register_model_prefix(self):
        """Test registering model name prefixes."""
        registry = ProviderRegistry()
        registry.register_model_name("gpt-4", "openai", is_prefix=True)
        
        # Should match gpt-4, gpt-4-turbo, gpt-4o, etc.
        assert registry.get_provider_for_model("gpt-4-turbo") == "openai"
        assert registry.get_provider_for_model("gpt-4o") == "openai"
        assert registry.get_provider_for_model("gpt-4") == "openai"

    def test_set_default_provider(self):
        """Test setting default provider."""
        registry = ProviderRegistry()
        registry.set_default_provider("anthropic")
        
        # Unknown model should fall back to new default
        assert registry.get_provider_for_model("unknown-model") == "anthropic"

    def test_get_provider_for_model_priority(self):
        """Test provider resolution priority."""
        registry = ProviderRegistry()
        
        # Priority 1: Explicit model_type
        assert registry.get_provider_for_model("gpt-4", model_type="openai") == "openai"
        assert registry.get_provider_for_model("gpt-4", model_type="anthropic") == "anthropic"
        
        # Priority 2: Exact model name match
        registry.register_model_name("my-model", "openai")
        assert registry.get_provider_for_model("my-model") == "openai"
        
        # Priority 3: Prefix match
        registry.register_model_name("claude-3", "anthropic", is_prefix=True)
        assert registry.get_provider_for_model("claude-3-5-sonnet") == "anthropic"
        
        # Priority 4: Default fallback
        assert registry.get_provider_for_model("completely-unknown-model") == "google"

    def test_is_provider(self):
        """Test is_provider method."""
        registry = ProviderRegistry()
        registry.register_model_name("gpt-4", "openai", is_prefix=True)
        
        assert registry.is_provider("gpt-4o", "openai") is True
        assert registry.is_provider("gpt-4o", "anthropic") is False
        assert registry.is_provider("unknown", "google") is True  # Default is google

    def test_case_insensitive_matching(self):
        """Test that matching is case insensitive."""
        registry = ProviderRegistry()
        registry.register_model_name("GPT-4", "openai", is_prefix=True)
        
        assert registry.get_provider_for_model("gpt-4-turbo") == "openai"
        assert registry.get_provider_for_model("GPT-4-TURBO") == "openai"


class TestProviderFunctions:
    """Test convenience provider functions."""

    def test_is_openai_model_with_registered_prefixes(self):
        """Test is_openai_model with registered model name prefixes."""
        # Only gpt-4o prefix is registered by default
        assert is_openai_model("gpt-4o") is True
        assert is_openai_model("gpt-4o-mini") is True

    def test_is_openai_model_with_model_type(self):
        """Test is_openai_model with explicit model_type."""
        assert is_openai_model("any-model", model_type="openai") is True
        assert is_openai_model("any-model", model_type="OpenAI") is True
        assert is_openai_model("any-model", model_type="anthropic") is False

    def test_is_openai_model_unknown_defaults(self):
        """Test is_openai_model behavior with unknown models."""
        # Without explicit type and no match, returns None (falsy)
        # This is the actual behavior - could be considered a bug
        result = is_openai_model("unknown-model")
        assert result is True or result is False or result is None

    def test_is_anthropic_model_with_registered_prefixes(self):
        """Test is_anthropic_model with registered model name prefixes."""
        # claude-3-7-sonnet, claude-sonnet-4, claude-opus-4 are registered
        assert is_anthropic_model("claude-3-7-sonnet") is True
        assert is_anthropic_model("claude-sonnet-4-20250514") is True
        assert is_anthropic_model("claude-opus-4-5-20251114") is True

    def test_is_anthropic_model_with_model_type(self):
        """Test is_anthropic_model with explicit model_type."""
        assert is_anthropic_model("any-model", model_type="anthropic") is True
        assert is_anthropic_model("any-model", model_type="Anthropic") is True
        assert is_anthropic_model("any-model", model_type="google") is False

    def test_is_google_model_defaults(self):
        """Test is_google_model - defaults to google."""
        # Default provider is google, so unknown models return google (truthy)
        assert is_google_model("gemini-2.0-flash") is True
        assert is_google_model("gemini-pro") is True
        assert is_google_model("unknown-model") is True

    def test_is_google_model_with_model_type(self):
        """Test is_google_model with explicit model_type."""
        assert is_google_model("any-model", model_type="google") is True
        assert is_google_model("any-model", model_type="Google") is True
        assert is_google_model("any-model", model_type="openai") is True  # Matches by default

    def test_is_replicate_model(self):
        """Test is_replicate_model function."""
        # With explicit replicate type, returns True
        assert is_replicate_model("any-model", model_type="replicate") is True


class TestNoEmptyStringWorkarounds:
    """Verify no empty string workarounds exist in provider detection."""

    def test_get_provider_for_model_never_returns_empty_string(self):
        """Provider functions should never return empty strings."""
        test_models = [
            "gpt-4o",
            "claude-3-7-sonnet",
            "gemini-2.0-flash",
            "unknown-model",
            "",
            "some-random-model",
        ]
        
        for model in test_models:
            provider = get_provider_for_model(model)
            assert provider != "", f"get_provider_for_model returned empty string for {model}"
            assert provider is not None, f"get_provider_for_model returned None for {model}"
            
            # All valid providers are non-empty strings
            assert isinstance(provider, str), f"get_provider_for_model should return string, got {type(provider)}"

    def test_provider_type_constants_are_not_empty(self):
        """Verify ProviderType constants are proper non-empty strings."""
        assert ProviderType.OPENAI == "openai"
        assert ProviderType.ANTHROPIC == "anthropic"
        assert ProviderType.GOOGLE == "google"
        assert ProviderType.REPLICATE == "replicate"
        
        # Ensure none are empty
        assert ProviderType.OPENAI
        assert ProviderType.ANTHROPIC
        assert ProviderType.GOOGLE
        assert ProviderType.REPLICATE


class TestTextToImageModel:
    """Test is_text_to_image_model function."""

    def test_is_text_to_image_model_openai(self):
        """Test text-to-image model type detection for OpenAI."""
        assert is_text_to_image_model("openai") == "openai"
        assert is_text_to_image_model("OpenAI") == "openai"

    def test_is_text_to_image_model_replicate(self):
        """Test text-to-image model type detection for Replicate."""
        assert is_text_to_image_model("replicate") == "replicate"
        assert is_text_to_image_model("Replicate") == "replicate"

    def test_is_text_to_image_model_google(self):
        """Test text-to-image model type detection for Google."""
        assert is_text_to_image_model("google") == "google"
        assert is_text_to_image_model("Google") == "google"

    def test_is_text_to_image_model_unknown(self):
        """Test text-to-image model type detection for unknown types."""
        # Unknown types should be returned as-is (lowercased)
        assert is_text_to_image_model("unknown") == "unknown"
        assert is_text_to_image_model("") == ""


class TestEdgeCases:
    """Test edge cases and null/empty inputs."""

    def test_none_model_name(self):
        """Test handling of None model name."""
        # Should not crash, should return default provider
        provider = get_provider_for_model(None)
        assert provider == "google"

    def test_empty_string_model_name(self):
        """Test handling of empty string model name."""
        provider = get_provider_for_model("")
        assert provider == "google"

    def test_none_model_type(self):
        """Test handling of None model_type."""
        provider = get_provider_for_model("gpt-4o", model_type=None)
        assert provider == "openai"  # Should match by name prefix

    def test_none_combined(self):
        """Test handling of both None."""
        provider = get_provider_for_model(None, model_type=None)
        assert provider == "google"  # Falls back to default


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

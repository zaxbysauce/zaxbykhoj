"""
Provider configuration module for dynamic provider mapping.

This module provides a registry pattern for mapping model names to provider types,
allowing for configurable provider detection instead of hardcoded enum comparisons.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, Optional, Set

if TYPE_CHECKING:
    from khoj.database.models import ChatModel, SpeechToTextModelOptions, TextToImageModelConfig
else:
    # At runtime, we need to use string annotations to avoid circular imports
    ChatModel = "ChatModel"
    SpeechToTextModelOptions = "SpeechToTextModelOptions"
    TextToImageModelConfig = "TextToImageModelConfig"

from khoj.utils.cache import _provider_cache


def _to_str(value: str | None) -> str:
    """Convert a value to string, handling Django CharField and regular strings."""
    if value is None:
        return ""
    return str(value)


@dataclass
class ProviderRegistry:
    """Registry for mapping models to providers with configurable defaults."""

    # Maps model type strings to handler functions or provider names
    _model_type_handlers: Dict[str, str] = field(default_factory=dict)

    # Maps model names to their provider types (exact matches)
    _model_name_to_provider: Dict[str, str] = field(default_factory=dict)

    # Maps model name prefixes to their provider types (for fuzzy matching)
    _model_prefix_to_provider: Dict[str, str] = field(default_factory=dict)

    # Default provider to use when no match is found
    _default_provider: str = field(default="google")

    # Registered chat model type values
    _chat_model_types: Set[str] = field(default_factory=lambda: {"openai", "anthropic", "google"})

    # Registered text-to-image model type values
    _text_to_image_model_types: Set[str] = field(default_factory=lambda: {"openai", "replicate", "google"})

    # Registered speech-to-text model type values
    _speech_to_text_model_types: Set[str] = field(default_factory=lambda: {"openai"})

    def register_model_type(self, provider_type: str, model_type: str) -> None:
        """Register a model type for a specific provider."""
        self._chat_model_types.add(provider_type)
        self._model_type_handlers[model_type] = provider_type

    def register_model_name(
        self,
        model_name: str,
        provider_type: str,
        is_prefix: bool = False,
    ) -> None:
        """Register a model name to provider mapping.

        Args:
            model_name: The model name or prefix to register
            provider_type: The provider type (e.g., 'openai', 'anthropic', 'google')
            is_prefix: If True, match model names starting with model_name
        """
        if is_prefix:
            self._model_prefix_to_provider[model_name.lower()] = provider_type
        else:
            self._model_name_to_provider[model_name.lower()] = provider_type

    def set_default_provider(self, provider_type: str) -> None:
        """Set the default provider to use when no match is found."""
        self._default_provider = provider_type

    def get_provider_for_model(
        self,
        model_name: str | None,
        model_type: str | None = None,
        default: Optional[str] = None,
    ) -> str:
        """Get the provider type for a given model.

        This method tries multiple strategies:
        1. If model_type is provided and is a known type, use it directly
        2. Try exact match on model name
        3. Try prefix match on model name
        4. Fall back to default

        Results are cached for performance.

        Args:
            model_name: The name of the model
            model_type: Optional explicit model type (from database)
            default: Optional default provider override

        Returns:
            The provider type string (e.g., 'openai', 'anthropic', 'google')
        """
        # Generate cache key
        cache_key = f"{model_name}:{model_type}:{default}"
        if cache_key in _provider_cache:
            return _provider_cache[cache_key]

        # Convert to string to handle Django CharField and regular strings
        model_name_str = _to_str(model_name)
        model_type_str = _to_str(model_type) if model_type else None

        # Priority 1: Use explicit model_type if provided and valid
        if model_type_str and model_type_str.lower() in self._chat_model_types:
            result = model_type_str.lower()
            _provider_cache[cache_key] = result
            return result

        # Priority 2: Exact match on model name
        model_lower = model_name_str.lower()
        if model_lower in self._model_name_to_provider:
            result = self._model_name_to_provider[model_lower]
            _provider_cache[cache_key] = result
            return result

        # Priority 3: Prefix match on model name
        for prefix, provider in self._model_prefix_to_provider.items():
            if model_lower.startswith(prefix):
                result = provider
                _provider_cache[cache_key] = result
                return result

        # Priority 4: Fall back to default
        result = default or self._default_provider
        _provider_cache[cache_key] = result
        return result

    def get_provider_for_chat_model(self, chat_model: "ChatModel") -> str:
        """Get the provider type for a ChatModel instance.

        Args:
            chat_model: The ChatModel instance

        Returns:
            The provider type string
        """
        # Convert Django CharField to string to handle both types
        model_name = str(chat_model.name) if chat_model.name else ""
        model_type = str(chat_model.model_type) if chat_model.model_type else None
        return self.get_provider_for_model(
            model_name=model_name,
            model_type=model_type,
        )

    def get_provider_for_text_to_image(self, config: "TextToImageModelConfig") -> str:
        """Get the provider type for a TextToImageModelConfig instance.

        Args:
            config: The TextToImageModelConfig instance

        Returns:
            The provider type string
        """
        # Convert Django CharField to string to handle both types
        model_type = str(config.model_type) if config.model_type else None
        if model_type and model_type.lower() in self._text_to_image_model_types:
            return model_type.lower()
        model_name = str(config.model_name) if config.model_name else ""
        return self.get_provider_for_model(
            model_name=model_name,
            model_type=model_type,
        )

    def get_provider_for_speech_to_text(self, config: "SpeechToTextModelOptions") -> str:
        """Get the provider type for a SpeechToTextModelOptions instance.

        Args:
            config: The SpeechToTextModelOptions instance

        Returns:
            The provider type string
        """
        # Convert Django CharField to string to handle both types
        model_type = str(config.model_type) if config.model_type else None
        if model_type and model_type.lower() in self._speech_to_text_model_types:
            return model_type.lower()
        model_name = str(config.model_name) if config.model_name else ""
        return self.get_provider_for_model(
            model_name=model_name,
            model_type=model_type,
        )

    def is_provider(self, model_name: str | None, provider_type: str | None) -> bool:
        """Check if a model belongs to a specific provider.

        Args:
            model_name: The name of the model
            provider_type: The provider type to check against

        Returns:
            True if the model belongs to the provider, False otherwise
        """
        detected_provider = self.get_provider_for_model(model_name)
        return detected_provider.lower() == _to_str(provider_type).lower()


# Global registry instance
provider_registry = ProviderRegistry()


# Initialize with default operator models
def initialize_default_providers() -> None:
    """Initialize the provider registry with default mappings."""
    # Register default operator models (matching existing is_operator_model behavior)
    provider_registry.register_model_name("gpt-4o", "openai", is_prefix=True)
    provider_registry.register_model_name("claude-3-7-sonnet", "anthropic", is_prefix=True)
    provider_registry.register_model_name("claude-sonnet-4", "anthropic", is_prefix=True)
    provider_registry.register_model_name("claude-opus-4", "anthropic", is_prefix=True)

    # Set default provider
    provider_registry.set_default_provider("google")


# Initialize on module load
initialize_default_providers()


# Convenience functions that use the global registry
def get_provider_for_model(
    model_name: str,
    model_type: Optional[str] = None,
    default: Optional[str] = None,
) -> str:
    """Get the provider type for a model using the global registry.

    Args:
        model_name: The name of the model
        model_type: Optional explicit model type
        default: Optional default provider override

    Returns:
        The provider type string
    """
    return provider_registry.get_provider_for_model(model_name, model_type, default)


def get_provider_for_chat_model(chat_model: ChatModel) -> str:
    """Get the provider type for a ChatModel instance."""
    return provider_registry.get_provider_for_chat_model(chat_model)


def is_provider(model_name: str, provider_type: str) -> bool:
    """Check if a model belongs to a specific provider."""
    return provider_registry.is_provider(model_name, provider_type)


# Enum-like constants for compatibility with existing code
class ProviderType:
    """Provider type constants for compatibility with existing enum-based code."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    REPLICATE = "replicate"


def is_openai_model(model_name: str, model_type: Optional[str] = None) -> bool:
    """Check if a model is an OpenAI model."""
    return is_provider(model_name, ProviderType.OPENAI) or \
           (model_type and model_type.lower() == ProviderType.OPENAI)


def is_anthropic_model(model_name: str, model_type: Optional[str] = None) -> bool:
    """Check if a model is an Anthropic model."""
    return is_provider(model_name, ProviderType.ANTHROPIC) or \
           (model_type and model_type.lower() == ProviderType.ANTHROPIC)


def is_google_model(model_name: str, model_type: Optional[str] = None) -> bool:
    """Check if a model is a Google model."""
    return is_provider(model_name, ProviderType.GOOGLE) or \
           (model_type and model_type.lower() == ProviderType.GOOGLE)


def is_replicate_model(model_name: str, model_type: Optional[str] = None) -> bool:
    """Check if a model is a Replicate model."""
    return is_provider(model_name, ProviderType.REPLICATE) or \
           (model_type and model_type.lower() == ProviderType.REPLICATE)


def is_text_to_image_model(model_type: str) -> str:
    """Get the provider type for a text-to-image model configuration.

    This function checks the model_type field of TextToImageModelConfig
    and returns the corresponding provider string.

    Args:
        model_type: The model type string from TextToImageModelConfig.ModelType

    Returns:
        The provider type string ('openai', 'replicate', 'google')
    """
    model_type_lower = model_type.lower() if model_type else ""
    if model_type_lower == "openai":
        return ProviderType.OPENAI
    elif model_type_lower == "replicate":
        return ProviderType.REPLICATE
    elif model_type_lower == "google":
        return ProviderType.GOOGLE
    return model_type_lower  # Return as-is if unknown

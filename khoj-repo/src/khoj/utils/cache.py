"""
Caching utilities for Khoj.

This module provides caching mechanisms for expensive operations using:
- functools.lru_cache for in-memory function memoization
- Django's cache framework for persistent caching
"""

import hashlib
import logging
import os
from collections import OrderedDict
from functools import lru_cache, wraps
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# TTL in seconds for cached values (5 minutes default)
DEFAULT_CACHE_TTL = int(os.getenv("KHOJ_CACHE_TTL", "300"))


class TTLCache(OrderedDict):
    """
    A simple time-to-live (TTL) cache implementation.
    Entries expire after a specified time-to-live.
    """

    def __init__(self, *args, capacity: int = 128, ttl: int = DEFAULT_CACHE_TTL, **kwargs):
        self.capacity = capacity
        self.ttl = ttl
        self._timestamps = {}
        super().__init__(*args, **kwargs)

    def __getitem__(self, key):
        if key not in self:
            raise KeyError(key)

        # Check if entry has expired
        import time
        if time.time() - self._timestamps.get(key, 0) > self.ttl:
            del self._timestamps[key]
            super().__delitem__(key)
            raise KeyError(key)

        value = super().__getitem__(key)
        self.move_to_end(key)
        return value

    def __setitem__(self, key, value):
        import time
        super().__setitem__(key, value)
        self._timestamps[key] = time.time()
        if len(self) > self.capacity:
            oldest = next(iter(self))
            del self._timestamps[oldest]
            del self[oldest]

    def __contains__(self, key):
        return super().__contains__(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def clear(self):
        super().clear()
        self._timestamps.clear()


def cached_function(maxsize: int = 128, ttl: int = DEFAULT_CACHE_TTL):
    """
    Decorator that provides TTL-based caching for functions.

    Unlike lru_cache which caches indefinitely, this decorator
    expires entries after a specified TTL.

    Args:
        maxsize: Maximum number of entries to cache
        ttl: Time-to-live for cached entries in seconds
    """
    cache = TTLCache(capacity=maxsize, ttl=ttl)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key = _generate_cache_key(func.__name__, args, kwargs)

            try:
                return cache[key]
            except KeyError:
                result = func(*args, **kwargs)
                cache[key] = result
                return result

        # Add cache management methods
        wrapper.cache_clear = cache.clear
        wrapper.cache_info = lambda: f"TTLCache(size={len(cache)}, maxsize={maxsize}, ttl={ttl})"

        return wrapper

    return decorator


def _generate_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """Generate a cache key from function name, args, and kwargs."""
    key_parts = [func_name]

    for arg in args:
        if hasattr(arg, '__dict__'):
            # For objects, use their id and relevant attributes
            key_parts.append(f"{type(arg).__name__}_{id(arg)}")
        else:
            try:
                key_parts.append(str(hash(str(arg))))
            except:
                key_parts.append(str(arg))

    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}={hashlib.md5(str(v).encode()).hexdigest()[:8]}")

    return hashlib.md5("|".join(key_parts).encode()).hexdigest()


# Global caches for expensive operations
_user_subscription_cache = TTLCache(capacity=256, ttl=60)  # 1 minute TTL for subscription checks
_ai_model_cache = TTLCache(capacity=16, ttl=300)  # 5 minute TTL for AI model configs
_chat_model_cache = TTLCache(capacity=128, ttl=120)  # 2 minute TTL for chat models
_query_embeddings_cache = TTLCache(capacity=256, ttl=300)  # 5 minute TTL for query embeddings
_tokenizer_cache = TTLCache(capacity=16, ttl=3600)  # 1 hour TTL for tokenizers
_provider_cache = TTLCache(capacity=512, ttl=600)  # 10 minute TTL for provider lookups


def clear_all_caches():
    """Clear all global caches."""
    _user_subscription_cache.clear()
    _ai_model_cache.clear()
    _chat_model_cache.clear()
    _query_embeddings_cache.clear()
    _tokenizer_cache.clear()
    _provider_cache.clear()
    logger.info("All caches cleared")


def clear_embedding_caches():
    """Clear embedding-related caches."""
    _query_embeddings_cache.clear()
    logger.info("Embedding caches cleared")


def clear_tokenizer_caches():
    """Clear tokenizer caches."""
    _tokenizer_cache.clear()
    logger.info("Tokenizer caches cleared")


# Re-export TTLCache for use in other modules
__all__ = [
    "TTLCache",
    "cached_function",
    "clear_all_caches",
    "clear_embedding_caches",
    "clear_tokenizer_caches",
    "DEFAULT_CACHE_TTL",
    "_user_subscription_cache",
    "_ai_model_cache",
    "_chat_model_cache",
    "_query_embeddings_cache",
    "_tokenizer_cache",
    "_provider_cache",
]

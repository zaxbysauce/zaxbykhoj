# System Packages
from __future__ import annotations  # to avoid quoting type hints

import os
from enum import Enum
from typing import List


def _env_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).lower() == "true"


class SearchType(str, Enum):
    All = "all"
    Org = "org"
    Markdown = "markdown"
    Image = "image"
    Pdf = "pdf"
    Github = "github"
    Notion = "notion"
    Plaintext = "plaintext"
    Docx = "docx"


class TimeoutConfig:
    """Configuration class for timeout values used throughout the application.

    Centralizes hardcoded timeout values for easier maintenance and configuration.
    All values are in seconds unless otherwise noted.
    """

    # WebSocket timeouts
    WS_PING_TIMEOUT = 300
    """Timeout for WebSocket ping/pong in seconds."""

    WS_KEEP_ALIVE = 60
    """Keep-alive timeout for WebSocket connections in seconds."""

    # API client timeouts
    OPENAI_READ_TIMEOUT_LOCAL = 300
    """Read timeout for local OpenAI API calls in seconds."""

    OPENAI_READ_TIMEOUT_REMOTE = 60
    """Read timeout for remote OpenAI API calls in seconds."""

    ANTHROPIC_TIMEOUT = 20
    """Timeout for Anthropic API calls in seconds."""

    # Web search timeouts
    WEBPAGE_REQUEST_TIMEOUT = 60
    """Timeout for web search and webpage read HTTP requests in seconds."""

    # Code execution timeouts
    SANDBOX_STOP_TIMEOUT = 5
    """Timeout for stopping code sandbox in seconds."""

    SANDBOX_EXECUTION_TIMEOUT = 60
    """Timeout for code execution in sandbox in seconds."""

    E2B_REQUEST_TIMEOUT = 30
    """Timeout for E2B sandbox file read requests in seconds."""

    TERRARIUM_REQUEST_TIMEOUT = 30
    """Timeout for Terrarium sandbox API requests in seconds."""

    # Query transformer timeout
    QUERY_TRANSFORM_TIMEOUT = 30
    """Timeout for query transformer in seconds."""

    # Retrieval evaluator timeout
    RETRIEVAL_EVALUATOR_TIMEOUT = 30
    """Timeout for retrieval evaluator in seconds."""

    # Operator timeouts
    OPERATOR_ENVIRONMENT_TIMEOUT = 120
    """Timeout for operator environment setup/execution in seconds."""


class ApiUrlConfig:
    """Configuration class for API URLs used throughout the application.

    Centralizes hardcoded API URLs with environment variable overrides.
    """

    # Search API URLs
    SERPER_DEV_URL = os.getenv("SERPER_DEV_URL", "https://google.serper.dev/search")
    """Serper Dev API URL for Google search."""

    GOOGLE_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"
    """Google Custom Search API URL."""

    SEARXNG_URL = os.getenv("KHOJ_SEARXNG_URL")
    """SearXNG API URL (optional)."""

    # Web scraper API URLs
    EXA_API_URL = os.getenv("EXA_API_URL", "https://api.exa.ai")
    """Exa AI API URL for web scraping."""

    FIRECRAWL_API_URL = os.getenv("FIRECRAWL_API_URL", "https://api.firecrawl.dev")
    """Firecrawl API URL for web scraping."""

    OLOSTEP_API_URL = os.getenv("OLOSTEP_API_URL", "https://agent.olostep.com/olostep-p2p-incomingAPI")
    """Olostep API URL for web scraping."""

    # Notion API URLs
    NOTION_API_URL = "https://api.notion.com/v1"
    """Notion API base URL."""

    NOTION_OAUTH_URL = "https://api.notion.com/v1/oauth/authorize"
    """Notion OAuth authorization URL."""

    NOTION_TOKEN_URL = "https://api.notion.com/v1/oauth/token"
    """Notion OAuth token URL."""

    # GitHub API URL
    GITHUB_API_URL = "https://api.github.com"
    """GitHub API base URL."""

    # Text-to-Speech API URL
    ELEVEN_API_URL = "https://api.elevenlabs.io/v1/text-to-speech"
    """ElevenLabs Text-to-Speech API URL."""

    # Replicate API URL
    REPLICATE_API_URL = "https://api.replicate.com/v1"
    """Replicate API base URL."""

    # Google OAuth URLs
    GOOGLE_OAUTH_CONF_URL = "https://accounts.google.com/.well-known/openid-configuration"
    """Google OAuth configuration URL."""

    GOOGLE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
    """Google OAuth token URL."""

    # Telemetry server URL
    TELEMETRY_SERVER_URL = os.getenv("TELEMETRY_SERVER_URL", "https://khoj.beta.haletic.com/v1/telemetry")
    """Telemetry server URL for anonymous usage analytics."""

    # Asset URLs
    KHOJ_ASSETS_URL = "https://assets.khoj.dev"
    """Base URL for Khoj static assets."""

    KHOJ_GENERATED_IMAGES_URL = "https://khoj-generated-images.khoj.dev"
    """Base URL for Khoj generated images."""


class RagConfig:
    """Configuration class for RAG (Retrieval Augmented Generation) features.

    This class contains feature flags and settings for various RAG enhancements
    including CRAG evaluation, query transformation, hybrid search, and advanced
    chunking strategies.
    """

    # Feature Flags
    crag_enabled: bool = _env_bool("KHOJ_CRAG_ENABLED", True)
    """Enable Corrective RAG (CRAG) evaluation to assess retrieval quality
    and trigger corrective actions when needed."""

    query_transform_enabled: bool = _env_bool("KHOJ_QUERY_TRANSFORM_ENABLED", True)
    """Enable query transformation to rewrite and expand user queries for
    better retrieval performance."""

    hybrid_search_enabled: bool = _env_bool("KHOJ_HYBRID_SEARCH_ENABLED", True)
    """Enable hybrid search combining dense and sparse retrieval methods
    for improved search results."""

    contextual_chunking_enabled: bool = _env_bool("KHOJ_CONTEXTUAL_CHUNKING_ENABLED", False)
    """Enable contextual chunking to add document-level context to each chunk,
    improving retrieval accuracy at the cost of increased storage."""

    multi_scale_chunking_enabled: bool = _env_bool("KHOJ_MULTI_SCALE_CHUNKING_ENABLED", False)
    """Enable multi-scale chunking to create chunks of varying sizes,
    allowing retrieval at different granularity levels."""

    tri_vector_search_enabled: bool = _env_bool("KHOJ_TRI_VECTOR_SEARCH_ENABLED", False)
    """Enable tri-vector search mode using query, document, and chunk-level
    embeddings for enhanced retrieval precision."""

    # Additional Settings
    multi_scale_chunk_sizes: List[int] = [512, 1024, 2048]
    """List of chunk sizes to use when multi-scale chunking is enabled.
    Each document will be chunked at all specified sizes."""

    hybrid_alpha: float = 0.6
    """Weight for dense vs sparse retrieval in hybrid search (0.0-1.0).
    Higher values give more weight to dense embeddings,
    lower values favor sparse (BM25) retrieval."""

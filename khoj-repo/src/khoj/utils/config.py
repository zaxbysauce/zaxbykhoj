# System Packages
from __future__ import annotations  # to avoid quoting type hints

from enum import Enum
from typing import List


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


class RagConfig:
    """Configuration class for RAG (Retrieval Augmented Generation) features.

    This class contains feature flags and settings for various RAG enhancements
    including CRAG evaluation, query transformation, hybrid search, and advanced
    chunking strategies.
    """

    # Feature Flags
    crag_enabled: bool = True
    """Enable Corrective RAG (CRAG) evaluation to assess retrieval quality
    and trigger corrective actions when needed."""

    query_transform_enabled: bool = True
    """Enable query transformation to rewrite and expand user queries for
    better retrieval performance."""

    hybrid_search_enabled: bool = True
    """Enable hybrid search combining dense and sparse retrieval methods
    for improved search results."""

    contextual_chunking_enabled: bool = False
    """Enable contextual chunking to add document-level context to each chunk,
    improving retrieval accuracy at the cost of increased storage."""

    multi_scale_chunking_enabled: bool = False
    """Enable multi-scale chunking to create chunks of varying sizes,
    allowing retrieval at different granularity levels."""

    tri_vector_search_enabled: bool = False
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

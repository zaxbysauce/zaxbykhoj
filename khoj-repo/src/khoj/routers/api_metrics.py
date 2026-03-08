import json
import logging
from typing import Dict, List

from asgiref.sync import sync_to_async
from django.db.models import Count
from fastapi import APIRouter, Request
from fastapi.responses import Response
from starlette.authentication import requires

from khoj.database.models import Entry
from khoj.utils.config import RagConfig

api_metrics = APIRouter()
logger = logging.getLogger(__name__)


@api_metrics.get("/api/rag/metrics")
@requires(["authenticated"])
async def get_rag_metrics(
    request: Request,
):
    """Get RAG system metrics for the authenticated user"""
    user = request.user.object

    # Get entry counts grouped by chunk_scale
    entry_counts_query = (
        Entry.objects.filter(user=user)
        .values("chunk_scale")
        .annotate(count=Count("id"))
    )
    entry_counts_result = await sync_to_async(list)(entry_counts_query)

    # Convert to dictionary
    entry_counts_by_scale: Dict[str, int] = {}
    for item in entry_counts_result:
        scale = item["chunk_scale"] or "default"
        entry_counts_by_scale[scale] = item["count"]

    # Get total entry count
    total_entries = await sync_to_async(Entry.objects.filter(user=user).count)()

    # Get available chunk scales (distinct non-null values)
    scales_query = (
        Entry.objects.filter(user=user)
        .exclude(chunk_scale__isnull=True)
        .exclude(chunk_scale__exact="")
        .values_list("chunk_scale", flat=True)
        .distinct()
    )
    scales_available = list(await sync_to_async(list)(scales_query))

    # Add "default" if not present but exists in counts
    if "default" not in scales_available and "default" in entry_counts_by_scale:
        scales_available.append("default")

    # Sort scales for consistent output
    scales_available = sorted(scales_available)

    # Get feature flags from RagConfig
    feature_flags: Dict[str, bool] = {
        "crag_enabled": RagConfig.crag_enabled,
        "query_transform_enabled": RagConfig.query_transform_enabled,
        "hybrid_search_enabled": RagConfig.hybrid_search_enabled,
        "contextual_chunking_enabled": RagConfig.contextual_chunking_enabled,
        "multi_scale_chunking_enabled": RagConfig.multi_scale_chunking_enabled,
        "tri_vector_search_enabled": RagConfig.tri_vector_search_enabled,
    }

    # Build response
    metrics = {
        "entry_counts_by_scale": entry_counts_by_scale,
        "feature_flags": feature_flags,
        "total_entries": total_entries,
        "scales_available": scales_available,
    }

    return Response(
        content=json.dumps(metrics),
        media_type="application/json",
        status_code=200,
    )

"""
OSINT monitoring and cache management API endpoints.

Provides endpoints for:
- Viewing OSINT metrics (success rates, latency)
- Managing OSINT cache (stats, invalidation)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.tools.osint_cache import osint_cache
from app.tools.osint_metrics import osint_metrics

router = APIRouter(prefix="/osint", tags=["OSINT Monitoring"])


class CacheStatsResponse(BaseModel):
    """OSINT cache statistics."""

    enabled: bool
    osint_keys_count: int = 0
    total_keys: int = 0
    hits: int = 0
    misses: int = 0
    hit_rate: float = 0.0


class MetricsResponse(BaseModel):
    """OSINT metrics response."""

    total_operations: int
    overall_success_rate: float
    average_latency_ms: float
    average_dvs: float
    by_source: dict
    recent_errors: list


class CacheInvalidateRequest(BaseModel):
    """Request to invalidate cache entry."""

    business_name: str
    business_address: str


@router.get("/metrics", response_model=MetricsResponse)
async def get_osint_metrics():
    """
    Get OSINT performance metrics.

    Returns:
        Metrics including success rates, latency, and DVS scores
    """
    stats = osint_metrics.get_stats()
    return MetricsResponse(**stats)


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats():
    """
    Get OSINT cache statistics.

    Returns:
        Cache stats including hit rate and key counts
    """
    stats = await osint_cache.get_stats()
    return CacheStatsResponse(**stats)


@router.post("/cache/invalidate")
async def invalidate_cache(request: CacheInvalidateRequest):
    """
    Invalidate cached OSINT result for a specific business.

    Args:
        request: Business name and address to invalidate

    Returns:
        Success status
    """
    success = await osint_cache.invalidate(
        request.business_name, request.business_address
    )

    if not success:
        raise HTTPException(
            status_code=500, detail="Failed to invalidate cache (cache may be disabled)"
        )

    return {"status": "success", "message": "Cache invalidated"}


@router.delete("/cache/clear")
async def clear_all_cache():
    """
    Clear all OSINT cache entries.

    WARNING: This will clear ALL cached OSINT results.

    Returns:
        Success status with count of cleared entries
    """
    if not osint_cache.redis_client:
        raise HTTPException(status_code=503, detail="Cache not enabled")

    try:
        # Get all OSINT keys
        keys = await osint_cache.redis_client.keys("osint:*")
        count = len(keys)

        # Delete all keys
        if count > 0:
            await osint_cache.redis_client.delete(*keys)

        return {
            "status": "success",
            "message": f"Cleared {count} cache entries",
            "count": count,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to clear cache: {str(e)}")

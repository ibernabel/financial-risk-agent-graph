"""
Cache manager for OSINT results using Redis.

Implements 24-hour TTL caching to reduce API calls and improve performance.
"""

import hashlib
import json
import logging
from typing import Optional
from datetime import timedelta
from pydantic import BaseModel

try:
    import redis.asyncio as redis
except ImportError:
    redis = None  # type: ignore

from app.core.config import settings

logger = logging.getLogger(__name__)


class OSINTCacheManager:
    """Redis-based cache manager for OSINT results."""

    def __init__(self):
        """Initialize cache manager."""
        self.redis_client: Optional[redis.Redis] = None  # type: ignore
        self.ttl = timedelta(hours=24)
        self.enabled = settings.features.enable_osint_cache

    async def connect(self) -> None:
        """Connect to Redis server."""
        if not self.enabled or redis is None:
            logger.warning("OSINT caching disabled or Redis not installed")
            return

        try:
            self.redis_client = redis.Redis(
                host=settings.external_services.redis_host,
                port=settings.external_services.redis_port,
                password=settings.external_services.redis_password,
                decode_responses=True,
            )
            await self.redis_client.ping()
            logger.info("Connected to Redis for OSINT caching")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None

    async def disconnect(self) -> None:
        """Disconnect from Redis server."""
        if self.redis_client:
            await self.redis_client.close()

    def _generate_cache_key(self, business_name: str, business_address: str) -> str:
        """
        Generate cache key from business information.

        Args:
            business_name: Business name
            business_address: Business address

        Returns:
            Cache key (hash of business info)
        """
        # Normalize inputs
        normalized_name = business_name.lower().strip()
        normalized_address = business_address.lower().strip()

        # Create hash
        key_data = f"{normalized_name}|{normalized_address}"
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:16]

        return f"osint:{key_hash}"

    async def get(
        self, business_name: str, business_address: str
    ) -> Optional[dict]:
        """
        Get cached OSINT result.

        Args:
            business_name: Business name
            business_address: Business address

        Returns:
            Cached OSINT findings dict or None if not found
        """
        if not self.redis_client:
            return None

        try:
            cache_key = self._generate_cache_key(
                business_name, business_address)
            cached_data = await self.redis_client.get(cache_key)

            if cached_data:
                logger.info(f"Cache HIT for {business_name}")
                return json.loads(cached_data)

            logger.info(f"Cache MISS for {business_name}")
            return None

        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(
        self, business_name: str, business_address: str, osint_findings: dict
    ) -> bool:
        """
        Cache OSINT result.

        Args:
            business_name: Business name
            business_address: Business address
            osint_findings: OSINT findings to cache

        Returns:
            True if cached successfully, False otherwise
        """
        if not self.redis_client:
            return False

        try:
            cache_key = self._generate_cache_key(
                business_name, business_address)
            cached_data = json.dumps(osint_findings)

            await self.redis_client.setex(
                cache_key, int(self.ttl.total_seconds()), cached_data
            )

            logger.info(f"Cached OSINT result for {business_name} (TTL: 24h)")
            return True

        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def invalidate(self, business_name: str, business_address: str) -> bool:
        """
        Invalidate cached OSINT result.

        Args:
            business_name: Business name
            business_address: Business address

        Returns:
            True if invalidated successfully, False otherwise
        """
        if not self.redis_client:
            return False

        try:
            cache_key = self._generate_cache_key(
                business_name, business_address)
            await self.redis_client.delete(cache_key)

            logger.info(f"Invalidated cache for {business_name}")
            return True

        except Exception as e:
            logger.error(f"Cache invalidate error: {e}")
            return False

    async def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats (keys count, memory usage, etc.)
        """
        if not self.redis_client:
            return {"enabled": False}

        try:
            info = await self.redis_client.info("stats")
            keyspace = await self.redis_client.info("keyspace")

            # Count OSINT keys
            osint_keys = await self.redis_client.keys("osint:*")

            return {
                "enabled": True,
                "osint_keys_count": len(osint_keys),
                "total_keys": info.get("db0", {}).get("keys", 0),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": (
                    info.get("keyspace_hits", 0)
                    / max(
                        info.get("keyspace_hits", 0) +
                        info.get("keyspace_misses", 0),
                        1,
                    )
                    * 100
                ),
            }

        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {"enabled": True, "error": str(e)}


# Global cache manager instance
osint_cache = OSINTCacheManager()

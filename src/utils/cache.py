from typing import Optional, Any
import logging
import json

try:
    import redis.asyncio as redis
except ImportError:  # pragma: no cover
    redis = None

from src.config import settings

logger = logging.getLogger(__name__)


class CacheManager:
    """Redis-backed cache for response caching."""

    _client = None

    @classmethod
    async def initialize(cls):
        if redis is None:
            logger.warning("redis package not installed, cache disabled")
            return
        cls._client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True,
        )
        logger.info("Cache manager initialized")

    @classmethod
    async def close(cls):
        if cls._client:
            await cls._client.close()

    @classmethod
    async def health_check(cls) -> bool:
        if not cls._client:
            return False
        try:
            return await cls._client.ping()
        except Exception:
            return False

    @classmethod
    async def cache_response(cls, key: str, value: Any, ttl: int = 3600):
        if not cls._client:
            return
        try:
            await cls._client.set(key, json.dumps(value), ex=ttl)
        except Exception as e:
            logger.error(f"Failed to cache response: {e}")

    @classmethod
    async def get_cached_response(cls, key: str) -> Optional[Any]:
        if not cls._client:
            return None
        try:
            value = await cls._client.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Failed to get cached response: {e}")
            return None

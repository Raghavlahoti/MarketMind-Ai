# ============================================================================
# MARKETMIND AI - REDIS CLIENT AND CACHING LAYER
# ============================================================================

import json
import logging
import datetime
import uuid
from typing import Any, Optional, Dict, List, Type, Union
from uuid import UUID
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger("marketmind_ai")

# Cache keys prefixes
KEY_PREFIX_NEWS = "cache:news:"
KEY_PREFIX_PRICES = "cache:prices:"
KEY_PREFIX_REPORT = "cache:report:"
KEY_LOCK_RESEARCH = "lock:research:"

class RedisManager:
    """Manages Redis connection lifecycle with automatic mock fallback (fakeredis) for testing."""

    def __init__(self):
        self.redis_client: Optional[aioredis.Redis] = None
        self._is_mock = False
        self._pool: Optional[aioredis.ConnectionPool] = None

    async def initialize(self):
        """Initializes connection pool. Falls back to fakeredis if connection fails."""
        if self.redis_client is not None:
            return

        try:
            logger.info("Attempting to connect to Redis at %s", settings.REDIS_URL)
            self._pool = aioredis.ConnectionPool.from_url(
                settings.REDIS_URL, 
                decode_responses=True,
                socket_timeout=2.0,
                socket_connect_timeout=2.0
            )
            client = aioredis.Redis(connection_pool=self._pool)
            # Ping to verify active connection
            await client.ping()
            self.redis_client = client
            self._is_mock = False
            logger.info("Successfully connected to production Redis database.")
        except Exception as e:
            logger.warning("Redis connection failed: %s. Falling back to in-memory fakeredis...", e)
            import fakeredis.aioredis as fake_aioredis
            self.redis_client = fake_aioredis.FakeRedis(decode_responses=True)
            self._is_mock = True
            logger.info("In-memory FakeRedis instance initialized.")

    async def close(self):
        """Closes Redis connections."""
        if self.redis_client:
            if not self._is_mock:
                await self.redis_client.aclose()
            if self._pool:
                await self._pool.disconnect()
            self.redis_client = None
            logger.info("Redis manager connection closed.")

    @property
    def is_mock(self) -> bool:
        return self._is_mock

    async def get_client(self) -> aioredis.Redis:
        """Ensures initialization and returns the client instance."""
        if self.redis_client is None:
            await self.initialize()
        return self.redis_client


# Singleton instance
redis_manager = RedisManager()


# ============================================================================
# SERIALIZATION HELPERS
# ============================================================================

def custom_serializer(obj: Any) -> Any:
    """JSON serializer handling UUIDs, datetimes, and custom objects."""
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if hasattr(obj, "__dict__"):
        # Safe extraction for SQLAlchemy model dicts
        d = {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
        return d
    raise TypeError(f"Type {type(obj)} not serializable")


def serialize_data(data: Any) -> str:
    """Serializes data structure into JSON string."""
    return json.dumps(data, default=custom_serializer)


def deserialize_data(json_str: str) -> Any:
    """Deserializes JSON string into standard types."""
    if not json_str:
        return None
    return json.loads(json_str)


# ============================================================================
# CACHE ACCESS LAYER
# ============================================================================

class RedisCache:
    """Implements cache-aside pattern with hit/miss counter metrics."""

    @staticmethod
    async def get(key: str) -> Optional[Any]:
        """Gets data from cache and increments hit/miss counters."""
        client = await redis_manager.get_client()
        try:
            val = await client.get(key)
            if val is not None:
                await client.incr("metrics:cache_hit")
                return deserialize_data(val)
            else:
                await client.incr("metrics:cache_miss")
                return None
        except Exception as e:
            logger.error("Failed to read from Redis cache for key %s: %s", key, e)
            return None

    @staticmethod
    async def set(key: str, data: Any, ttl_seconds: int) -> bool:
        """Saves data into cache with a TTL."""
        client = await redis_manager.get_client()
        try:
            serialized = serialize_data(data)
            await client.set(key, serialized, ex=ttl_seconds)
            return True
        except Exception as e:
            logger.error("Failed to write to Redis cache for key %s: %s", key, e)
            return False

    @staticmethod
    async def delete(key: str) -> bool:
        """Deletes key from cache."""
        client = await redis_manager.get_client()
        try:
            await client.delete(key)
            return True
        except Exception as e:
            logger.error("Failed to delete Redis cache key %s: %s", key, e)
            return False

    @staticmethod
    async def get_metrics() -> Dict[str, int]:
        """Returns hits, misses, and calculated hit ratio."""
        client = await redis_manager.get_client()
        try:
            hits = int(await client.get("metrics:cache_hit") or 0)
            misses = int(await client.get("metrics:cache_miss") or 0)
            total = hits + misses
            ratio = round(hits / total, 4) if total > 0 else 0.0
            return {
                "hits": hits,
                "misses": misses,
                "total_requests": total,
                "hit_ratio": ratio
            }
        except Exception as e:
            logger.error("Failed to retrieve cache metrics: %s", e)
            return {"hits": 0, "misses": 0, "total_requests": 0, "hit_ratio": 0.0}

    @staticmethod
    async def reset_metrics():
        """Resets the metrics counters."""
        client = await redis_manager.get_client()
        try:
            await client.set("metrics:cache_hit", 0)
            await client.set("metrics:cache_miss", 0)
        except Exception as e:
            logger.error("Failed to reset cache metrics: %s", e)


# ============================================================================
# SYSTEM HEALTH
# ============================================================================

async def check_redis_health() -> Dict[str, Any]:
    """Tests connection to Redis and returns diagnostic state."""
    try:
        t_start = datetime.datetime.now()
        client = await redis_manager.get_client()
        await client.ping()
        latency_ms = (datetime.datetime.now() - t_start).total_seconds() * 1000
        return {
            "status": "healthy",
            "mock": redis_manager.is_mock,
            "latency_ms": round(latency_ms, 2)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def create_arq_pool() -> Any:
    """Creates a connection pool for ARQ. Returns ArqRedis instance."""
    client = await redis_manager.get_client()
    if redis_manager.is_mock:
        return client
    
    from arq.connections import ArqRedis
    return ArqRedis(connection_pool=redis_manager._pool)

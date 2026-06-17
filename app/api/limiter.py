# ============================================================================
# MARKETMIND AI - REDIS-BACKED SLIDING WINDOW RATE LIMITER
# ============================================================================

import time
import uuid
import logging
from fastapi import Request, HTTPException, status
from app.core.redis import redis_manager

logger = logging.getLogger("marketmind_ai")


class InMemoryRateLimiter:
    """Redis-backed sliding-window rate limiter (retained class name for import compatibility)."""

    def __init__(self, limit: int, window: int):
        self.limit = limit
        self.window = window

    async def __call__(self, request: Request):
        # Identify client using IP address
        ip = request.client.host if request.client else "unknown"
        path = request.url.path
        
        # Exclude health checks from rate limiting to prevent load balancer eviction
        if path in ("/healthz", "/health"):
            return
            
        # Unique Redis key for this client and endpoint
        key = f"rate_limit:{ip}:{path}"
        
        try:
            client = await redis_manager.get_client()
            now = time.time()
            cutoff = now - self.window
            
            # Use pipeline to run ZSET operations atomically
            pipe = client.pipeline()
            
            # 1. Clean up stale requests outside the current window
            pipe.zremrangebyscore(key, 0, cutoff)
            
            # 2. Count requests inside the window
            pipe.zcard(key)
            
            # 3. Add current request timestamp (using UUID to guarantee uniqueness of value)
            member = f"{now}:{uuid.uuid4()}"
            pipe.zadd(key, {member: now})
            
            # 4. Set sliding window expiry TTL on ZSET
            pipe.expire(key, self.window + 5)
            
            # Execute pipeline
            _, current_count, _, _ = await pipe.execute()
            
            # Note: since zadd happens inside the pipeline, current_count represents requests *before* the zadd.
            # Thus, total active requests is current_count + 1.
            if current_count >= self.limit:
                logger.warning("Rate limit exceeded for IP %s on path %s (%d/%d requests)", ip, path, current_count + 1, self.limit)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again later."
                )
                
        except HTTPException:
            raise
        except Exception as e:
            # Fallback fail-open strategy for rate limiting
            logger.error("Redis rate limiter encountered error, failing open: %s", e)

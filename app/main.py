# ============================================================================
# MARKETMIND AI - MAIN APPLICATION ENTRYPOINT
# ============================================================================

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from app.api.middleware import setup_middlewares
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, logger
from app.api.limiter import InMemoryRateLimiter

global_limiter = InMemoryRateLimiter(limit=100, window=60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Context manager executing setup and teardown routines during startup/shutdown."""
    # Setup
    configure_logging()
    logger.info(f"Initializing {settings.APP_NAME} in environment: {settings.ENV}")
    
    # Initialize Redis Manager and ARQ pool
    from app.core.redis import redis_manager, create_arq_pool
    await redis_manager.initialize()
    app.state.arq_pool = await create_arq_pool()
    
    yield
    
    # Teardown
    logger.info(f"Shutting down {settings.APP_NAME}...")
    from app.core.redis import redis_manager
    await redis_manager.close()


# Create FastAPI Instance
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered Financial Research Platform Backend API",
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
    dependencies=[Depends(global_limiter)]
)

# Setup Middlewares (CORS, logs tracking)
setup_middlewares(app)

# Register Custom Error Handlers
register_exception_handlers(app)

# Include Router bindings
app.include_router(api_router, prefix="/v1")


from fastapi import Response, status
import datetime

@app.get("/healthz", tags=["System"])
async def health_check(response: Response):
    """System health check endpoint verifying DB, Redis, and Worker connectivity."""
    db_healthy = False
    redis_healthy = False
    worker_status = "unknown"
    
    # 1. Verify PostgreSQL Database
    try:
        from sqlalchemy import text
        from app.core.database import async_session_factory
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
            db_healthy = True
    except Exception as db_err:
        logger.error("Health check failed for database: %s", db_err)
        
    # 2. Verify Redis
    try:
        from app.core.redis import redis_manager
        client = await redis_manager.get_client()
        await client.ping()
        redis_healthy = True
        
        # 3. Verify ARQ Worker availability (check heartbeat key)
        heartbeat = await client.get("worker:heartbeat")
        if heartbeat:
            try:
                dt = datetime.datetime.fromisoformat(heartbeat)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=datetime.timezone.utc)
                now = datetime.datetime.now(datetime.timezone.utc)
                if (now - dt).total_seconds() <= 90:
                    worker_status = "healthy"
                else:
                    worker_status = "stale"
            except Exception:
                worker_status = "invalid"
        else:
            if redis_manager.is_mock:
                worker_status = "healthy (mock)"
            else:
                worker_status = "unavailable"
    except Exception as redis_err:
        logger.error("Health check failed for Redis: %s", redis_err)
        
    is_healthy = db_healthy and redis_healthy
    
    payload = {
        "status": "healthy" if is_healthy else "unhealthy",
        "app": settings.APP_NAME,
        "environment": settings.ENV,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "dependencies": {
            "database": "healthy" if db_healthy else "unhealthy",
            "redis": "healthy" if redis_healthy else "unhealthy",
            "worker": worker_status
        }
    }
    
    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        
    return payload

# ============================================================================
# MARKETMIND AI - ARQ BACKGROUND WORKER
# ============================================================================

import asyncio
import logging
import datetime
from uuid import UUID
import arq
from arq.connections import RedisSettings, ArqRedis
from app.core.config import settings
from app.core.redis import redis_manager, KEY_LOCK_RESEARCH
from app.services.research import ResearchEngineService
from app.core.database import async_session_factory
from app.models import RunStatusEnum

logger = logging.getLogger("marketmind_ai")


async def generate_research_report_job(ctx, user_id_str: str, symbol: str, run_id_str: str) -> str:
    """ARQ job to execute research report generation with exponential backoff retries."""
    user_id = UUID(user_id_str)
    run_id = UUID(run_id_str)
    
    logger.info("Worker started report generation job for ticker %s (Run ID: %s)", symbol, run_id)
    
    async with async_session_factory() as session:
        try:
            service = ResearchEngineService(session)
            await service.generate_research_report(user_id=user_id, symbol=symbol, run_id=run_id)
            return f"Report generated successfully for {symbol}"
        except Exception as e:
            # Check if this is a lock contention duplicate error
            if "already in progress" in str(e):
                logger.info("Ignoring duplicate report task for %s", symbol)
                return "Duplicate request ignored"
                
            # Retry strategy with exponential backoff (max 3 retries)
            job_try = ctx.get('job_try', 1)
            if job_try < 3:
                backoff = 5 * (2 ** (job_try - 1))  # 5s, 10s
                logger.warning("Job failed (try %d/3). Retrying in %ds... Error: %s", job_try, backoff, e)
                raise arq.Retry(defer=backoff)
            
            logger.error("Job failed after max retries. Error: %s", e)
            raise e


async def reconcile_dangling_runs_job(ctx) -> int:
    """Job to execute the dangling runs sweeper."""
    logger.info("Executing periodic dangling runs reconciliation sweep...")
    async with async_session_factory() as session:
        service = ResearchEngineService(session)
        count = await service.reconcile_dangling_runs()
        logger.info("Sweeper completed. Reconciled %d run(s).", count)
        return count


async def worker_heartbeat_job(ctx) -> str:
    """Updates the worker heartbeat key in Redis."""
    redis_client = ctx.get('redis')
    if redis_client:
        await redis_client.set("worker:heartbeat", datetime.datetime.now(datetime.timezone.utc).isoformat(), ex=90)
        return "Heartbeat updated"
    return "Redis unavailable"


async def on_startup(ctx):
    """Executes on worker startup. Runs recovery sweeper and boots uvicorn health check endpoint."""
    logger.info("ARQ Worker starting up...")
    
    # 1. Execute startup recovery sweep
    try:
        async with async_session_factory() as session:
            service = ResearchEngineService(session)
            count = await service.reconcile_dangling_runs()
            logger.info("Startup recovery sweep completed. Reconciled %d run(s).", count)
    except Exception as e:
        logger.error("Startup recovery sweep failed: %s", e)

    # Set worker heartbeat key in Redis on startup
    try:
        redis_client = ctx.get('redis')
        if redis_client:
            await redis_client.set("worker:heartbeat", datetime.datetime.now(datetime.timezone.utc).isoformat(), ex=90)
            logger.info("Startup heartbeat registered in Redis.")
    except Exception as e:
        logger.error("Failed to register startup heartbeat: %s", e)

    # 2. Boot HTTP health check server on port 8010 in background
    import uvicorn
    from fastapi import FastAPI
    
    app = FastAPI(title="MarketMind AI Worker Health")
    
    @app.get("/health")
    async def health_check():
        try:
            # Query queue metrics
            redis_client = ctx.get('redis')
            queue_len = 0
            if redis_client:
                # Arq stores queued job IDs in a list at "arq:queue"
                queue_len = await redis_client.llen("arq:queue") or 0
                hits = int(await redis_client.get("metrics:cache_hit") or 0)
                misses = int(await redis_client.get("metrics:cache_miss") or 0)
            else:
                hits, misses = 0, 0
                
            return {
                "status": "healthy",
                "queue_length": queue_len,
                "cache_hits": hits,
                "cache_misses": misses,
                "timestamp": datetime.datetime.now().isoformat()
            }
        except Exception as err:
            return {"status": "degraded", "error": str(err)}

    config = uvicorn.Config(app, host="0.0.0.0", port=8010, log_level="warning")
    server = uvicorn.Server(config)
    ctx['health_server_task'] = asyncio.create_task(server.serve())
    logger.info("Worker health check HTTP server started on port 8010.")


async def on_shutdown(ctx):
    """Cleans up background health check tasks on worker exit."""
    logger.info("ARQ Worker shutting down...")
    health_task = ctx.get('health_server_task')
    if health_task:
        health_task.cancel()
        try:
            await health_task
        except asyncio.CancelledError:
            pass
        logger.info("Worker health check HTTP server stopped.")


# ARQ settings class used by the CLI runner
class WorkerSettings:
    functions = [generate_research_report_job, reconcile_dangling_runs_job, worker_heartbeat_job]
    on_startup = on_startup
    on_shutdown = on_shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    
    # Run reconciliation sweeper every 5 minutes and heartbeat every 30 seconds
    # arq uses standard CronJob to schedule tasks
    cron_jobs = [
        arq.cron(reconcile_dangling_runs_job, second=0, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),
        arq.cron(worker_heartbeat_job, second={0, 30})
    ]

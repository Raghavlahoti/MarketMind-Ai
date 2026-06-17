# ============================================================================
# MARKETMIND AI - RESEARCH REPORTS ROUTER
# ============================================================================

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user_id
from app.schemas import stocks as schemas
from app.services.research import ResearchEngineService
from app.services.stock import StockService
from app.models import ResearchRun, RunStatusEnum
from app.core.config import settings
from app.api.limiter import InMemoryRateLimiter

router = APIRouter()
research_generate_limiter = InMemoryRateLimiter(limit=2, window=60)


from fastapi import Request

@router.post("/{symbol}/generate", response_model=schemas.ResearchRunResponse, status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(research_generate_limiter)])
async def generate_report(
    symbol: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id_str: str = Depends(get_current_user_id)
):
    """Triggers institutional stock research report generation in the background."""
    try:
        user_uuid = UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
        
    stock_service = StockService(db)
    stock = await stock_service.get_stock(symbol)
    
    # Create the run record in PENDING status
    run = ResearchRun(
        user_id=user_uuid,
        stock_id=stock.id,
        trigger_type="manual",
        status=RunStatusEnum.pending,
        config={"model": settings.NVIDIA_LLM_MODEL}
    )
    db.add(run)
    await db.commit()  # Save so the client has an immediate run ID to query
    
    # Queue the background task using ARQ
    try:
        arq_pool = request.app.state.arq_pool
        await arq_pool.enqueue_job(
            'generate_research_report_job',
            str(user_uuid),
            symbol,
            str(run.id)
        )
    except Exception as e:
        # If queueing fails, fail-open or log it (since the db run is committed in PENDING status,
        # the sweeper will recover it if it remains stale, but let's raise error for client awareness)
        from app.core.logging import logger
        logger.error("Failed to enqueue job to ARQ: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enqueue background generation task."
        )
    
    return run


@router.get("/runs/{id}", response_model=schemas.ResearchRunResponse)
async def get_run_status(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Retrieves status and metadata of a specific research run."""
    research_service = ResearchEngineService(db)
    run = await research_service.get_run_status(id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Research run {id} not found")
    return run


@router.get("/{symbol}", response_model=schemas.PaginatedResearchReportResponse)
async def get_reports(
    symbol: str,
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Retrieves list of all generated research reports for a stock symbol."""
    research_service = ResearchEngineService(db)
    return await research_service.get_reports_list(symbol, limit=limit, offset=offset)


@router.get("/{symbol}/latest", response_model=schemas.ResearchReportResponse)
async def get_latest_report(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Retrieves the latest completed research report with all sections for a stock symbol."""
    research_service = ResearchEngineService(db)
    report = await research_service.get_latest_report(symbol)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No research report found for stock {symbol}")
    return report

# ============================================================================
# MARKETMIND AI - STOCKS ROUTER
# ============================================================================

from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user_id
from app.schemas import stocks as schemas
from app.services.stock import StockService

router = APIRouter()


@router.get("/", response_model=List[schemas.Stock])
async def list_stocks(
    query: Optional[str] = None,
    sector: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Lists tracked stocks, optionally filtered by sector or fuzzy search query."""
    stock_service = StockService(db)
    return await stock_service.stock_repo.list_active_stocks(sector=sector, search_query=query)


@router.get("/{symbol}", response_model=schemas.StockDetail)
async def get_stock(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Fetches stock details including company profile and analyst consensus."""
    stock_service = StockService(db)
    stock = await stock_service.get_stock_detail(symbol)

    return schemas.StockDetail(
        id=stock.id,
        ticker=stock.ticker,
        name=stock.name,
        exchange=stock.exchange,
        sector=stock.sector,
        industry=stock.industry,
        is_active=stock.is_active,
        profile=stock.profile,
        consensus=stock.consensus
    )


@router.get("/{symbol}/profile", response_model=schemas.CompanyProfile)
async def get_stock_profile(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Retrieves detailed company profile metadata."""
    stock_service = StockService(db)
    return await stock_service.get_profile(symbol)


@router.get("/{symbol}/prices", response_model=schemas.PaginatedStockPriceResponse)
async def get_stock_prices(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Fetches daily historical prices for a given date range."""
    import datetime
    stock_service = StockService(db)
    stock = await stock_service.get_stock(symbol)
    
    # Calculate date range parameters to retrieve the correct database count
    end_dt = datetime.datetime.now(datetime.timezone.utc).date()
    if end_date:
        end_dt = datetime.date.fromisoformat(end_date)
    start_dt = end_dt - datetime.timedelta(days=365)
    if start_date:
        start_dt = datetime.date.fromisoformat(start_date)

    items = await stock_service.get_prices(symbol, start_date, end_date, limit=limit, offset=offset)
    total = await stock_service.stock_repo.count_prices_by_range(stock.id, start_dt, end_dt)
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/{symbol}/fundamentals", response_model=schemas.PaginatedCompanyFundamentalResponse)
async def get_stock_fundamentals(
    symbol: str,
    period_type: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Fetches corporate fundamentals history, optionally filtered by period type."""
    stock_service = StockService(db)
    stock = await stock_service.get_stock(symbol)
    items = await stock_service.get_fundamentals(symbol, period_type, limit=limit, offset=offset)
    total = await stock_service.fundamentals_repo.count_by_stock_id(stock.id, period_type)
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/{symbol}/consensus", response_model=schemas.AnalystConsensus)
async def get_stock_consensus(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Fetches external analyst ratings consensus and target pricing."""
    stock_service = StockService(db)
    return await stock_service.get_consensus(symbol)

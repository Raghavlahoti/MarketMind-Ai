# ============================================================================
# MARKETMIND AI - NEWS ROUTER
# ============================================================================

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user_id
from app.schemas import stocks as schemas
from app.services.news import NewsService
from app.services.stock import StockService

router = APIRouter()


@router.get("/{symbol}", response_model=schemas.PaginatedNewsResponse)
async def get_news(
    symbol: str,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Retrieves cached news for a stock symbol, automatic refresh if missing or stale."""
    news_service = NewsService(db)
    items = await news_service.get_news(symbol, limit=limit, offset=offset)
    stock_service = StockService(db)
    stock = await stock_service.get_stock(symbol)
    total = await news_service.news_repo.count_by_stock_id(stock.id)
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/{symbol}/latest", response_model=schemas.PaginatedNewsResponse)
async def get_latest_news(
    symbol: str,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Retrieves persisted stock news from database cache only (no external fetch)."""
    news_service = NewsService(db)
    items = await news_service.get_latest_cached_news(symbol, limit=limit, offset=offset)
    stock_service = StockService(db)
    stock = await stock_service.get_stock(symbol)
    total = await news_service.news_repo.count_by_stock_id(stock.id)
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/{symbol}/refresh", response_model=schemas.PaginatedNewsResponse)
async def refresh_news(
    symbol: str,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Forces an immediate refresh of stock news from external RSS feeds."""
    news_service = NewsService(db)
    items = await news_service.refresh_news(symbol, limit=limit, offset=offset)
    stock_service = StockService(db)
    stock = await stock_service.get_stock(symbol)
    total = await news_service.news_repo.count_by_stock_id(stock.id)
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset
    }

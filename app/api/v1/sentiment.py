# ============================================================================
# MARKETMIND AI - SENTIMENT ROUTER
# ============================================================================

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user_id
from app.schemas import stocks as schemas
from app.services.sentiment import SentimentService

from app.api.limiter import InMemoryRateLimiter

router = APIRouter()
sentiment_refresh_limiter = InMemoryRateLimiter(limit=5, window=60)


@router.get("/{symbol}", response_model=schemas.AggregatedSentimentResponse)
async def get_sentiment(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Retrieves cached stock sentiment and aggregates article-level scores."""
    sentiment_service = SentimentService(db)
    return await sentiment_service.get_stock_sentiment(symbol)


@router.post("/{symbol}/refresh", response_model=schemas.AggregatedSentimentResponse, dependencies=[Depends(sentiment_refresh_limiter)])
async def refresh_sentiment(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Forces immediate recalculation and cache update of stock sentiment."""
    sentiment_service = SentimentService(db)
    return await sentiment_service.refresh_stock_sentiment(symbol)

# ============================================================================
# MARKETMIND AI - NEWS SERVICE LAYER
# ============================================================================

import datetime
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Stock, NewsArticle
from app.providers.news import NewsProvider
from app.repositories.news import NewsRepository
from app.services.stock import StockService
from app.services.base import BaseService
from app.core.redis import RedisCache, KEY_PREFIX_NEWS
from app.core.config import settings

logger = logging.getLogger("marketmind_ai")


class NewsService(BaseService):
    """Orchestrates news data ingestion, caching, and persistence policies."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.news_repo = NewsRepository(session)
        self.news_provider = NewsProvider()
        
        # Cache Expiry Configuration (e.g., refresh news if older than 4 hours)
        self.news_expiry_hours = 4

    async def get_news(self, symbol: str, limit: Optional[int] = None, offset: Optional[int] = None) -> List[NewsArticle]:
        """Retrieves news for a stock symbol, automatically refreshing if missing or stale."""
        symbol = symbol.upper().strip()
        
        # Redis Cache Aside
        is_standard_query = (limit is None or limit <= 50) and (offset is None or offset == 0)
        cache_key = f"{KEY_PREFIX_NEWS}{symbol}"
        
        if is_standard_query:
            cached_data = await RedisCache.get(cache_key)
            if cached_data:
                articles = []
                for item in cached_data:
                    if "id" in item and isinstance(item["id"], str):
                        item["id"] = UUID(item["id"])
                    if "published_at" in item and isinstance(item["published_at"], str):
                        item["published_at"] = datetime.datetime.fromisoformat(item["published_at"])
                    if "created_at" in item and isinstance(item["created_at"], str):
                        item["created_at"] = datetime.datetime.fromisoformat(item["created_at"])
                    if "updated_at" in item and isinstance(item["updated_at"], str):
                        item["updated_at"] = datetime.datetime.fromisoformat(item["updated_at"])
                    articles.append(NewsArticle(**item))
                return articles[:limit] if limit else articles

        # 1. Resolve stock record (ingesting from yfinance if missing in DB)
        stock_service = StockService(self.session)
        stock = await stock_service.get_stock(symbol)

        # 2. Query persisted news articles from database (first check how many exist in DB)
        total = await self.news_repo.count_by_stock_id(stock.id)

        # 3. Determine if cache is stale
        now = datetime.datetime.now(datetime.timezone.utc)
        stale = True
        if total > 0:
            articles = await self.news_repo.get_by_stock_id(stock.id, limit=1, offset=0)
            if articles:
                latest_update = articles[0].updated_at
                if not latest_update.tzinfo:
                    latest_update = latest_update.replace(tzinfo=datetime.timezone.utc)
                stale = (now - latest_update).total_seconds() > self.news_expiry_hours * 3600
            else:
                stale = True

        # 4. If missing or stale, refresh from providers
        if total == 0 or stale:
            logger.info("News cache for %s is missing or stale. Refreshing from RSS providers...", symbol)
            await self.refresh_news(symbol)

        # 5. Fetch paginated list
        articles = await self.news_repo.get_by_stock_id(stock.id, limit=limit or 50, offset=offset or 0)

        # Write to cache
        if is_standard_query and articles:
            serializable = []
            for art in articles:
                serializable.append({
                    "id": str(art.id),
                    "title": art.title,
                    "content": art.content,
                    "summary": art.summary,
                    "source_name": art.source_name,
                    "url": art.url,
                    "published_at": art.published_at.isoformat() if art.published_at else None,
                    "metadata_": art.metadata_,
                    "created_at": art.created_at.isoformat() if art.created_at else None,
                    "updated_at": art.updated_at.isoformat() if art.updated_at else None
                })
            await RedisCache.set(cache_key, serializable, settings.REDIS_CACHE_TTL_NEWS)

        return articles

    async def get_latest_cached_news(self, symbol: str, limit: Optional[int] = None, offset: Optional[int] = None) -> List[NewsArticle]:
        """Retrieves news for a stock symbol from DB cache only (no external provider fetch)."""
        stock_service = StockService(self.session)
        stock = await stock_service.get_stock(symbol)
        return await self.news_repo.get_by_stock_id(stock.id, limit=limit or 50, offset=offset or 0)

    async def refresh_news(self, symbol: str, limit: Optional[int] = None, offset: Optional[int] = None) -> List[NewsArticle]:
        """Forces a bypass of the cache check, fetches new articles, and upserts them."""
        stock_service = StockService(self.session)
        stock = await stock_service.get_stock(symbol)

        logger.info("Forcing news refresh for %s from external RSS providers...", symbol)
        
        # Fetch fresh news items from providers
        news_items = await self.news_provider.get_news(stock.ticker)
        
        # Persist and link to stock
        await self.news_repo.upsert_articles(stock.id, news_items)
        
        # Retrieve latest persisted list
        return await self.news_repo.get_by_stock_id(stock.id, limit=limit or 50, offset=offset or 0)

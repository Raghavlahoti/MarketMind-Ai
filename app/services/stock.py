import datetime
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Stock, CompanyProfile, AnalystConsensus, StockPrice, CompanyFundamental
from app.providers.yahoo_finance import YahooFinanceProvider
from app.repositories.stock import StockRepository
from app.repositories.company_profile import CompanyProfileRepository
from app.repositories.fundamentals import FundamentalsRepository
from app.services.base import BaseService
from app.core.redis import RedisCache, KEY_PREFIX_PRICES
from app.core.config import settings

logger = logging.getLogger("marketmind_ai")


class StockService(BaseService):
    """Orchestrates stock data ingestion, persistence, and caching/refresh policies."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.stock_repo = StockRepository(session)
        self.profile_repo = CompanyProfileRepository(session)
        self.fundamentals_repo = FundamentalsRepository(session)
        self.yf_provider = YahooFinanceProvider()

        # Cache Expiry Configurations (in hours/days)
        self.profile_expiry_hours = 24
        self.consensus_expiry_hours = 24
        self.prices_expiry_hours = 24
        self.fundamentals_expiry_days = 30

    def _ensure_utc(self, dt: datetime.datetime) -> datetime.datetime:
        if not dt.tzinfo:
            return dt.replace(tzinfo=datetime.timezone.utc)
        return dt

    async def get_stock(self, symbol: str) -> Stock:
        """Fetches a stock record by ticker. Ingests or refreshes if missing/stale."""
        symbol = symbol.upper().strip()
        
        import re
        if not re.match(r"^[A-Z0-9.-]{1,12}$", symbol):
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ticker symbol format")
            
        stock = await self.stock_repo.get_by_ticker(symbol)

        now = datetime.datetime.now(datetime.timezone.utc)

        if not stock:
            logger.info("Stock %s not found in database. Ingesting from Yahoo Finance...", symbol)
            metadata = await self.yf_provider.get_stock_metadata(symbol)
            stock = Stock(
                ticker=metadata["ticker"],
                name=metadata["name"],
                exchange=metadata["exchange"],
                sector=metadata["sector"],
                industry=metadata["industry"],
                is_active=metadata["is_active"]
            )
            stock = await self.stock_repo.create(stock)
        elif (now - self._ensure_utc(stock.updated_at)).total_seconds() > self.profile_expiry_hours * 3600:
            logger.info("Stock %s cache is stale. Refreshing metadata...", symbol)
            metadata = await self.yf_provider.get_stock_metadata(symbol)
            stock.name = metadata["name"]
            stock.exchange = metadata["exchange"]
            stock.sector = metadata["sector"]
            stock.industry = metadata["industry"]
            await self.session.flush()

        return stock

    async def get_stock_detail(self, symbol: str) -> Stock:
        """Fetches stock record by ticker, preloading profile and consensus. Refreshes if missing/stale."""
        symbol = symbol.upper().strip()
        
        import re
        if not re.match(r"^[A-Z0-9.-]{1,12}$", symbol):
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ticker symbol format")
            
        stock = await self.stock_repo.get_stock_with_relations(symbol)
        
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # Determine if we need to ingest stock or refresh profile/consensus
        need_ref_stock = not stock or (now - self._ensure_utc(stock.updated_at)).total_seconds() > self.profile_expiry_hours * 3600
        need_ref_profile = not stock or not stock.profile or (now - self._ensure_utc(stock.profile.updated_at)).total_seconds() > self.profile_expiry_hours * 3600
        need_ref_consensus = not stock or not stock.consensus or (now - self._ensure_utc(stock.consensus.updated_at)).total_seconds() > self.consensus_expiry_hours * 3600
        
        if need_ref_stock or need_ref_profile or need_ref_consensus:
            # Let the standard sequential paths handle missing/stale updates and caching
            stock = await self.get_stock(symbol)
            await self.get_profile(symbol)
            await self.get_consensus(symbol)
            
            # Re-fetch with relations to make sure they are attached
            stock = await self.stock_repo.get_stock_with_relations(symbol)
            
        return stock

    async def get_profile(self, symbol: str) -> CompanyProfile:
        """Gets company profile. Ingests or refreshes if missing/stale."""
        stock = await self.get_stock(symbol)
        profile = await self.profile_repo.get_by_stock_id(stock.id)

        now = datetime.datetime.now(datetime.timezone.utc)
        stale = False
        if profile:
            stale = (now - self._ensure_utc(profile.updated_at)).total_seconds() > self.profile_expiry_hours * 3600

        if not profile or stale:
            logger.info("Profile for %s is missing or stale. Fetching fresh details...", symbol)
            profile_data = await self.yf_provider.get_company_profile(stock.ticker)
            profile = await self.profile_repo.upsert_profile(stock.id, profile_data)

        return profile

    async def get_consensus(self, symbol: str) -> AnalystConsensus:
        """Gets analyst rating consensus. Ingests or refreshes if missing/stale."""
        stock = await self.get_stock(symbol)
        
        # Query DB directly to avoid lazy loading issues in async context
        from sqlalchemy import select
        q = select(AnalystConsensus).where(AnalystConsensus.stock_id == stock.id)
        res = await self.session.execute(q)
        consensus = res.scalars().first()

        now = datetime.datetime.now(datetime.timezone.utc)
        stale = False
        if consensus:
            stale = (now - self._ensure_utc(consensus.updated_at)).total_seconds() > self.consensus_expiry_hours * 3600

        if not consensus or stale:
            logger.info("Analyst consensus for %s is missing or stale. Fetching fresh details...", symbol)
            consensus_data = await self.yf_provider.get_analyst_consensus(stock.ticker)
            consensus = await self.stock_repo.upsert_consensus(stock.id, consensus_data)

        return consensus

    async def get_prices(
        self, symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[StockPrice]:
        """Gets daily historical prices. Refreshes cache from yfinance if missing/stale."""
        symbol = symbol.upper().strip()
        
        # Redis Cache Aside
        is_standard_query = start_date is None and end_date is None and (offset is None or offset == 0)
        cache_key = f"{KEY_PREFIX_PRICES}{symbol}"
        
        if is_standard_query:
            cached_data = await RedisCache.get(cache_key)
            if cached_data:
                prices = []
                for item in cached_data:
                    if "id" in item and isinstance(item["id"], str):
                        item["id"] = UUID(item["id"])
                    if "stock_id" in item and isinstance(item["stock_id"], str):
                        item["stock_id"] = UUID(item["stock_id"])
                    if "price_date" in item and isinstance(item["price_date"], str):
                        item["price_date"] = datetime.date.fromisoformat(item["price_date"])
                    if "created_at" in item and isinstance(item["created_at"], str):
                        item["created_at"] = datetime.datetime.fromisoformat(item["created_at"])
                    if "updated_at" in item and isinstance(item["updated_at"], str):
                        item["updated_at"] = datetime.datetime.fromisoformat(item["updated_at"])
                    prices.append(StockPrice(**item))
                return prices[:limit] if limit else prices

        stock = await self.get_stock(symbol)
        
        # Convert start/end dates to datetime.date objects for querying
        end_dt = datetime.datetime.now(datetime.timezone.utc).date()
        if end_date:
            end_dt = datetime.date.fromisoformat(end_date)
            
        start_dt = end_dt - datetime.timedelta(days=365)  # Default 1 year back
        if start_date:
            start_dt = datetime.date.fromisoformat(start_date)

        # Check latest price in DB to evaluate cache freshness
        latest_price = await self.stock_repo.get_latest_price(stock.id)
        now = datetime.datetime.now(datetime.timezone.utc)
        
        stale = True
        if latest_price:
            # If the latest price date is today (or yesterday if weekend), we might be fresh.
            # To keep it simple: if the latest price update timestamp is less than 24 hours ago, we are fresh.
            stale = (now - self._ensure_utc(latest_price.updated_at)).total_seconds() > self.prices_expiry_hours * 3600

        if not latest_price or stale:
            logger.info("Stock prices for %s are missing or stale. Fetching from Yahoo Finance...", symbol)
            # Ingest last 2 years of history to build a solid database cache
            prices_data = await self.yf_provider.get_historical_prices(stock.ticker)
            await self.stock_repo.upsert_prices(stock.id, prices_data)

        # Retrieve prices from DB matching requested range
        prices = await self.stock_repo.get_prices_by_range(stock.id, start_dt, end_dt, limit=limit, offset=offset)

        # Write to cache
        if is_standard_query and prices:
            serializable = []
            for p in prices:
                serializable.append({
                    "id": str(p.id),
                    "stock_id": str(p.stock_id),
                    "price_date": p.price_date.isoformat() if p.price_date else None,
                    "open_price": float(p.open_price),
                    "high_price": float(p.high_price),
                    "low_price": float(p.low_price),
                    "close_price": float(p.close_price),
                    "volume": int(p.volume),
                    "adjusted_close": float(p.adjusted_close),
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None
                })
            await RedisCache.set(cache_key, serializable, settings.REDIS_CACHE_TTL_PRICES)

        return prices

    async def get_fundamentals(
        self, symbol: str, period_type: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[CompanyFundamental]:
        """Gets corporate fundamentals. Refreshes cache from yfinance if missing/stale."""
        stock = await self.get_stock(symbol)
        
        # Check if we have fundamentals
        fundamentals = await self.fundamentals_repo.get_by_stock_id(stock.id, period_type)
        
        now = datetime.datetime.now(datetime.timezone.utc)
        stale = True
        if fundamentals:
            # Check the most recently updated fundamental
            latest_update = max(f.updated_at for f in fundamentals)
            stale = (now - self._ensure_utc(latest_update)).days > self.fundamentals_expiry_days

        if not fundamentals or stale:
            logger.info("Fundamentals for %s are missing or stale. Fetching fresh sheets...", symbol)
            fundamentals_data = await self.yf_provider.get_fundamentals(stock.ticker)
            await self.fundamentals_repo.upsert_fundamentals(stock.id, fundamentals_data)
            
            # Re-fetch from DB after ingestion
            fundamentals = await self.fundamentals_repo.get_by_stock_id(stock.id, period_type)

        # Re-fetch paginated subset from DB
        return await self.fundamentals_repo.get_by_stock_id(stock.id, period_type, limit=limit, offset=offset)

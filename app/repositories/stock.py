# ============================================================================
# MARKETMIND AI - STOCK DATABASE REPOSITORY
# ============================================================================

import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Stock, StockPrice, AnalystConsensus
from app.repositories.base import BaseRepository


class StockRepository(BaseRepository[Stock]):
    """SQLAlchemy 2.0 concrete implementation of stock & price operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Stock, session)

    async def get_by_ticker(self, ticker: str) -> Optional[Stock]:
        """Queries for a stock by its ticker symbol (case-insensitive)."""
        query = select(Stock).where(func.lower(Stock.ticker) == func.lower(ticker))
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_stock_with_relations(self, ticker: str) -> Optional[Stock]:
        """Queries for a stock by its ticker symbol, preloading profile and consensus relations."""
        from sqlalchemy.orm import selectinload
        query = (
            select(Stock)
            .options(
                selectinload(Stock.profile),
                selectinload(Stock.consensus)
            )
            .where(func.lower(Stock.ticker) == func.lower(ticker))
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def list_active_stocks(
        self, sector: Optional[str] = None, search_query: Optional[str] = None
    ) -> List[Stock]:
        """Lists active stock records, optionally filtered by sector or search term."""
        query = select(Stock).where(Stock.is_active == True)
        if sector:
            query = query.where(func.lower(Stock.sector) == func.lower(sector))
        if search_query:
            query = query.where(
                (func.lower(Stock.ticker).contains(search_query.lower())) |
                (func.lower(Stock.name).contains(search_query.lower()))
            )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_prices_by_range(
        self, stock_id: UUID, start_date: datetime.date, end_date: datetime.date, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[StockPrice]:
        """Fetches daily price bars for a stock within a date range."""
        query = (
            select(StockPrice)
            .where(StockPrice.stock_id == stock_id)
            .where(StockPrice.price_date >= start_date)
            .where(StockPrice.price_date <= end_date)
            .order_by(StockPrice.price_date.asc())
        )
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)
            
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_prices_by_range(
        self, stock_id: UUID, start_date: datetime.date, end_date: datetime.date
    ) -> int:
        """Counts total daily price bars for a stock within a date range."""
        query = (
            select(func.count(StockPrice.id))
            .where(StockPrice.stock_id == stock_id)
            .where(StockPrice.price_date >= start_date)
            .where(StockPrice.price_date <= end_date)
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_latest_price(self, stock_id: UUID) -> Optional[StockPrice]:
        """Fetches the single most recent price entry for a stock."""
        query = (
            select(StockPrice)
            .where(StockPrice.stock_id == stock_id)
            .order_by(StockPrice.price_date.desc())
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def upsert_prices(self, stock_id: UUID, prices_data: List[Dict[str, Any]]) -> None:
        """Performs a bulk insert/upsert of historical prices in PostgreSQL."""
        if not prices_data:
            return

        values_to_insert = []
        for p in prices_data:
            open_p = p["open_price"]
            high_p = p["high_price"]
            low_p = p["low_price"]
            close_p = p["close_price"]
            
            # Defensively ensure price extremes satisfy database check constraints
            if not (high_p >= low_p and high_p >= open_p and high_p >= close_p):
                high_p = max(open_p, high_p, low_p, close_p)
                low_p = min(open_p, high_p, low_p, close_p)
                
            values_to_insert.append({
                "stock_id": stock_id,
                "price_date": p["price_date"],
                "open_price": open_p,
                "high_price": high_p,
                "low_price": low_p,
                "close_price": close_p,
                "volume": p["volume"],
                "adjusted_close": p["adjusted_close"],
            })

        stmt = insert(StockPrice).values(values_to_insert)
        stmt = stmt.on_conflict_do_update(
            index_elements=["stock_id", "price_date"],
            set_={
                "open_price": stmt.excluded.open_price,
                "high_price": stmt.excluded.high_price,
                "low_price": stmt.excluded.low_price,
                "close_price": stmt.excluded.close_price,
                "volume": stmt.excluded.volume,
                "adjusted_close": stmt.excluded.adjusted_close,
                "updated_at": func.now(),
            }
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def upsert_consensus(self, stock_id: UUID, consensus_data: Dict[str, Any]) -> AnalystConsensus:
        """Upserts the analyst consensus recommendation records."""
        stmt = insert(AnalystConsensus).values(
            stock_id=stock_id,
            buy_count=consensus_data["buy_count"],
            hold_count=consensus_data["hold_count"],
            sell_count=consensus_data["sell_count"],
            average_target_price=consensus_data["average_target_price"],
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["stock_id"],
            set_={
                "buy_count": stmt.excluded.buy_count,
                "hold_count": stmt.excluded.hold_count,
                "sell_count": stmt.excluded.sell_count,
                "average_target_price": stmt.excluded.average_target_price,
                "updated_at": func.now(),
            }
        )
        await self.session.execute(stmt)
        await self.session.flush()

        # Retrieve and return the updated entity
        query = select(AnalystConsensus).where(AnalystConsensus.stock_id == stock_id)
        result = await self.session.execute(query)
        return result.scalars().first()

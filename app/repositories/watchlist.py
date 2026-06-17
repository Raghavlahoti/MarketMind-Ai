# ============================================================================
# MARKETMIND AI - WATCHLIST REPOSITORY CONCRETE IMPLEMENTATION
# ============================================================================

from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Watchlist, WatchlistItem
from app.repositories.base import BaseRepository


class WatchlistRepository(BaseRepository[Watchlist]):
    """SQLAlchemy 2.0 concrete implementation of Watchlist operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Watchlist, session)

    async def get_watchlist_with_items(self, watchlist_id: UUID) -> Optional[Watchlist]:
        """Fetches a watchlist by ID and preloads its items and stock profile metadata."""
        query = (
            select(Watchlist)
            .where(Watchlist.id == watchlist_id)
            .options(
                selectinload(Watchlist.items).selectinload(WatchlistItem.stock)
            )
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def list_user_watchlists(self, user_id: UUID) -> List[Watchlist]:
        """Lists all watchlists created by a specific user."""
        query = (
            select(Watchlist)
            .where(Watchlist.user_id == user_id)
            .options(
                selectinload(Watchlist.items).selectinload(WatchlistItem.stock)
            )
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())


class WatchlistItemRepository(BaseRepository[WatchlistItem]):
    """SQLAlchemy 2.0 concrete implementation of WatchlistItem operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(WatchlistItem, session)

    async def get_item(self, watchlist_id: UUID, stock_id: UUID) -> Optional[WatchlistItem]:
        """Fetches a watchlist item by watchlist ID and stock ID."""
        query = (
            select(WatchlistItem)
            .where(
                WatchlistItem.watchlist_id == watchlist_id,
                WatchlistItem.stock_id == stock_id
            )
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def list_items_for_watchlist(self, watchlist_id: UUID) -> List[WatchlistItem]:
        """Lists all items in a watchlist preloaded with stock info."""
        query = (
            select(WatchlistItem)
            .where(WatchlistItem.watchlist_id == watchlist_id)
            .options(selectinload(WatchlistItem.stock))
            .order_by(WatchlistItem.sort_order.asc(), WatchlistItem.added_at.asc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

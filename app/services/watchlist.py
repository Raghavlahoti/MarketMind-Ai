# ============================================================================
# MARKETMIND AI - WATCHLIST SERVICE LAYER
# ============================================================================

import logging
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Watchlist, WatchlistItem
from app.repositories.watchlist import WatchlistRepository, WatchlistItemRepository
from app.services.stock import StockService
from app.services.base import BaseService

logger = logging.getLogger("marketmind_ai")


class WatchlistService(BaseService):
    """Orchestrates Watchlist CRUD and Watchlist Items CRUD."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.watchlist_repo = WatchlistRepository(session)
        self.item_repo = WatchlistItemRepository(session)
        self.stock_service = StockService(session)

    async def create_watchlist(self, user_id: UUID, name: str, description: Optional[str] = None) -> Watchlist:
        """Creates a new watchlist for a user."""
        watchlist = Watchlist(
            user_id=user_id,
            name=name.strip(),
            description=description.strip() if description else None
        )
        await self.watchlist_repo.create(watchlist)
        await self.session.flush()
        # Retrieve with loaded items (empty list initially)
        return await self.watchlist_repo.get_watchlist_with_items(watchlist.id)

    async def get_watchlist(self, watchlist_id: UUID, user_id: UUID) -> Watchlist:
        """Retrieves a watchlist by ID, verifying user ownership."""
        watchlist = await self.watchlist_repo.get_watchlist_with_items(watchlist_id)
        if not watchlist:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found")
        if watchlist.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this watchlist")
        return watchlist

    async def list_user_watchlists(self, user_id: UUID) -> List[Watchlist]:
        """Lists all watchlists for a specific user."""
        return await self.watchlist_repo.list_user_watchlists(user_id)

    async def update_watchlist(
        self, watchlist_id: UUID, user_id: UUID, name: Optional[str] = None, description: Optional[str] = None
    ) -> Watchlist:
        """Updates watchlist metadata (name, description)."""
        watchlist = await self.get_watchlist(watchlist_id, user_id)
        if name is not None:
            watchlist.name = name.strip()
        if description is not None:
            watchlist.description = description.strip() if description else None
        await self.session.flush()
        # Re-fetch or refresh to ensure columns like updated_at are populated
        await self.session.refresh(watchlist)
        return await self.watchlist_repo.get_watchlist_with_items(watchlist_id)

    async def delete_watchlist(self, watchlist_id: UUID, user_id: UUID) -> None:
        """Deletes a watchlist."""
        watchlist = await self.get_watchlist(watchlist_id, user_id)
        await self.watchlist_repo.delete(watchlist)
        await self.session.flush()

    async def add_watchlist_item(
        self, watchlist_id: UUID, user_id: UUID, stock_id: Optional[UUID] = None, ticker: Optional[str] = None
    ) -> WatchlistItem:
        """Adds a stock to a watchlist. Automatically resolves ticker or validates stock_id."""
        watchlist = await self.get_watchlist(watchlist_id, user_id)
        
        # 1. Resolve stock record
        if ticker:
            stock = await self.stock_service.get_stock(ticker)
            resolved_stock_id = stock.id
        elif stock_id:
            from sqlalchemy import select
            from app.models import Stock
            res = await self.session.execute(select(Stock).where(Stock.id == stock_id))
            stock = res.scalars().first()
            if not stock:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock not found")
            resolved_stock_id = stock_id
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Must provide stock_id or ticker")

        # 2. Check if already exists in watchlist
        existing_item = await self.item_repo.get_item(watchlist_id, resolved_stock_id)
        if existing_item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stock is already in watchlist"
            )

        # 3. Determine sort order (append to end)
        existing_items = await self.item_repo.list_items_for_watchlist(watchlist_id)
        next_sort_order = max([item.sort_order for item in existing_items], default=-1) + 1

        # 4. Create and save item
        item = WatchlistItem(
            watchlist_id=watchlist_id,
            stock_id=resolved_stock_id,
            sort_order=next_sort_order
        )
        await self.item_repo.create(item)
        await self.session.flush()

        # Re-fetch item to load stock relation
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        query = (
            select(WatchlistItem)
            .where(WatchlistItem.id == item.id)
            .options(
                selectinload(WatchlistItem.stock)
            )
        )
        res = await self.session.execute(query)
        return res.scalars().first()

    async def remove_watchlist_item(self, watchlist_id: UUID, user_id: UUID, stock_id: UUID) -> None:
        """Removes a stock from a watchlist."""
        watchlist = await self.get_watchlist(watchlist_id, user_id)
        item = await self.item_repo.get_item(watchlist_id, stock_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stock is not in this watchlist"
            )
        await self.item_repo.delete(item)
        await self.session.flush()

    async def list_items(self, watchlist_id: UUID, user_id: UUID) -> List[WatchlistItem]:
        """Lists all items in a watchlist, verifying user ownership."""
        await self.get_watchlist(watchlist_id, user_id)
        return await self.item_repo.list_items_for_watchlist(watchlist_id)

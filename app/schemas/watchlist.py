# ============================================================================
# MARKETMIND AI - WATCHLIST PYDANTIC SCHEMAS
# ============================================================================

import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.schemas.stocks import StockBase


class WatchlistItemBase(BaseModel):
    stock_id: UUID
    sort_order: int = 0


class WatchlistItemCreate(BaseModel):
    stock_id: Optional[UUID] = None
    ticker: Optional[str] = None


class WatchlistItemResponse(BaseModel):
    id: UUID
    watchlist_id: UUID
    stock_id: UUID
    added_at: datetime.datetime
    sort_order: int
    stock: Optional[StockBase] = None

    model_config = ConfigDict(from_attributes=True)


class WatchlistBase(BaseModel):
    name: str
    description: Optional[str] = None


class WatchlistCreate(WatchlistBase):
    pass


class WatchlistUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class WatchlistResponse(WatchlistBase):
    id: UUID
    user_id: UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime
    items: List[WatchlistItemResponse] = []

    model_config = ConfigDict(from_attributes=True)

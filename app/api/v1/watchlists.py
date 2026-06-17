# ============================================================================
# MARKETMIND AI - WATCHLISTS ROUTER
# ============================================================================

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user_id
from app.schemas import watchlist as schemas
from app.services.watchlist import WatchlistService

router = APIRouter()


@router.get("/", response_model=List[schemas.WatchlistResponse])
async def list_watchlists(
    db: AsyncSession = Depends(get_db),
    user_id_str: str = Depends(get_current_user_id)
):
    """Retrieves all watchlists created by the authenticated user."""
    user_uuid = UUID(user_id_str)
    service = WatchlistService(db)
    return await service.list_user_watchlists(user_uuid)


@router.post("/", response_model=schemas.WatchlistResponse, status_code=status.HTTP_201_CREATED)
async def create_watchlist(
    payload: schemas.WatchlistCreate,
    db: AsyncSession = Depends(get_db),
    user_id_str: str = Depends(get_current_user_id)
):
    """Creates a new watchlist for the authenticated user."""
    user_uuid = UUID(user_id_str)
    service = WatchlistService(db)
    return await service.create_watchlist(
        user_id=user_uuid,
        name=payload.name,
        description=payload.description
    )


@router.get("/{id}", response_model=schemas.WatchlistResponse)
async def get_watchlist(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id_str: str = Depends(get_current_user_id)
):
    """Retrieves a specific watchlist including all items and stock metadata."""
    user_uuid = UUID(user_id_str)
    service = WatchlistService(db)
    return await service.get_watchlist(id, user_uuid)


@router.put("/{id}", response_model=schemas.WatchlistResponse)
async def update_watchlist(
    id: UUID,
    payload: schemas.WatchlistUpdate,
    db: AsyncSession = Depends(get_db),
    user_id_str: str = Depends(get_current_user_id)
):
    """Updates a watchlist's metadata (name and/or description)."""
    user_uuid = UUID(user_id_str)
    service = WatchlistService(db)
    return await service.update_watchlist(
        watchlist_id=id,
        user_id=user_uuid,
        name=payload.name,
        description=payload.description
    )


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watchlist(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id_str: str = Depends(get_current_user_id)
):
    """Deletes a specific watchlist owned by the authenticated user."""
    user_uuid = UUID(user_id_str)
    service = WatchlistService(db)
    await service.delete_watchlist(id, user_uuid)


@router.post("/{id}/items", response_model=schemas.WatchlistItemResponse, status_code=status.HTTP_201_CREATED)
async def add_watchlist_item(
    id: UUID,
    payload: schemas.WatchlistItemCreate,
    db: AsyncSession = Depends(get_db),
    user_id_str: str = Depends(get_current_user_id)
):
    """Adds a stock (by ID or ticker symbol) to the specified watchlist."""
    user_uuid = UUID(user_id_str)
    if not payload.stock_id and not payload.ticker:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either stock_id or ticker"
        )
    service = WatchlistService(db)
    return await service.add_watchlist_item(
        watchlist_id=id,
        user_id=user_uuid,
        stock_id=payload.stock_id,
        ticker=payload.ticker
    )


@router.delete("/{id}/items/{stock_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_watchlist_item(
    id: UUID,
    stock_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id_str: str = Depends(get_current_user_id)
):
    """Removes a stock from the specified watchlist."""
    user_uuid = UUID(user_id_str)
    service = WatchlistService(db)
    await service.remove_watchlist_item(
        watchlist_id=id,
        user_id=user_uuid,
        stock_id=stock_id
    )

# ============================================================================
# MARKETMIND AI - ALERTS ROUTER
# ============================================================================

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user_id
from app.schemas import alert as schemas
from app.services.alert import AlertService

router = APIRouter()


@router.get("/", response_model=List[schemas.AlertResponse])
async def list_alerts(
    stock_id: Optional[UUID] = None,
    triggered_only: bool = False,
    db: AsyncSession = Depends(get_db),
    user_id_str: str = Depends(get_current_user_id)
):
    """Retrieves all alert triggers set by the authenticated user."""
    user_uuid = UUID(user_id_str)
    service = AlertService(db)
    return await service.list_user_alerts(user_uuid, stock_id=stock_id, triggered_only=triggered_only)


@router.post("/", response_model=schemas.AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    payload: schemas.AlertCreate,
    db: AsyncSession = Depends(get_db),
    user_id_str: str = Depends(get_current_user_id)
):
    """Creates a new price/sentiment trigger alert configuration."""
    user_uuid = UUID(user_id_str)
    service = AlertService(db)
    return await service.create_alert(
        user_id=user_uuid,
        alert_type=payload.alert_type,
        target_value=payload.target_value,
        stock_id=payload.stock_id,
        ticker=payload.ticker
    )


@router.get("/{id}", response_model=schemas.AlertResponse)
async def get_alert(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id_str: str = Depends(get_current_user_id)
):
    """Retrieves metadata of a specific alert by ID."""
    user_uuid = UUID(user_id_str)
    service = AlertService(db)
    return await service.get_alert(id, user_uuid)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id_str: str = Depends(get_current_user_id)
):
    """Removes a specific alert configuration."""
    user_uuid = UUID(user_id_str)
    service = AlertService(db)
    await service.delete_alert(id, user_uuid)


@router.post("/evaluate/{symbol}", response_model=List[schemas.AlertEvaluationResult])
async def evaluate_alerts(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    user_id_str: str = Depends(get_current_user_id)
):
    """Triggers immediate rule evaluation for all active alerts configured on a stock."""
    service = AlertService(db)
    return await service.evaluate_alerts_for_stock(symbol)

# ============================================================================
# MARKETMIND AI - ALERT REPOSITORY CONCRETE IMPLEMENTATION
# ============================================================================

from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Alert
from app.repositories.base import BaseRepository


class AlertRepository(BaseRepository[Alert]):
    """SQLAlchemy 2.0 concrete implementation of Alert operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Alert, session)

    async def get_alert_with_stock(self, alert_id: UUID) -> Optional[Alert]:
        """Fetches an alert by ID with preloaded stock metadata."""
        query = (
            select(Alert)
            .where(Alert.id == alert_id)
            .options(selectinload(Alert.stock))
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def list_user_alerts(
        self, user_id: UUID, stock_id: Optional[UUID] = None, triggered_only: bool = False
    ) -> List[Alert]:
        """Lists alerts for a user, optionally filtered by stock and/or trigger status."""
        query = (
            select(Alert)
            .where(Alert.user_id == user_id)
            .options(selectinload(Alert.stock))
            .order_by(Alert.created_at.desc())
        )
        if stock_id:
            query = query.where(Alert.stock_id == stock_id)
        if triggered_only:
            query = query.where(Alert.is_triggered == True)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_active_alerts_for_stock(self, stock_id: UUID) -> List[Alert]:
        """Lists all untriggered alerts for a given stock (used by evaluation engine)."""
        query = (
            select(Alert)
            .where(Alert.stock_id == stock_id, Alert.is_triggered == False)
            .options(selectinload(Alert.stock))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def mark_triggered(self, alert_id: UUID) -> None:
        """Marks an alert as triggered."""
        stmt = (
            update(Alert)
            .where(Alert.id == alert_id)
            .values(is_triggered=True)
        )
        await self.session.execute(stmt)
        await self.session.flush()

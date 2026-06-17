# ============================================================================
# MARKETMIND AI - ALERT SERVICE LAYER
# ============================================================================

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Alert, AlertTypeEnum, Stock
from app.repositories.alert import AlertRepository
from app.services.stock import StockService
from app.services.sentiment import SentimentService
from app.services.base import BaseService

logger = logging.getLogger("marketmind_ai")


class AlertService(BaseService):
    """Orchestrates Alert CRUD and Alert Evaluation Engine."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.alert_repo = AlertRepository(session)
        self.stock_service = StockService(session)

    async def create_alert(
        self,
        user_id: UUID,
        alert_type: str,
        target_value: float,
        stock_id: Optional[UUID] = None,
        ticker: Optional[str] = None
    ) -> Alert:
        """Creates a new alert for a user on a specific stock."""
        # Validate alert_type
        try:
            validated_type = AlertTypeEnum(alert_type)
        except ValueError:
            valid_types = [e.value for e in AlertTypeEnum]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid alert_type '{alert_type}'. Must be one of: {valid_types}"
            )

        # Resolve stock
        if ticker:
            stock = await self.stock_service.get_stock(ticker)
            resolved_stock_id = stock.id
        elif stock_id:
            from sqlalchemy import select
            res = await self.session.execute(select(Stock).where(Stock.id == stock_id))
            stock = res.scalars().first()
            if not stock:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock not found")
            resolved_stock_id = stock_id
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must provide stock_id or ticker"
            )

        # Validate target_value
        if validated_type in (AlertTypeEnum.sentiment_above, AlertTypeEnum.sentiment_below):
            if target_value < -1.0 or target_value > 1.0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Sentiment target_value must be between -1.0 and 1.0"
                )
        elif validated_type in (AlertTypeEnum.price_above, AlertTypeEnum.price_below):
            if target_value <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Price target_value must be greater than 0"
                )

        alert = Alert(
            user_id=user_id,
            stock_id=resolved_stock_id,
            alert_type=validated_type,
            target_value=target_value,
            is_triggered=False
        )
        await self.alert_repo.create(alert)
        await self.session.flush()
        return await self.alert_repo.get_alert_with_stock(alert.id)

    async def get_alert(self, alert_id: UUID, user_id: UUID) -> Alert:
        """Retrieves an alert by ID, verifying user ownership."""
        alert = await self.alert_repo.get_alert_with_stock(alert_id)
        if not alert:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
        if alert.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this alert")
        return alert

    async def list_user_alerts(
        self, user_id: UUID, stock_id: Optional[UUID] = None, triggered_only: bool = False
    ) -> List[Alert]:
        """Lists all alerts for a user with optional filters."""
        return await self.alert_repo.list_user_alerts(user_id, stock_id, triggered_only)

    async def delete_alert(self, alert_id: UUID, user_id: UUID) -> None:
        """Deletes a specific alert owned by the user."""
        alert = await self.get_alert(alert_id, user_id)
        await self.alert_repo.delete(alert)
        await self.session.flush()

    async def evaluate_alerts_for_stock(self, symbol: str, user_id: Optional[UUID] = None) -> List[Dict[str, Any]]:
        """
        Evaluates all active (untriggered) alerts for a given stock.
        
        For price alerts: compares target_value against the latest close price.
        For sentiment alerts: compares target_value against the current aggregated sentiment score.
        
        Returns a list of evaluation results indicating which alerts were triggered.
        """
        stock = await self.stock_service.get_stock(symbol)
        
        # Get all untriggered alerts for this stock
        active_alerts = await self.alert_repo.list_active_alerts_for_stock(stock.id)
        
        if not active_alerts:
            return []

        results = []
        
        # Lazily fetch current values only when needed
        current_price = None
        current_sentiment = None

        for alert in active_alerts:
            # Optionally filter by user_id if provided
            if user_id and alert.user_id != user_id:
                continue

            triggered = False
            current_value = 0.0
            message = ""

            if alert.alert_type in (AlertTypeEnum.price_above, AlertTypeEnum.price_below):
                # Fetch latest price if not already fetched
                if current_price is None:
                    latest_price = await self.stock_service.stock_repo.get_latest_price(stock.id)
                    current_price = float(latest_price.close_price) if latest_price else 0.0

                current_value = current_price

                if alert.alert_type == AlertTypeEnum.price_above:
                    triggered = current_price >= float(alert.target_value)
                    message = (
                        f"Price ${current_price:.2f} {'>=' if triggered else '<'} "
                        f"target ${float(alert.target_value):.2f}"
                    )
                else:  # price_below
                    triggered = current_price <= float(alert.target_value)
                    message = (
                        f"Price ${current_price:.2f} {'<=' if triggered else '>'} "
                        f"target ${float(alert.target_value):.2f}"
                    )

            elif alert.alert_type in (AlertTypeEnum.sentiment_above, AlertTypeEnum.sentiment_below):
                # Fetch current sentiment if not already fetched
                if current_sentiment is None:
                    sentiment_service = SentimentService(self.session)
                    sentiment_data = await sentiment_service.get_stock_sentiment(symbol)
                    current_sentiment = sentiment_data.get("overall_score", 0.0)

                current_value = current_sentiment

                if alert.alert_type == AlertTypeEnum.sentiment_above:
                    triggered = current_sentiment >= float(alert.target_value)
                    message = (
                        f"Sentiment {current_sentiment:.3f} {'>=' if triggered else '<'} "
                        f"target {float(alert.target_value):.3f}"
                    )
                else:  # sentiment_below
                    triggered = current_sentiment <= float(alert.target_value)
                    message = (
                        f"Sentiment {current_sentiment:.3f} {'<=' if triggered else '>'} "
                        f"target {float(alert.target_value):.3f}"
                    )

            elif alert.alert_type == AlertTypeEnum.new_research_report:
                # This type is event-driven, not poll-based. Skip during evaluation.
                message = "Event-driven alert (evaluated on report generation)"
                current_value = 0.0

            # If triggered, mark it in the database
            if triggered:
                await self.alert_repo.mark_triggered(alert.id)
                logger.info(
                    "Alert triggered: %s for %s (target=%s, current=%s)",
                    alert.alert_type.value, stock.ticker, alert.target_value, current_value
                )

            results.append({
                "alert_id": alert.id,
                "alert_type": alert.alert_type.value,
                "stock_ticker": stock.ticker,
                "target_value": float(alert.target_value),
                "current_value": current_value,
                "triggered": triggered,
                "message": message
            })

        return results

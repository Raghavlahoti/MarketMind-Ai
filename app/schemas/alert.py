# ============================================================================
# MARKETMIND AI - ALERT PYDANTIC SCHEMAS
# ============================================================================

import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.stocks import StockBase


class AlertCreate(BaseModel):
    stock_id: Optional[UUID] = None
    ticker: Optional[str] = None
    alert_type: str = Field(
        ...,
        description="One of: price_above, price_below, sentiment_above, sentiment_below, new_research_report"
    )
    target_value: float = Field(..., description="Threshold value for the alert trigger")


class AlertResponse(BaseModel):
    id: UUID
    user_id: UUID
    stock_id: UUID
    alert_type: str
    target_value: float
    is_triggered: bool
    created_at: datetime.datetime
    stock: Optional[StockBase] = None

    model_config = ConfigDict(from_attributes=True)


class AlertEvaluationResult(BaseModel):
    alert_id: UUID
    alert_type: str
    stock_ticker: str
    target_value: float
    current_value: float
    triggered: bool
    message: str

# ============================================================================
# MARKETMIND AI - COMPANY FUNDAMENTALS DATABASE REPOSITORY
# ============================================================================

import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import CompanyFundamental, PeriodTypeEnum
from app.repositories.base import BaseRepository


class FundamentalsRepository(BaseRepository[CompanyFundamental]):
    """SQLAlchemy 2.0 concrete implementation of company fundamentals operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(CompanyFundamental, session)

    async def get_by_stock_id(
        self, stock_id: UUID, period_type: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[CompanyFundamental]:
        """Queries for fundamentals records by stock ID, optionally filtered by period type."""
        query = select(CompanyFundamental).where(CompanyFundamental.stock_id == stock_id)
        if period_type:
            # Match enum string
            query = query.where(CompanyFundamental.period_type == PeriodTypeEnum(period_type))
        query = query.order_by(CompanyFundamental.report_date.desc())
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)
            
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_by_stock_id(
        self, stock_id: UUID, period_type: Optional[str] = None
    ) -> int:
        """Counts total fundamentals records by stock ID, optionally filtered by period type."""
        query = select(func.count(CompanyFundamental.id)).where(CompanyFundamental.stock_id == stock_id)
        if period_type:
            query = query.where(CompanyFundamental.period_type == PeriodTypeEnum(period_type))
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def upsert_fundamentals(
        self, stock_id: UUID, fundamentals_data: List[Dict[str, Any]]
    ) -> None:
        """Performs bulk upsert of company fundamentals in PostgreSQL."""
        if not fundamentals_data:
            return

        values_to_insert = []
        for f in fundamentals_data:
            # We map period_type to the enum value or handle it as string
            period_val = f["period_type"]
            if isinstance(period_val, str):
                period_val = PeriodTypeEnum(period_val)

            values_to_insert.append({
                "stock_id": stock_id,
                "report_date": f["report_date"],
                "period_type": period_val,
                "revenue": f.get("revenue"),
                "net_income": f.get("net_income"),
                "eps": f.get("eps"),
                "ebitda": f.get("ebitda"),
                "assets": f.get("assets"),
                "liabilities": f.get("liabilities"),
                "cash_flow": f.get("cash_flow"),
                "metadata_": f.get("metadata", {}),
            })

        stmt = insert(CompanyFundamental).values(values_to_insert)
        stmt = stmt.on_conflict_do_update(
            index_elements=["stock_id", "report_date", "period_type"],
            set_={
                "revenue": stmt.excluded.revenue,
                "net_income": stmt.excluded.net_income,
                "eps": stmt.excluded.eps,
                "ebitda": stmt.excluded.ebitda,
                "assets": stmt.excluded.assets,
                "liabilities": stmt.excluded.liabilities,
                "cash_flow": stmt.excluded.cash_flow,
                "metadata": stmt.excluded.metadata,
                "updated_at": func.now(),
            }
        )
        await self.session.execute(stmt)
        await self.session.flush()

# ============================================================================
# MARKETMIND AI - COMPANY PROFILE DATABASE REPOSITORY
# ============================================================================

from typing import Any, Dict, Optional
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import CompanyProfile
from app.repositories.base import BaseRepository


class CompanyProfileRepository(BaseRepository[CompanyProfile]):
    """SQLAlchemy 2.0 concrete implementation of company profile operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(CompanyProfile, session)

    async def get_by_stock_id(self, stock_id: UUID) -> Optional[CompanyProfile]:
        """Queries for a profile by the associated stock ID."""
        query = select(CompanyProfile).where(CompanyProfile.stock_id == stock_id)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def upsert_profile(self, stock_id: UUID, profile_data: Dict[str, Any]) -> CompanyProfile:
        """Upserts a company profile record associated with a stock ID."""
        stmt = insert(CompanyProfile).values(
            stock_id=stock_id,
            description=profile_data.get("description"),
            headquarters=profile_data.get("headquarters"),
            ceo=profile_data.get("ceo"),
            employees=profile_data.get("employees"),
            website=profile_data.get("website"),
            founded_year=profile_data.get("founded_year"),
            market_cap=profile_data.get("market_cap"),
            shares_outstanding=profile_data.get("shares_outstanding"),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["stock_id"],
            set_={
                "description": stmt.excluded.description,
                "headquarters": stmt.excluded.headquarters,
                "ceo": stmt.excluded.ceo,
                "employees": stmt.excluded.employees,
                "website": stmt.excluded.website,
                "founded_year": stmt.excluded.founded_year,
                "market_cap": stmt.excluded.market_cap,
                "shares_outstanding": stmt.excluded.shares_outstanding,
                "updated_at": func.now(),
            }
        )
        await self.session.execute(stmt)
        await self.session.flush()

        # Retrieve, refresh from DB to clear session caching, and return
        profile = await self.get_by_stock_id(stock_id)
        if profile:
            await self.session.refresh(profile)
        return profile

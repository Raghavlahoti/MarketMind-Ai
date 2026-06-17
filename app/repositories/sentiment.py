# ============================================================================
# MARKETMIND AI - SENTIMENT DATABASE REPOSITORY
# ============================================================================

from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Sentiment, SourceTypeEnum
from app.repositories.base import BaseRepository


class SentimentRepository(BaseRepository[Sentiment]):
    """SQLAlchemy 2.0 implementation for news and source sentiment data operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Sentiment, session)

    async def get_by_stock_id(self, stock_id: UUID) -> List[Sentiment]:
        """Gets all sentiment entries associated with a stock."""
        query = select(Sentiment).where(Sentiment.stock_id == stock_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_source(self, source_type: SourceTypeEnum, source_id: UUID) -> Optional[Sentiment]:
        """Retrieves cached sentiment for a specific source article/document."""
        query = select(Sentiment).where(
            Sentiment.source_type == source_type,
            Sentiment.source_id == source_id
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_by_sources(self, source_type: SourceTypeEnum, source_ids: List[UUID]) -> List[Sentiment]:
        """Batch fetches sentiments for a list of source IDs."""
        if not source_ids:
            return []
        query = select(Sentiment).where(
            Sentiment.source_type == source_type,
            Sentiment.source_id.in_(source_ids)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def delete_by_stock_id(self, stock_id: UUID, source_type: Optional[SourceTypeEnum] = None):
        """Clears sentiment cache for a stock."""
        stmt = delete(Sentiment).where(Sentiment.stock_id == stock_id)
        if source_type:
            stmt = stmt.where(Sentiment.source_type == source_type)
        await self.session.execute(stmt)
        await self.session.flush()

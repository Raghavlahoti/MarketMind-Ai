# ============================================================================
# MARKETMIND AI - RESEARCH REPOSITORY
# ============================================================================

from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import ResearchRun, ResearchReport, ResearchReportSection, ResearchSource, AIModelUsage
from app.repositories.base import BaseRepository


class ResearchRepository(BaseRepository[ResearchReport]):
    """SQLAlchemy 2.0 implementation for Research runs, reports, sections, and model usage records."""

    def __init__(self, session: AsyncSession):
        super().__init__(ResearchReport, session)

    async def create_run(self, run: ResearchRun) -> ResearchRun:
        """Saves a new ResearchRun entry."""
        self.session.add(run)
        await self.session.flush()
        return run

    async def create_source_link(self, source: ResearchSource) -> ResearchSource:
        """Links a source document (news article) to a research run."""
        self.session.add(source)
        await self.session.flush()
        return source

    async def create_sources_bulk(self, sources: List[ResearchSource]):
        """Bulk creates source linkages."""
        if not sources:
            return
        self.session.add_all(sources)
        await self.session.flush()

    async def create_model_usage(self, usage: AIModelUsage) -> AIModelUsage:
        """Saves LLM token usage audit record."""
        self.session.add(usage)
        await self.session.flush()
        return usage

    async def save_report(self, report: ResearchReport) -> ResearchReport:
        """Saves the main research report metadata."""
        self.session.add(report)
        await self.session.flush()
        return report

    async def save_sections_bulk(self, sections: List[ResearchReportSection]):
        """Saves research report text sections."""
        if not sections:
            return
        self.session.add_all(sections)
        await self.session.flush()

    async def get_report_with_sections(self, report_id: UUID) -> Optional[ResearchReport]:
        """Fetches a research report with its child sections preloaded."""
        query = (
            select(ResearchReport)
            .options(selectinload(ResearchReport.sections))
            .where(ResearchReport.id == report_id)
        )
        res = await self.session.execute(query)
        return res.scalars().first()

    async def get_latest_report_for_stock(self, stock_id: UUID) -> Optional[ResearchReport]:
        """Retrieves the latest completed report for a stock with preloaded sections."""
        query = (
            select(ResearchReport)
            .options(selectinload(ResearchReport.sections))
            .where(ResearchReport.stock_id == stock_id)
            .order_by(desc(ResearchReport.created_at))
            .limit(1)
        )
        res = await self.session.execute(query)
        return res.scalars().first()

    async def get_reports_for_stock(self, stock_id: UUID, limit: int = 10, offset: int = 0) -> List[ResearchReport]:
        """Retrieves a list of all research reports generated for a stock with sections preloaded."""
        query = (
            select(ResearchReport)
            .options(selectinload(ResearchReport.sections))
            .where(ResearchReport.stock_id == stock_id)
            .order_by(desc(ResearchReport.created_at))
            .limit(limit)
            .offset(offset)
        )
        res = await self.session.execute(query)
        return list(res.scalars().all())

    async def count_reports_for_stock(self, stock_id: UUID) -> int:
        """Counts total research reports generated for a stock."""
        query = (
            select(func.count(ResearchReport.id))
            .where(ResearchReport.stock_id == stock_id)
        )
        res = await self.session.execute(query)
        return res.scalar() or 0

    async def get_run(self, run_id: UUID) -> Optional[ResearchRun]:
        """Queries for a research run by its ID."""
        query = select(ResearchRun).where(ResearchRun.id == run_id)
        res = await self.session.execute(query)
        return res.scalars().first()

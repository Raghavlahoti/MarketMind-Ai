# ============================================================================
# MARKETMIND AI - RESEARCH REPORT REPOSITORY INTERFACE
# ============================================================================

from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession


class ReportRepositoryInterface:
    """Interface outlining custom database queries on Research Report & Section records."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_report_with_sections(self, report_id: UUID) -> Optional[Any := None]:
        """Fetches report object with pre-loaded sections."""
        raise NotImplementedError

    async def get_section_by_type(self, report_id: UUID, section_type: str) -> Optional[Any := None]:
        """Fetches a specific section content from a report."""
        raise NotImplementedError

    async def list_reports_by_stock(self, stock_id: UUID) -> List[Any := None]:
        """Lists reports subject to a specific stock."""
        raise NotImplementedError

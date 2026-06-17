# ============================================================================
# MARKETMIND AI - BASE SERVICE LAYER
# ============================================================================

from sqlalchemy.ext.asyncio import AsyncSession


class BaseService:
    """Base class orchestrating database session lifetimes for services."""

    def __init__(self, session: AsyncSession):
        self.session = session

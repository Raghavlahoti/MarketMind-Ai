# ============================================================================
# MARKETMIND AI - USER REPOSITORY CONCRETE IMPLEMENTATION
# ============================================================================

from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """SQLAlchemy 2.0 concrete implementation of user operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Queries for a user by their registered email address."""
        query = select(User).where(User.email == email)
        result = await self.session.execute(query)
        return result.scalars().first()

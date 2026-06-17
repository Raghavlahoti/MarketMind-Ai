# ============================================================================
# MARKETMIND AI - REPOSITORY PATTERN INTERFACES (BASE)
# ============================================================================

from typing import Generic, List, Optional, Type, TypeVar
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """Abstract interface defining standard CRUD signatures."""

    def __init__(self, model_class: Type[ModelType], session: AsyncSession):
        self.model_class = model_class
        self.session = session

    async def get_by_id(self, id: UUID) -> Optional[ModelType]:
        """Fetches a record by primary key."""
        result = await self.session.execute(
            select(self.model_class).where(self.model_class.id == id)
        )
        return result.scalars().first()

    async def list_all(self, limit: int = 100, offset: int = 0) -> List[ModelType]:
        """Lists records with pagination parameters."""
        query = select(self.model_class).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, entity: ModelType) -> ModelType:
        """Saves a new entity state to the database session."""
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def delete(self, entity: ModelType) -> None:
        """Removes an entity state from the database session."""
        await self.session.delete(entity)
        await self.session.flush()

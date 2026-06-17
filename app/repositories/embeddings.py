# ============================================================================
# MARKETMIND AI - EMBEDDING DATABASE REPOSITORY
# ============================================================================

from typing import List, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Embedding
from app.repositories.base import BaseRepository


class EmbeddingRepository(BaseRepository[Embedding]):
    """SQLAlchemy 2.0 implementation for vector embeddings and semantic search."""

    def __init__(self, session: AsyncSession):
        super().__init__(Embedding, session)

    async def bulk_insert_embeddings(self, embeddings_list: List[Embedding]) -> None:
        """Saves a list of Embedding models to the database session in bulk."""
        if not embeddings_list:
            return
        self.session.add_all(embeddings_list)
        await self.session.flush()

    async def semantic_search(
        self,
        query_vector: List[float],
        dimension: int,
        limit: int = 5
    ) -> List[Tuple[Embedding, float]]:
        """Performs cosine distance vector similarity search on pgvector index.
        
        Returns a list of tuples containing (Embedding object, cosine_distance float).
        """
        # Under pgvector-python, we calculate distance using column.cosine_distance(vector)
        distance_expr = Embedding.embedding.cosine_distance(query_vector).label("cosine_distance")
        
        query = (
            select(Embedding, distance_expr)
            .where(Embedding.embedding_dimension == dimension)
            .order_by(distance_expr.asc())
            .limit(limit)
        )
        
        result = await self.session.execute(query)
        rows = result.all()
        
        # rows will contain tuples: (Embedding, cosine_distance)
        return [(row[0], float(row[1])) for row in rows]

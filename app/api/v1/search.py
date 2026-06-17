# ============================================================================
# MARKETMIND AI - SEMANTIC SEARCH API ROUTER
# ============================================================================

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user_id
from app.schemas.search import SemanticSearchRequest, SemanticSearchResult
from app.services.embeddings import EmbeddingsService

from app.api.limiter import InMemoryRateLimiter

router = APIRouter()
semantic_search_limiter = InMemoryRateLimiter(limit=10, window=60)


@router.post("/semantic", response_model=List[SemanticSearchResult], dependencies=[Depends(semantic_search_limiter)])
async def search_semantic(
    payload: SemanticSearchRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Query database context semantics using text embeddings."""
    embeddings_service = EmbeddingsService(db)
    
    return await embeddings_service.search_semantics_by_vector(
        query_vector=payload.query_vector,
        dimension=payload.dimension,
        limit=payload.limit or 5
    )

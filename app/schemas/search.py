# ============================================================================
# MARKETMIND AI - SEMANTIC SEARCH PYDANTIC SCHEMAS
# ============================================================================

from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class SemanticSearchRequest(BaseModel):
    query_vector: List[float] = Field(..., description="Float vector representation of search query")
    dimension: int = Field(..., description="Expected embedding dimension (e.g. 1536, 4096)")
    limit: Optional[int] = Field(5, description="Maximum number of search results to return")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query_vector": [0.015, -0.024, 0.081],
                "dimension": 1536,
                "limit": 5
            }
        }
    )


class SemanticSearchResult(BaseModel):
    id: UUID
    content_chunk: str
    source_type: str
    source_id: UUID
    cosine_distance: float

    model_config = ConfigDict(from_attributes=True)

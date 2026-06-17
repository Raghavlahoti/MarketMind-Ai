# ============================================================================
# MARKETMIND AI - EMBEDDING SERVICE LAYER
# ============================================================================

import logging
from typing import List, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Embedding, SourceTypeEnum
from app.providers.embeddings import get_embeddings_provider
from app.repositories.embeddings import EmbeddingRepository
from app.services.base import BaseService

logger = logging.getLogger("marketmind_ai")


class EmbeddingsService(BaseService):
    """Orchestrates vector embedding generation, chunking of financial articles, and similarity queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.embedding_repo = EmbeddingRepository(session)
        self.provider = get_embeddings_provider()

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Converts raw text array into embeddings vectors."""
        if not texts:
            return []
        return await self.provider.get_embeddings_bulk(texts)

    async def chunk_and_embed_article(self, article_id: UUID, title: str, content: str) -> List[Embedding]:
        """Splits article content into chunks, generates embeddings, and persists them to PostgreSQL."""
        full_text = f"Title: {title}\n\nContent: {content}"
        chunks = self.chunk_text_by_words(full_text, chunk_size_words=150, overlap_words=30)
        
        if not chunks:
            return []

        # Generate embeddings in bulk for all chunks
        vectors = await self.generate_embeddings(chunks)
        
        embeddings_to_save = []
        for idx, (chunk, vector) in enumerate(zip(chunks, vectors)):
            embeddings_to_save.append(Embedding(
                source_type=SourceTypeEnum.news_article,
                source_id=article_id,
                chunk_index=idx,
                content_chunk=chunk,
                embedding_model=self.provider.model_name,
                embedding_dimension=self.provider.dimension,
                embedding=vector
            ))
            
        await self.embedding_repo.bulk_insert_embeddings(embeddings_to_save)
        logger.info("Successfully chunked, embedded, and saved %d chunks for article ID: %s", 
                    len(embeddings_to_save), article_id)
        return embeddings_to_save

    async def search_semantics_by_vector(
        self,
        query_vector: List[float],
        dimension: int,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Performs pgvector search using query vector."""
        results = await self.embedding_repo.semantic_search(query_vector, dimension, limit)
        
        return [
            {
                "id": emb.id,
                "content_chunk": emb.content_chunk,
                "source_type": emb.source_type.value,
                "source_id": emb.source_id,
                "cosine_distance": dist
            }
            for emb, dist in results
        ]

    async def search_semantics_by_text(
        self,
        query_text: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Generates query vector for query text and retrieves most similar database chunks."""
        query_vector = await self.provider.get_embedding(query_text)
        return await self.search_semantics_by_vector(
            query_vector=query_vector,
            dimension=self.provider.dimension,
            limit=limit
        )

    @staticmethod
    def chunk_text_by_words(text: str, chunk_size_words: int = 150, overlap_words: int = 30) -> List[str]:
        """Helper to split text into overlapping chunks based on word count."""
        words = text.split()
        chunks = []
        if not words:
            return chunks
        
        start = 0
        while start < len(words):
            end = min(start + chunk_size_words, len(words))
            chunks.append(" ".join(words[start:end]))
            if end == len(words):
                break
            start += (chunk_size_words - overlap_words)
            
        return chunks

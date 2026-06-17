# ============================================================================
# MARKETMIND AI - EMBEDDINGS ENGINE PROVIDER CONTRACT & IMPLEMENTATION
# ============================================================================

import logging
import math
import hashlib
import random
from typing import List
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger("marketmind_ai")


class EmbeddingsProviderInterface:
    """Contract for text vector embedding providers (OpenAI, Local, or NVIDIA NIM)."""

    def __init__(self, provider_name: str, model_name: str, dimension: int):
        self.provider_name = provider_name
        self.model_name = model_name
        self.dimension = dimension

    async def get_embedding(self, text: str) -> List[float]:
        """Converts text segment into standard float vector array."""
        raise NotImplementedError

    async def get_embeddings_bulk(self, texts: List[str]) -> List[List[float]]:
        """Converts a batch list of text segments into list of vectors."""
        raise NotImplementedError


class OpenAIEmbeddingsProvider(EmbeddingsProviderInterface):
    """Concrete client using OpenAI API for embedding generation."""

    def __init__(self, api_key: str, model_name: str, dimension: int):
        super().__init__("openai", model_name, dimension)
        self.client = AsyncOpenAI(api_key=api_key)

    async def get_embedding(self, text: str) -> List[float]:
        embeddings = await self.get_embeddings_bulk([text])
        return embeddings[0]

    async def get_embeddings_bulk(self, texts: List[str]) -> List[List[float]]:
        try:
            logger.info("Generating bulk embeddings via OpenAI: model=%s, count=%d", self.model_name, len(texts))
            response = await self.client.embeddings.create(
                input=texts,
                model=self.model_name,
                dimensions=self.dimension
            )
            # OpenAI response objects contain data mapping to embedding vectors
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error("Error calling OpenAI embeddings: %s", e)
            raise e


class NvidiaEmbeddingsProvider(EmbeddingsProviderInterface):
    """Concrete client using NVIDIA NIM API for embedding generation."""

    def __init__(self, api_key: str, base_url: str, model_name: str, dimension: int):
        super().__init__("nim", model_name, dimension)
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )

    async def get_embedding(self, text: str) -> List[float]:
        embeddings = await self.get_embeddings_bulk([text])
        return embeddings[0]

    async def get_embeddings_bulk(self, texts: List[str]) -> List[List[float]]:
        try:
            logger.info("Generating bulk embeddings via NVIDIA NIM: model=%s, count=%d", self.model_name, len(texts))
            response = await self.client.embeddings.create(
                input=texts,
                model=self.model_name
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error("Error calling NVIDIA NIM embeddings: %s", e)
            raise e


class LocalEmbeddingsProvider(EmbeddingsProviderInterface):
    """Fallback local mock provider generating deterministic unit-normalized vectors from text hash."""

    def __init__(self, model_name: str, dimension: int):
        super().__init__("local", model_name, dimension)

    async def get_embedding(self, text: str) -> List[float]:
        return self._generate_deterministic_vector(text)

    async def get_embeddings_bulk(self, texts: List[str]) -> List[List[float]]:
        return [self._generate_deterministic_vector(text) for text in texts]

    def _generate_deterministic_vector(self, text: str) -> List[float]:
        # Generate MD5 hash of text to seed standard python Random
        seed = int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)
        rng = random.Random(seed)
        
        # Generate random values in range [-1, 1]
        vec = [rng.uniform(-1.0, 1.0) for _ in range(self.dimension)]
        
        # Normalize to unit length (so dot product equals cosine similarity)
        magnitude = math.sqrt(sum(x * x for x in vec))
        if magnitude > 0:
            vec = [x / magnitude for x in vec]
        return vec


def get_embeddings_provider() -> EmbeddingsProviderInterface:
    """Factory function returning active EmbeddingsProviderInterface instance depending on settings."""
    provider = settings.EMBEDDING_PROVIDER.lower()
    
    if provider == "nim":
        if not settings.NVIDIA_API_KEY:
            logger.warning("NVIDIA API key not configured for embeddings. Falling back to Local provider.")
            return LocalEmbeddingsProvider(settings.EMBEDDING_MODEL, settings.EMBEDDING_DIMENSION)
        return NvidiaEmbeddingsProvider(
            api_key=settings.NVIDIA_API_KEY,
            base_url=settings.NVIDIA_NIM_BASE_URL,
            model_name=settings.EMBEDDING_MODEL,
            dimension=settings.EMBEDDING_DIMENSION
        )
    elif provider == "openai":
        if not settings.OPENAI_API_KEY:
            logger.warning("OpenAI API key not configured for embeddings. Falling back to Local provider.")
            return LocalEmbeddingsProvider(settings.EMBEDDING_MODEL, settings.EMBEDDING_DIMENSION)
        return OpenAIEmbeddingsProvider(
            api_key=settings.OPENAI_API_KEY,
            model_name=settings.EMBEDDING_MODEL,
            dimension=settings.EMBEDDING_DIMENSION
        )
    else:
        logger.info("Using Local mock embeddings provider.")
        return LocalEmbeddingsProvider(settings.EMBEDDING_MODEL, settings.EMBEDDING_DIMENSION)

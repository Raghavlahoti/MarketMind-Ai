# ============================================================================
# MARKETMIND AI - DATABASE CONNECTION LAYER & SESSION MANAGEMENT
# ============================================================================

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine
)
from app.core.config import settings
from app.core.logging import logger

import re

# Create Async Engine with connection pooling config
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True
)

# Async Session Factory
async_session_factory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


def redact_secrets(text: str) -> str:
    """Hides connection string passwords and key formats from traceback strings."""
    # Redact PostgreSQL async connection password: postgresql+asyncpg://postgres:***@host:5432/postgres
    redacted = re.sub(r'(postgresql\+asyncpg://[^:]+:)[^@]+(@)', r'\1***\2', text)
    # Redact standard postgres connection password
    redacted = re.sub(r'(postgresql://[^:]+:)[^@]+(@)', r'\1***\2', redacted)
    # Redact NVIDIA NIM API Key pattern
    redacted = re.sub(r'nvapi-[a-zA-Z0-9_-]+', 'nvapi-***', redacted)
    # Redact Supabase Secret Keys
    redacted = re.sub(r'sb_secret_[a-zA-Z0-9_-]+', 'sb_secret_***', redacted)
    return redacted


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Dependency injector yielding a managed async database session.
    Automatically commits transactions or performs rollbacks on uncaught exceptions.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            redacted_err = redact_secrets(str(e))
            logger.error("Database transaction failed. Rolling back session.", error=redacted_err)
            await session.rollback()
            raise
        finally:
            await session.close()

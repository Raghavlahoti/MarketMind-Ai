# ============================================================================
# MARKETMIND AI - TEST CONFIGURATION & SQLITE COMPATIBILITY
# ============================================================================
# Shared test setup for unittest-based test modules.
# Registers SQLite compiler shims for PostgreSQL-specific types (JSONB, Enums)
# and provides schema initialization helpers.
# ============================================================================

from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB

# Register JSONB -> JSON compiler shim for SQLite so that models using JSONB
# columns can be created against an in-memory or file-based SQLite database.
# This decorator is idempotent; if already registered, SQLAlchemy ignores it.
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


# Import all models to ensure they are registered with Base.metadata BEFORE
# create_all() is called.  This import must happen AFTER the JSONB shim is
# registered because the model module references JSONB at import time.
from app.models import Base  # noqa: E402


# Tables that can be created on SQLite (excludes pgvector-dependent tables)
SQLITE_SAFE_TABLES = [
    table
    for name, table in Base.metadata.tables.items()
    if name != "embeddings"
]


async def create_test_schema(engine):
    """Create all SQLite-safe tables against the given async engine."""
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda connection: Base.metadata.create_all(
                connection, tables=SQLITE_SAFE_TABLES
            )
        )


async def drop_test_schema(engine):
    """Drop all SQLite-safe tables from the given async engine."""
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda connection: Base.metadata.drop_all(
                connection, tables=SQLITE_SAFE_TABLES
            )
        )

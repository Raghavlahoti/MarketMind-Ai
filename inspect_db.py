# ============================================================================
# MARKETMIND AI - DATABASE SCHEMA INSPECTOR
# ============================================================================

import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings


async def inspect_db() -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    try:
        async with engine.connect() as conn:
            # 1. Fetch tables
            print("--- PUBLIC TABLES ---")
            table_query = await conn.execute(
                text("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY tablename;
                """)
            )
            tables = table_query.scalars().all()
            for t in tables:
                print(f"Table: {t}")
            
            # 2. Fetch indexes
            print("\n--- PUBLIC INDEXES ---")
            index_query = await conn.execute(
                text("""
                SELECT indexname, tablename, indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                ORDER BY tablename, indexname;
                """)
            )
            indexes = index_query.fetchall()
            for idx in indexes:
                print(f"Index: {idx[0]} on {idx[1]} -> {idx[2]}")
                
    except Exception as e:
        print(f"Error during inspection: {e}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(inspect_db())

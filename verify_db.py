# ============================================================================
# MARKETMIND AI - DATABASE CONNECTION & PERMISSION VERIFIER
# ============================================================================

import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.core.database import redact_secrets


async def verify_database() -> None:
    print("======================================================================")
    print("MarketMind AI - Database Verification Utility")
    print("======================================================================")
    
    # 1. Redacted DSN output
    safe_dsn = redact_secrets(settings.DATABASE_URL)
    print(f"Targeting Database URL: {safe_dsn}")
    
    # Create temp async engine
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    success = True
    
    try:
        async with engine.connect() as conn:
            # 2. Test connectivity
            print("\n[1/3] Testing database connectivity...")
            await conn.execute(text("SELECT 1;"))
            print("  -> Success: Database is reachable.")
            
            # 3. Test pgvector presence
            print("\n[2/3] Verifying pgvector extension availability...")
            ext_check = await conn.execute(
                text("SELECT extname FROM pg_extension WHERE extname = 'vector';")
            )
            extension_loaded = ext_check.scalars().first()
            
            if extension_loaded:
                print("  -> Success: 'vector' extension is loaded and active in the database.")
            else:
                print("  -> Extension not loaded. Checking available extensions catalog...")
                avail_check = await conn.execute(
                    text("SELECT name FROM pg_available_extensions WHERE name = 'vector';")
                )
                extension_available = avail_check.scalars().first()
                if extension_available:
                    print("  -> Info: 'vector' extension is available in Postgres catalog but not yet loaded.")
                    print("  -> (Alembic will automatically load it using CREATE EXTENSION IF NOT EXISTS vector)")
                else:
                    print("  -> WARNING: pgvector extension is NOT found in available extensions.")
                    print("     Please enable pgvector in your Supabase project dashboard.")
                    success = False
            
            # 4. Check schema creation privileges
            print("\n[3/3] Auditing database and schema privileges...")
            db_priv = await conn.execute(
                text("SELECT has_database_privilege(current_user, current_database(), 'CREATE');")
            )
            has_db_create = db_priv.scalars().first()
            
            schema_priv = await conn.execute(
                text("SELECT has_schema_privilege(current_user, 'public', 'CREATE');")
            )
            has_schema_create = schema_priv.scalars().first()
            
            print(f"  -> Database Create Privilege: {has_db_create}")
            print(f"  -> 'public' Schema Create Privilege: {has_schema_create}")
            
            if has_db_create or has_schema_create:
                print("  -> Success: User has necessary schema/table creation privileges.")
            else:
                print("  -> WARNING: User lacks standard creation privileges. Migrations may fail.")
                success = False

    except Exception as e:
        redacted_err = redact_secrets(str(e))
        print(f"\n[ERROR] Connectivity verification failed:")
        print(f"  -> {redacted_err}")
        success = False
    finally:
        await engine.dispose()
        
    print("\n======================================================================")
    if success:
        print("VERIFICATION STATUS: SUCCESS")
        print("All database requirements verified. Ready for migrations.")
        sys.exit(0)
    else:
        print("VERIFICATION STATUS: FAILED")
        print("Please check warnings and errors listed above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(verify_database())

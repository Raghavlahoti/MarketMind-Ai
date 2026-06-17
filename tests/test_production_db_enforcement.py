# ============================================================================
# MARKETMIND AI - CONFIG & DATABASE ENFORCEMENT TEST SUITE
# ============================================================================

from pydantic import ValidationError
from app.core.config import Settings

def test_production_db_enforcement():
    print("\nRunning test_production_db_enforcement...")
    
    # 1. Dev environment with SQLite (should pass)
    dev_settings = Settings(
        ENV="development",
        DATABASE_URL="sqlite+aiosqlite:///test.db",
        JWT_SECRET_KEY="test_secret_key_long_enough_to_pass_validation_abcdef",
        SUPABASE_URL="https://example.supabase.co",
        SUPABASE_SECRET_KEY="sb_secret_mock_test_key_value",
        NVIDIA_API_KEY="nvapi-mock_test_api_key_value",
        ALLOWED_ORIGINS="http://localhost:3000"
    )
    assert dev_settings.ENV == "development"
    assert "sqlite" in dev_settings.DATABASE_URL
    print("  [PASS] SQLite permitted in development environment.")

    # 2. Prod environment with PostgreSQL (should pass)
    prod_settings_pg = Settings(
        ENV="production",
        DATABASE_URL="postgresql+asyncpg://postgres:password123@localhost:5432/marketmind",
        JWT_SECRET_KEY="test_secret_key_long_enough_to_pass_validation_abcdef",
        SUPABASE_URL="https://example.supabase.co",
        SUPABASE_SECRET_KEY="sb_secret_mock_test_key_value",
        NVIDIA_API_KEY="nvapi-mock_test_api_key_value",
        ALLOWED_ORIGINS="http://localhost:3000"
    )
    assert prod_settings_pg.ENV == "production"
    assert prod_settings_pg.DATABASE_URL.startswith("postgresql")
    print("  [PASS] PostgreSQL permitted in production environment.")

    # 3. Prod environment with SQLite (should fail validation)
    try:
        Settings(
            ENV="production",
            DATABASE_URL="sqlite+aiosqlite:///test.db",
            JWT_SECRET_KEY="test_secret_key_long_enough_to_pass_validation_abcdef",
            SUPABASE_URL="https://example.supabase.co",
            SUPABASE_SECRET_KEY="sb_secret_mock_test_key_value",
            NVIDIA_API_KEY="nvapi-mock_test_api_key_value",
            ALLOWED_ORIGINS="http://localhost:3000"
        )
        assert False, "Should have failed with ValidationError"
    except ValidationError as e:
        assert "PostgreSQL database URL is required in production environment" in str(e)
        print("  [PASS] SQLite database URL blocked in production environment.")

    # 4. Prod environment with CORS wildcard (should fail validation)
    try:
        Settings(
            ENV="production",
            DATABASE_URL="postgresql+asyncpg://postgres:password123@localhost:5432/marketmind",
            JWT_SECRET_KEY="test_secret_key_long_enough_to_pass_validation_abcdef",
            SUPABASE_URL="https://example.supabase.co",
            SUPABASE_SECRET_KEY="sb_secret_mock_test_key_value",
            NVIDIA_API_KEY="nvapi-mock_test_api_key_value",
            ALLOWED_ORIGINS="*"
        )
        assert False, "Should have failed with ValidationError"
    except ValidationError as e:
        assert "Wildcard CORS origins ('*') are not allowed in production environment" in str(e)
        print("  [PASS] Wildcard CORS blocked in production environment.")

if __name__ == "__main__":
    test_production_db_enforcement()
    print("\nALL PRODUCTION CONFIG ENFORCEMENT TESTS PASSED SUCCESSFULLY!")

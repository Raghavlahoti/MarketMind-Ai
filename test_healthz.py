# ============================================================================
# MARKETMIND AI - HEALTH CHECK ENDPOINT TEST SUITE
# ============================================================================

from fastapi.testclient import TestClient
from app.main import app as fastapi_app
import app.core.database
import app.core.redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from unittest.mock import AsyncMock, MagicMock, patch
import redis.exceptions

client = TestClient(fastapi_app)

def print_banner(title: str):
    print("\n" + "="*80)
    print(f" HEALTHCHECK TEST: {title.upper()} ")
    print("="*80)

def test_healthz_all_healthy():
    print_banner("1. All Dependencies Healthy")
    
    # Mock database session factory success
    mock_db_session = AsyncMock(spec=AsyncSession)
    mock_db_session.__aenter__.return_value = mock_db_session
    mock_db_session.execute = AsyncMock(return_value=None)
    
    # Mock redis client ping success
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.get = AsyncMock(return_value="2026-06-17T12:00:00+00:00") # Heartbeat active
    
    # Mock Redis pipeline for rate limiter to avoid fail-open logs
    mock_pipe = AsyncMock()
    mock_pipe.execute = AsyncMock(return_value=[None, 0, None, None])
    mock_redis.pipeline = MagicMock(return_value=mock_pipe)

    with patch("app.core.database.async_session_factory", return_value=mock_db_session), \
         patch("app.core.redis.redis_manager.get_client", new_callable=AsyncMock, return_value=mock_redis), \
         patch("app.core.redis.redis_manager._is_mock", False):
        
        response = client.get("/healthz")
        print(f"  Response Code: {response.status_code}")
        print(f"  Response Body: {response.json()}")
        
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "healthy"
        assert body["dependencies"]["database"] == "healthy"
        assert body["dependencies"]["redis"] == "healthy"
        assert body["dependencies"]["worker"] == "healthy"

def test_healthz_database_unhealthy():
    print_banner("2. Database Offline")
    
    # Mock database session factory throwing connection error
    mock_db_session = AsyncMock(spec=AsyncSession)
    mock_db_session.__aenter__.return_value = mock_db_session
    mock_db_session.execute = AsyncMock(side_effect=Exception("Database connection timeout"))
    
    # Mock redis client ping success
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.get = AsyncMock(return_value="2026-06-17T12:00:00+00:00")
    
    # Mock Redis pipeline for rate limiter
    mock_pipe = AsyncMock()
    mock_pipe.execute = AsyncMock(return_value=[None, 0, None, None])
    mock_redis.pipeline = MagicMock(return_value=mock_pipe)

    with patch("app.core.database.async_session_factory", return_value=mock_db_session), \
         patch("app.core.redis.redis_manager.get_client", new_callable=AsyncMock, return_value=mock_redis):
        
        response = client.get("/healthz")
        print(f"  Response Code: {response.status_code}")
        print(f"  Response Body: {response.json()}")
        
        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "unhealthy"
        assert body["dependencies"]["database"] == "unhealthy"
        assert body["dependencies"]["redis"] == "healthy"

def test_healthz_redis_unhealthy():
    print_banner("3. Redis Offline")
    
    # Mock database session factory success
    mock_db_session = AsyncMock(spec=AsyncSession)
    mock_db_session.__aenter__.return_value = mock_db_session
    mock_db_session.execute = AsyncMock(return_value=None)
    
    # Mock redis client ping throwing connection error
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(side_effect=redis.exceptions.ConnectionError("Redis connection lost"))

    with patch("app.core.database.async_session_factory", return_value=mock_db_session), \
         patch("app.core.redis.redis_manager.get_client", new_callable=AsyncMock, return_value=mock_redis):
        
        response = client.get("/healthz")
        print(f"  Response Code: {response.status_code}")
        print(f"  Response Body: {response.json()}")
        
        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "unhealthy"
        assert body["dependencies"]["database"] == "healthy"
        assert body["dependencies"]["redis"] == "unhealthy"
        assert body["dependencies"]["worker"] == "unknown"

def test_healthz_worker_stale():
    print_banner("4. Worker Heartbeat Stale")
    
    # Mock database session factory success
    mock_db_session = AsyncMock(spec=AsyncSession)
    mock_db_session.__aenter__.return_value = mock_db_session
    mock_db_session.execute = AsyncMock(return_value=None)
    
    # Mock redis client ping success
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    # Heartbeat generated 10 minutes ago
    import datetime
    stale_time = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=600)).isoformat()
    mock_redis.get = AsyncMock(return_value=stale_time)
    
    # Mock Redis pipeline for rate limiter
    mock_pipe = AsyncMock()
    mock_pipe.execute = AsyncMock(return_value=[None, 0, None, None])
    mock_redis.pipeline = MagicMock(return_value=mock_pipe)

    with patch("app.core.database.async_session_factory", return_value=mock_db_session), \
         patch("app.core.redis.redis_manager.get_client", new_callable=AsyncMock, return_value=mock_redis), \
         patch("app.core.redis.redis_manager._is_mock", False):
        
        response = client.get("/healthz")
        print(f"  Response Code: {response.status_code}")
        print(f"  Response Body: {response.json()}")
        
        assert response.status_code == 200  # API is still operational, worker is just stale
        body = response.json()
        assert body["status"] == "healthy"
        assert body["dependencies"]["database"] == "healthy"
        assert body["dependencies"]["redis"] == "healthy"
        assert body["dependencies"]["worker"] == "stale"

if __name__ == "__main__":
    test_healthz_all_healthy()
    test_healthz_database_unhealthy()
    test_healthz_redis_unhealthy()
    test_healthz_worker_stale()
    print("\nALL DYNAMIC HEALTH CHECK VERIFICATIONS PASSED SUCCESSFULLY!")

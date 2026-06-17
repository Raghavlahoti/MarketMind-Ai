import asyncio
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

async def run_test():
    # Test 1: DB session __aenter__ behavior
    mock_db_session = AsyncMock(spec=AsyncSession)
    mock_db_session.execute = AsyncMock(side_effect=Exception("Database connection timeout"))
    
    # Let's see what happens by default
    async with mock_db_session as session:
        print("session is mock_db_session:", session is mock_db_session)
        try:
            await session.execute("SELECT 1")
            print("Session execute succeeded (this is unexpected for unhealthy DB)")
        except Exception as e:
            print("Session execute failed as expected:", e)
            
    # Test 2: setting __aenter__.return_value
    mock_db_session2 = AsyncMock(spec=AsyncSession)
    mock_db_session2.__aenter__.return_value = mock_db_session2
    mock_db_session2.execute = AsyncMock(side_effect=Exception("Database connection timeout"))
    async with mock_db_session2 as session2:
        print("session2 is mock_db_session2:", session2 is mock_db_session2)
        try:
            await session2.execute("SELECT 1")
            print("Session2 execute succeeded")
        except Exception as e:
            print("Session2 execute failed as expected:", e)

    # Test 3: Redis get_client mocking
    mock_redis = AsyncMock()
    
    # If get_client is a MagicMock returning AsyncMock
    with patch("app.core.redis.redis_manager.get_client", return_value=mock_redis) as mock_get:
        client = await mock_get()
        print("With MagicMock, client is:", type(client), client)
        
    # If get_client is an AsyncMock returning AsyncMock
    mock_get_client = AsyncMock(return_value=mock_redis)
    client = await mock_get_client()
    print("With AsyncMock, client is:", type(client), client is mock_redis)

if __name__ == "__main__":
    asyncio.run(run_test())

# ============================================================================
# MARKETMIND AI - API PAGINATION INTEGRATION TESTER
# ============================================================================

import asyncio
import uuid
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.models import User, Stock

BASE_URL = "http://127.0.0.1:8000/v1"


def print_section(title: str):
    print("\n" + "="*80)
    print(f" {title.upper()} ")
    print("="*80)


async def run_pagination_test() -> None:
    # 0. Set up database connection to clean up before/after test
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    print_section("1. User Registration and Login")
    email = f"pagination.tester.{uuid.uuid4().hex[:6]}@marketmind.ai"
    password = "securePassword123!"
    
    register_payload = {
        "email": email,
        "password": password,
        "first_name": "Pagination",
        "last_name": "Tester"
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Register user
        reg_resp = await client.post(f"{BASE_URL}/auth/register", json=register_payload)
        print(f"POST /auth/register status: {reg_resp.status_code}")
        if reg_resp.status_code != 201:
            print(f"Registration failed: {reg_resp.text}")
            await engine.dispose()
            return
            
        # Login user
        login_resp = await client.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
        print(f"POST /auth/login status: {login_resp.status_code}")
        if login_resp.status_code != 200:
            print(f"Login failed: {login_resp.text}")
            await engine.dispose()
            return
            
        token_data = login_resp.json()
        token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(" -> Authentication Token acquired successfully.")

        # Ensure stock caches are loaded for NVDA
        async with async_session() as session:
            nvda = (await session.execute(select(Stock).where(Stock.ticker == "NVDA"))).scalars().first()
            if not nvda:
                from app.services.stock import StockService
                stock_service = StockService(session)
                nvda = await stock_service.get_stock("NVDA")
                await session.commit()
            nvda_id = nvda.id
            print(f" -> Stock NVDA resolved: ID={nvda_id}")

        print_section("2. News Endpoints Pagination")
        
        # Test GET /news/{symbol} with limit/offset
        print("\n[A] GET /v1/news/NVDA?limit=5&offset=0")
        resp_news1 = await client.get(f"{BASE_URL}/news/NVDA?limit=5&offset=0", headers=headers)
        print(f"  HTTP Status: {resp_news1.status_code}")
        news_data1 = resp_news1.json()
        print(f"  Response Keys: {list(news_data1.keys())}")
        print(f"  Total items in database: {news_data1['total']}")
        print(f"  Items returned: {len(news_data1['items'])} (Expected <= 5)")
        print(f"  Limit used: {news_data1['limit']} | Offset used: {news_data1['offset']}")
        
        assert "items" in news_data1
        assert "total" in news_data1
        assert news_data1["limit"] == 5
        assert news_data1["offset"] == 0
        assert len(news_data1["items"]) <= 5

        # Test GET /news/{symbol} with offset
        if news_data1["total"] > 2:
            print("\n[B] GET /v1/news/NVDA?limit=2&offset=2")
            resp_news2 = await client.get(f"{BASE_URL}/news/NVDA?limit=2&offset=2", headers=headers)
            news_data2 = resp_news2.json()
            print(f"  Items returned: {len(news_data2['items'])} (Expected <= 2)")
            print(f"  Limit used: {news_data2['limit']} | Offset used: {news_data2['offset']}")
            assert len(news_data2["items"]) <= 2
            assert news_data2["offset"] == 2

        print_section("3. Prices Endpoints Pagination")
        
        # Test GET /stocks/{symbol}/prices with limit/offset
        print("\n[A] GET /v1/stocks/NVDA/prices?limit=10&offset=0")
        resp_prices1 = await client.get(f"{BASE_URL}/stocks/NVDA/prices?limit=10&offset=0", headers=headers)
        print(f"  HTTP Status: {resp_prices1.status_code}")
        prices_data1 = resp_prices1.json()
        print(f"  Response Keys: {list(prices_data1.keys())}")
        print(f"  Total items in database: {prices_data1['total']}")
        print(f"  Items returned: {len(prices_data1['items'])} (Expected <= 10)")
        
        assert "items" in prices_data1
        assert "total" in prices_data1
        assert prices_data1["limit"] == 10
        assert prices_data1["offset"] == 0
        assert len(prices_data1["items"]) <= 10

        if prices_data1["total"] > 10:
            print("\n[B] GET /v1/stocks/NVDA/prices?limit=10&offset=10")
            resp_prices2 = await client.get(f"{BASE_URL}/stocks/NVDA/prices?limit=10&offset=10", headers=headers)
            prices_data2 = resp_prices2.json()
            print(f"  Items returned: {len(prices_data2['items'])} (Expected <= 10)")
            assert len(prices_data2["items"]) <= 10
            assert prices_data2["offset"] == 10

        print_section("4. Fundamentals Endpoints Pagination")
        
        # Test GET /stocks/{symbol}/fundamentals with limit/offset
        print("\n[A] GET /v1/stocks/NVDA/fundamentals?limit=3&offset=0")
        resp_fund1 = await client.get(f"{BASE_URL}/stocks/NVDA/fundamentals?limit=3&offset=0", headers=headers)
        print(f"  HTTP Status: {resp_fund1.status_code}")
        fund_data1 = resp_fund1.json()
        print(f"  Response Keys: {list(fund_data1.keys())}")
        print(f"  Total items in database: {fund_data1['total']}")
        print(f"  Items returned: {len(fund_data1['items'])} (Expected <= 3)")
        
        assert "items" in fund_data1
        assert "total" in fund_data1
        assert fund_data1["limit"] == 3
        assert fund_data1["offset"] == 0
        assert len(fund_data1["items"]) <= 3

        print_section("5. Research Endpoints Pagination")
        
        # Test GET /research/{symbol} with limit/offset
        print("\n[A] GET /v1/research/NVDA?limit=5&offset=0")
        resp_res1 = await client.get(f"{BASE_URL}/research/NVDA?limit=5&offset=0", headers=headers)
        print(f"  HTTP Status: {resp_res1.status_code}")
        res_data1 = resp_res1.json()
        print(f"  Response Keys: {list(res_data1.keys())}")
        print(f"  Total items in database: {res_data1['total']}")
        print(f"  Items returned: {len(res_data1['items'])} (Expected <= 5)")
        
        assert "items" in res_data1
        assert "total" in res_data1
        assert res_data1["limit"] == 5
        assert res_data1["offset"] == 0
        assert len(res_data1["items"]) <= 5

    await engine.dispose()
    print("\nALL PAGINATION VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(run_pagination_test())

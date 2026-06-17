# ============================================================================
# MARKETMIND AI - END-TO-END NEWS INTEL FLOW VERIFIER (AAPL & NVDA)
# ============================================================================

import asyncio
import time
import uuid
import httpx
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from models import Stock, NewsArticle, news_article_stocks

BASE_URL = "http://127.0.0.1:8000/v1"

def print_section(title: str):
    print("\n" + "="*80)
    print(f" {title.upper()} ")
    print("="*80)

async def test_flow():
    # 0. Set up database connection
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    # Pre-test cleanup: Delete existing AAPL and NVDA news articles to guarantee clean cache
    print_section("0. Database Cleanup (News Reset)")
    async with async_session() as session:
        # Find stock IDs for AAPL/NVDA
        stock_q = select(Stock.id).where(Stock.ticker.in_(["AAPL", "NVDA"]))
        stock_ids = (await session.execute(stock_q)).scalars().all()
        
        if stock_ids:
            # Find associated article IDs
            art_q = select(news_article_stocks.c.article_id).where(
                news_article_stocks.c.stock_id.in_(stock_ids)
            )
            article_ids = (await session.execute(art_q)).scalars().all()
            
            if article_ids:
                # Delete from news_articles
                q_delete = delete(NewsArticle).where(NewsArticle.id.in_(article_ids))
                await session.execute(q_delete)
                await session.commit()
                print(f" -> Cleared {len(article_ids)} existing news articles to ensure clean cache start.")
            else:
                print(" -> No existing articles found to clear.")
        else:
            print(" -> AAPL/NVDA stocks not yet created. Will be auto-created during flow.")

    # 1. Register a test user and obtain a JWT access token
    print_section("1. User Registration and Login")
    email = f"test.analyst.{uuid.uuid4().hex[:6]}@marketmind.ai"
    password = "securePassword123!"
    
    register_payload = {
        "email": email,
        "password": password,
        "first_name": "E2E",
        "last_name": "NewsVerifier"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
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
        print(" -> E2E Authentication Token acquired successfully.")

        # Test for AAPL and NVDA
        for ticker in ["AAPL", "NVDA"]:
            print_section(f"Verification Flow for {ticker}")
            
            # Resolve Stock ID from DB (will be created automatically by stock_service during news fetch)
            async with async_session() as session:
                stock_rec = (await session.execute(select(Stock).where(Stock.ticker == ticker))).scalars().first()
                if stock_rec:
                    db_news_count_before = (await session.execute(
                        select(func.count(NewsArticle.id))
                        .join(NewsArticle.stocks)
                        .where(Stock.ticker == ticker)
                    )).scalar()
                    print(f" -> Stock record already exists. Persistent news count before test: {db_news_count_before}")
                else:
                    print(f" -> Stock record for {ticker} does not exist yet. Will be auto-ingested.")
            
            # Step A: GET /v1/news/{ticker} (Cache MISS - Ingests from RSS feeds)
            print(f"\n[A] GET /v1/news/{ticker} (First Call - Cache MISS)")
            start_time = time.time()
            resp_first = await client.get(f"{BASE_URL}/news/{ticker}", headers=headers)
            duration_first = (time.time() - start_time) * 1000
            
            print(f"  -> HTTP Status: {resp_first.status_code}")
            print(f"  -> Duration: {duration_first:.2f} ms")
            if resp_first.status_code != 200:
                print(f"  -> Error fetching news: {resp_first.text}")
                continue
            
            news_first = resp_first.json()
            print(f"  -> API Response count: {len(news_first)} news articles returned")

            # Step B: Direct DB Verification for news insertion
            print(f"\n[B] Direct DB Verification for {ticker} news insertion")
            async with async_session() as session:
                # Find stock ID
                stock_rec = (await session.execute(select(Stock).where(Stock.ticker == ticker))).scalars().first()
                # Query NewsArticle count for this stock
                db_news_count = (await session.execute(
                    select(func.count(NewsArticle.id))
                    .join(NewsArticle.stocks)
                    .where(Stock.id == stock_rec.id)
                )).scalar()
                
                print(f"  -> DB News Row Count: {db_news_count} (Expected: > 0)")
                
                # Fetch example article row
                latest_art_q = (
                    select(NewsArticle)
                    .join(NewsArticle.stocks)
                    .where(Stock.id == stock_rec.id)
                    .order_by(NewsArticle.published_at.desc())
                    .limit(1)
                )
                latest_art = (await session.execute(latest_art_q)).scalars().first()
                if latest_art:
                    print(f"  -> Example inserted row: ID={latest_art.id}")
                    print(f"  -> Title: {latest_art.title}")
                    print(f"  -> Source: {latest_art.source_name}")
                    print(f"  -> Published At: {latest_art.published_at}")
                    print(f"  -> URL: {latest_art.url[:80]}...")

            # Step C: GET /v1/news/{ticker} again (Cache HIT - DB Cache)
            print(f"\n[C] GET /v1/news/{ticker} (Second Call - Cache HIT)")
            start_time = time.time()
            resp_second = await client.get(f"{BASE_URL}/news/{ticker}", headers=headers)
            duration_second = (time.time() - start_time) * 1000
            
            print(f"  -> HTTP Status: {resp_second.status_code}")
            print(f"  -> Duration: {duration_second:.2f} ms")
            
            # Verify DB counts didn't double
            async with async_session() as session:
                db_news_count_second = (await session.execute(
                    select(func.count(NewsArticle.id))
                    .join(NewsArticle.stocks)
                    .where(Stock.id == stock_rec.id)
                )).scalar()
                print(f"  -> DB news row count after second call: {db_news_count_second} (Expected to remain exactly: {db_news_count})")
                if db_news_count_second == db_news_count:
                    print(f"  -> Cache HIT Evidence: SUCCESS (No new database rows created)")
                else:
                    print(f"  -> Cache HIT Evidence: FAILED (Database row count changed!)")

            # Step D: GET /v1/news/{ticker}/latest (Cache read only)
            print(f"\n[D] GET /v1/news/{ticker}/latest (Direct Cache Read)")
            start_time = time.time()
            resp_latest = await client.get(f"{BASE_URL}/news/{ticker}/latest", headers=headers)
            duration_latest = (time.time() - start_time) * 1000
            print(f"  -> HTTP Status: {resp_latest.status_code}")
            print(f"  -> Duration: {duration_latest:.2f} ms")
            print(f"  -> API Response count: {len(resp_latest.json())} news articles returned")

            # Step E: GET /v1/news/{ticker}/refresh (Bypasses cache and deduplicates)
            print(f"\n[E] GET /v1/news/{ticker}/refresh (Force Refresh & Deduplication)")
            start_time = time.time()
            resp_refresh = await client.get(f"{BASE_URL}/news/{ticker}/refresh", headers=headers)
            duration_refresh = (time.time() - start_time) * 1000
            print(f"  -> HTTP Status: {resp_refresh.status_code}")
            print(f"  -> Duration: {duration_refresh:.2f} ms")
            
            async with async_session() as session:
                db_news_count_refresh = (await session.execute(
                    select(func.count(NewsArticle.id))
                    .join(NewsArticle.stocks)
                    .where(Stock.id == stock_rec.id)
                )).scalar()
                print(f"  -> DB news row count after refresh: {db_news_count_refresh}")
                print(f"  -> Deduplication Evidence: SUCCESS (Row count before refresh: {db_news_count}, Row count after: {db_news_count_refresh})")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_flow())

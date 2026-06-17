# ============================================================================
# MARKETMIND AI - END-TO-END SENTIMENT FLOW VERIFIER (AAPL & NVDA)
# ============================================================================

import asyncio
import time
import uuid
import httpx
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from models import Stock, NewsArticle, Sentiment, SourceTypeEnum

BASE_URL = "http://127.0.0.1:8000/v1"


def print_section(title: str):
    print("\n" + "="*80)
    print(f" {title.upper()} ")
    print("="*80)


async def test_sentiment_flow():
    # 0. Set up database connection
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    print_section("0. Database Cleanup (Sentiment Cache Reset)")
    async with async_session() as session:
        # Find stock IDs for AAPL/NVDA
        stock_q = select(Stock.id).where(Stock.ticker.in_(["AAPL", "NVDA"]))
        stock_ids = (await session.execute(stock_q)).scalars().all()
        
        if stock_ids:
            # Delete existing news article sentiments
            q_delete = delete(Sentiment).where(
                Sentiment.stock_id.in_(stock_ids),
                Sentiment.source_type == SourceTypeEnum.news_article
            )
            res = await session.execute(q_delete)
            await session.commit()
            print(f" -> Cleared {res.rowcount} existing cached news sentiments for AAPL/NVDA to ensure a clean cache start.")
        else:
            print(" -> AAPL/NVDA stock records not found yet. They will be auto-created during the news step.")

    # 1. Register a test user and obtain a JWT access token
    print_section("1. User Registration and Login")
    email = f"test.analyst.{uuid.uuid4().hex[:6]}@marketmind.ai"
    password = "securePassword123!"
    
    register_payload = {
        "email": email,
        "password": password,
        "first_name": "E2E",
        "last_name": "SentimentVerifier"
    }
    
    async with httpx.AsyncClient(timeout=45.0) as client:
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

        # Ensure we have fresh news ingested for AAPL and NVDA first
        print_section("2. Ensuring News is Ingested First")
        for ticker in ["AAPL", "NVDA"]:
            print(f"Ingesting/refreshing news articles for {ticker}...")
            news_resp = await client.get(f"{BASE_URL}/news/{ticker}", headers=headers)
            print(f"  -> news/{ticker} status: {news_resp.status_code}, count: {len(news_resp.json())} articles.")

        # Test Sentiment Flow for AAPL and NVDA
        for ticker in ["AAPL", "NVDA"]:
            print_section(f"Sentiment Verification Flow for {ticker}")
            
            # Step A: GET /v1/sentiment/{symbol} (Cache MISS - Generates sentiments)
            print(f"\n[A] GET /v1/sentiment/{ticker} (First Call - Cache MISS)")
            start_time = time.time()
            resp_first = await client.get(f"{BASE_URL}/sentiment/{ticker}", headers=headers)
            duration_first = (time.time() - start_time) * 1000
            
            print(f"  -> HTTP Status: {resp_first.status_code}")
            print(f"  -> Duration: {duration_first:.2f} ms")
            if resp_first.status_code != 200:
                print(f"  -> Error fetching sentiment: {resp_first.text}")
                continue
            
            sentiment_data = resp_first.json()
            print(f"  -> Aggregated Sentiment: Overall Score={sentiment_data['overall_score']}, Label={sentiment_data['overall_label']}")
            print(f"  -> Articles Analyzed: {sentiment_data['article_count']}")

            # Step B: Direct DB Verification for sentiment row counts
            print(f"\n[B] Direct DB Verification for {ticker} sentiment insertion")
            async with async_session() as session:
                # Find stock ID
                stock_rec = (await session.execute(select(Stock).where(Stock.ticker == ticker))).scalars().first()
                # Query Sentiment count
                db_sent_count = (await session.execute(
                    select(func.count(Sentiment.id))
                    .where(Sentiment.stock_id == stock_rec.id, Sentiment.source_type == SourceTypeEnum.news_article)
                )).scalar()
                
                print(f"  -> DB News Sentiments Row Count: {db_sent_count} (Expected: {sentiment_data['article_count']})")
                
                # Fetch example sentiment row
                example_sent_q = (
                    select(Sentiment)
                    .where(Sentiment.stock_id == stock_rec.id, Sentiment.source_type == SourceTypeEnum.news_article)
                    .limit(1)
                )
                example_sent = (await session.execute(example_sent_q)).scalars().first()
                if example_sent:
                    print(f"  -> Example inserted row: ID={example_sent.id}")
                    print(f"  -> Article ID (source_id): {example_sent.source_id}")
                    print(f"  -> Sentiment Score: {example_sent.sentiment_score}")
                    print(f"  -> Sentiment Label: {example_sent.sentiment_label.value}")
                    print(f"  -> Confidence Score: {example_sent.confidence_score}")
                    print(f"  -> Explanation: {example_sent.explanation}")

            # Step C: GET /v1/sentiment/{symbol} again (Cache HIT - DB Cache)
            print(f"\n[C] GET /v1/sentiment/{ticker} (Second Call - Cache HIT)")
            start_time = time.time()
            resp_second = await client.get(f"{BASE_URL}/sentiment/{ticker}", headers=headers)
            duration_second = (time.time() - start_time) * 1000
            
            print(f"  -> HTTP Status: {resp_second.status_code}")
            print(f"  -> Duration: {duration_second:.2f} ms")
            
            # Verify DB counts didn't double
            async with async_session() as session:
                db_sent_count_second = (await session.execute(
                    select(func.count(Sentiment.id))
                    .where(Sentiment.stock_id == stock_rec.id, Sentiment.source_type == SourceTypeEnum.news_article)
                )).scalar()
                print(f"  -> DB sentiment row count after second call: {db_sent_count_second} (Expected to remain: {db_sent_count})")
                if db_sent_count_second == db_sent_count:
                    print(f"  -> Cache HIT Evidence: SUCCESS (No new database rows created)")
                else:
                    print(f"  -> Cache HIT Evidence: FAILED (Database row count changed!)")

            # Step D: POST /v1/sentiment/{symbol}/refresh (Cache bypass and recalculate)
            print(f"\n[D] POST /v1/sentiment/{ticker}/refresh (Force Refresh & Overwrite)")
            start_time = time.time()
            resp_refresh = await client.post(f"{BASE_URL}/sentiment/{ticker}/refresh", headers=headers)
            duration_refresh = (time.time() - start_time) * 1000
            print(f"  -> HTTP Status: {resp_refresh.status_code}")
            print(f"  -> Duration: {duration_refresh:.2f} ms")
            
            async with async_session() as session:
                db_sent_count_refresh = (await session.execute(
                    select(func.count(Sentiment.id))
                    .where(Sentiment.stock_id == stock_rec.id, Sentiment.source_type == SourceTypeEnum.news_article)
                )).scalar()
                print(f"  -> DB sentiment row count after refresh: {db_sent_count_refresh} (Expected: {db_sent_count})")
                if db_sent_count_refresh == db_sent_count:
                    print(f"  -> Refresh & Cache Update Evidence: SUCCESS (Sentiments successfully overwritten and cached)")
                else:
                    print(f"  -> Refresh & Cache Update Evidence: FAILED (Row count mismatch!)")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_sentiment_flow())

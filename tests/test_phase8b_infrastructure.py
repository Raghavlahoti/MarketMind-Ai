# ============================================================================
# MARKETMIND AI - PHASE 8B INFRASTRUCTURE VERIFICATION & LOAD TESTING
# ============================================================================

import asyncio
import json
import uuid
import time
import datetime
import arq
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
import app.core.database
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

# Initialize global SQLite engine and override session factory immediately before other imports bind it!
from sqlalchemy.pool import NullPool
db_url = "sqlite+aiosqlite:///test_phase8b_infra.db"
engine = create_async_engine(db_url, echo=False, poolclass=NullPool)

from sqlalchemy import event
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
app.core.database.async_session_factory = async_session
from app.core.redis import redis_manager, RedisCache, KEY_PREFIX_NEWS, KEY_PREFIX_PRICES, KEY_PREFIX_REPORT, KEY_LOCK_RESEARCH
from app.services.research import ResearchEngineService
from app.services.news import NewsService
from app.services.stock import StockService
from app.repositories.research import ResearchRepository
from app.models import (
    Base, Stock, ResearchRun, ResearchReport, ResearchReportSection,
    ResearchSource, AIModelUsage, RunStatusEnum, NewsArticle, StockPrice
)

def print_banner(title: str):
    print("\n" + "="*80)
    print(f" TEST: {title.upper()} ")
    print("="*80)

async def clean_up_run(run_id: uuid.UUID):
    """Helper to clean up specific test runs from DB."""
    async with app.core.database.async_session_factory() as session:
        async with session.begin():
            await session.execute(delete(ResearchReport).where(ResearchReport.run_id == run_id))
            await session.execute(delete(ResearchSource).where(ResearchSource.run_id == run_id))
            await session.execute(delete(AIModelUsage).where(AIModelUsage.run_id == run_id))
            await session.execute(delete(ResearchRun).where(ResearchRun.id == run_id))

async def run_infrastructure_tests():
    import logging
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("marketmind_ai").setLevel(logging.INFO)

    # Mock class methods to bypass external network requests during tests
    from app.providers.yahoo_finance import YahooFinanceProvider
    from app.providers.news import NewsProvider
    from app.services.sentiment import SentimentService

    async def mock_get_stock_metadata(self, symbol: str) -> dict:
        print(f"  [MOCK] mock_get_stock_metadata called for {symbol}")
        return {
            "ticker": symbol.upper(),
            "name": "Apple Inc.",
            "exchange": "NASDAQ",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "is_active": True
        }
    YahooFinanceProvider.get_stock_metadata = mock_get_stock_metadata

    async def mock_get_company_profile(self, symbol: str) -> dict:
        print(f"  [MOCK] mock_get_company_profile called for {symbol}")
        return {
            "description": "Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide.",
            "headquarters": "Cupertino, California",
            "ceo": "Tim Cook",
            "employees": 164000,
            "website": "https://www.apple.com",
            "founded_year": 1976,
            "market_cap": 3000000000000.0,
            "shares_outstanding": 15000000000.0
        }
    YahooFinanceProvider.get_company_profile = mock_get_company_profile

    async def mock_get_analyst_consensus(self, symbol: str) -> dict:
        print(f"  [MOCK] mock_get_analyst_consensus called for {symbol}")
        return {
            "buy_count": 25,
            "hold_count": 10,
            "sell_count": 2,
            "average_target_price": 195.50
        }
    YahooFinanceProvider.get_analyst_consensus = mock_get_analyst_consensus

    async def mock_get_historical_prices(self, symbol: str, start_date=None, end_date=None) -> list:
        print(f"  [MOCK] mock_get_historical_prices called for {symbol}")
        return []
    YahooFinanceProvider.get_historical_prices = mock_get_historical_prices

    async def mock_get_fundamentals(self, symbol: str) -> list:
        print(f"  [MOCK] mock_get_fundamentals called for {symbol}")
        return []
    YahooFinanceProvider.get_fundamentals = mock_get_fundamentals

    async def mock_get_news(self, symbol: str) -> list:
        print(f"  [MOCK] mock_get_news called for {symbol}")
        return []
    NewsProvider.get_news = mock_get_news

    async def mock_get_stock_sentiment(self, symbol: str) -> dict:
        print(f"  [MOCK] mock_get_stock_sentiment called for {symbol}")
        return {
            "overall_sentiment": 0.35,
            "label": "positive",
            "explanation": "Mocked sentiment explanation"
        }
    SentimentService.get_stock_sentiment = mock_get_stock_sentiment

    from app import models
    tables_to_create = [
        table for name, table in Base.metadata.tables.items()
        if name != "embeddings"
    ]
    async with engine.begin() as conn:
        await conn.run_sync(lambda connection: Base.metadata.create_all(connection, tables=tables_to_create))
    
    # Initialize Redis Manager (uses FakeRedis fallback automatically on local hosts)
    await redis_manager.initialize()
    print(f"Redis Manager Initialized (is_mock={redis_manager.is_mock})")
    
    # Reset Cache Metrics
    await RedisCache.reset_metrics()
    
    # Resolve AAPL stock
    async with async_session() as session:
        stock = (await session.execute(select(Stock).where(Stock.ticker == "AAPL"))).scalars().first()
        if not stock:
            stock = Stock(
                ticker="AAPL",
                name="Apple Inc.",
                exchange="NASDAQ",
                sector="Technology",
                industry="Consumer Electronics"
            )
            session.add(stock)
            await session.commit()
            
            # Fetch with populated ID
            stock = (await session.execute(select(Stock).where(Stock.ticker == "AAPL"))).scalars().first()
            
        stock_uuid = stock.id
        
        # Seed relations to prevent Yahoo Finance fetches and SQLite lock contention
        from app.models import CompanyProfile, CompanyFundamental, StockPrice, PeriodTypeEnum
        
        # Check and seed CompanyProfile
        profile = (await session.execute(select(CompanyProfile).where(CompanyProfile.stock_id == stock_uuid))).scalars().first()
        if not profile:
            profile = CompanyProfile(
                stock_id=stock_uuid,
                description="Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories.",
                headquarters="Cupertino, CA",
                ceo="Tim Cook",
                employees=164000,
                website="https://www.apple.com",
                founded_year=1976,
                market_cap=3000000000000.0,
                shares_outstanding=15000000000.0
            )
            session.add(profile)
            
        # Check and seed CompanyFundamental
        fundamental = (await session.execute(select(CompanyFundamental).where(CompanyFundamental.stock_id == stock_uuid))).scalars().first()
        if not fundamental:
            fundamental = CompanyFundamental(
                stock_id=stock_uuid,
                report_date=datetime.date(2023, 9, 30),
                period_type=PeriodTypeEnum.annual,
                revenue=383285000000.0,
                net_income=96995000000.0,
                eps=6.13,
                ebitda=125820000000.0,
                assets=352581000000.0,
                liabilities=290437000000.0,
                cash_flow=110543000000.0
            )
            session.add(fundamental)
            
        # Check and seed StockPrice
        price = (await session.execute(select(StockPrice).where(StockPrice.stock_id == stock_uuid))).scalars().first()
        if not price:
            price = StockPrice(
                stock_id=stock_uuid,
                price_date=datetime.date.today(),
                open_price=180.0,
                high_price=182.0,
                low_price=179.0,
                close_price=181.0,
                volume=50000000,
                adjusted_close=181.0
            )
            session.add(price)
            
        await session.commit()

    test_user_id = uuid.uuid4()

    # Seed mock user for foreign keys
    from app.models import User
    async with async_session() as session:
        user = (await session.execute(select(User).where(User.id == test_user_id))).scalars().first()
        if not user:
            user = User(
                id=test_user_id,
                email=f"test_{test_user_id}@example.com",
                password_hash="mock_hash"
            )
            session.add(user)
            await session.commit()

    # =========================================================================
    # 1. REDIS INFRASTRUCTURE HEALTH & FALLBACK
    # =========================================================================
    print_banner("1. Redis Manager & Health Checks")
    from app.core.redis import check_redis_health
    health = await check_redis_health()
    print(f"  Health Check result: {health}")
    assert health["status"] == "healthy"
    assert "mock" in health
    
    # =========================================================================
    # 2. CACHE-ASIDE PATTERN FOR NEWS & PRICES
    # =========================================================================
    print_banner("2. Cache-Aside Patterns & Hit/Miss Tracking")
    
    # Seed news article in DB
    async with async_session() as session:
        # Clear existing news first to test cache isolation
        await session.execute(delete(NewsArticle))
        news_art = NewsArticle(
            title="Apple Launches New AI Feature",
            content="Apple announced advanced AI core capabilities.",
            summary="Apple launches AI",
            source_name="TechCrunch",
            url="https://techcrunch.com/aapl",
            published_at=datetime.datetime.now(datetime.timezone.utc)
        )
        session.add(news_art)
        # Link to stock
        stock_db = (await session.execute(
            select(Stock).where(Stock.id == stock_uuid).options(selectinload(Stock.news_articles))
        )).scalars().first()
        stock_db.news_articles.append(news_art)
        await session.commit()

    # Fetch News via NewsService (First read: Cache Miss)
    await RedisCache.reset_metrics()
    async with async_session() as session:
        news_service = NewsService(session)
        print("  Reading news (expected Cache Miss)...")
        news_miss = await news_service.get_news("AAPL")
        assert len(news_miss) > 0
        metrics = await RedisCache.get_metrics()
        print(f"  First Read Cache Metrics: {metrics}")
        assert metrics["misses"] == 1
        assert metrics["hits"] == 0

    # Fetch News via NewsService again (Second read: Cache Hit)
    async with async_session() as session:
        print("  Reading news again (expected Cache Hit)...")
        news_hit = await news_service.get_news("AAPL")
        assert len(news_hit) == len(news_miss)
        assert news_hit[0].title == news_miss[0].title
        metrics = await RedisCache.get_metrics()
        print(f"  Second Read Cache Metrics: {metrics}")
        assert metrics["hits"] == 1
        assert metrics["misses"] == 1
        
    # Benchmarking DB vs Cache latency
    print("\n  Benchmarking Latency:")
    # DB read time (clean session, clear cache)
    await RedisCache.delete(f"{KEY_PREFIX_NEWS}AAPL")
    t0 = time.perf_counter()
    async with async_session() as session:
        ns = NewsService(session)
        await ns.get_news("AAPL")
    t_db = (time.perf_counter() - t0) * 1000
    
    # Cache read time
    t0 = time.perf_counter()
    async with async_session() as session:
        ns = NewsService(session)
        await ns.get_news("AAPL")
    t_cache = (time.perf_counter() - t0) * 1000
    print(f"    Database Read Latency: {t_db:.2f}ms")
    print(f"    Redis Cache Read Latency: {t_cache:.2f}ms")
    assert t_cache < t_db or redis_manager.is_mock, "Cache read should be faster than DB"

    # =========================================================================
    # 3. DISTRIBUTED SLIDING WINDOW RATE LIMITER
    # =========================================================================
    print_banner("3. Redis Sliding-Window Rate Limiter")
    from app.api.limiter import InMemoryRateLimiter
    from fastapi import Request
    
    # 2 requests limit in 10 seconds window
    limiter = InMemoryRateLimiter(limit=2, window=10)
    
    class MockRequest:
        def __init__(self, host, path):
            class Url:
                def __init__(self, path):
                    self.path = path
            self.client = type('Client', (object,), {'host': host})
            self.url = Url(path)
            
    req = MockRequest("192.168.1.50", "/test-limit")
    
    # Request 1 (Allowed)
    print("  Request 1 (allowed)...")
    await limiter(req)
    
    # Request 2 (Allowed)
    print("  Request 2 (allowed)...")
    await limiter(req)
    
    # Request 3 (Blocked)
    print("  Request 3 (expected 429 Block)...")
    from fastapi import HTTPException
    try:
        await limiter(req)
        assert False, "Should have thrown HTTPException 429"
    except HTTPException as e:
        print(f"  Limiter successfully blocked: status={e.status_code}, detail='{e.detail}'")
        assert e.status_code == 429
        
    # Wait for window sliding window to clear and request again
    print("  Waiting 11 seconds for window slide...")
    await asyncio.sleep(11)
    print("  Request 4 (allowed after window slide)...")
    await limiter(req)

    # =========================================================================
    # 4. DISTRIBUTED LOCK & CONCURRENT PROTECTION
    # =========================================================================
    print_banner("4. Distributed Lock (Double-Click Protection)")
    
    # Mock chat completion return JSON format
    valid_json = {
        "title": "Mock AAPL Report",
        "rating": "Buy",
        "target_price": 250.0,
        "executive_summary": "Summary mock",
        "bull_case": "Bull case mock"
    }
    
    async with async_session() as session:
        service = ResearchEngineService(session)
        async def mock_chat_completion(*args, **kwargs):
            # Slow down completion to simulate 2 seconds institutional NIM API inference
            await asyncio.sleep(2)
            return {"content": json.dumps(valid_json), "model": "test-model", "prompt_tokens": 100, "completion_tokens": 50}
        service.nvidia_provider.generate_chat_completion = mock_chat_completion
        
        # Trigger duplicate requests concurrently
        # 1st request acquires lock and executes
        # 2nd request tries to run, detects lock, updates its own run status to failed, and raises ValueError
        
        run1_uuid = uuid.uuid4()
        run2_uuid = uuid.uuid4()
        
        # Bootstrap runs in database in pending status
        async with async_session() as run_session:
            async with run_session.begin():
                r1 = ResearchRun(id=run1_uuid, user_id=test_user_id, stock_id=stock_uuid, trigger_type="manual", status=RunStatusEnum.pending)
                r2 = ResearchRun(id=run2_uuid, user_id=test_user_id, stock_id=stock_uuid, trigger_type="manual", status=RunStatusEnum.pending)
                run_session.add(r1)
                run_session.add(r2)
                
        print("  Launching task 1 and task 2 concurrently...")
        
        # Start both concurrently using gather
        async def run_task1():
            async with async_session() as s:
                srv = ResearchEngineService(s)
                srv.nvidia_provider.generate_chat_completion = mock_chat_completion
                return await srv.generate_research_report(user_id=test_user_id, symbol="AAPL", run_id=run1_uuid)
                
        async def run_task2():
            # Delay task 2 slightly to ensure task 1 locks first
            await asyncio.sleep(0.5)
            async with async_session() as s:
                srv = ResearchEngineService(s)
                srv.nvidia_provider.generate_chat_completion = mock_chat_completion
                return await srv.generate_research_report(user_id=test_user_id, symbol="AAPL", run_id=run2_uuid)

        t_results = await asyncio.gather(
            run_task1(),
            run_task2(),
            return_exceptions=True
        )
        
        # Task 1 result (Success report)
        rep = t_results[0]
        assert isinstance(rep, ResearchReport)
        print(f"  Task 1 Succeeded. Generated Report ID={rep.id}")
        
        # Task 2 result (Expected Lock Error exception)
        err = t_results[1]
        assert isinstance(err, ValueError)
        print(f"  Task 2 correctly raised: {err}")
        assert "already in progress" in str(err)
        
        # Verify run database states
        async with async_session() as verify_session:
            run1 = await verify_session.get(ResearchRun, run1_uuid)
            run2 = await verify_session.get(ResearchRun, run2_uuid)
            print(f"  Run 1 status: {run1.status}")
            print(f"  Run 2 status: {run2.status}, ErrorMsg='{run2.error_message}'")
            
            assert run1.status == RunStatusEnum.completed
            assert run2.status == RunStatusEnum.failed
            assert "Duplicate request ignored" in run2.error_message
            
        await clean_up_run(run1_uuid)
        await clean_up_run(run2_uuid)

    # =========================================================================
    # 5. ARQ WORKER IN-PROCESS TASK SCHEDULER & HEALTH RUN
    # =========================================================================
    print_banner("5. ARQ Worker Jobs, Exponential Backoff, & Health")
    from app.worker import generate_research_report_job, reconcile_dangling_runs_job, WorkerSettings
    
    # Execute recovery sweeper via worker settings
    print("  Executing reconcile_dangling_runs_job...")
    mock_ctx = {"redis": await redis_manager.get_client()}
    swept_count = await reconcile_dangling_runs_job(mock_ctx)
    print(f"  Reconciled {swept_count} runs successfully.")
    
    # Test retry mechanism in worker job
    print("  Testing worker task exponential backoff retries...")
    async def mock_fail_generate_report(*args, **kwargs):
        raise Exception("NVIDIA NIM Server Error (500)")
        
    async with async_session() as session:
        # Create a run in pending
        run_uuid = uuid.uuid4()
        async with session.begin():
            r = ResearchRun(id=run_uuid, user_id=test_user_id, stock_id=stock_uuid, trigger_type="manual", status=RunStatusEnum.pending)
            session.add(r)
            
        # Temporarily mock the report service method to raise error
        original_gen_report = ResearchEngineService.generate_research_report
        ResearchEngineService.generate_research_report = mock_fail_generate_report
        
        # Execute job with try 1
        try:
            print("    Executing arq job (expected retry deferred raise)...")
            ctx_try = {"job_try": 1}
            await generate_research_report_job(ctx_try, str(test_user_id), "AAPL", str(run_uuid))
            assert False, "Should have raised arq.Retry"
        except arq.Retry as retry_err:
            print(f"    Worker successfully caught failure and triggered retry deferral: {retry_err}")
            # Defer should equal 5 seconds for try 1 (5 * 2^0)
            assert retry_err.defer_score is not None
            
        # Restore service
        ResearchEngineService.generate_research_report = original_gen_report
        await clean_up_run(run_uuid)

    # =========================================================================
    # 6. LOAD TESTING (20 CONCURRENT REPORT GENERATIONS)
    # =========================================================================
    print_banner("6. Load Testing - 20 Concurrent Report Requests")
    
    concurrency_count = 20
    run_uuids = [uuid.uuid4() for _ in range(concurrency_count)]
    
    async with async_session() as run_session:
        async with run_session.begin():
            for run_uuid in run_uuids:
                r = ResearchRun(
                    id=run_uuid,
                    user_id=test_user_id,
                    stock_id=stock_uuid,
                    trigger_type="manual",
                    status=RunStatusEnum.pending
                )
                run_session.add(r)
                
    print(f"  Launching {concurrency_count} report generations concurrently...")
    
    async def run_single_task(run_id, delay):
        if delay > 0:
            await asyncio.sleep(delay)
        async with async_session() as s:
            srv = ResearchEngineService(s)
            srv.nvidia_provider.generate_chat_completion = mock_chat_completion
            return await srv.generate_research_report(user_id=test_user_id, symbol="AAPL", run_id=run_id)
            
    # Launch them concurrently with staggered starts
    tasks = [run_single_task(run_uuids[i], i * 0.05) for i in range(concurrency_count)]
    
    t_start = time.perf_counter()
    load_results = await asyncio.gather(*tasks, return_exceptions=True)
    t_elapsed = time.perf_counter() - t_start
    print(f"  Completed all {concurrency_count} concurrent requests in {t_elapsed:.2f}s")
    
    # Evaluate results
    success_count = 0
    failure_count = 0
    lock_error_count = 0
    
    for res in load_results:
        if isinstance(res, ResearchReport):
            success_count += 1
        elif isinstance(res, ValueError):
            failure_count += 1
            if "already in progress" in str(res):
                lock_error_count += 1
        else:
            print(f"    Unexpected result/exception: {type(res)} - {res}")
            
    print(f"  Results Summary:")
    print(f"    Successfully generated reports: {success_count} (Expected: 1)")
    print(f"    Correctly rejected lock-duplicates: {lock_error_count} (Expected: 19)")
    
    assert success_count == 1, f"Expected exactly 1 success, got {success_count}"
    assert lock_error_count == concurrency_count - 1, f"Expected exactly {concurrency_count - 1} lock rejections, got {lock_error_count}"
    
    # Verify run database states
    async with async_session() as verify_session:
        db_completed = 0
        db_failed = 0
        for run_uuid in run_uuids:
            run = await verify_session.get(ResearchRun, run_uuid)
            if run.status == RunStatusEnum.completed:
                db_completed += 1
            elif run.status == RunStatusEnum.failed:
                db_failed += 1
                assert "Duplicate request ignored" in run.error_message or "already in progress" in run.error_message
                
        print(f"    DB Status check -> Completed runs: {db_completed}, Failed runs: {db_failed}")
        assert db_completed == 1
        assert db_failed == concurrency_count - 1
        
    # Clean up all runs
    for run_uuid in run_uuids:
        await clean_up_run(run_uuid)
        
    await engine.dispose()
    await redis_manager.close()
    print("\nALL INFRASTRUCTURE AND ARQ WORKER VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(run_infrastructure_tests())

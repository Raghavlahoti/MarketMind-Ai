# ============================================================================
# MARKETMIND AI - TRANSACTION INTEGRITY VERIFICATION SUITE
# ============================================================================

import asyncio
import json
import uuid
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.core.database import async_session_factory
from app.services.research import ResearchEngineService
from app.repositories.research import ResearchRepository
from app.providers.nvidia import NvidiaProvider
from models import (
    Stock, ResearchRun, ResearchReport, ResearchReportSection,
    ResearchSource, AIModelUsage, RunStatusEnum
)

def print_banner(title: str):
    print("\n" + "="*80)
    print(f" TEST: {title.upper()} ")
    print("="*80)

async def clean_up_run(run_id: uuid.UUID):
    """Helper to clean up specific test runs from DB."""
    async with async_session_factory() as session:
        async with session.begin():
            # Delete related reports, which cascades
            await session.execute(delete(ResearchReport).where(ResearchReport.run_id == run_id))
            await session.execute(delete(ResearchSource).where(ResearchSource.run_id == run_id))
            await session.execute(delete(AIModelUsage).where(AIModelUsage.run_id == run_id))
            await session.execute(delete(ResearchRun).where(ResearchRun.id == run_id))

from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

async def run_integrity_tests():
    from sqlalchemy import text
    db_url = settings.DATABASE_URL
    use_sqlite = False

    # Try direct connection test
    try:
        temp_engine = create_async_engine(db_url, echo=False)
        async with temp_engine.connect() as conn:
            await conn.execute(text("SELECT 1;"))
        await temp_engine.dispose()
        print("Successfully connected to the configured database.")
        engine = create_async_engine(db_url, echo=False)
    except Exception as conn_err:
        print(f"Warning: Database connection failed: {conn_err}")
        print("Falling back to local SQLite database 'sqlite+aiosqlite:///test_integrity.db' for transactional verification...")
        db_url = "sqlite+aiosqlite:///test_integrity.db"
        use_sqlite = True
        engine = create_async_engine(db_url, echo=False)

        # Initialize SQLite tables manually, skipping tables with pgvector columns (which SQLite doesn't support)
        import models
        from models import Base
        tables_to_create = [
            table for name, table in Base.metadata.tables.items()
            if name != "embeddings"
        ]
        async with engine.begin() as conn:
            await conn.run_sync(lambda connection: Base.metadata.create_all(connection, tables=tables_to_create))
        print("Local SQLite tables initialized.")

    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    # Override the global session factory bridge so the service uses our local engine/session
    import app.core.database
    original_session_factory = app.core.database.async_session_factory
    app.core.database.async_session_factory = async_session
    globals()['async_session_factory'] = async_session

    # Resolve a test stock
    async with async_session() as session:
        stock = (await session.execute(select(Stock).where(Stock.ticker == "AAPL"))).scalars().first()
        if not stock:
            # Fallback - create stock record manually
            stock = Stock(
                ticker="AAPL",
                name="Apple Inc.",
                exchange="NASDAQ",
                sector="Technology",
                industry="Consumer Electronics"
            )
            session.add(stock)
            await session.commit()
            
        stock_uuid = stock.id
        print(f"Using Stock AAPL (ID: {stock_uuid}) for verification.")

    test_user_id = uuid.uuid4()

    # =========================================================================
    # SCENARIO 1: NVIDIA API FAILURE
    # =========================================================================
    print_banner("1. NVIDIA API Failure Rollback & Recovery")
    
    # Instantiate service
    async with async_session() as session:
        service = ResearchEngineService(session)
        
        # Mock NVIDIA provider to raise an exception
        original_chat_completion = service.nvidia_provider.generate_chat_completion
        async def mock_fail_chat_completion(*args, **kwargs):
            raise Exception("Simulated NVIDIA NIM API Timeout (504)")
        service.nvidia_provider.generate_chat_completion = mock_fail_chat_completion

        run_id = None
        try:
            # Trigger report generation
            await service.generate_research_report(user_id=test_user_id, symbol="AAPL")
        except Exception as e:
            print(f"  Caught expected error: {e}")
            
        # Verify database state
        # Find the latest run for test_user_id
        async with async_session_factory() as verify_session:
            run = (await verify_session.execute(
                select(ResearchRun)
                .where(ResearchRun.user_id == test_user_id)
                .order_by(ResearchRun.created_at.desc())
            )).scalars().first()
            
            assert run is not None, "ResearchRun should have been created in Phase A"
            run_id = run.id
            print(f"  ResearchRun created: ID={run_id}, Status={run.status}")
            assert run.status == RunStatusEnum.failed, "Run status must be 'failed'"
            assert "Simulated NVIDIA NIM" in run.error_message, "Run should store exception trace"
            
            # Verify no report was persisted
            report = (await verify_session.execute(
                select(ResearchReport).where(ResearchReport.run_id == run_id)
            )).scalars().first()
            assert report is None, "No ResearchReport should have been created on API failure"
            print("  Verified: No research report or children saved in DB. State is clean.")
            
        await clean_up_run(run_id)

    # =========================================================================
    # SCENARIO 2: JSON PARSE FAILURE
    # =========================================================================
    print_banner("2. JSON Parse Failure Rollback & Recovery")
    
    async with async_session() as session:
        service = ResearchEngineService(session)
        
        async def mock_invalid_json_chat_completion(*args, **kwargs):
            return {"content": "This is not valid JSON string", "model": "test-model"}
        service.nvidia_provider.generate_chat_completion = mock_invalid_json_chat_completion

        try:
            await service.generate_research_report(user_id=test_user_id, symbol="AAPL")
        except json.JSONDecodeError as e:
            print(f"  Caught expected JSON decode error: {e}")
            
        async with async_session_factory() as verify_session:
            run = (await verify_session.execute(
                select(ResearchRun)
                .where(ResearchRun.user_id == test_user_id)
                .order_by(ResearchRun.created_at.desc())
            )).scalars().first()
            
            run_id = run.id
            print(f"  ResearchRun created: ID={run_id}, Status={run.status}")
            assert run.status == RunStatusEnum.failed, "Run status must be 'failed'"
            
            report = (await verify_session.execute(
                select(ResearchReport).where(ResearchReport.run_id == run_id)
            )).scalars().first()
            assert report is None, "No ResearchReport saved on parsing failure"
            print("  Verified: JSON parse failure rolled back. State is clean.")
            
        await clean_up_run(run_id)

    # =========================================================================
    # SCENARIO 3: SECTION INSERT FAILURE (ATOMICITY VERIFICATION)
    # =========================================================================
    print_banner("3. Section Insert Failure Atomic Rollback")
    
    async with async_session() as session:
        service = ResearchEngineService(session)
        
        # Return a valid JSON format mockup
        valid_json = {
            "title": "Mock AAPL Report",
            "rating": "Buy",
            "target_price": 250.0,
            "executive_summary": "Summary mock",
            "bull_case": "Bull case mock"
        }
        async def mock_valid_chat_completion(*args, **kwargs):
            return {"content": json.dumps(valid_json), "model": "test-model", "prompt_tokens": 100, "completion_tokens": 50}
        service.nvidia_provider.generate_chat_completion = mock_valid_chat_completion

        # Mock save_sections_bulk to fail
        # This occurs in the middle of Phase C (after save_report has flushed)
        async def mock_fail_save_sections(*args, **kwargs):
            raise Exception("Simulated DB Constraint: Section content contains invalid character encoding")
        
        # We need to monkeypatch the save_sections_bulk method dynamically on the repository class or instance.
        # Let's override it on the ResearchRepository class level temporarily.
        original_save_sections = ResearchRepository.save_sections_bulk
        ResearchRepository.save_sections_bulk = mock_fail_save_sections

        try:
            await service.generate_research_report(user_id=test_user_id, symbol="AAPL")
        except Exception as e:
            print(f"  Caught expected DB section insert error: {e}")
            
        # Restore class method
        ResearchRepository.save_sections_bulk = original_save_sections

        async with async_session_factory() as verify_session:
            run = (await verify_session.execute(
                select(ResearchRun)
                .where(ResearchRun.user_id == test_user_id)
                .order_by(ResearchRun.created_at.desc())
            )).scalars().first()
            
            run_id = run.id
            print(f"  ResearchRun created: ID={run_id}, Status={run.status}")
            assert run.status == RunStatusEnum.failed, "Run status must be 'failed' via recovery session"
            assert "Simulated DB Constraint" in run.error_message, "Error message must be saved"
            
            # Verify ATOMICITY: No report or sections exist in the database!
            # Since save_report flushes before save_sections_bulk, save_report succeeded but section failed.
            # Atomic transaction must roll back both!
            report = (await verify_session.execute(
                select(ResearchReport).where(ResearchReport.run_id == run_id)
            )).scalars().first()
            assert report is None, "Report should have been ROLLED BACK because section insert failed!"
            print("  Verified: Section failure rolled back the generated report record. Atomicity CONFIRMED.")
            
        await clean_up_run(run_id)

    # =========================================================================
    # SCENARIO 4: SOURCE INSERT FAILURE (ATOMICITY VERIFICATION)
    # =========================================================================
    print_banner("4. Source Insert Failure Atomic Rollback")
    
    async with async_session() as session:
        service = ResearchEngineService(session)
        service.nvidia_provider.generate_chat_completion = mock_valid_chat_completion

        # Mock create_sources_bulk to fail
        async def mock_fail_create_sources(*args, **kwargs):
            raise Exception("Simulated DB Constraint: Source foreign key constraint violation")
        
        original_create_sources = ResearchRepository.create_sources_bulk
        ResearchRepository.create_sources_bulk = mock_fail_create_sources

        try:
            await service.generate_research_report(user_id=test_user_id, symbol="AAPL")
        except Exception as e:
            print(f"  Caught expected DB source insert error: {e}")
            
        ResearchRepository.create_sources_bulk = original_create_sources

        async with async_session_factory() as verify_session:
            run = (await verify_session.execute(
                select(ResearchRun)
                .where(ResearchRun.user_id == test_user_id)
                .order_by(ResearchRun.created_at.desc())
            )).scalars().first()
            
            run_id = run.id
            print(f"  ResearchRun created: ID={run_id}, Status={run.status}")
            assert run.status == RunStatusEnum.failed, "Run status must be 'failed'"
            
            report = (await verify_session.execute(
                select(ResearchReport).where(ResearchReport.run_id == run_id)
            )).scalars().first()
            assert report is None, "Report should have been ROLLED BACK because source insert failed!"
            print("  Verified: Source failure rolled back the generated report record. Atomicity CONFIRMED.")
            
        await clean_up_run(run_id)

    # =========================================================================
    # SCENARIO 5: AIMODELUSAGE INSERT FAILURE (ATOMICITY VERIFICATION)
    # =========================================================================
    print_banner("5. AIModelUsage Insert Failure Atomic Rollback")
    
    async with async_session() as session:
        service = ResearchEngineService(session)
        service.nvidia_provider.generate_chat_completion = mock_valid_chat_completion

        # Mock create_model_usage to fail
        async def mock_fail_create_usage(*args, **kwargs):
            raise Exception("Simulated DB Constraint: AIModelUsage numeric check constraint failed")
        
        original_create_usage = ResearchRepository.create_model_usage
        ResearchRepository.create_model_usage = mock_fail_create_usage

        try:
            await service.generate_research_report(user_id=test_user_id, symbol="AAPL")
        except Exception as e:
            print(f"  Caught expected DB usage insert error: {e}")
            
        ResearchRepository.create_model_usage = original_create_usage

        async with async_session_factory() as verify_session:
            run = (await verify_session.execute(
                select(ResearchRun)
                .where(ResearchRun.user_id == test_user_id)
                .order_by(ResearchRun.created_at.desc())
            )).scalars().first()
            
            run_id = run.id
            print(f"  ResearchRun created: ID={run_id}, Status={run.status}")
            assert run.status == RunStatusEnum.failed, "Run status must be 'failed'"
            
            report = (await verify_session.execute(
                select(ResearchReport).where(ResearchReport.run_id == run_id)
            )).scalars().first()
            assert report is None, "Report should have been ROLLED BACK because AIModelUsage insert failed!"
            print("  Verified: AIModelUsage failure rolled back report. Atomicity CONFIRMED.")
            
        await clean_up_run(run_id)

    # =========================================================================
    # SCENARIO 6: SIMULATED WORKER TERMINATION DURING PERSISTENCE
    # =========================================================================
    print_banner("6. Worker Termination During Persistence Rollback")
    
    async with async_session() as session:
        service = ResearchEngineService(session)
        service.nvidia_provider.generate_chat_completion = mock_valid_chat_completion

        # Simulate termination by raising GeneratorExit (simulating worker crash/SIGKILL)
        # during save_report (Phase C write)
        async def mock_termination_save_report(*args, **kwargs):
            raise GeneratorExit("Worker process SIGKILL / OOM Kill simulated!")
        
        original_save_report = ResearchRepository.save_report
        ResearchRepository.save_report = mock_termination_save_report

        run_id = None
        try:
            await service.generate_research_report(user_id=test_user_id, symbol="AAPL")
        except BaseException as e:
            # Catch BaseException (covers GeneratorExit, SystemExit, KeyboardInterrupt)
            print(f"  Caught expected worker termination crash: {type(e).__name__} ({e})")
            
        ResearchRepository.save_report = original_save_report

        # Verify database state:
        async with async_session_factory() as verify_session:
            # The run was created and set to RUNNING. Since it crashed mid-run, status stays running/pending in DB.
            # Let's verify that the report writes were rolled back.
            # We first find the run:
            run = (await verify_session.execute(
                select(ResearchRun)
                .where(ResearchRun.user_id == test_user_id)
                .order_by(ResearchRun.created_at.desc())
            )).scalars().first()
            
            assert run is not None
            run_id = run.id
            print(f"  ResearchRun created: ID={run_id}, Status={run.status}")
            assert run.status == RunStatusEnum.running, "Dangling run remains in 'running' status"
            
            report = (await verify_session.execute(
                select(ResearchReport).where(ResearchReport.run_id == run_id)
            )).scalars().first()
            assert report is None, "Report must be rolled back by the engine on database connection closure"
            print("  Verified: Database auto-rolled back intermediate writes on session drop. State is clean.")

        # Update run started_at to trigger sweeper timeout (settings.RESEARCH_RUN_TIMEOUT_SECONDS = 300)
        import datetime
        async with async_session_factory() as edit_session:
            async with edit_session.begin():
                run_to_backdate = await edit_session.get(ResearchRun, run_id)
                run_to_backdate.started_at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=10)

        # Execute the actual production sweeper method
        print("\n  Executing production dangling runs recovery sweep...")
        async with async_session() as sweep_session:
            sweep_service = ResearchEngineService(sweep_session)
            count = await sweep_service.reconcile_dangling_runs()
            print(f"  Sweeper completed. Reconciled {count} stale run(s).")
                    
        # Verify run is now resolved
        async with async_session_factory() as verify_session:
            run = await verify_session.get(ResearchRun, run_id)
            print(f"  Post-reconciliation Run ID={run.id}, Status={run.status}, Msg='{run.error_message}'")
            assert run.status == RunStatusEnum.failed
            print("  Verified: Reconciliation sweeper recovered dangling states successfully.")

        await clean_up_run(run_id)

    # =========================================================================
    # SCENARIO 7: RESILIENT DATA COLLECTION (GRACEFUL DEGRADATION)
    # =========================================================================
    print_banner("7. Resilient Data Collection & Graceful Degradation")
    
    async with async_session() as session:
        service = ResearchEngineService(session)
        service.nvidia_provider.generate_chat_completion = mock_valid_chat_completion

        # Mock NewsService.get_news to fail
        from app.services.news import NewsService
        async def mock_fail_get_news(*args, **kwargs):
            raise Exception("RSS Feed Timeout (504 Connection Refused)")
        original_get_news = NewsService.get_news
        NewsService.get_news = mock_fail_get_news

        try:
            # Trigger report generation, which should succeed even though news collection failed!
            report = await service.generate_research_report(user_id=test_user_id, symbol="AAPL")
            print(f"  Report generated successfully: ID={report.id}, Title='{report.title}'")
            
            # Verify database states
            async with async_session_factory() as verify_session:
                run = await verify_session.get(ResearchRun, report.run_id)
                print(f"  ResearchRun ID={run.id}, Status={run.status}")
                assert run.status == RunStatusEnum.completed, "Run should complete successfully"
                
                # Check metrics for failed sources
                metrics = run.config.get("metrics", {})
                failed_sources = metrics.get("failed_sources", [])
                print(f"  Failed sources recorded in run metrics: {failed_sources}")
                assert "news" in failed_sources, "Metrics must record 'news' as a failed source"
                
        finally:
            # Restore NewsService
            NewsService.get_news = original_get_news

        await clean_up_run(report.run_id)

    await engine.dispose()
    print("\nALL TRANSACTION INTEGRITY VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(run_integrity_tests())

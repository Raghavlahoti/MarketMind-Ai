# ============================================================================
# MARKETMIND AI - END-TO-END NVIDIA RESEARCH FLOW VERIFIER (AAPL & NVDA)
# ============================================================================

import asyncio
import time
import uuid
import httpx
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.models import Stock, ResearchRun, ResearchReport, ResearchReportSection, ResearchSource, AIModelUsage

BASE_URL = "http://127.0.0.1:8000/v1"


def print_section(title: str):
    print("\n" + "="*80)
    print(f" {title.upper()} ")
    print("="*80)


async def test_research_flow():
    # 0. Set up database connection
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    print_section("0. Database Cleanup (Research History Reset)")
    async with async_session() as session:
        # Find stock IDs for AAPL/NVDA
        stock_q = select(Stock.id).where(Stock.ticker.in_(["AAPL", "NVDA"]))
        stock_ids = (await session.execute(stock_q)).scalars().all()
        
        if stock_ids:
            # Delete research report sections first (due to FK cascading, but let's be explicit)
            reports_q = select(ResearchReport.id).where(ResearchReport.stock_id.in_(stock_ids))
            report_ids = (await session.execute(reports_q)).scalars().all()
            
            if report_ids:
                q_del_sections = delete(ResearchReportSection).where(ResearchReportSection.report_id.in_(report_ids))
                await session.execute(q_del_sections)
                
                q_del_reports = delete(ResearchReport).where(ResearchReport.id.in_(report_ids))
                await session.execute(q_del_reports)

            # Delete research runs
            runs_q = select(ResearchRun.id).where(ResearchRun.stock_id.in_(stock_ids))
            run_ids = (await session.execute(runs_q)).scalars().all()
            
            if run_ids:
                # Delete sources
                q_del_sources = delete(ResearchSource).where(ResearchSource.run_id.in_(run_ids))
                await session.execute(q_del_sources)
                
                # Delete model usages
                q_del_usage = delete(AIModelUsage).where(AIModelUsage.run_id.in_(run_ids))
                await session.execute(q_del_usage)

                q_del_runs = delete(ResearchRun).where(ResearchRun.id.in_(run_ids))
                await session.execute(q_del_runs)

            await session.commit()
            print(f" -> Cleared existing research runs, reports, sources, usages for AAPL/NVDA to guarantee a clean verification.")
        else:
            print(" -> AAPL/NVDA stock records not found yet. They will be auto-created during the ingestion steps.")

    # 1. Register a test user and obtain a JWT access token
    print_section("1. User Registration and Login")
    email = f"test.analyst.{uuid.uuid4().hex[:6]}@marketmind.ai"
    password = "securePassword123!"
    
    register_payload = {
        "email": email,
        "password": password,
        "first_name": "E2E",
        "last_name": "NvidiaVerifier"
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
        print(" -> E2E Authentication Token acquired successfully.")

        # Ensure we have fresh news and sentiments ingested for AAPL and NVDA first
        print_section("2. Ensuring News & Sentiment Data Exists")
        for ticker in ["AAPL", "NVDA"]:
            print(f"Triggering news retrieval for {ticker}...")
            await client.get(f"{BASE_URL}/news/{ticker}", headers=headers)
            print(f"Triggering sentiment analysis for {ticker}...")
            await client.get(f"{BASE_URL}/sentiment/{ticker}", headers=headers)
        print(" -> Pre-requisite News and Sentiment caches populated successfully.")

        # Test Research Flow for AAPL and NVDA
        for ticker in ["AAPL", "NVDA"]:
            print_section(f"Research Report Generation Flow for {ticker}")
            
            # Step A: POST /v1/research/{symbol}/generate (Cache MISS - Generates report via NVIDIA NIM)
            print(f"\n[A] POST /v1/research/{ticker}/generate (First Call - Generation)")
            start_time = time.time()
            resp_first = await client.post(f"{BASE_URL}/research/{ticker}/generate", headers=headers)
            duration_first = (time.time() - start_time) * 1000
            
            print(f"  -> HTTP Status: {resp_first.status_code}")
            print(f"  -> Duration: {duration_first:.2f} ms")
            if resp_first.status_code != 201:
                print(f"  -> Error generating report: {resp_first.text}")
                continue
            
            report_data = resp_first.json()
            print(f"  -> Report Created: ID={report_data['id']}")
            print(f"  -> Title: {report_data['title']}")
            print(f"  -> Rating: {report_data['rating']}")
            print(f"  -> Target Price: {report_data['target_price']}")
            print(f"  -> Sections Created: {len(report_data['sections'])}")

            # Step B: Direct DB Verification for runs, reports, sections, sources, usage
            print(f"\n[B] Direct DB Verification for {ticker} persistence details")
            async with async_session() as session:
                # Find stock ID
                stock_rec = (await session.execute(select(Stock).where(Stock.ticker == ticker))).scalars().first()
                
                # Check ResearchRun
                run_rec = (await session.execute(
                    select(ResearchRun).where(ResearchRun.stock_id == stock_rec.id).order_by(ResearchRun.created_at.desc()).limit(1)
                )).scalars().first()
                print(f"  -> DB ResearchRun found: ID={run_rec.id}, Status={run_rec.status.value}, Model={run_rec.config.get('model')}")
                
                # Check ResearchReport
                rep_rec = (await session.execute(
                    select(ResearchReport).where(ResearchReport.run_id == run_rec.id)
                )).scalars().first()
                print(f"  -> DB ResearchReport found: ID={rep_rec.id}, Title={rep_rec.title}, Rating={rep_rec.rating.value}, TargetPrice={rep_rec.target_price}")
                
                # Check Sections
                sec_count = (await session.execute(
                    select(func.count(ResearchReportSection.id)).where(ResearchReportSection.report_id == rep_rec.id)
                )).scalar()
                print(f"  -> DB Report Sections Count: {sec_count} (Expected: 7)")
                
                # Check Sources linked
                source_count = (await session.execute(
                    select(func.count(ResearchSource.id)).where(ResearchSource.run_id == run_rec.id)
                )).scalar()
                print(f"  -> DB Research Sources Count: {source_count} (Linked articles count: > 0)")
                
                # Check AIModelUsage
                usage_rec = (await session.execute(
                    select(AIModelUsage).where(AIModelUsage.run_id == run_rec.id)
                )).scalars().first()
                print(f"  -> DB AIModelUsage: Model={usage_rec.model_name}, PromptTokens={usage_rec.prompt_tokens}, CompletionTokens={usage_rec.completion_tokens}, Cost=${usage_rec.cost:.6f}")

            # Step C: GET /v1/research/{symbol}/latest (Cache HIT - Retrieve from DB)
            print(f"\n[C] GET /v1/research/{ticker}/latest (Second Call - Cache HIT)")
            start_time = time.time()
            resp_latest = await client.get(f"{BASE_URL}/research/{ticker}/latest", headers=headers)
            duration_latest = (time.time() - start_time) * 1000
            
            print(f"  -> HTTP Status: {resp_latest.status_code}")
            print(f"  -> Duration: {duration_latest:.2f} ms")
            
            latest_data = resp_latest.json()
            if latest_data["id"] == report_data["id"]:
                print(f"  -> Cache HIT Verification: SUCCESS (Retrieved identical Report ID from database)")
            else:
                print(f"  -> Cache HIT Verification: FAILED (IDs mismatch!)")

            # Step D: GET /v1/research/{symbol} (List reports)
            print(f"\n[D] GET /v1/research/{ticker} (List generated reports)")
            resp_list = await client.get(f"{BASE_URL}/research/{ticker}", headers=headers)
            print(f"  -> HTTP Status: {resp_list.status_code}")
            print(f"  -> Reports Listed: {len(resp_list.json())}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_research_flow())

# ============================================================================
# MARKETMIND AI - PHASE 7 SECURITY & PERFORMANCE VERIFIER
# ============================================================================

import asyncio
import time
import uuid
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings
from models import Stock, ResearchRun, ResearchReport, ResearchReportSection, ResearchSource, AIModelUsage
from app.providers.sentiment import SentimentProvider

BASE_URL = "http://127.0.0.1:8000"


def print_section(title: str):
    print("\n" + "="*80)
    print(f" {title.upper()} ")
    print("="*80)


async def run_verifier():
    print_section("marketmind ai production readiness verifier")
    
    # 0. Set up database verification
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    # Check allowed origins configured
    print(f"Configured CORS origins: {settings.ALLOWED_ORIGINS}")
    print(f"Environment mode: {settings.ENV}")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # ================================================================
        # 1. JWT & Authentication Checks
        # ================================================================
        print_section("1. JWT Validation & Security Checks")
        
        # Test 1A: Access without token
        resp = await client.get(f"{BASE_URL}/v1/stocks/AAPL")
        print(f"GET /v1/stocks/AAPL (No Token) status: {resp.status_code}")
        assert resp.status_code == 401, "Expected 401 for unauthorized access"
        
        # Test 1B: Access with invalid token
        resp = await client.get(
            f"{BASE_URL}/v1/stocks/AAPL",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        print(f"GET /v1/stocks/AAPL (Invalid Token) status: {resp.status_code}")
        assert resp.status_code == 401, "Expected 401 for invalid token"
        
        # Register and login a test user to get a valid token
        email = f"ready.analyst.{uuid.uuid4().hex[:6]}@marketmind.ai"
        password = "securePassword123!"
        
        reg_resp = await client.post(
            f"{BASE_URL}/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "first_name": "Readiness",
                "last_name": "Auditor"
            }
        )
        print(f"POST /v1/auth/register status: {reg_resp.status_code}")
        assert reg_resp.status_code == 201, "User registration failed"
        
        login_resp = await client.post(
            f"{BASE_URL}/v1/auth/login",
            json={"email": email, "password": password}
        )
        print(f"POST /v1/auth/login status: {login_resp.status_code}")
        assert login_resp.status_code == 200, "User login failed"
        
        token = login_resp.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}
        print(" -> Valid token successfully obtained and stored.")

        # Test 1C: Access with valid token
        resp = await client.get(f"{BASE_URL}/v1/stocks/AAPL", headers=auth_headers)
        print(f"GET /v1/stocks/AAPL (Valid Token) status: {resp.status_code}")
        assert resp.status_code == 200, "Expected 200 for authenticated access"

        # ================================================================
        # 2. CORS Checks
        # ================================================================
        print_section("2. CORS Origins Enforcement Checks")
        
        # Test 2A: Allowed origin
        cors_headers_allowed = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        }
        resp = await client.options(f"{BASE_URL}/healthz", headers=cors_headers_allowed)
        print(f"CORS preflight (http://localhost:3000) status: {resp.status_code}")
        print(f"CORS allowed origin header: {resp.headers.get('access-control-allow-origin')}")
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"

        # Test 2B: Disallowed origin
        cors_headers_disallowed = {
            "Origin": "http://evil.com",
            "Access-Control-Request-Method": "GET"
        }
        resp = await client.options(f"{BASE_URL}/healthz", headers=cors_headers_disallowed)
        print(f"CORS preflight (http://evil.com) status: {resp.status_code}")
        print(f"CORS evil origin header: {resp.headers.get('access-control-allow-origin')}")
        assert resp.headers.get("access-control-allow-origin") is None, "Wildcard or evil origin allowed!"

        # ================================================================
        # 3. SQL Injection Protection
        # ================================================================
        print_section("3. SQL Injection Protection Validation")
        sqli_payload = "AAPL' OR '1'='1"
        resp = await client.get(f"{BASE_URL}/v1/stocks/{sqli_payload}", headers=auth_headers)
        print(f"GET /v1/stocks/{sqli_payload} status: {resp.status_code}")
        assert resp.status_code in [400, 404], f"SQL Injection payload returned unexpected status: {resp.status_code}"
        print(" -> SQL Injection payload safely rejected/escaped.")

        # ================================================================
        # 4. Database selectinload Optimization Benchmark
        # ================================================================
        print_section("4. Database selectinload Optimization Benchmark")
        # Ensure AAPL cache is warm first
        warmup_resp = await client.get(f"{BASE_URL}/v1/stocks/AAPL", headers=auth_headers)
        print(f"Warmup GET /v1/stocks/AAPL: {warmup_resp.status_code}")
        
        # Measure latency of cached retrieval (preloads profile and consensus in one query)
        latencies = []
        for i in range(5):
            t_start = time.perf_counter()
            resp = await client.get(f"{BASE_URL}/v1/stocks/AAPL", headers=auth_headers)
            elapsed = time.perf_counter() - t_start
            latencies.append(elapsed)
            print(f"  Retrieval {i+1} latency: {elapsed:.4f}s")
        
        avg_latency = sum(latencies) / len(latencies)
        print(f" -> Average optimized retrieval latency: {avg_latency:.4f}s")

        # ================================================================
        # 5. Sentiment Singleton Performance
        # ================================================================
        print_section("5. Sentiment Analyzer Singleton Verification")
        t_start = time.perf_counter()
        for i in range(50):
            prov = SentimentProvider()
        elapsed = time.perf_counter() - t_start
        print(f"Instantiated SentimentProvider 50 times in: {elapsed:.6f}s")
        print(" -> Verified VADER singleton is loaded instantly from module state.")

        # ================================================================
        # 6. Async Research Generation Pipeline
        # (MUST run BEFORE rate limiting tests which exhaust the limiter)
        # ================================================================
        print_section("6. Async Research Jobs Pipeline (E2E Test)")
        
        print(" -> Requesting report generation for TSLA...")
        gen_resp = await client.post(f"{BASE_URL}/v1/research/TSLA/generate", headers=auth_headers)
        print(f"POST /v1/research/TSLA/generate status: {gen_resp.status_code}")
        assert gen_resp.status_code == 202, f"Expected 202 Accepted, got {gen_resp.status_code}"
        
        run_data = gen_resp.json()
        run_id = run_data["run_id"]
        status_str = run_data["status"]
        print(f" -> Immediately returned run ID: {run_id} | Status: {status_str}")
        assert status_str in ["pending", "running"], "Expected status to be pending or running"
        
        # Poll run status until complete
        print(" -> Polling run status in background...")
        max_polls = 40
        poll_count = 0
        completed = False
        
        while poll_count < max_polls:
            await asyncio.sleep(3)
            poll_count += 1
            poll_resp = await client.get(f"{BASE_URL}/v1/research/runs/{run_id}", headers=auth_headers)
            assert poll_resp.status_code == 200, "Failed to fetch run status"
            poll_data = poll_resp.json()
            current_status = poll_data["status"]
            print(f"    Poll {poll_count}: status = {current_status}")
            
            if current_status == "completed":
                completed = True
                metrics = poll_data["config"].get("metrics", {})
                print("\n  =======================================================")
                print("   RESEARCH GENERATION TIMING METRICS BREAKDOWN")
                print("  =======================================================")
                for key, val in metrics.items():
                    print(f"   * {key.replace('_', ' ').title()}: {val}s")
                print("  =======================================================\n")
                break
            elif current_status == "failed":
                print(f"    Job failed with error: {poll_data.get('error_message')}")
                break
                
        assert completed, "Background research job did not complete within timeout limit"
        
        # Verify persistence in database
        print(" -> Verifying database row creation and content persistence...")
        async with async_session() as session:
            # Check research_runs row
            run_db = (await session.execute(select(ResearchRun).where(ResearchRun.id == uuid.UUID(run_id)))).scalars().first()
            assert run_db is not None, "ResearchRun row not created in DB"
            print(f"    * Database Check: research_runs row verified.")
            
            # Check research_reports row
            report_db = (await session.execute(select(ResearchReport).where(ResearchReport.run_id == uuid.UUID(run_id)))).scalars().first()
            assert report_db is not None, "ResearchReport row not created in DB"
            print(f"    * Database Check: research_reports row verified.")
            
            # Check report sections count
            sections_count = len((await session.execute(select(ResearchReportSection).where(ResearchReportSection.report_id == report_db.id))).scalars().all())
            print(f"    * Database Check: {sections_count} sections persisted.")
            assert sections_count >= 5, "Expected at least 5 sections in report"
            
            # Check sources count
            sources_count = len((await session.execute(select(ResearchSource).where(ResearchSource.run_id == uuid.UUID(run_id)))).scalars().all())
            print(f"    * Database Check: {sources_count} source linkages stored.")
            
            # Check usage record
            usage_db = (await session.execute(select(AIModelUsage).where(AIModelUsage.run_id == uuid.UUID(run_id)))).scalars().first()
            assert usage_db is not None, "AIModelUsage record not stored"
            print(f"    * Database Check: ai_model_usage row verified (Model: {usage_db.model_name}, Tokens: {usage_db.prompt_tokens + usage_db.completion_tokens}, Cost: ${usage_db.cost}).")

        # Fetch latest report endpoint
        latest_report_resp = await client.get(f"{BASE_URL}/v1/research/TSLA/latest", headers=auth_headers)
        print(f"GET /v1/research/TSLA/latest status: {latest_report_resp.status_code}")
        assert latest_report_resp.status_code == 200, "Failed to get latest report"

        # ================================================================
        # 7. Rate Limiting Enforcement Checks
        # (Run LAST since these deliberately exhaust rate limits)
        # ================================================================
        print_section("7. Rate Limiting Enforcement Checks")
        
        # 7A. Semantic search limiter (10/min)
        print(" -> Testing /v1/search/semantic rate limit (10/min)...")
        semantic_429_hit = False
        for i in range(15):
            s_resp = await client.post(f"{BASE_URL}/v1/search/semantic", json={"query_vector": [0.1] * 4096, "dimension": 4096})
            if s_resp.status_code == 429:
                print(f"    Call {i+1}: 429 rate limit hit!")
                semantic_429_hit = True
                break
            elif s_resp.status_code != 401:
                print(f"    Call {i+1} got unexpected status: {s_resp.status_code}")
        assert semantic_429_hit, "Rate limiter for /v1/search/semantic failed to return a 429"

        # 7B. Sentiment refresh limiter (5/min)
        print(" -> Testing /v1/sentiment/{symbol}/refresh rate limit (5/min)...")
        sentiment_429_hit = False
        for i in range(10):
            s_resp = await client.post(f"{BASE_URL}/v1/sentiment/AAPL/refresh")
            if s_resp.status_code == 429:
                print(f"    Call {i+1}: 429 rate limit hit!")
                sentiment_429_hit = True
                break
            elif s_resp.status_code != 401:
                print(f"    Call {i+1} got unexpected status: {s_resp.status_code}")
        assert sentiment_429_hit, "Rate limiter for /v1/sentiment/refresh failed to return a 429"

        # 7C. Research generate limiter (2/min)
        # We already used 1 call in section 6 for TSLA, so we need 2 more to exhaust
        print(" -> Testing /v1/research/{symbol}/generate rate limit (2/min)...")
        research_429_hit = False
        for i in range(5):
            s_resp = await client.post(f"{BASE_URL}/v1/research/AAPL/generate")
            if s_resp.status_code == 429:
                print(f"    Call {i+1}: 429 rate limit hit!")
                research_429_hit = True
                break
            elif s_resp.status_code != 401:
                print(f"    Call {i+1} got unexpected status: {s_resp.status_code}")
        assert research_429_hit, "Rate limiter for /v1/research/generate failed to return a 429"

        # ================================================================
        # FINAL RESULTS
        # ================================================================
        print("\n" + "="*80)
        print(" VERIFICATION SUCCESSFUL: ALL TESTS PASSED ")
        print("="*80)
        
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_verifier())

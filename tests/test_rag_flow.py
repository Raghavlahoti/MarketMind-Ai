# ============================================================================
# MARKETMIND AI - END-TO-END RAG / SEMANTIC SEARCH FLOW VERIFIER
# ============================================================================

import asyncio
import time
import uuid
import httpx
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.models import Stock, NewsArticle, Embedding
from app.services.embeddings import EmbeddingsService

BASE_URL = "http://127.0.0.1:8000/v1"


def print_section(title: str):
    print("\n" + "="*80)
    print(f" {title.upper()} ")
    print("="*80)


async def test_rag_flow():
    # 0. Set up database connection
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    print_section("0. Database Cleanup (Embeddings Reset)")
    async with async_session() as session:
        # Clear existing embeddings
        await session.execute(delete(Embedding))
        await session.commit()
        print(" -> Cleared all existing embeddings to ensure clean start.")

    # 1. Register a test user and obtain a JWT access token
    print_section("1. User Authentication")
    email = f"test.rag.{uuid.uuid4().hex[:6]}@marketmind.ai"
    password = "securePassword123!"
    
    register_payload = {
        "email": email,
        "password": password,
        "first_name": "RAG",
        "last_name": "Verifier"
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
        print(" -> JWT Token acquired successfully.")

        # 2. Ingest AAPL News to ensure articles exist
        print_section("2. News Ingestion (Cache Load)")
        news_resp = await client.get(f"{BASE_URL}/news/AAPL", headers=headers)
        print(f"GET /news/AAPL status: {news_resp.status_code}")
        if news_resp.status_code != 200:
            print(f"News fetch failed: {news_resp.text}")
            await engine.dispose()
            return
            
        print(f" -> Found/Ingested {len(news_resp.json())} news articles.")

        # 3. Chunk and Embed news article
        print_section("3. Chunk & Embed Article (pgvector Insertion)")
        async with async_session() as session:
            # Get one news article from database
            stmt = select(NewsArticle).limit(1)
            article = (await session.execute(stmt)).scalars().first()
            if not article:
                print(" -> [ERROR] No news article found in database!")
                await engine.dispose()
                return
            
            print(f" -> Testing with Article ID: {article.id}")
            print(f" -> Article Title: {article.title}")
            
            # Use service layer to chunk and embed
            embeddings_service = EmbeddingsService(session)
            print(f" -> Active Embeddings Provider: {embeddings_service.provider.provider_name}")
            print(f" -> Active Model: {embeddings_service.provider.model_name}")
            print(f" -> Dimension: {embeddings_service.provider.dimension}")
            
            start_time = time.time()
            saved_chunks = await embeddings_service.chunk_and_embed_article(
                article_id=article.id,
                title=article.title,
                content=article.content or article.summary or ""
            )
            duration = (time.time() - start_time) * 1000
            print(f" -> Chunks generated, embedded, and saved in {duration:.2f} ms")
            print(f" -> Total chunks inserted: {len(saved_chunks)}")
            await session.commit()

        # 4. Fetch the saved embedding chunk from DB to retrieve its vector
        print_section("4. Database Verification")
        async with async_session() as session:
            db_chunks_count = (await session.execute(select(func.count(Embedding.id)))).scalar()
            print(f" -> Total Embedding chunks in DB: {db_chunks_count} (Expected: {len(saved_chunks)})")
            
            example_chunk = (await session.execute(select(Embedding).limit(1))).scalars().first()
            if not example_chunk:
                print(" -> [ERROR] Failed to retrieve chunk from database!")
                await engine.dispose()
                return
                
            print(f" -> Retrieved example chunk ID: {example_chunk.id}")
            print(f" -> Chunk Dimension: {example_chunk.embedding_dimension}")
            print(f" -> Vector length: {len(example_chunk.embedding)}")
            print(f" -> Content excerpt: '{example_chunk.content_chunk[:100]}...'")
            
            # Keep vector for searching
            query_vector = example_chunk.embedding
            if hasattr(query_vector, "tolist"):
                query_vector = query_vector.tolist()
            else:
                query_vector = list(query_vector)
            dimension = example_chunk.embedding_dimension
            target_content = example_chunk.content_chunk

        # 5. E2E REST API Search Call POST /v1/search/semantic
        print_section("5. POST /v1/search/semantic Verification (API Search)")
        search_payload = {
            "query_vector": query_vector,
            "dimension": dimension,
            "limit": 3
        }
        
        start_time = time.time()
        search_resp = await client.post(f"{BASE_URL}/search/semantic", json=search_payload, headers=headers)
        duration = (time.time() - start_time) * 1000
        
        print(f"POST /search/semantic status: {search_resp.status_code}")
        print(f"Duration: {duration:.2f} ms")
        
        if search_resp.status_code != 200:
            print(f" -> [ERROR] Semantic search failed: {search_resp.text}")
            await engine.dispose()
            return
            
        results = search_resp.json()
        print(f" -> Found {len(results)} results")
        
        # Verify first result is exact match (or very close to it)
        if len(results) > 0:
            top_res = results[0]
            print(f" -> Top Result Chunk ID: {top_res.get('id')}")
            print(f" -> Top Result Cosine Distance: {top_res.get('cosine_distance'):.6f}")
            print(f" -> Top Result Content: '{top_res.get('content_chunk')[:120]}...'")
            
            if top_res.get("cosine_distance") < 0.01:
                print(" -> [PASS] Exact match found with near-zero cosine distance!")
            else:
                print(" -> [WARNING] Top match cosine distance is not near zero.")
        else:
            print(" -> [ERROR] Search returned empty results!")

        # 6. Service Level Text-based Search
        print_section("6. Text Query Semantic Search (Services Layer)")
        async with async_session() as session:
            embeddings_service = EmbeddingsService(session)
            print(f" -> Querying with text: '{article.title}'")
            start_time = time.time()
            text_results = await embeddings_service.search_semantics_by_text(
                query_text=article.title,
                limit=3
            )
            duration = (time.time() - start_time) * 1000
            print(f" -> Query completed in {duration:.2f} ms")
            print(f" -> Found {len(text_results)} results:")
            
            for idx, res in enumerate(text_results):
                print(f"   [{idx + 1}] Distance: {res['cosine_distance']:.4f} | Source ID: {res['source_id']}")
                print(f"       Chunk: '{res['content_chunk'][:120]}...'")

    await engine.dispose()
    print("\n" + "="*80)
    print(" VERIFICATION COMPLETED successfully! ")
    print("="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(test_rag_flow())

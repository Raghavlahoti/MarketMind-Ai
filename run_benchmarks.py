import asyncio
import os
import time
import json
import re
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.services.stock import StockService
from app.services.news import NewsService
from app.services.sentiment import SentimentService
from app.services.prompt_builder import ResearchPromptBuilder
from app.providers.nvidia import NvidiaProvider

# Define models to test
MODELS = [
    "meta/llama-3.1-70b-instruct",
    "meta/llama-3.3-70b-instruct",
    "nvidia/llama-3.1-nemotron-70b-instruct",
    "meta/llama-3.1-8b-instruct"
]

def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    model_lower = model.lower()
    if "70b" in model_lower:
        input_rate = 0.70 / 1_000_000
        output_rate = 0.90 / 1_000_000
    elif "8b" in model_lower:
        input_rate = 0.15 / 1_000_000
        output_rate = 0.15 / 1_000_000
    else:
        # default to 70B rates
        input_rate = 0.70 / 1_000_000
        output_rate = 0.90 / 1_000_000
    return (prompt_tokens * input_rate) + (completion_tokens * output_rate)

def evaluate_citations(text: str) -> int:
    # count patterns like [1], [2], [15], etc.
    return len(re.findall(r'\[\d+\]', text))

async def test_model(provider: NvidiaProvider, model_name: str, prompts: List[Dict[str, str]]) -> Dict[str, Any]:
    print(f"\nBenchmarking model: {model_name}...")
    start_time = time.perf_counter()
    
    try:
        response = await provider.generate_chat_completion(
            messages=prompts,
            model=model_name,
            response_format={"type": "json_object"}
        )
        latency = time.perf_counter() - start_time
        
        content_str = response["content"]
        prompt_tokens = response.get("prompt_tokens", 0)
        completion_tokens = response.get("completion_tokens", 0)
        total_tokens = response.get("total_tokens", 0)
        cost = calculate_cost(model_name, prompt_tokens, completion_tokens)
        
        # Parse JSON
        is_valid_json = False
        parsed_json = {}
        try:
            parsed_json = json.loads(content_str)
            is_valid_json = True
        except Exception as je:
            print(f"JSON Parsing Error for {model_name}: {je}")
            # Try cleaning up markdown blocks if any
            cleaned = content_str.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            try:
                parsed_json = json.loads(cleaned)
                is_valid_json = True
            except Exception:
                pass
        
        # Calculate section lengths and citations
        section_lengths = {}
        total_citations = 0
        sections_to_check = [
            "executive_summary", "bull_case", "bear_case", 
            "key_risks", "financial_highlights", "sentiment_summary", 
            "investment_thesis"
        ]
        
        for sec in sections_to_check:
            sec_val = parsed_json.get(sec, "")
            if isinstance(sec_val, list):
                sec_text = " ".join(str(x) for x in sec_val)
            elif isinstance(sec_val, dict):
                sec_text = json.dumps(sec_val)
            else:
                sec_text = str(sec_val)
            section_lengths[sec] = len(sec_text)
            total_citations += evaluate_citations(sec_text)
            
        rating = parsed_json.get("rating", "N/A")
        target_price = parsed_json.get("target_price", "N/A")
        
        # Save output to a file for manual quality inspection
        safe_model_name = model_name.replace("/", "_").replace(".", "_")
        os.makedirs("benchmarks", exist_ok=True)
        with open(f"benchmarks/{safe_model_name}_report.json", "w", encoding="utf-8") as f:
            f.write(content_str)
            
        return {
            "model": model_name,
            "latency_seconds": round(latency, 2),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost": round(cost, 6),
            "is_valid_json": is_valid_json,
            "rating": rating,
            "target_price": target_price,
            "total_citations": total_citations,
            "section_lengths": section_lengths,
            "total_char_length": sum(section_lengths.values()),
            "status": "success",
            "error": None
        }
        
    except Exception as e:
        latency = time.perf_counter() - start_time
        print(f"Error benchmarking {model_name}: {e}")
        return {
            "model": model_name,
            "latency_seconds": round(latency, 2),
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cost": 0.0,
            "is_valid_json": False,
            "rating": "N/A",
            "target_price": "N/A",
            "total_citations": 0,
            "section_lengths": {},
            "total_char_length": 0,
            "status": "failed",
            "error": str(e)
        }

async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    # Load input data from DB
    async with async_session() as session:
        stock_service = StockService(session)
        news_service = NewsService(session)
        sentiment_service = SentimentService(session)
        
        stock = await stock_service.get_stock("NVDA")
        profile = await stock_service.get_profile("NVDA")
        await stock_service.get_prices("NVDA")
        latest_price_rec = await stock_service.stock_repo.get_latest_price(stock.id)
        current_price = float(latest_price_rec.close_price) if latest_price_rec else None
        
        profile_data = {
            "name": stock.name,
            "sector": stock.sector,
            "industry": stock.industry,
            "ceo": profile.ceo,
            "headquarters": profile.headquarters,
            "founded_year": profile.founded_year,
            "description": profile.description,
            "market_cap": float(profile.market_cap) if profile.market_cap is not None else None,
            "shares_outstanding": float(profile.shares_outstanding) if profile.shares_outstanding is not None else None,
            "current_price": current_price
        }
        
        fundamentals = await stock_service.get_fundamentals("NVDA")
        fundamentals_data = []
        for item in fundamentals:
            fundamentals_data.append({
                "period_type": item.period_type.value,
                "report_date": str(item.report_date),
                "revenue": float(item.revenue) if item.revenue is not None else None,
                "net_income": float(item.net_income) if item.net_income is not None else None,
                "eps": float(item.eps) if item.eps is not None else None,
                "ebitda": float(item.ebitda) if item.ebitda is not None else None,
                "assets": float(item.assets) if item.assets is not None else None,
                "liabilities": float(item.liabilities) if item.liabilities is not None else None,
                "cash_flow": float(item.cash_flow) if item.cash_flow is not None else None
            })
            
        articles = await news_service.get_news("NVDA")
        news_data = []
        for art in articles:
            news_data.append({
                "title": art.title,
                "source_name": art.source_name,
                "published_at": str(art.published_at),
                "summary": art.summary
            })
            
        sentiment_data = await sentiment_service.get_stock_sentiment("NVDA")
        
    await engine.dispose()
    
    # Build prompts
    prompts = ResearchPromptBuilder.build_prompts(
        symbol="NVDA",
        profile=profile_data,
        fundamentals=fundamentals_data,
        news=news_data,
        sentiment=sentiment_data
    )
    
    # Instantiate provider
    provider = NvidiaProvider(
        api_key=settings.NVIDIA_API_KEY,
        base_url=settings.NVIDIA_NIM_BASE_URL,
        default_model=settings.NVIDIA_LLM_MODEL
    )
    
    results = []
    for model in MODELS:
        res = await test_model(provider, model, prompts)
        results.append(res)
        
    print("\n" + "="*80)
    print(" BENCHMARK RESULTS SUMMARY ")
    print("="*80)
    print(f"{'Model':<40} | {'Latency':<8} | {'Tokens (P/C)':<15} | {'Citations':<9} | {'Cost ($)':<8} | {'Valid JSON':<10}")
    print("-"*102)
    for r in results:
        if r["status"] == "success":
            tokens_str = f"{r['prompt_tokens']}/{r['completion_tokens']}"
            print(f"{r['model']:<40} | {r['latency_seconds']:<7}s | {tokens_str:<15} | {r['total_citations']:<9} | ${r['cost']:<7.5f} | {str(r['is_valid_json']):<10}")
        else:
            print(f"{r['model']:<40} | FAILED: {r['error'][:45]}")
    print("="*80)
    
    # Save comparison metadata
    with open("benchmarks/results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())

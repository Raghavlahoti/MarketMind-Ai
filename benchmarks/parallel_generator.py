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
from app.providers.nvidia import NvidiaProvider

# Define parallel generator class
class ParallelResearchReportGenerator:
    def __init__(self, provider: NvidiaProvider):
        self.provider = provider

    async def generate_metrics(self, symbol: str, profile: Dict[str, Any], fundamentals: List[Dict[str, Any]], news: List[Dict[str, Any]], sentiment: Dict[str, Any], model: str) -> Dict[str, Any]:
        """Step 1: Rapid key metrics extraction."""
        # Simple summary profiles
        profile_summary = f"Company: {profile.get('name')}, Current Price: ${profile.get('current_price')}, Sector: {profile.get('sector')}"
        fundamentals_summary = "\n".join([f"- {f.get('period_type')} {f.get('report_date')}: Revenue={f.get('revenue')}, Net Income={f.get('net_income')}, EPS={f.get('eps')}" for f in fundamentals[:2]])
        news_titles = "\n".join([f"{idx+1}. {n.get('title')}" for idx, n in enumerate(news[:10])])
        sentiment_summary = f"Overall score: {sentiment.get('overall_score')}, label: {sentiment.get('overall_label')}"

        prompt = (
            "You are a Senior Equity Research Analyst. Based on the following stock summary, determine the investment rating (Bullish, Neutral, or Bearish), "
            "a 12-month target price as a float, and 3 brief bullet points of key investment thesis arguments.\n\n"
            f"=== STOCK PROFILE ===\n{profile_summary}\n"
            f"=== FUNDAMENTALS ===\n{fundamentals_summary}\n"
            f"=== NEWS ARTICLES ===\n{news_titles}\n"
            f"=== SENTIMENT ===\n{sentiment_summary}\n\n"
            "Return ONLY a JSON object with keys:\n"
            "{\n"
            "  \"rating\": \"Bullish\" | \"Neutral\" | \"Bearish\",\n"
            "  \"target_price\": 0.00,\n"
            "  \"key_arguments\": [\"bullet 1\", \"bullet 2\", \"bullet 3\"]\n"
            "}"
        )

        response = await self.provider.generate_chat_completion(
            messages=[
                {"role": "system", "content": "You are a financial analyst. Return raw JSON only."},
                {"role": "user", "content": prompt}
            ],
            model=model,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response["content"])

    async def generate_section(
        self, 
        section_name: str, 
        symbol: str, 
        profile_str: str, 
        fundamentals_str: str, 
        news_str: str, 
        sentiment_str: str,
        metrics: Dict[str, Any],
        model: str
    ) -> str:
        """Step 2: Generate a single section of the report."""
        section_instructions = {
            "executive_summary": (
                "Write a comprehensive executive summary of the investment findings (minimum 2-3 paragraphs). "
                "You MUST explicitly mention the current market price of the stock, reference the target price, "
                "and calculate the upside or downside percentage relative to the current market price. "
                "Integrate inline citations using brackets (e.g. [1], [2]) pointing to articles in the news list."
            ),
            "bull_case": (
                "Write a detailed bullish thesis for the stock explaining the growth drivers, competitive advantages, "
                "and market opportunities. Cite sources using brackets (e.g. [1], [2]) where appropriate."
            ),
            "bear_case": (
                "Write a detailed bearish thesis for the stock explaining key challenges, valuation risks, and "
                "threats. Cite sources using brackets (e.g. [1], [2]) where appropriate."
            ),
            "key_risks": (
                "Highlight 3-4 major operational, regulatory, or market risks for this company in detail. "
                "Cite sources using brackets (e.g. [1], [2]) where appropriate."
            ),
            "financial_highlights": (
                "Summarize key fundamental highlights, revenue growth trends, debt structure, margins, and cash flows. "
                "Use the fundamentals data provided."
            ),
            "sentiment_summary": (
                "Analyze recent news headlines and overall sentiment trends, highlighting key media events. "
                "Cite sources using brackets (e.g. [1], [2])."
            ),
            "investment_thesis": (
                "Provide a strong concluding section summarizing the overall investment thesis and rating logic, "
                "referencing the key arguments, rating, and target price."
            )
        }

        instruction = section_instructions[section_name]
        
        prompt = (
            f"You are writing the '{section_name.replace('_', ' ').title()}' section of an institutional-grade equity research report for {symbol}.\n\n"
            f"=== CORE DECISIONS ===\n"
            f"Rating: {metrics.get('rating')}\n"
            f"Target Price: ${metrics.get('target_price')}\n"
            f"Key Arguments: {metrics.get('key_arguments')}\n\n"
            f"=== STOCK DATA ===\n"
            f"=== PROFILE ===\n{profile_str}\n"
            f"=== FUNDAMENTALS ===\n{fundamentals_str}\n"
            f"=== NEWS ARTICLES ===\n{news_str}\n"
            f"=== SENTIMENT ===\n{sentiment_str}\n\n"
            f"=== INSTRUCTIONS ===\n{instruction}\n\n"
            "Return ONLY the plain text of this section. Do not include markdown headers, bullet lists (unless asked), or JSON keys. "
            "Start writing directly:"
        )

        response = await self.provider.generate_chat_completion(
            messages=[
                {"role": "system", "content": "You are a financial writer. Output only the content of the section, no headers or wrappers."},
                {"role": "user", "content": prompt}
            ],
            model=model
        )
        return response["content"].strip()

    async def generate_report_parallel(
        self,
        symbol: str,
        profile: Dict[str, Any],
        fundamentals: List[Dict[str, Any]],
        news: List[Dict[str, Any]],
        sentiment: Dict[str, Any],
        model: str
    ) -> Dict[str, Any]:
        t_start = time.perf_counter()
        
        # 1. Format inputs
        profile_str = (
            f"Company Name: {profile.get('name', 'N/A')}\n"
            f"Ticker: {symbol}\n"
            f"Sector: {profile.get('sector', 'N/A')}\n"
            f"Industry: {profile.get('industry', 'N/A')}\n"
            f"CEO: {profile.get('ceo', 'N/A')}\n"
            f"Headquarters: {profile.get('headquarters', 'N/A')}\n"
            f"Current Market Price: ${profile.get('current_price', 'N/A')}\n"
        )
        fundamentals_str = ""
        for item in fundamentals[:4]:
            fundamentals_str += (
                f"- Period: {item.get('period_type')} | Date: {item.get('report_date')}\n"
                f"  Revenue: {item.get('revenue')} | Net Income: {item.get('net_income')} | EPS: {item.get('eps')} | Debt/Equity: {item.get('debt_to_equity', 'N/A')}\n"
            )
        news_str = ""
        for idx, item in enumerate(news[:15]):
            news_str += (
                f"{idx + 1}. Title: {item.get('title')}\n"
                f"   Source: {item.get('source_name')} | Date: {item.get('published_at')}\n"
                f"   Summary: {item.get('summary')}\n"
            )
        sentiment_str = f"Score: {sentiment.get('overall_score')}, Label: {sentiment.get('overall_label')}\n"
        
        # Step 1: Generate key metrics
        print(" -> Step 1: Getting core metrics...")
        t1 = time.perf_counter()
        metrics = await self.generate_metrics(symbol, profile, fundamentals, news, sentiment, model)
        t_metrics = time.perf_counter() - t1
        print(f" -> Metrics determined in {t_metrics:.2f}s: Rating={metrics.get('rating')}, Target={metrics.get('target_price')}")
        
        # Step 2: Generate sections in parallel
        print(" -> Step 2: Generating all 7 sections in parallel...")
        t2 = time.perf_counter()
        sections_to_generate = [
            "executive_summary", "bull_case", "bear_case", 
            "key_risks", "financial_highlights", "sentiment_summary", 
            "investment_thesis"
        ]
        
        tasks = [
            self.generate_section(sec, symbol, profile_str, fundamentals_str, news_str, sentiment_str, metrics, model)
            for sec in sections_to_generate
        ]
        
        section_results = await asyncio.gather(*tasks)
        t_sections = time.perf_counter() - t2
        print(f" -> All sections completed in {t_sections:.2f}s")
        
        total_time = time.perf_counter() - t_start
        
        report = {
            "title": f"Equity Research Report: {profile.get('name')} ({symbol})",
            "rating": metrics.get("rating"),
            "target_price": metrics.get("target_price"),
            "executive_summary": section_results[0],
            "bull_case": section_results[1],
            "bear_case": section_results[2],
            "key_risks": section_results[3],
            "financial_highlights": section_results[4],
            "sentiment_summary": section_results[5],
            "investment_thesis": section_results[6],
            "total_time_seconds": total_time,
            "metrics_seconds": t_metrics,
            "sections_seconds": t_sections
        }
        return report

async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    # Load input data
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
    
    provider = NvidiaProvider(
        api_key=settings.NVIDIA_API_KEY,
        base_url=settings.NVIDIA_NIM_BASE_URL,
        default_model=settings.NVIDIA_LLM_MODEL
    )
    
    generator = ParallelResearchReportGenerator(provider)
    
    # We will test parallel generation using llama-3.1-70b-instruct!
    model_name = "meta/llama-3.1-70b-instruct"
    print(f"Testing parallel generation on {model_name}...")
    report = await generator.generate_report_parallel(
        symbol="NVDA",
        profile=profile_data,
        fundamentals=fundamentals_data,
        news=news_data,
        sentiment=sentiment_data,
        model=model_name
    )
    
    print("\n" + "="*80)
    print(" PARALLEL REPORT COMPLETED ")
    print("="*80)
    print(f"Total time: {report['total_time_seconds']:.2f} seconds")
    print(f"Step 1 time: {report['metrics_seconds']:.2f} seconds")
    print(f"Step 2 time: {report['sections_seconds']:.2f} seconds")
    print(f"Rating: {report['rating']}, Target Price: ${report['target_price']}")
    
    # Save the output
    with open("benchmarks/parallel_llama33_70b_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())

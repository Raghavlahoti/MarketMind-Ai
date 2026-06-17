# ============================================================================
# MARKETMIND AI - RESEARCH DATA COLLECTION BENCHMARK
# ============================================================================

import asyncio
import time
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.services.stock import StockService
from app.services.news import NewsService
from app.services.sentiment import SentimentService
from app.core.database import async_session_factory

async def run_sequential_collection(symbol: str):
    t0 = time.perf_counter()
    async with async_session_factory() as session:
        stock_service = StockService(session)
        news_service = NewsService(session)
        sentiment_service = SentimentService(session)
        
        # 1. Stock Profile and prices
        stock = await stock_service.get_stock(symbol)
        profile = await stock_service.get_profile(stock.ticker)
        await stock_service.get_prices(stock.ticker)
        latest_price_rec = await stock_service.stock_repo.get_latest_price(stock.id)
        current_price = float(latest_price_rec.close_price) if latest_price_rec else None
        
        # 2. Fundamentals
        fundamentals = await stock_service.get_fundamentals(stock.ticker)
        
        # 3. News
        articles = await news_service.get_news(stock.ticker)
        
        # 4. Sentiment
        sentiment_data = await sentiment_service.get_stock_sentiment(stock.ticker)
        
    duration = time.perf_counter() - t0
    return duration, profile, current_price, fundamentals, articles, sentiment_data

async def run_parallel_collection(symbol: str):
    t0 = time.perf_counter()
    
    # We resolve stock first as both tasks need the stock ID
    async with async_session_factory() as session:
        stock_service = StockService(session)
        stock = await stock_service.get_stock(symbol)
        stock_id = stock.id
        ticker = stock.ticker
        stock_name = stock.name
        stock_sector = stock.sector
        stock_industry = stock.industry

    # Concurrently load
    async def get_profile_and_price_task():
        async with async_session_factory() as local_session:
            local_stock_service = StockService(local_session)
            local_profile = await local_stock_service.get_profile(ticker)
            await local_stock_service.get_prices(ticker)
            local_latest_price = await local_stock_service.stock_repo.get_latest_price(stock_id)
            local_current_price = float(local_latest_price.close_price) if local_latest_price else None
            return {
                "ceo": local_profile.ceo,
                "headquarters": local_profile.headquarters,
                "founded_year": local_profile.founded_year,
                "description": local_profile.description,
                "market_cap": float(local_profile.market_cap) if local_profile.market_cap is not None else None,
                "shares_outstanding": float(local_profile.shares_outstanding) if local_profile.shares_outstanding is not None else None,
                "current_price": local_current_price
            }

    async def get_fundamentals_task():
        async with async_session_factory() as local_session:
            local_stock_service = StockService(local_session)
            local_fundamentals = await local_stock_service.get_fundamentals(ticker)
            return local_fundamentals

    async def get_news_task():
        async with async_session_factory() as local_session:
            local_news_service = NewsService(local_session)
            return await local_news_service.get_news(ticker)

    async def get_sentiment_task():
        async with async_session_factory() as local_session:
            local_sentiment_service = SentimentService(local_session)
            return await local_sentiment_service.get_stock_sentiment(ticker)

    (
        profile_details,
        fundamentals,
        articles,
        sentiment_data
    ) = await asyncio.gather(
        get_profile_and_price_task(),
        get_fundamentals_task(),
        get_news_task(),
        get_sentiment_task()
    )

    profile_data = {
        "name": stock_name,
        "sector": stock_sector,
        "industry": stock_industry,
        **profile_details
    }
    
    duration = time.perf_counter() - t0
    return duration, profile_data, fundamentals, articles, sentiment_data

async def main():
    symbol = "NVDA"
    print(f"Warm up cache for {symbol}...")
    # Warm up caches
    await run_sequential_collection(symbol)
    
    print("\nStarting sequential collection benchmark...")
    seq_time, _, _, _, _, _ = await run_sequential_collection(symbol)
    print(f"Sequential Duration: {seq_time:.4f} seconds")

    print("\nStarting parallel collection benchmark...")
    par_time, _, _, _, _ = await run_parallel_collection(symbol)
    print(f"Parallel Duration: {par_time:.4f} seconds")

    speedup = seq_time / par_time
    improvement = (1 - (par_time / seq_time)) * 100
    
    print("\n" + "="*50)
    print(" BENCHMARK RESULTS ")
    print("="*50)
    print(f"Sequential Data Collection: {seq_time*1000:.2f} ms")
    print(f"Parallel Data Collection:   {par_time*1000:.2f} ms")
    print(f"Speedup Factor:             {speedup:.2f}x")
    print(f"Latency Reduction:          {improvement:.1f}%")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.services.stock import StockService
from app.services.news import NewsService
from app.services.sentiment import SentimentService

async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        stock_service = StockService(session)
        news_service = NewsService(session)
        sentiment_service = SentimentService(session)
        
        try:
            stock = await stock_service.get_stock("NVDA")
            print("Stock found:", stock.ticker, stock.name)
            
            profile = await stock_service.get_profile("NVDA")
            print("Profile found:", profile.ceo, profile.headquarters)
            
            fundamentals = await stock_service.get_fundamentals("NVDA")
            print(f"Fundamentals found: {len(fundamentals)} records")
            
            news = await news_service.get_news("NVDA")
            print(f"News articles found: {len(news)} records")
            
            sentiment = await sentiment_service.get_stock_sentiment("NVDA")
            print(f"Sentiment found: overall score = {sentiment.get('overall_score')}")
        except Exception as e:
            print("Error checking/ingesting data:", e)
            print("Trying to ingest data directly...")
            try:
                # This will auto-create and ingest
                stock = await stock_service.get_stock("NVDA")
                await stock_service.get_profile("NVDA")
                await stock_service.get_prices("NVDA")
                await stock_service.get_fundamentals("NVDA")
                await news_service.get_news("NVDA")
                await sentiment_service.get_stock_sentiment("NVDA")
                print("NVDA data ingested successfully!")
            except Exception as ex:
                print("Failed to ingest NVDA data:", ex)
                
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())

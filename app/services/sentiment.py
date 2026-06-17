# ============================================================================
# MARKETMIND AI - SENTIMENT SERVICE LAYER
# ============================================================================

import logging
from typing import Dict, Any, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Stock, Sentiment, NewsArticle, SourceTypeEnum, SentimentLabelEnum
from app.providers.sentiment import SentimentProvider
from app.repositories.sentiment import SentimentRepository
from app.repositories.news import NewsRepository
from app.services.stock import StockService
from app.services.base import BaseService

logger = logging.getLogger("marketmind_ai")


class SentimentService(BaseService):
    """Orchestrates sentiment analysis execution, caching, aggregation, and database persistence."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.sentiment_repo = SentimentRepository(session)
        self.news_repo = NewsRepository(session)
        self.sentiment_provider = SentimentProvider()

    async def get_stock_sentiment(self, symbol: str) -> Dict[str, Any]:
        """Fetches sentiment records for stock news articles, analyzing missing ones and caching them."""
        # 1. Resolve stock record
        stock_service = StockService(self.session)
        stock = await stock_service.get_stock(symbol)

        # 2. Get all stored news articles for this stock
        articles = await self.news_repo.get_by_stock_id(stock.id)
        if not articles:
            return {
                "symbol": stock.ticker,
                "overall_score": 0.0,
                "overall_label": "neutral",
                "article_count": 0,
                "articles": []
            }

        article_ids = [art.id for art in articles]

        # 3. Batch query existing cached sentiments from DB
        cached_sentiments = await self.sentiment_repo.get_by_sources(
            SourceTypeEnum.news_article,
            article_ids
        )
        cached_map = {sent.source_id: sent for sent in cached_sentiments}

        # 4. Identify missing articles and generate sentiment
        to_create = []
        for art in articles:
            if art.id not in cached_map:
                # Generate sentiment for this article
                text_content = f"{art.title}. {art.summary or ''}. {art.content or ''}"
                analysis = self.sentiment_provider.analyze_text(text_content)
                
                new_sent = Sentiment(
                    stock_id=stock.id,
                    source_type=SourceTypeEnum.news_article,
                    source_id=art.id,
                    sentiment_score=analysis["score"],
                    sentiment_label=SentimentLabelEnum(analysis["label"]),
                    explanation=analysis["explanation"],
                    confidence_score=analysis["confidence_score"]
                )
                self.session.add(new_sent)
                to_create.append(new_sent)

        if to_create:
            await self.session.flush()
            # Combine newly created sentiments with already cached ones
            cached_sentiments.extend(to_create)
            cached_map = {sent.source_id: sent for sent in cached_sentiments}

        # 5. Build detailed response mapping back to article info
        article_details = []
        total_score = 0.0
        
        for art in articles:
            sent = cached_map.get(art.id)
            if sent:
                total_score += float(sent.sentiment_score)
                article_details.append({
                    "article_id": art.id,
                    "title": art.title,
                    "url": art.url,
                    "published_at": art.published_at,
                    "sentiment_score": float(sent.sentiment_score),
                    "sentiment_label": sent.sentiment_label.value,
                    "explanation": sent.explanation,
                    "confidence_score": float(sent.confidence_score) if sent.confidence_score is not None else None
                })

        overall_score = total_score / len(articles) if articles else 0.0
        
        if overall_score >= 0.05:
            overall_label = "positive"
        elif overall_score <= -0.05:
            overall_label = "negative"
        else:
            overall_label = "neutral"

        return {
            "symbol": stock.ticker,
            "overall_score": round(overall_score, 3),
            "overall_label": overall_label,
            "article_count": len(articles),
            "articles": article_details
        }

    async def refresh_stock_sentiment(self, symbol: str) -> Dict[str, Any]:
        """Clears existing sentiment cache for the stock's news and recalculates them from scratch."""
        # 1. Resolve stock record
        stock_service = StockService(self.session)
        stock = await stock_service.get_stock(symbol)

        # 2. Delete existing sentiments of source_type 'news_article'
        await self.sentiment_repo.delete_by_stock_id(stock.id, SourceTypeEnum.news_article)

        # 3. Call get_stock_sentiment to perform clean generation and caching
        return await self.get_stock_sentiment(stock.ticker)

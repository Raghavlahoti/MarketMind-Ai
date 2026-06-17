# ============================================================================
# MARKETMIND AI - NEWS DATABASE REPOSITORY
# ============================================================================

import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Stock, NewsArticle, news_article_stocks
from app.repositories.base import BaseRepository


class NewsRepository(BaseRepository[NewsArticle]):
    """SQLAlchemy 2.0 concrete implementation of news ingestion and retrieval."""

    def __init__(self, session: AsyncSession):
        super().__init__(NewsArticle, session)

    async def get_by_stock_id(self, stock_id: UUID, limit: int = 50, offset: int = 0) -> List[NewsArticle]:
        """Fetches news articles associated with a stock ticker, ordered chronologically."""
        query = (
            select(NewsArticle)
            .join(NewsArticle.stocks)
            .where(Stock.id == stock_id)
            .order_by(NewsArticle.published_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_by_stock_id(self, stock_id: UUID) -> int:
        """Counts total news articles associated with a stock ticker."""
        query = (
            select(func.count(NewsArticle.id))
            .join(NewsArticle.stocks)
            .where(Stock.id == stock_id)
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_by_url(self, url: str) -> Optional[NewsArticle]:
        """Queries for a single news article by its unique source URL."""
        query = select(NewsArticle).where(NewsArticle.url == url)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def upsert_articles(self, stock_id: UUID, articles_data: List[Dict[str, Any]]) -> List[NewsArticle]:
        """Upserts news articles and links them to the specified stock ID using optimized batch operations."""
        if not articles_data:
            return []

        # 1. Deduplicate input by URL and filter empty URLs
        unique_input = {}
        for data in articles_data:
            url = data.get("url")
            if url:
                unique_input[url] = data

        urls = list(unique_input.keys())
        if not urls:
            return []

        # 2. Query all existing articles by URL in one batch
        existing_articles_query = select(NewsArticle).where(NewsArticle.url.in_(urls))
        res = await self.session.execute(existing_articles_query)
        existing_articles = res.scalars().all()
        existing_map = {art.url: art for art in existing_articles}

        persisted_articles = []
        new_articles = []

        # 3. Separate into updates and new inserts
        for url, data in unique_input.items():
            if url in existing_map:
                art = existing_map[url]
                # Update existing
                art.title = data["title"]
                art.content = data["content"]
                art.summary = data.get("summary")
                art.source_name = data.get("source_name")
                art.published_at = data["published_at"]
                art.metadata_ = data.get("metadata", {})
                persisted_articles.append(art)
            else:
                # Create new
                art = NewsArticle(
                    title=data["title"],
                    content=data["content"],
                    summary=data.get("summary"),
                    source_name=data.get("source_name"),
                    url=url,
                    published_at=data["published_at"],
                    metadata_=data.get("metadata", {}),
                )
                self.session.add(art)
                new_articles.append(art)

        # Flush once to persist new articles and get their IDs, and save updates
        if new_articles or existing_map:
            await self.session.flush()
        
        # Add new articles to the persisted list
        persisted_articles.extend(new_articles)

        # 4. Batch query existing stock-article associations
        all_article_ids = [art.id for art in persisted_articles]
        link_query = select(news_article_stocks.c.article_id).where(
            news_article_stocks.c.stock_id == stock_id,
            news_article_stocks.c.article_id.in_(all_article_ids)
        )
        link_res = await self.session.execute(link_query)
        existing_links = set(link_res.scalars().all())

        # 5. Insert missing links in bulk
        links_to_insert = []
        for art in persisted_articles:
            if art.id not in existing_links:
                links_to_insert.append({
                    "article_id": art.id,
                    "stock_id": stock_id
                })

        if links_to_insert:
            stmt = news_article_stocks.insert().values(links_to_insert)
            await self.session.execute(stmt)
            await self.session.flush()

        return persisted_articles

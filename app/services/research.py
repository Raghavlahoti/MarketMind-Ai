# ============================================================================
# MARKETMIND AI - RESEARCH SERVICE LAYER
# ============================================================================

import json
import logging
import datetime
import time
from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models import (
    Stock, ResearchRun, ResearchReport, ResearchReportSection,
    ResearchSource, AIModelUsage, RunStatusEnum, ReportStatusEnum,
    RatingTypeEnum, ReportSectionTypeEnum, SourceTypeEnum
)
from app.providers.nvidia import NvidiaProvider
from app.services.prompt_builder import ResearchPromptBuilder
from app.repositories.research import ResearchRepository
from app.services.stock import StockService
from app.services.news import NewsService
from app.services.sentiment import SentimentService
from app.services.base import BaseService
from app.core.redis import RedisCache, KEY_PREFIX_REPORT, KEY_LOCK_RESEARCH, redis_manager
from app.core.database import async_session_factory

logger = logging.getLogger("marketmind_ai")


class ResearchServiceInterface(BaseService):
    """Interface outlining orchestration of AI Research and Report Generation."""

    async def initiate_research_run(self, user_id: UUID, stock_id: UUID, run_config: Dict[str, Any]) -> UUID:
        raise NotImplementedError

    async def fetch_completed_report(self, report_id: UUID) -> Dict[str, Any]:
        raise NotImplementedError


class ResearchEngineService(BaseService):
    """Orchestrates AI Research Run, retrieves news/sentiment/fundamentals, generates reports via NVIDIA NIM, and persists results."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.research_repo = ResearchRepository(session)
        
        # Instantiate NvidiaProvider using configurations
        self.nvidia_provider = NvidiaProvider(
            api_key=settings.NVIDIA_API_KEY,
            base_url=settings.NVIDIA_NIM_BASE_URL,
            default_model=settings.NVIDIA_LLM_MODEL
        )

    async def generate_research_report(self, user_id: UUID, symbol: str, run_id: Optional[UUID] = None) -> ResearchReport:
        """Triggers E2E research report generation and saves all run context and reports in database."""
        
        # 1. Resolve stock record
        stock_service = StockService(self.session)
        stock = await stock_service.get_stock(symbol)

        # Check if research lock exists for this stock
        lock_key = f"{KEY_LOCK_RESEARCH}{symbol.upper().strip()}"
        
        # Try to acquire lock, degrade gracefully on Redis error
        try:
            client = await redis_manager.get_client()
            acquired = await client.set(lock_key, str(run_id or "locked"), nx=True, ex=settings.RESEARCH_LOCK_TTL_SECONDS)
        except Exception as lock_err:
            logger.error("Failed to acquire distributed lock for %s due to Redis error, proceeding without lock: %s", symbol, lock_err)
            acquired = True
        
        if not acquired:
            logger.info("Distributed research lock held for ticker %s. A generation is already in progress.", symbol)
            # Find the active run in database
            from sqlalchemy import select
            query = select(ResearchRun).where(
                ResearchRun.stock_id == stock.id,
                ResearchRun.status.in_([RunStatusEnum.pending, RunStatusEnum.running])
            ).order_by(ResearchRun.created_at.desc())
            
            res = await self.session.execute(query)
            active_run = res.scalars().first()
            
            # If we were given a duplicate run_id, mark it failed to prevent it from getting stuck
            if run_id and active_run and run_id != active_run.id:
                try:
                    async with async_session_factory() as err_session:
                        async with err_session.begin():
                            err_repo = ResearchRepository(err_session)
                            duplicate_run = await err_repo.get_run(run_id)
                            if duplicate_run:
                                duplicate_run.status = RunStatusEnum.failed
                                duplicate_run.error_message = f"Duplicate request ignored. Generation already in progress under run {active_run.id}."
                                duplicate_run.completed_at = datetime.datetime.now(datetime.timezone.utc)
                except Exception as err:
                    logger.error("Failed to mark duplicate run %s as failed: %s", run_id, err)
            
            raise ValueError(f"Research generation already in progress for ticker {symbol} (Run ID: {active_run.id if active_run else 'unknown'})")

        if run_id:
            # Retrieve the existing run
            run = await self.research_repo.get_run(run_id)
            if not run:
                raise ValueError(f"Research run {run_id} not found")
            run.status = RunStatusEnum.running
            await self.session.commit()
        else:
            # Create research run history in database (RUNNING status)
            run = ResearchRun(
                user_id=user_id,
                stock_id=stock.id,
                trigger_type="manual",
                status=RunStatusEnum.running,
                config={"model": settings.NVIDIA_LLM_MODEL}
            )
            await self.research_repo.create_run(run)
            await self.session.commit()  # Commit run creation so we have a persistent record
        
        run_uuid = run.id
        stock_uuid = stock.id
        stock_ticker = stock.ticker
        stock_name = stock.name
        stock_sector = stock.sector
        stock_industry = stock.industry

        # Close the primary session to release its connection during Phase B (long-running network API call)
        await self.session.close()

        try:
            # 2. Gather inputs concurrently: Company Profile, Fundamentals, News, Sentiment
            # Start timer for Data Collection
            t_collection_start = time.perf_counter()

            import asyncio

            async def get_profile_and_price_task():
                async with async_session_factory() as local_session:
                    local_stock_service = StockService(local_session)
                    local_profile = await local_stock_service.get_profile(stock_ticker)
                    # Fetch prices to ensure standard daily prices are updated and cached
                    await local_stock_service.get_prices(stock_ticker)
                    local_latest_price = await local_stock_service.stock_repo.get_latest_price(stock_uuid)
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
                    local_fundamentals = await local_stock_service.get_fundamentals(stock_ticker)
                    return [
                        {
                            "period_type": item.period_type.value,
                            "report_date": str(item.report_date),
                            "revenue": float(item.revenue) if item.revenue is not None else None,
                            "net_income": float(item.net_income) if item.net_income is not None else None,
                            "eps": float(item.eps) if item.eps is not None else None,
                            "ebitda": float(item.ebitda) if item.ebitda is not None else None,
                            "assets": float(item.assets) if item.assets is not None else None,
                            "liabilities": float(item.liabilities) if item.liabilities is not None else None,
                            "cash_flow": float(item.cash_flow) if item.cash_flow is not None else None
                        }
                        for item in local_fundamentals
                    ]

            async def get_news_task():
                async with async_session_factory() as local_session:
                    local_news_service = NewsService(local_session)
                    local_articles = await local_news_service.get_news(stock_ticker)
                    return [
                        {
                            "id": art.id,
                            "title": art.title,
                            "source_name": art.source_name,
                            "published_at": str(art.published_at),
                            "summary": art.summary
                        }
                        for art in local_articles
                    ]

            async def get_sentiment_task():
                async with async_session_factory() as local_session:
                    local_sentiment_service = SentimentService(local_session)
                    return await local_sentiment_service.get_stock_sentiment(stock_ticker)

            # Gather data concurrently using asyncio.gather with return_exceptions=True
            results = await asyncio.gather(
                get_profile_and_price_task(),
                get_fundamentals_task(),
                get_news_task(),
                get_sentiment_task(),
                return_exceptions=True
            )

            failed_sources = []
            
            # 1. Profile and Price Task
            if isinstance(results[0], Exception):
                logger.error("Failed to gather profile and price: %s", results[0])
                failed_sources.append("profile_and_price")
                local_profile_data = {
                    "ceo": None,
                    "headquarters": None,
                    "founded_year": None,
                    "description": "Company profile ingestion failed. Showing metadata from registry.",
                    "market_cap": None,
                    "shares_outstanding": None,
                    "current_price": None
                }
            else:
                local_profile_data = results[0]

            # 2. Fundamentals Task
            if isinstance(results[1], Exception):
                logger.error("Failed to gather fundamentals: %s", results[1])
                failed_sources.append("fundamentals")
                fundamentals_data = []
            else:
                fundamentals_data = results[1]

            # 3. News Task
            if isinstance(results[2], Exception):
                logger.error("Failed to gather news: %s", results[2])
                failed_sources.append("news")
                news_data = []
            else:
                news_data = results[2]

            # 4. Sentiment Task
            if isinstance(results[3], Exception):
                logger.error("Failed to gather sentiment: %s", results[3])
                failed_sources.append("sentiment")
                sentiment_data = {"overall_sentiment": 0.0, "label": "neutral", "explanation": "Sentiment analysis failed."}
            else:
                sentiment_data = results[3]

            profile_data = {
                "name": stock_name,
                "sector": stock_sector,
                "industry": stock_industry,
                **local_profile_data
            }

            t_data_collection = time.perf_counter() - t_collection_start

            # 3. Construct prompts using PromptBuilder
            t_prompt_start = time.perf_counter()
            prompts = ResearchPromptBuilder.build_prompts(
                symbol=stock_ticker,
                profile=profile_data,
                fundamentals=fundamentals_data,
                news=news_data,
                sentiment=sentiment_data
            )
            t_prompt_building = time.perf_counter() - t_prompt_start

            # 4. Generate report via NvidiaProvider
            t_inference_start = time.perf_counter()
            response = await self.nvidia_provider.generate_chat_completion(
                messages=prompts,
                response_format={"type": "json_object"}
            )
            t_inference = time.perf_counter() - t_inference_start

            # 5. Persist ResearchReport & Sections
            t_persistence_start = time.perf_counter()
            
            # Parse JSON content from output
            content_str = response["content"]
            report_json = json.loads(content_str)

            # Map the string rating to RatingTypeEnum
            rating_str = report_json.get("rating", "Neutral").lower()
            if "bull" in rating_str:
                rating = RatingTypeEnum.buy
            elif "bear" in rating_str:
                rating = RatingTypeEnum.sell
            else:
                rating = RatingTypeEnum.hold

            target_price = report_json.get("target_price")
            if target_price is not None:
                try:
                    target_price = float(target_price)
                except ValueError:
                    target_price = None

            # Persist ResearchReport
            summary_content = report_json.get("executive_summary", "No summary provided.")
            if isinstance(summary_content, list):
                summary_content = "\n\n".join(str(item) for item in summary_content)
            elif not isinstance(summary_content, str):
                summary_content = str(summary_content)

            # Calculate metrics
            t_persistence = time.perf_counter() - t_persistence_start
            total_time = t_data_collection + t_prompt_building + t_inference + t_persistence
            metrics = {
                "data_collection_seconds": round(t_data_collection, 4),
                "prompt_building_seconds": round(t_prompt_building, 4),
                "nvidia_inference_seconds": round(t_inference, 4),
                "db_persistence_seconds": round(t_persistence, 4),
                "total_execution_seconds": round(total_time, 4),
                "failed_sources": failed_sources
            }

            # Phase C: Single atomic database transaction using async with session.begin()
            # This locks down transaction boundaries and ensures rollback on failure
            async with async_session_factory() as write_session:
                async with write_session.begin():
                    write_repo = ResearchRepository(write_session)
                    
                    report = ResearchReport(
                        user_id=user_id,
                        stock_id=stock_uuid,
                        run_id=run_uuid,
                        title=report_json.get("title", f"Equity Research Report: {stock_ticker}"),
                        summary=summary_content,
                        target_price=target_price,
                        rating=rating,
                        status=ReportStatusEnum.completed
                    )
                    await write_repo.save_report(report)
                    report_id = report.id

                    # Persist Report Sections
                    sections_map = {
                        ReportSectionTypeEnum.EXECUTIVE_SUMMARY: report_json.get("executive_summary"),
                        ReportSectionTypeEnum.BULL_CASE: report_json.get("bull_case"),
                        ReportSectionTypeEnum.BEAR_CASE: report_json.get("bear_case"),
                        ReportSectionTypeEnum.RISKS: report_json.get("key_risks"),
                        ReportSectionTypeEnum.VALUATION: report_json.get("financial_highlights"),
                        ReportSectionTypeEnum.SENTIMENT_ANALYSIS: report_json.get("sentiment_summary"),
                        ReportSectionTypeEnum.INVESTMENT_THESIS: report_json.get("investment_thesis")
                    }

                    sections_to_save = []
                    for sec_type, sec_content in sections_map.items():
                        if sec_content:
                            if isinstance(sec_content, list):
                                formatted_content = "\n".join(f"- {str(item)}" for item in sec_content)
                            elif isinstance(sec_content, dict):
                                formatted_content = json.dumps(sec_content, indent=2)
                            else:
                                formatted_content = str(sec_content)

                            sections_to_save.append(ResearchReportSection(
                                report_id=report_id,
                                section_type=sec_type,
                                content=formatted_content
                            ))
                    await write_repo.save_sections_bulk(sections_to_save)

                    # Save Research Sources (link news articles used in this run)
                    sources_to_save = []
                    for art in news_data:
                        sources_to_save.append(ResearchSource(
                            run_id=run_uuid,
                            source_type=SourceTypeEnum.news_article,
                            source_id=art["id"]
                        ))
                    await write_repo.create_sources_bulk(sources_to_save)

                    # Save AIModelUsage record
                    prompt_tokens = response.get("prompt_tokens", 0)
                    completion_tokens = response.get("completion_tokens", 0)
                    cost = self._calculate_usage_cost(
                        model=response["model"],
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens
                    )

                    usage = AIModelUsage(
                        run_id=run_uuid,
                        user_id=user_id,
                        model_name=response["model"],
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        cost=cost,
                        action_performed="report_generation"
                    )
                    await write_repo.create_model_usage(usage)

                    # Update run to COMPLETED
                    local_run = await write_repo.get_run(run_uuid)
                    if local_run:
                        local_run.status = RunStatusEnum.completed
                        local_run.completed_at = datetime.datetime.now(datetime.timezone.utc)
                        local_run.config = {**(local_run.config or {}), "metrics": metrics}

            # Invalidate cache for this symbol
            await RedisCache.delete(f"{KEY_PREFIX_REPORT}{stock_ticker.upper()}")

            # Release lock
            try:
                lock_key = f"{KEY_LOCK_RESEARCH}{stock_ticker.upper()}"
                client = await redis_manager.get_client()
                await client.delete(lock_key)
            except Exception as lock_err:
                logger.error("Failed to release lock on success for %s: %s", stock_ticker, lock_err)

            # Retrieve report preloaded with sections using a clean session context
            async with async_session_factory() as read_session:
                read_repo = ResearchRepository(read_session)
                return await read_repo.get_report_with_sections(report_id)

        except Exception as e:
            logger.error("Exception during E2E research generation: %s", e)
            
            # Release lock on failure
            try:
                lock_key = f"{KEY_LOCK_RESEARCH}{symbol.upper().strip()}"
                client = await redis_manager.get_client()
                await client.delete(lock_key)
            except Exception as lock_err:
                logger.error("Failed to release lock on failure for %s: %s", symbol, lock_err)
                
            # Recovery Path: Mark the run status as failed using a clean recovery session context
            try:
                async with async_session_factory() as err_session:
                    async with err_session.begin():
                        err_repo = ResearchRepository(err_session)
                        local_run = await err_repo.get_run(run_uuid)
                        if local_run:
                            local_run.status = RunStatusEnum.failed
                            local_run.error_message = str(e)[:500]
                            local_run.completed_at = datetime.datetime.now(datetime.timezone.utc)
            except Exception as inner_err:
                logger.error("Failed to persist failed status update for run %s: %s", run_uuid, inner_err)
            raise e

    async def reconcile_dangling_runs(self) -> int:
        """Scans the database for research runs stuck in 'pending' or 'running' status for longer than the timeout threshold, and transitions them to 'failed'."""
        import datetime
        from sqlalchemy import select, or_, and_
        
        # Calculate timeout cutoff
        cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=settings.RESEARCH_RUN_TIMEOUT_SECONDS)
        
        # In SQLite, dates are saved as naive strings in some configs. Let's make sure we query correctly
        # Query dangling runs
        query = select(ResearchRun).where(
            and_(
                ResearchRun.status.in_([RunStatusEnum.pending, RunStatusEnum.running]),
                ResearchRun.started_at < cutoff
            )
        )
        
        res = await self.session.execute(query)
        dangling_runs = res.scalars().all()
        
        count = len(dangling_runs)
        if count > 0:
            logger.info("Sweeper found %d dangling research runs to reconcile", count)
            for run in dangling_runs:
                run.status = RunStatusEnum.failed
                run.error_message = f"Stale task marked failed by sweeper (exceeded timeout threshold of {settings.RESEARCH_RUN_TIMEOUT_SECONDS}s)"
                run.completed_at = datetime.datetime.now(datetime.timezone.utc)
            await self.session.commit()
            
        return count

    async def get_latest_report(self, symbol: str) -> Optional[ResearchReport]:
        """Fetches the latest completed research report for a stock symbol, pre-loading sections."""
        symbol = symbol.upper().strip()
        cache_key = f"{KEY_PREFIX_REPORT}{symbol}"
        
        cached_data = await RedisCache.get(cache_key)
        if cached_data:
            sections_data = cached_data.pop("sections", [])
            
            # Reconstruct model instances
            if "created_at" in cached_data and isinstance(cached_data["created_at"], str):
                cached_data["created_at"] = datetime.datetime.fromisoformat(cached_data["created_at"])
            if "updated_at" in cached_data and isinstance(cached_data["updated_at"], str):
                cached_data["updated_at"] = datetime.datetime.fromisoformat(cached_data["updated_at"])
            if "rating" in cached_data and cached_data["rating"]:
                cached_data["rating"] = RatingTypeEnum(cached_data["rating"])
            if "status" in cached_data and cached_data["status"]:
                cached_data["status"] = ReportStatusEnum(cached_data["status"])
                
            report = ResearchReport(**cached_data)
            
            sections = []
            for sec in sections_data:
                if "created_at" in sec and isinstance(sec["created_at"], str):
                    sec["created_at"] = datetime.datetime.fromisoformat(sec["created_at"])
                if "section_type" in sec and sec["section_type"]:
                    sec["section_type"] = ReportSectionTypeEnum(sec["section_type"])
                sections.append(ResearchReportSection(**sec))
                
            report.sections = sections
            return report

        stock_service = StockService(self.session)
        stock = await stock_service.get_stock(symbol)
        report = await self.research_repo.get_latest_report_for_stock(stock.id)
        
        if report:
            # Serialize report with its sections
            serializable = {
                "id": str(report.id),
                "user_id": str(report.user_id) if report.user_id else None,
                "stock_id": str(report.stock_id),
                "run_id": str(report.run_id) if report.run_id else None,
                "title": report.title,
                "summary": report.summary,
                "target_price": float(report.target_price) if report.target_price is not None else None,
                "rating": report.rating.value if report.rating else None,
                "status": report.status.value if report.status else None,
                "created_at": report.created_at.isoformat() if report.created_at else None,
                "updated_at": report.updated_at.isoformat() if report.updated_at else None,
                "sections": [
                    {
                        "id": str(sec.id),
                        "report_id": str(sec.report_id),
                        "section_type": sec.section_type.value if sec.section_type else None,
                        "content": sec.content,
                        "created_at": sec.created_at.isoformat() if sec.created_at else None
                    }
                    for sec in report.sections
                ]
            }
            await RedisCache.set(cache_key, serializable, settings.REDIS_CACHE_TTL_REPORTS)
            
        return report

    async def get_reports_list(self, symbol: str, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """Fetches list of all generated reports for a stock symbol."""
        stock_service = StockService(self.session)
        stock = await stock_service.get_stock(symbol)
        total = await self.research_repo.count_reports_for_stock(stock.id)
        reports = await self.research_repo.get_reports_for_stock(stock.id, limit=limit, offset=offset)
        return {
            "items": reports,
            "total": total,
            "limit": limit,
            "offset": offset
        }

    def _calculate_usage_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimates NVIDIA NIM usage cost based on prompt and completion tokens."""
        model_lower = model.lower()
        
        # Default: Llama 3.1 70B rates
        input_rate = 0.70 / 1_000_000
        output_rate = 0.90 / 1_000_000
        
        if "70b" in model_lower:
            input_rate = 0.70 / 1_000_000
            output_rate = 0.90 / 1_000_000
        elif "8b" in model_lower:
            input_rate = 0.15 / 1_000_000
            output_rate = 0.15 / 1_000_000
        elif "405b" in model_lower:
            input_rate = 2.66 / 1_000_000
            output_rate = 2.66 / 1_000_000
            
        cost = (prompt_tokens * input_rate) + (completion_tokens * output_rate)
        return round(cost, 6)

    async def get_run_status(self, run_id: UUID) -> Optional[ResearchRun]:
        """Retrieves research run status and metadata by ID."""
        return await self.research_repo.get_run(run_id)

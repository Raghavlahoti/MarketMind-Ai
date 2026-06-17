# ============================================================================
# FINANCIAL AI RESEARCH PLATFORM - SQLALCHEMY MODELS
# Target: SQLAlchemy 2.0+ (with pgvector integration)
# Author: Antigravity AI Architect
# Description: Production-ready SQLAlchemy models matching schema.sql
# ============================================================================

import datetime
import enum
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Column, Integer, String, Text, Numeric, Date, Boolean, DateTime,
    ForeignKey, Table, Enum, BigInteger, CheckConstraint, UniqueConstraint, func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""
    pass


# ----------------------------------------------------------------------------
# PYTHON ENUMS MAPPED TO DATABASE ENUM TYPES
# ----------------------------------------------------------------------------

class PeriodTypeEnum(str, enum.Enum):
    annual = "annual"
    quarterly = "quarterly"
    trailing_twelve_months = "trailing_twelve_months"


class RatingTypeEnum(str, enum.Enum):
    strong_buy = "strong_buy"
    buy = "buy"
    hold = "hold"
    sell = "sell"
    strong_sell = "strong_sell"


class ReportStatusEnum(str, enum.Enum):
    draft = "draft"
    generating = "generating"
    completed = "completed"
    failed = "failed"


class RunStatusEnum(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class SentimentLabelEnum(str, enum.Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


class SourceTypeEnum(str, enum.Enum):
    news_article = "news_article"
    earnings_transcript = "earnings_transcript"
    research_report = "research_report"


class EventImpactEnum(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


class AlertTypeEnum(str, enum.Enum):
    price_above = "price_above"
    price_below = "price_below"
    sentiment_above = "sentiment_above"
    sentiment_below = "sentiment_below"
    new_research_report = "new_research_report"


class ReportSectionTypeEnum(str, enum.Enum):
    EXECUTIVE_SUMMARY = "EXECUTIVE_SUMMARY"
    BULL_CASE = "BULL_CASE"
    BEAR_CASE = "BEAR_CASE"
    RISKS = "RISKS"
    CATALYSTS = "CATALYSTS"
    VALUATION = "VALUATION"
    SENTIMENT_ANALYSIS = "SENTIMENT_ANALYSIS"
    INVESTMENT_THESIS = "INVESTMENT_THESIS"


# ----------------------------------------------------------------------------
# MANY-TO-MANY ASSOCIATIVE TABLES
# ----------------------------------------------------------------------------

news_article_stocks = Table(
    "news_article_stocks",
    Base.metadata,
    Column("article_id", ForeignKey("news_articles.id", ondelete="CASCADE"), primary_key=True),
    Column("stock_id", ForeignKey("stocks.id", ondelete="CASCADE"), primary_key=True)
)


# ----------------------------------------------------------------------------
# CORE MODELS
# ----------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    watchlists: Mapped[List["Watchlist"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    research_runs: Mapped[List["ResearchRun"]] = relationship(back_populates="user")
    research_reports: Mapped[List["ResearchReport"]] = relationship(back_populates="user")
    scheduled_jobs: Mapped[List["ScheduledJob"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    alerts: Mapped[List["Alert"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    model_usages: Mapped[List["AIModelUsage"]] = relationship(back_populates="user")


class Stock(Base):
    __tablename__ = "stocks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    ticker: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    exchange: Mapped[str] = mapped_column(String(50), nullable=False)
    sector: Mapped[Optional[str]] = mapped_column(String(100))
    industry: Mapped[Optional[str]] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 1-to-1 Relationships
    profile: Mapped[Optional["CompanyProfile"]] = relationship(back_populates="stock", cascade="all, delete-orphan")
    consensus: Mapped[Optional["AnalystConsensus"]] = relationship(back_populates="stock", cascade="all, delete-orphan")

    # 1-to-Many Relationships
    prices: Mapped[List["StockPrice"]] = relationship(back_populates="stock", cascade="all, delete-orphan")
    fundamentals: Mapped[List["CompanyFundamental"]] = relationship(back_populates="stock", cascade="all, delete-orphan")
    transcripts: Mapped[List["EarningsTranscript"]] = relationship(back_populates="stock", cascade="all, delete-orphan")
    research_runs: Mapped[List["ResearchRun"]] = relationship(back_populates="stock", cascade="all, delete-orphan")
    research_reports: Mapped[List["ResearchReport"]] = relationship(back_populates="stock", cascade="all, delete-orphan")
    watchlist_items: Mapped[List["WatchlistItem"]] = relationship(back_populates="stock", cascade="all, delete-orphan")
    scheduled_jobs: Mapped[List["ScheduledJob"]] = relationship(back_populates="stock", cascade="all, delete-orphan")
    alerts: Mapped[List["Alert"]] = relationship(back_populates="stock", cascade="all, delete-orphan")
    market_events: Mapped[List["MarketEvent"]] = relationship(back_populates="stock", cascade="all, delete-orphan")
    sentiments: Mapped[List["Sentiment"]] = relationship(back_populates="stock", cascade="all, delete-orphan")

    # Many-to-Many Relationships
    news_articles: Mapped[List["NewsArticle"]] = relationship(
        secondary=news_article_stocks, back_populates="stocks"
    )


class CompanyProfile(Base):
    __tablename__ = "company_profiles"
    __table_args__ = (
        CheckConstraint("employees >= 0", name="chk_employees_positive"),
        CheckConstraint("founded_year >= 1600", name="chk_founded_year_min"),
        CheckConstraint("market_cap >= 0", name="chk_market_cap"),
        CheckConstraint("shares_outstanding >= 0", name="chk_shares_outstanding"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    stock_id: Mapped[UUID] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    headquarters: Mapped[Optional[str]] = mapped_column(String(255))
    ceo: Mapped[Optional[str]] = mapped_column(String(150))
    employees: Mapped[Optional[int]] = mapped_column(Integer)
    website: Mapped[Optional[str]] = mapped_column(String(255))
    founded_year: Mapped[Optional[int]] = mapped_column(Integer)
    market_cap: Mapped[Optional[float]] = mapped_column(Numeric(20, 2))
    shares_outstanding: Mapped[Optional[float]] = mapped_column(Numeric(20, 2))
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    stock: Mapped["Stock"] = relationship(back_populates="profile")


class AnalystConsensus(Base):
    __tablename__ = "analyst_consensus"
    __table_args__ = (
        CheckConstraint("buy_count >= 0", name="chk_buy_count"),
        CheckConstraint("hold_count >= 0", name="chk_hold_count"),
        CheckConstraint("sell_count >= 0", name="chk_sell_count"),
        CheckConstraint("average_target_price >= 0", name="chk_avg_target_price"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    stock_id: Mapped[UUID] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), unique=True, nullable=False)
    buy_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hold_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sell_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    average_target_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    stock: Mapped["Stock"] = relationship(back_populates="consensus")


class StockPrice(Base):
    __tablename__ = "stock_prices"
    __table_args__ = (
        UniqueConstraint("stock_id", "price_date", name="uq_stock_price_date"),
        CheckConstraint("open_price >= 0", name="chk_open_price"),
        CheckConstraint("high_price >= 0", name="chk_high_price"),
        CheckConstraint("low_price >= 0", name="chk_low_price"),
        CheckConstraint("close_price >= 0", name="chk_close_price"),
        CheckConstraint("volume >= 0", name="chk_volume"),
        CheckConstraint("adjusted_close >= 0", name="chk_adj_close"),
        CheckConstraint(
            "high_price >= low_price AND high_price >= open_price AND high_price >= close_price",
            name="chk_price_extremes"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    stock_id: Mapped[UUID] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    price_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    open_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    high_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    low_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    close_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    adjusted_close: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    stock: Mapped["Stock"] = relationship(back_populates="prices")


class CompanyFundamental(Base):
    __tablename__ = "company_fundamentals"
    __table_args__ = (
        UniqueConstraint("stock_id", "report_date", "period_type", name="uq_stock_fundamental_period"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    stock_id: Mapped[UUID] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    report_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    period_type: Mapped[PeriodTypeEnum] = mapped_column(Enum(PeriodTypeEnum, name="period_type_enum"), nullable=False)
    revenue: Mapped[Optional[float]] = mapped_column(Numeric(18, 2))
    net_income: Mapped[Optional[float]] = mapped_column(Numeric(18, 2))
    eps: Mapped[Optional[float]] = mapped_column(Numeric(12, 4))
    ebitda: Mapped[Optional[float]] = mapped_column(Numeric(18, 2))
    assets: Mapped[Optional[float]] = mapped_column(Numeric(18, 2))
    liabilities: Mapped[Optional[float]] = mapped_column(Numeric(18, 2))
    cash_flow: Mapped[Optional[float]] = mapped_column(Numeric(18, 2))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, server_default="{}", nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    stock: Mapped["Stock"] = relationship(back_populates="fundamentals")


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    source_name: Mapped[Optional[str]] = mapped_column(String(100))
    url: Mapped[Optional[str]] = mapped_column(Text)
    published_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, server_default="{}", nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    stocks: Mapped[List["Stock"]] = relationship(
        secondary=news_article_stocks, back_populates="news_articles"
    )


class EarningsTranscript(Base):
    __tablename__ = "earnings_transcripts"
    __table_args__ = (
        UniqueConstraint("stock_id", "year", "quarter", name="uq_stock_transcript_period"),
        CheckConstraint("quarter >= 1 AND quarter <= 4", name="chk_transcript_quarter"),
        CheckConstraint("year >= 1900 AND year <= 2100", name="chk_transcript_year"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    stock_id: Mapped[UUID] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    quarter: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    publish_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    sections: Mapped[list] = mapped_column(JSONB, server_default="[]", nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, server_default="{}", nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    stock: Mapped["Stock"] = relationship(back_populates="transcripts")


class ResearchRun(Base):
    __tablename__ = "research_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    stock_id: Mapped[UUID] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[RunStatusEnum] = mapped_column(Enum(RunStatusEnum, name="run_status_enum"), default=RunStatusEnum.pending, nullable=False)
    started_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    config: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped[Optional["User"]] = relationship(back_populates="research_runs")
    stock: Mapped["Stock"] = relationship(back_populates="research_runs")
    reports: Mapped[List["ResearchReport"]] = relationship(back_populates="run")
    sources: Mapped[List["ResearchSource"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    model_usages: Mapped[List["AIModelUsage"]] = relationship(back_populates="run")


class ResearchReport(Base):
    __tablename__ = "research_reports"
    __table_args__ = (
        CheckConstraint("target_price >= 0", name="chk_target_price"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    stock_id: Mapped[UUID] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    run_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("research_runs.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    target_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))
    rating: Mapped[Optional[RatingTypeEnum]] = mapped_column(Enum(RatingTypeEnum, name="rating_type_enum"))
    status: Mapped[ReportStatusEnum] = mapped_column(Enum(ReportStatusEnum, name="report_status_enum"), default=ReportStatusEnum.draft, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(back_populates="research_reports")
    stock: Mapped["Stock"] = relationship(back_populates="research_reports")
    run: Mapped[Optional["ResearchRun"]] = relationship(back_populates="reports")
    sections: Mapped[List["ResearchReportSection"]] = relationship(back_populates="report", cascade="all, delete-orphan")


class ResearchReportSection(Base):
    __tablename__ = "research_report_sections"
    __table_args__ = (
        UniqueConstraint("report_id", "section_type", name="uq_report_section"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    report_id: Mapped[UUID] = mapped_column(ForeignKey("research_reports.id", ondelete="CASCADE"), nullable=False)
    section_type: Mapped[ReportSectionTypeEnum] = mapped_column(Enum(ReportSectionTypeEnum, name="report_section_type_enum"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    report: Mapped["ResearchReport"] = relationship(back_populates="sections")


class ResearchSource(Base):
    __tablename__ = "research_sources"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False)
    source_type: Mapped[SourceTypeEnum] = mapped_column(Enum(SourceTypeEnum, name="source_type_enum"), nullable=False)
    source_id: Mapped[UUID] = mapped_column(nullable=False) # Dynamic logic UUID (does not use standard physical FK)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    run: Mapped["ResearchRun"] = relationship(back_populates="sources")


class Sentiment(Base):
    __tablename__ = "sentiments"
    __table_args__ = (
        CheckConstraint("sentiment_score >= -1.000 AND sentiment_score <= 1.000", name="chk_sentiment_score"),
        CheckConstraint("confidence_score >= 0.000 AND confidence_score <= 1.000", name="chk_confidence_score"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    stock_id: Mapped[UUID] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    source_type: Mapped[SourceTypeEnum] = mapped_column(Enum(SourceTypeEnum, name="source_type_enum"), nullable=False)
    source_id: Mapped[UUID] = mapped_column(nullable=False) # Dynamic reference
    sentiment_score: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    sentiment_label: Mapped[SentimentLabelEnum] = mapped_column(Enum(SentimentLabelEnum, name="sentiment_label_enum"), nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text)
    confidence_score: Mapped[Optional[float]] = mapped_column(Numeric(4, 3))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    stock: Mapped["Stock"] = relationship(back_populates="sentiments")


class Watchlist(Base):
    __tablename__ = "watchlists"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="watchlists")
    items: Mapped[List["WatchlistItem"]] = relationship(back_populates="watchlist", cascade="all, delete-orphan")


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (
        UniqueConstraint("watchlist_id", "stock_id", name="uq_watchlist_stock"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    watchlist_id: Mapped[UUID] = mapped_column(ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False)
    stock_id: Mapped[UUID] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    added_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    watchlist: Mapped["Watchlist"] = relationship(back_populates="items")
    stock: Mapped["Stock"] = relationship(back_populates="watchlist_items")


class ScheduledJob(Base):
    __tablename__ = "scheduled_jobs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    stock_id: Mapped[UUID] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    job_name: Mapped[str] = mapped_column(String(150), nullable=False)
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_run_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="scheduled_jobs")
    stock: Mapped["Stock"] = relationship(back_populates="scheduled_jobs")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    stock_id: Mapped[UUID] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    alert_type: Mapped[AlertTypeEnum] = mapped_column(Enum(AlertTypeEnum, name="alert_type_enum"), nullable=False)
    target_value: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    is_triggered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="alerts")
    stock: Mapped["Stock"] = relationship(back_populates="alerts")


class MarketEvent(Base):
    __tablename__ = "market_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    stock_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_date: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    impact_level: Mapped[EventImpactEnum] = mapped_column(Enum(EventImpactEnum, name="event_impact_enum"), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    stock: Mapped[Optional["Stock"]] = relationship(back_populates="market_events")


class AIModelUsage(Base):
    __tablename__ = "ai_model_usage"
    __table_args__ = (
        CheckConstraint("prompt_tokens >= 0", name="chk_prompt_tokens"),
        CheckConstraint("completion_tokens >= 0", name="chk_comp_tokens"),
        CheckConstraint("cost >= 0", name="chk_usage_cost"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("research_runs.id", ondelete="SET NULL"))
    user_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost: Mapped[float] = mapped_column(Numeric(10, 6), default=0.000000, nullable=False)
    action_performed: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    run: Mapped[Optional["ResearchRun"]] = relationship(back_populates="model_usages")
    user: Mapped[Optional["User"]] = relationship(back_populates="model_usages")


class Embedding(Base):
    __tablename__ = "embeddings"
    __table_args__ = (
        CheckConstraint("embedding_dimension > 0", name="chk_dimension_positive"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_type: Mapped[SourceTypeEnum] = mapped_column(Enum(SourceTypeEnum, name="source_type_enum"), nullable=False)
    source_id: Mapped[UUID] = mapped_column(nullable=False) # Dynamic reference
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content_chunk: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)
    embedding_dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list] = mapped_column(Vector, nullable=False) # Unconstrained pgvector column
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

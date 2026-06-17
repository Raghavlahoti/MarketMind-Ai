# ============================================================================
# MARKETMIND AI - MODELS NAMESPACE BRIDGE
# ============================================================================

import sys
from pathlib import Path

# Add project root to path so we can resolve models.py in root
sys.path.append(str(Path(__file__).resolve().parents[2]))

from models import (
    Base, User, Stock, CompanyProfile, AnalystConsensus, StockPrice, CompanyFundamental,
    NewsArticle, EarningsTranscript, ResearchRun, ResearchReport, ResearchReportSection,
    ResearchSource, Sentiment, Watchlist, WatchlistItem, ScheduledJob, Alert, MarketEvent,
    AIModelUsage, Embedding, PeriodTypeEnum, RatingTypeEnum, ReportStatusEnum, RunStatusEnum,
    SentimentLabelEnum, SourceTypeEnum, EventImpactEnum, AlertTypeEnum, ReportSectionTypeEnum,
    news_article_stocks
)

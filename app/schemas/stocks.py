# ============================================================================
# MARKETMIND AI - STOCK PYDANTIC SCHEMAS
# ============================================================================

import datetime
from typing import Any, Dict, Optional, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, AliasChoices, computed_field


class StockBase(BaseModel):
    id: UUID
    ticker: str
    name: str
    exchange: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class Stock(StockBase):
    pass


class CompanyProfile(BaseModel):
    id: UUID
    stock_id: UUID
    description: Optional[str] = None
    headquarters: Optional[str] = None
    ceo: Optional[str] = None
    employees: Optional[int] = None
    website: Optional[str] = None
    founded_year: Optional[int] = None
    market_cap: Optional[float] = None
    shares_outstanding: Optional[float] = None
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class AnalystConsensus(BaseModel):
    id: UUID
    stock_id: UUID
    buy_count: int
    hold_count: int
    sell_count: int
    average_target_price: Optional[float] = None
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class StockDetail(Stock):
    profile: Optional[CompanyProfile] = None
    consensus: Optional[AnalystConsensus] = None


class StockPrice(BaseModel):
    id: UUID
    stock_id: UUID
    price_date: datetime.date
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    adjusted_close: float

    model_config = ConfigDict(from_attributes=True)


class CompanyFundamental(BaseModel):
    id: UUID
    stock_id: UUID
    report_date: datetime.date
    period_type: str
    revenue: Optional[float] = None
    net_income: Optional[float] = None
    eps: Optional[float] = None
    ebitda: Optional[float] = None
    assets: Optional[float] = None
    liabilities: Optional[float] = None
    cash_flow: Optional[float] = None
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("metadata_", "metadata")
    )

    model_config = ConfigDict(from_attributes=True)


class NewsArticle(BaseModel):
    id: UUID
    title: str
    content: str
    summary: Optional[str] = None
    source_name: Optional[str] = None
    url: Optional[str] = None
    published_at: datetime.datetime
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("metadata_", "metadata")
    )
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class ArticleSentimentDetail(BaseModel):
    article_id: UUID
    title: str
    url: Optional[str] = None
    published_at: datetime.datetime
    sentiment_score: float
    sentiment_label: str
    explanation: Optional[str] = None
    confidence_score: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class AggregatedSentimentResponse(BaseModel):
    symbol: str
    overall_score: float
    overall_label: str
    article_count: int
    articles: List[ArticleSentimentDetail]

    model_config = ConfigDict(from_attributes=True)


class ResearchSectionResponse(BaseModel):
    id: UUID
    report_id: UUID
    section_type: str
    content: str

    model_config = ConfigDict(from_attributes=True)


class ResearchReportResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    stock_id: UUID
    run_id: Optional[UUID] = None
    title: str
    summary: Optional[str] = None
    target_price: Optional[float] = None
    rating: Optional[str] = None
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    sections: List[ResearchSectionResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ResearchRunResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    stock_id: UUID
    trigger_type: str
    status: str
    started_at: datetime.datetime
    completed_at: Optional[datetime.datetime] = None
    error_message: Optional[str] = None
    config: Dict[str, Any] = {}
    created_at: datetime.datetime

    @computed_field
    @property
    def run_id(self) -> UUID:
        return self.id

    model_config = ConfigDict(from_attributes=True)


class PaginatedNewsResponse(BaseModel):
    items: List[NewsArticle]
    total: int
    limit: int
    offset: int


class PaginatedResearchReportResponse(BaseModel):
    items: List[ResearchReportResponse]
    total: int
    limit: int
    offset: int


class PaginatedStockPriceResponse(BaseModel):
    items: List[StockPrice]
    total: int
    limit: int
    offset: int


class PaginatedCompanyFundamentalResponse(BaseModel):
    items: List[CompanyFundamental]
    total: int
    limit: int
    offset: int


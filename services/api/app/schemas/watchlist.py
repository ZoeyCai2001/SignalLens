from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.feed import FeedItem


class StockWatchlistItem(BaseModel):
    ticker: str
    company_name: str
    exchange: str
    sector: str
    industry: str
    priority: str
    group_name: str
    display_order: int = 100
    is_pinned: bool = False
    is_holding: bool = False
    shares: float | None = None
    average_cost: float | None = None
    related_keywords: list[str] = Field(default_factory=list)
    related_companies: list[str] = Field(default_factory=list)
    related_ai_themes: list[str] = Field(default_factory=list)
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)


class StockPricePoint(BaseModel):
    price_date: date
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    adjusted_close: float | None = None
    volume: int | None = None

    model_config = ConfigDict(from_attributes=True)


class StockMarketSnapshot(BaseModel):
    latest: StockPricePoint | None = None
    previous_close: float | None = None
    change: float | None = None
    change_percent: float | None = None
    volume_change_percent: float | None = None
    history: list[StockPricePoint] = Field(default_factory=list)


class StockSignalSummary(BaseModel):
    stock: StockWatchlistItem
    signal_count: int
    today_signal_count: int = 0
    high_impact_count: int = 0
    attention_score: float
    market: StockMarketSnapshot | None = None
    latest_event_title: str | None = None
    latest_event_at: datetime | None = None
    last_updated_at: datetime | None = None
    sentiment_counts: dict[str, int] = Field(default_factory=dict)
    top_signals: list[FeedItem]
    disclaimer: str


class StockBriefingTimelineItem(BaseModel):
    item: FeedItem
    signal_score: float
    reason: str
    event_type: str
    possible_market_impact: str
    price_reaction: str
    confidence: float
    time_sensitivity: str
    event_summary: str
    uncertainties: list[str] = Field(default_factory=list)


class StockThemeBreakdown(BaseModel):
    theme: str
    item_count: int


class StockMarketImpactEvent(BaseModel):
    event_type: str
    item_count: int
    latest_title: str | None = None
    latest_at: datetime | None = None


class StockBriefing(BaseModel):
    stock: StockWatchlistItem
    signal_count: int
    attention_score: float
    market: StockMarketSnapshot | None = None
    urgency: str
    latest_signal_at: datetime | None
    sentiment_counts: dict[str, int]
    key_themes: list[str]
    ai_relevance_summary: str
    theme_breakdown: list[StockThemeBreakdown]
    market_impact_events: list[StockMarketImpactEvent]
    recent_timeline: list[StockBriefingTimelineItem]
    disclaimer: str


class StockWatchlistItemCreate(BaseModel):
    ticker: str | None = None
    company_name: str | None = None
    exchange: str = "NASDAQ"
    sector: str = "Technology"
    industry: str = "Technology"
    priority: str = "Medium"
    group_name: str = "Watch Only"
    display_order: int | None = None
    is_pinned: bool = False
    is_holding: bool = False
    shares: float | None = Field(default=None, ge=0)
    average_cost: float | None = Field(default=None, ge=0)
    related_keywords: list[str] = Field(default_factory=list)
    related_companies: list[str] = Field(default_factory=list)
    related_ai_themes: list[str] = Field(default_factory=list)
    notes: str | None = None


class StockWatchlistItemUpdate(BaseModel):
    company_name: str | None = None
    exchange: str | None = None
    sector: str | None = None
    industry: str | None = None
    priority: str | None = None
    group_name: str | None = None
    display_order: int | None = None
    is_pinned: bool | None = None
    is_holding: bool | None = None
    shares: float | None = Field(default=None, ge=0)
    average_cost: float | None = Field(default=None, ge=0)
    related_keywords: list[str] | None = None
    related_companies: list[str] | None = None
    related_ai_themes: list[str] | None = None
    notes: str | None = None


class CompanyWatchlistItem(BaseModel):
    company_key: str
    company_name: str
    ticker: str | None = None
    category: str = "ai_company"
    priority: str = "Medium"
    is_pinned: bool = False
    include_in_digest: bool = True
    related_terms: list[str] = Field(default_factory=list)
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CompanyWatchlistItemCreate(BaseModel):
    company_name: str
    company_key: str | None = None
    ticker: str | None = None
    category: str = "ai_company"
    priority: str = "Medium"
    is_pinned: bool = False
    include_in_digest: bool = True
    related_terms: list[str] = Field(default_factory=list)
    notes: str | None = None


class CompanyWatchlistItemUpdate(BaseModel):
    company_name: str | None = None
    ticker: str | None = None
    category: str | None = None
    priority: str | None = None
    is_pinned: bool | None = None
    include_in_digest: bool | None = None
    related_terms: list[str] | None = None
    notes: str | None = None


class TopicWatchlistItem(BaseModel):
    topic: str
    label: str
    category: str = "technical_trend"
    priority: str = "Medium"
    is_pinned: bool = False
    include_in_digest: bool = True
    related_terms: list[str] = Field(default_factory=list)
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TopicSourceCount(BaseModel):
    source_name: str
    item_count: int


class TopicActivityBucket(BaseModel):
    activity_date: date
    item_count: int


class CompanyBriefing(BaseModel):
    company: CompanyWatchlistItem
    item_count: int
    high_impact_count: int = 0
    average_importance_score: float = 0
    trending_sources: list[TopicSourceCount]
    related_topics: list[str]
    related_products: list[str]
    related_tickers: list[str]
    recent_timeline: list[FeedItem]
    activity_timeline: list[TopicActivityBucket]


class TopicBriefing(BaseModel):
    topic: TopicWatchlistItem
    definition: str = ""
    item_count: int
    high_impact_count: int = 0
    average_importance_score: float = 0
    trending_sources: list[TopicSourceCount]
    related_papers: list[FeedItem]
    related_products: list[FeedItem]
    related_companies: list[str]
    recent_timeline: list[FeedItem]
    activity_timeline: list[TopicActivityBucket]


class TopicWatchlistItemCreate(BaseModel):
    topic: str
    label: str | None = None
    category: str = "technical_trend"
    priority: str = "Medium"
    is_pinned: bool = False
    include_in_digest: bool = True
    related_terms: list[str] = Field(default_factory=list)
    notes: str | None = None


class TopicWatchlistItemUpdate(BaseModel):
    label: str | None = None
    category: str | None = None
    priority: str | None = None
    is_pinned: bool | None = None
    include_in_digest: bool | None = None
    related_terms: list[str] | None = None
    notes: str | None = None


class ProductWatchlistItem(BaseModel):
    category: str
    label: str
    priority: str = "Medium"
    is_pinned: bool = False
    include_in_digest: bool = True
    related_terms: list[str] = Field(default_factory=list)
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ProductWatchlistItemCreate(BaseModel):
    category: str
    label: str | None = None
    priority: str = "Medium"
    is_pinned: bool = False
    include_in_digest: bool = True
    related_terms: list[str] = Field(default_factory=list)
    notes: str | None = None


class ProductWatchlistItemUpdate(BaseModel):
    label: str | None = None
    priority: str | None = None
    is_pinned: bool | None = None
    include_in_digest: bool | None = None
    related_terms: list[str] | None = None
    notes: str | None = None


class ProductBriefing(BaseModel):
    product: ProductWatchlistItem
    item_count: int
    high_impact_count: int = 0
    average_importance_score: float = 0
    trending_sources: list[TopicSourceCount]
    matched_products: list[str]
    related_companies: list[str]
    recent_timeline: list[FeedItem]
    activity_timeline: list[TopicActivityBucket]

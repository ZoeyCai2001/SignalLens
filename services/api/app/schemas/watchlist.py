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
    is_pinned: bool = False
    is_holding: bool = False
    shares: float | None = None
    average_cost: float | None = None
    related_keywords: list[str] = Field(default_factory=list)
    related_companies: list[str] = Field(default_factory=list)
    related_ai_themes: list[str] = Field(default_factory=list)
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)


class StockSignalSummary(BaseModel):
    stock: StockWatchlistItem
    signal_count: int
    top_signals: list[FeedItem]
    disclaimer: str


class StockWatchlistItemCreate(BaseModel):
    ticker: str
    company_name: str
    exchange: str = "NASDAQ"
    sector: str = "Technology"
    industry: str = "Technology"
    priority: str = "Medium"
    group_name: str = "Watch Only"
    is_pinned: bool = False
    is_holding: bool = False
    shares: float | None = None
    average_cost: float | None = None
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
    is_pinned: bool | None = None
    is_holding: bool | None = None
    shares: float | None = None
    average_cost: float | None = None
    related_keywords: list[str] | None = None
    related_companies: list[str] | None = None
    related_ai_themes: list[str] | None = None
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


class TopicWatchlistItemCreate(BaseModel):
    topic: str
    label: str | None = None
    category: str = "technical_trend"
    priority: str = "Medium"
    is_pinned: bool = False
    include_in_digest: bool = True
    related_terms: list[str] = Field(default_factory=list)
    notes: str | None = None

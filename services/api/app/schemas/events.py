from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.feed import FeedItem
from app.schemas.watchlist import StockMarketSnapshot


class EventClusterTimelineItem(BaseModel):
    item_id: int
    title: str
    source_name: str
    published_at: datetime | None
    importance_score: float


class EventClusterMarketReaction(BaseModel):
    ticker: str
    possible_market_impact: str
    price_reaction: str
    event_price_date: date | None = None
    event_price_change_percent: float | None = None
    summary: str


class EventCluster(BaseModel):
    cluster_key: str
    title: str
    main_summary: str
    explanation: str
    uncertainty_notes: list[str]
    category: str
    topics: list[str]
    tickers: list[str]
    sources: list[str]
    item_count: int
    source_count: int = 0
    duplicate_item_count: int = 0
    confirmation_level: str = "single_source"
    top_score: float
    importance_score: float
    confidence: float
    earliest_source: str | None
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    latest_update_at: datetime | None
    related_market_ticker: str | None = None
    related_market: StockMarketSnapshot | None = None
    related_market_reaction: EventClusterMarketReaction | None = None
    timeline: list[EventClusterTimelineItem]
    representative_item: FeedItem
    items: list[FeedItem]


class EventClusterLlmExplanation(BaseModel):
    cluster_key: str
    model: str
    explanation: str
    input_tokens: int
    output_tokens: int
    total_tokens: int

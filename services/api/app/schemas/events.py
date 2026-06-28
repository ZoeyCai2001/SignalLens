from datetime import datetime

from pydantic import BaseModel

from app.schemas.feed import FeedItem


class EventClusterTimelineItem(BaseModel):
    item_id: int
    title: str
    source_name: str
    published_at: datetime | None
    importance_score: float


class EventCluster(BaseModel):
    cluster_key: str
    title: str
    main_summary: str
    category: str
    topics: list[str]
    tickers: list[str]
    sources: list[str]
    item_count: int
    top_score: float
    importance_score: float
    confidence: float
    earliest_source: str | None
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    latest_update_at: datetime | None
    timeline: list[EventClusterTimelineItem]
    representative_item: FeedItem
    items: list[FeedItem]

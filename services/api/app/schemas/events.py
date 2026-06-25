from datetime import datetime

from pydantic import BaseModel

from app.schemas.feed import FeedItem


class EventCluster(BaseModel):
    cluster_key: str
    title: str
    category: str
    topics: list[str]
    tickers: list[str]
    sources: list[str]
    item_count: int
    top_score: float
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    representative_item: FeedItem
    items: list[FeedItem]

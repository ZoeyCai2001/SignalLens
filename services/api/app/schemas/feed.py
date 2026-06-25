from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FeedItem(BaseModel):
    id: int
    title: str
    url: str
    source_name: str
    author: str | None
    language: str
    published_at: datetime | None
    category: str
    subcategory: str | None
    tickers: list[str]
    companies: list[str]
    products: list[str]
    topics: list[str]
    sentiment: str
    relevance_score: float
    importance_score: float
    novelty_score: float
    source_quality_score: float
    stock_impact_score: float
    summary_short: str | None
    why_it_matters: str | None

    model_config = ConfigDict(from_attributes=True)

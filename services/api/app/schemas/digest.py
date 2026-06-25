from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.feed import FeedItem


class DigestSourceCoverage(BaseModel):
    source_name: str
    item_count: int


class DigestSection(BaseModel):
    key: str
    title: str
    focus: str
    items: list[FeedItem]


class DailyDigest(BaseModel):
    digest_date: date
    generated_at: datetime
    headline: str
    total_items: int
    sections: list[DigestSection]
    source_coverage: list[DigestSourceCoverage]
    watchlist_tickers: list[str]
    disclaimer: str


class DailyDigestMarkdown(BaseModel):
    digest_date: date
    generated_at: datetime
    markdown: str

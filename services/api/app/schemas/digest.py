from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.feed import FeedItem


class DigestSourceCoverage(BaseModel):
    source_name: str
    item_count: int


class DigestSectionMetrics(BaseModel):
    item_count: int = 0
    high_impact_count: int = 0
    stock_signal_count: int = 0
    read_later_count: int = 0
    source_count: int = 0


class DigestSection(BaseModel):
    key: str
    title: str
    focus: str
    items: list[FeedItem]
    metrics: DigestSectionMetrics = Field(default_factory=DigestSectionMetrics)


class DigestAlertItem(BaseModel):
    id: int
    title: str
    reason: str
    severity: str
    rule_name: str
    created_at: datetime
    item: FeedItem


class DailyDigest(BaseModel):
    digest_date: date
    generated_at: datetime
    headline: str
    total_items: int
    high_impact_count: int = 0
    stock_signal_count: int = 0
    read_later_count: int = 0
    active_alert_count: int = 0
    source_count: int = 0
    sections: list[DigestSection]
    active_alerts: list[DigestAlertItem] = Field(default_factory=list)
    source_coverage: list[DigestSourceCoverage]
    watchlist_tickers: list[str] = Field(default_factory=list)
    watchlist_companies: list[str] = Field(default_factory=list)
    watchlist_topics: list[str] = Field(default_factory=list)
    watchlist_products: list[str] = Field(default_factory=list)
    disclaimer: str


class DailyDigestMarkdown(BaseModel):
    digest_date: date
    generated_at: datetime
    markdown: str


class DailyDigestSnapshot(BaseModel):
    id: int
    digest_date: date
    generated_at: datetime
    headline: str
    total_items: int
    limit_per_section: int
    digest: DailyDigest
    markdown: str
    created_at: datetime
    updated_at: datetime

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    technologies: list[str] = Field(default_factory=list)
    sentiment: str
    is_ai_related: bool = True
    relevance_score: float
    classification_confidence: float = 0.5
    importance_score: float
    novelty_score: float
    source_quality_score: float
    social_signal_score: float = 0
    stock_impact_score: float
    cross_source_confirmation_score: float = 0
    cross_source_confirmation_label: str | None = None
    market_impact_type: str = "none"
    summary_short: str | None
    summary_detailed: str | None
    why_it_matters: str | None
    is_saved: bool = False
    is_hidden: bool = False
    is_important: bool = False
    is_read: bool = False
    read_at: datetime | None = None
    personal_note: str | None = None
    manual_tags: list[str] = Field(default_factory=list)
    usefulness_feedback: str | None = None
    usefulness_feedback_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("classification_confidence", mode="before")
    @classmethod
    def default_classification_confidence(cls, value: float | None) -> float:
        return 0.5 if value is None else value


class FeedStockReactionSummary(BaseModel):
    ticker: str
    possible_market_impact: str
    price_reaction: str
    event_price_date: date | None = None
    event_price_change_percent: float | None = None
    summary: str


class FeedPublicEngagementMetric(BaseModel):
    key: str
    label: str
    value: int


class FeedItemDetail(FeedItem):
    text: str | None = None
    one_line_summary: str | None = None
    card_summary: list[str] = Field(default_factory=list)
    technical_summary: str | None = None
    market_watch_summary: str | None = None
    stock_reaction_summary: FeedStockReactionSummary | None = None
    public_engagement: list[FeedPublicEngagementMetric] = Field(default_factory=list)
    summary_source: str = "deterministic"
    score_explanation: str
    uncertainty_notes: list[str]
    personalization_notes: list[str] = Field(default_factory=list)
    action_state: dict[str, bool]


class FeedItemPersonalMetadataUpdate(BaseModel):
    personal_note: str | None = None
    manual_tags: list[str] = Field(default_factory=list)


class SavedItemsMarkdownExport(BaseModel):
    generated_at: datetime
    item_count: int
    markdown: str


class SavedItemsJsonExport(BaseModel):
    generated_at: datetime
    item_count: int
    items: list[FeedItem] = Field(default_factory=list)

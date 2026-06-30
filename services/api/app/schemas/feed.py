from datetime import datetime

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
    sentiment: str
    relevance_score: float
    classification_confidence: float = 0.5
    importance_score: float
    novelty_score: float
    source_quality_score: float
    social_signal_score: float = 0
    stock_impact_score: float
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

    model_config = ConfigDict(from_attributes=True)

    @field_validator("classification_confidence", mode="before")
    @classmethod
    def default_classification_confidence(cls, value: float | None) -> float:
        return 0.5 if value is None else value


class FeedItemDetail(FeedItem):
    text: str | None = None
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

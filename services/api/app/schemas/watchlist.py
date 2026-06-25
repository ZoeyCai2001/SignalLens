from pydantic import BaseModel, ConfigDict, Field


class StockWatchlistItem(BaseModel):
    ticker: str
    company_name: str
    exchange: str
    sector: str
    industry: str
    priority: str
    group_name: str
    is_pinned: bool = False
    related_keywords: list[str] = Field(default_factory=list)
    related_companies: list[str] = Field(default_factory=list)
    related_ai_themes: list[str] = Field(default_factory=list)
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)


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

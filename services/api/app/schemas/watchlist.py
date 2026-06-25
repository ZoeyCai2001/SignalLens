from pydantic import BaseModel, Field


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

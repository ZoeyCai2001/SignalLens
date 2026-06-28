from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.feed import FeedItem


class SearchIntentResponse(BaseModel):
    query: str | None = None
    category: str | None = None
    ticker: str | None = None
    company: str | None = None
    topic: str | None = None
    language: str | None = None
    date_from: date | None = None
    min_importance_score: float | None = None
    saved_only: bool = False

    model_config = ConfigDict(from_attributes=True)


class NaturalLanguageSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=300)
    limit: int = Field(default=30, ge=1, le=100)


class NaturalLanguageSearchResponse(BaseModel):
    intent: SearchIntentResponse
    items: list[FeedItem]

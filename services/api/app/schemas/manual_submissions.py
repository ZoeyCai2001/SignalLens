from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.schemas.feed import FeedItem


class ManualEngagementMetrics(BaseModel):
    likes: int | None = Field(default=None, ge=0)
    comments_count: int | None = Field(default=None, ge=0)
    collects: int | None = Field(default=None, ge=0)
    reposts: int | None = Field(default=None, ge=0)
    views: int | None = Field(default=None, ge=0)


class ManualSubmissionRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=500)
    url: HttpUrl
    text: str | None = Field(default=None, max_length=12000)
    source_name: str = Field(default="Manual Submission", min_length=2, max_length=120)
    public_engagement: ManualEngagementMetrics | None = None
    save_item: bool = False
    personal_note: str | None = Field(default=None, max_length=4000)
    manual_tags: list[str] | None = Field(default=None, max_length=12)
    classify_with_llm: bool = False
    summarize_with_llm: bool = False

    @field_validator("title", mode="before")
    @classmethod
    def normalize_optional_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        title = value.strip()
        return title or None


class ManualSubmissionResponse(BaseModel):
    item: FeedItem
    created: bool = True
    updated_existing: bool = False
    classification_status: str = "not_requested"
    classification_error: str | None = None
    summary_status: str = "not_requested"
    summary_error: str | None = None

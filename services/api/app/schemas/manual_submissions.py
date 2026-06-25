from pydantic import BaseModel, Field, HttpUrl

from app.schemas.feed import FeedItem


class ManualSubmissionRequest(BaseModel):
    title: str = Field(min_length=3, max_length=500)
    url: HttpUrl
    text: str | None = Field(default=None, max_length=12000)
    source_name: str = Field(default="Manual Submission", min_length=2, max_length=120)


class ManualSubmissionResponse(BaseModel):
    item: FeedItem

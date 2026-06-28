from pydantic import BaseModel, Field


class SmokeTestRequest(BaseModel):
    prompt: str = Field(default="Reply with only OK.", min_length=1, max_length=500)
    max_tokens: int = Field(default=16, ge=1, le=256)


class SmokeTestResponse(BaseModel):
    model: str
    text: str
    input_tokens: int
    output_tokens: int
    total_tokens: int


class FeedProcessingRequest(BaseModel):
    limit: int = Field(default=3, ge=1, le=10)
    summarize: bool = True
    classify: bool = False
    skip_summarized: bool = True
    skip_classified: bool = True
    min_classification_confidence: float = Field(default=0.7, ge=0, le=1)


class FeedProcessingError(BaseModel):
    item_id: int
    stage: str
    error: str


class FeedProcessingResponse(BaseModel):
    requested_limit: int
    candidates_seen: int
    summarized_count: int
    classified_count: int
    skipped_count: int
    item_ids: list[int]
    errors: list[FeedProcessingError]

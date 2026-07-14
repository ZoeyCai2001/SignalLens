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
    dry_run: bool = False
    skip_summarized: bool = True
    skip_classified: bool = True
    min_classification_confidence: float = Field(default=0.7, ge=0, le=1)
    module: str | None = Field(default=None, max_length=80)


class FeedProcessingError(BaseModel):
    item_id: int
    stage: str
    error: str


class FeedProcessingCandidatePreview(BaseModel):
    item_id: int
    title: str
    source_name: str
    category: str | None = None
    planned_operations: list[str] = Field(default_factory=list)
    skipped_operations: list[str] = Field(default_factory=list)


class FeedProcessingResponse(BaseModel):
    requested_limit: int
    dry_run: bool = False
    candidates_seen: int
    planned_model_calls: int = 0
    summarized_count: int
    classified_count: int
    skipped_count: int
    model_call_budget: int = 0
    model_calls_attempted: int = 0
    model_calls_succeeded: int = 0
    model_calls_failed: int = 0
    model_calls_skipped: int = 0
    model_calls_unused: int = 0
    item_ids: list[int]
    candidate_previews: list[FeedProcessingCandidatePreview] = Field(default_factory=list)
    errors: list[FeedProcessingError]

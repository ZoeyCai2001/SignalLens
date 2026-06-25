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

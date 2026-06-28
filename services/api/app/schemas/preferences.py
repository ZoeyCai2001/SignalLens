from pydantic import BaseModel, ConfigDict, Field, field_validator


class RankingWeights(BaseModel):
    relevance: float = Field(default=0.25, ge=0, le=1)
    importance: float = Field(default=0.20, ge=0, le=1)
    novelty: float = Field(default=0.15, ge=0, le=1)
    source_quality: float = Field(default=0.15, ge=0, le=1)
    stock_impact: float = Field(default=0.10, ge=0, le=1)
    freshness: float = Field(default=0.05, ge=0, le=1)


class UserPreferences(BaseModel):
    user_id: str
    ranking_weights: RankingWeights
    preferred_sources: list[str] = Field(default_factory=list)
    blocked_sources: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

    @field_validator("preferred_sources", "blocked_sources", mode="before")
    @classmethod
    def normalize_source_lists(cls, value: list[str] | None) -> list[str]:
        if not value:
            return []
        return [str(item).strip() for item in value if str(item).strip()]


class UserPreferencesUpdate(BaseModel):
    ranking_weights: RankingWeights | None = None
    preferred_sources: list[str] | None = None
    blocked_sources: list[str] | None = None

    @field_validator("preferred_sources", "blocked_sources", mode="before")
    @classmethod
    def normalize_update_source_lists(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return [str(item).strip() for item in value if str(item).strip()]

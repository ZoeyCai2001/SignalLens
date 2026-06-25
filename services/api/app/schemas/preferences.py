from pydantic import BaseModel, ConfigDict, Field


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

    model_config = ConfigDict(from_attributes=True)


class UserPreferencesUpdate(BaseModel):
    ranking_weights: RankingWeights | None = None

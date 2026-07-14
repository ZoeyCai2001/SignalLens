from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.feed import FeedItem


class AlertRule(BaseModel):
    id: int
    name: str
    description: str | None
    category: str
    severity: str
    min_importance_score: float
    min_stock_impact_score: float
    tickers: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    enabled: bool
    snoozed_until: datetime | None

    model_config = ConfigDict(from_attributes=True)


class AlertRuleCreate(BaseModel):
    name: str
    description: str | None = None
    category: str = "all"
    severity: str = "medium"
    min_importance_score: float = 0.75
    min_stock_impact_score: float = 0
    tickers: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    enabled: bool = True
    snoozed_until: datetime | None = None


class AlertRuleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    severity: str | None = None
    min_importance_score: float | None = None
    min_stock_impact_score: float | None = None
    tickers: list[str] | None = None
    topics: list[str] | None = None
    enabled: bool | None = None
    snoozed_until: datetime | None = None


class AlertItem(BaseModel):
    id: int
    title: str
    reason: str
    severity: str
    status: str
    created_at: datetime
    usefulness_feedback: str | None = None
    usefulness_feedback_at: datetime | None = None
    rule: AlertRule
    item: FeedItem
    disclaimer: str

    model_config = ConfigDict(from_attributes=True)


class AlertFeedbackUpdate(BaseModel):
    usefulness_feedback: str | None = None


class AlertGenerationResult(BaseModel):
    rules_seeded: int
    alerts_created: int
    active_alerts: int

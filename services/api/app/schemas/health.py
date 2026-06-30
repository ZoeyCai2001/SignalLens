from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class IntegrationStatus(BaseModel):
    kimi_coding_api: bool
    github_api: bool
    product_hunt_api: bool
    alpha_vantage_api: bool
    sec_user_agent: bool
    chinese_rss_feeds: bool


class SetupItem(BaseModel):
    key: str
    label: str
    configured: bool
    importance: Literal["core", "recommended", "optional"]
    required_for: str
    env_var: str
    setup_hint: str


class SetupSummary(BaseModel):
    total: int
    configured: int
    missing: int
    core_missing: int
    recommended_missing: int
    optional_missing: int
    core_ready: bool


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str
    llm_provider: str
    llm_model: str
    llm_configured: bool
    integrations: IntegrationStatus
    setup_items: list[SetupItem]
    setup_summary: SetupSummary
    missing_env_template: str = ""


class LlmOperationUsage(BaseModel):
    operation: str
    call_count: int
    input_tokens: int
    output_tokens: int
    total_tokens: int


class QualityFinding(BaseModel):
    severity: Literal["info", "warning", "critical"]
    title: str
    metric: str
    recommendation: str
    action_label: str | None = None
    action_module: Literal["dashboard", "digest", "sources", "settings"] | None = None
    action_source_filter: Literal[
        "all",
        "attention",
        "failed",
        "stale",
        "never_run",
        "disabled",
        "blocked",
    ] | None = None


class QualityMetricsResponse(BaseModel):
    generated_at: datetime
    window_days: int
    total_item_count: int
    recent_item_count: int
    high_value_item_count: int
    high_value_unsummarized_count: int = 0
    relevance_precision_proxy: float
    duplicate_rate: float
    summary_coverage: float
    source_failure_rate: float
    save_count: int
    hide_count: int
    save_hide_ratio: float | None
    active_alert_count: int
    dismissed_alert_count: int
    alert_dismissal_rate: float
    digest_snapshot_count: int
    latest_digest_snapshot_date: date | None = None
    llm_call_count: int = 0
    llm_input_tokens: int = 0
    llm_output_tokens: int = 0
    llm_total_tokens: int = 0
    llm_calls_per_recent_item: float = 0
    llm_operation_usage: list[LlmOperationUsage] = Field(default_factory=list)
    quality_findings: list[QualityFinding] = Field(default_factory=list)

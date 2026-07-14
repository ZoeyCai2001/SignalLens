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
    estimated_cost_usd: float = 0


class QualityFinding(BaseModel):
    severity: Literal["info", "warning", "critical"]
    title: str
    metric: str
    recommendation: str
    action_label: str | None = None
    action_module: Literal[
        "alerts", "dashboard", "digest", "sources", "settings", "stocks", "submit"
    ] | None = None
    action_operation: Literal[
        "cycle",
        "llm:classify",
        "llm:summarize",
        "digest:save-snapshot",
        "stock-prices:refresh",
        "alerts:generate",
        "demo-data:seed",
    ] | None = None
    action_source_filter: Literal[
        "all",
        "attention",
        "failed",
        "stale",
        "never_run",
        "disabled",
        "blocked",
    ] | None = None


class MvpChecklistItem(BaseModel):
    key: str
    label: str
    status: Literal["ready", "partial", "needs_action"]
    metric: str
    note: str
    action_label: str | None = None
    action_module: Literal[
        "alerts", "dashboard", "digest", "sources", "settings", "stocks", "submit"
    ] | None = None
    action_operation: Literal[
        "cycle",
        "llm:classify",
        "llm:summarize",
        "digest:save-snapshot",
        "stock-prices:refresh",
        "alerts:generate",
        "demo-data:seed",
    ] | None = None
    action_source_filter: Literal[
        "all",
        "attention",
        "failed",
        "stale",
        "never_run",
        "disabled",
        "blocked",
    ] | None = None
    action_target_id: str | None = None


class MvpChecklistResponse(BaseModel):
    generated_at: datetime
    total_count: int
    ready_count: int
    partial_count: int
    needs_action_count: int
    items: list[MvpChecklistItem]


class QualityMetricsResponse(BaseModel):
    generated_at: datetime
    window_days: int
    total_item_count: int
    recent_item_count: int
    recent_module_counts: dict[str, int] = Field(default_factory=dict)
    covered_module_count: int = 0
    recent_source_count: int = 0
    dominant_source_share: float = 0
    trusted_source_coverage: float = 0
    low_quality_item_count: int = 0
    search_facet_coverage: float = 0
    unfaceted_item_count: int = 0
    high_value_item_count: int
    high_value_unsummarized_count: int = 0
    classification_coverage: float = 0
    low_confidence_item_count: int = 0
    relevance_precision_proxy: float
    duplicate_rate: float
    summary_coverage: float
    source_failure_rate: float
    save_count: int
    hide_count: int
    feedback_action_count: int = 0
    manual_submission_count: int = 0
    manual_enrichment_gap_count: int = 0
    stock_watchlist_count: int = 0
    company_watchlist_count: int = 0
    topic_watchlist_count: int = 0
    product_watchlist_count: int = 0
    watchlist_area_count: int = 0
    saved_read_count: int = 0
    saved_read_later_count: int = 0
    save_hide_ratio: float | None
    active_alert_count: int
    dismissed_alert_count: int
    alert_dismissal_rate: float
    digest_snapshot_count: int
    latest_digest_snapshot_date: date | None = None
    latest_digest_age_days: int | None = None
    latest_digest_snapshot_item_count: int | None = None
    latest_stock_price_date: date | None = None
    latest_stock_price_age_days: int | None = None
    llm_call_count: int = 0
    llm_input_tokens: int = 0
    llm_output_tokens: int = 0
    llm_total_tokens: int = 0
    llm_calls_per_recent_item: float = 0
    llm_pricing_configured: bool = False
    llm_estimated_cost_usd: float = 0
    llm_projected_monthly_cost_usd: float = 0
    llm_monthly_budget_usd: float = 0
    llm_monthly_budget_usage: float | None = None
    llm_estimated_cost_per_recent_item_usd: float | None = None
    llm_estimated_cost_per_digest_usd: float | None = None
    llm_estimated_cost_per_active_alert_usd: float | None = None
    llm_operation_usage: list[LlmOperationUsage] = Field(default_factory=list)
    quality_findings: list[QualityFinding] = Field(default_factory=list)

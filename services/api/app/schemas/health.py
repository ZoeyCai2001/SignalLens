from typing import Literal

from pydantic import BaseModel


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

from pydantic import BaseModel


class IntegrationStatus(BaseModel):
    kimi_coding_api: bool
    github_api: bool
    product_hunt_api: bool
    alpha_vantage_api: bool
    chinese_rss_feeds: bool


class SetupItem(BaseModel):
    key: str
    label: str
    configured: bool
    required_for: str
    env_var: str
    setup_hint: str


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str
    llm_provider: str
    llm_model: str
    llm_configured: bool
    integrations: IntegrationStatus
    setup_items: list[SetupItem]

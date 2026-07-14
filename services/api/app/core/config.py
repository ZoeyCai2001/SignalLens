from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SEC_USER_AGENT = "SignalLens/0.1 personal research; configure SEC_USER_AGENT"
DEFAULT_REDDIT_USER_AGENT = "SignalLens/0.1 personal research; configure REDDIT_USER_AGENT"


class Settings(BaseSettings):
    environment: str = Field(default="local", alias="ENVIRONMENT")
    api_host: str = Field(default="127.0.0.1", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    database_url: str = Field(
        default="postgresql+psycopg://signallens:signallens@localhost:55432/signallens",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    llm_provider: str = Field(default="kimi_coding", alias="LLM_PROVIDER")
    moonshot_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("MOONSHOT_API_KEY", "KIMI_API_KEY"),
    )
    moonshot_base_url: str = Field(
        default="https://api.kimi.com/coding/v1",
        alias="MOONSHOT_BASE_URL",
    )
    moonshot_model: str = Field(default="kimi-for-coding", alias="MOONSHOT_MODEL")
    kimi_api_format: str = Field(default="anthropic_messages", alias="KIMI_API_FORMAT")
    llm_input_cost_per_1m_tokens: float = Field(
        default=0,
        ge=0,
        alias="LLM_INPUT_COST_PER_1M_TOKENS",
    )
    llm_output_cost_per_1m_tokens: float = Field(
        default=0,
        ge=0,
        alias="LLM_OUTPUT_COST_PER_1M_TOKENS",
    )
    llm_monthly_budget_usd: float = Field(default=0, ge=0, alias="LLM_MONTHLY_BUDGET_USD")
    source_api_cost_per_1k_calls_usd: float = Field(
        default=0,
        ge=0,
        alias="SOURCE_API_COST_PER_1K_CALLS_USD",
    )
    source_api_monthly_budget_usd: float = Field(
        default=0,
        ge=0,
        alias="SOURCE_API_MONTHLY_BUDGET_USD",
    )
    github_token: str | None = Field(default=None, alias="GITHUB_TOKEN")
    product_hunt_api_token: str | None = Field(default=None, alias="PRODUCT_HUNT_API_TOKEN")
    alpha_vantage_api_key: str | None = Field(default=None, alias="ALPHA_VANTAGE_API_KEY")
    sec_user_agent: str = Field(
        default=DEFAULT_SEC_USER_AGENT,
        alias="SEC_USER_AGENT",
    )
    sec_forms: str = Field(default="8-K,10-K,10-Q", alias="SEC_FORMS")
    reddit_user_agent: str = Field(
        default=DEFAULT_REDDIT_USER_AGENT,
        alias="REDDIT_USER_AGENT",
    )
    reddit_subreddits: str = Field(
        default="LocalLLaMA,MachineLearning,artificial,singularity",
        alias="REDDIT_SUBREDDITS",
    )
    chinese_rss_feeds: str | None = Field(default=None, alias="CHINESE_RSS_FEEDS")
    signallens_scheduler_mode: str = Field(default="once", alias="SIGNALLENS_SCHEDULER_MODE")
    signallens_scheduler_interval_minutes: int = Field(
        default=360,
        ge=1,
        alias="SIGNALLENS_SCHEDULER_INTERVAL_MINUTES",
    )
    digest_target_hour_utc: int = Field(default=0, ge=0, le=23, alias="DIGEST_TARGET_HOUR_UTC")
    cors_origins: list[str] = Field(default=["http://localhost:3000", "http://127.0.0.1:3000"])

    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

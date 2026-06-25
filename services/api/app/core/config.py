from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    moonshot_api_key: str | None = Field(default=None, alias="MOONSHOT_API_KEY")
    moonshot_base_url: str = Field(
        default="https://api.kimi.com/coding/v1",
        alias="MOONSHOT_BASE_URL",
    )
    moonshot_model: str = Field(default="kimi-for-coding", alias="MOONSHOT_MODEL")
    kimi_api_format: str = Field(default="anthropic_messages", alias="KIMI_API_FORMAT")
    product_hunt_api_token: str | None = Field(default=None, alias="PRODUCT_HUNT_API_TOKEN")
    alpha_vantage_api_key: str | None = Field(default=None, alias="ALPHA_VANTAGE_API_KEY")
    cors_origins: list[str] = Field(default=["http://localhost:3000", "http://127.0.0.1:3000"])

    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.health import HealthResponse, IntegrationStatus

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service="signallens-api",
        environment=settings.environment,
        llm_provider=settings.llm_provider,
        llm_model=settings.moonshot_model,
        llm_configured=has_config_value(settings.moonshot_api_key),
        integrations=IntegrationStatus(
            kimi_coding_api=has_config_value(settings.moonshot_api_key),
            product_hunt_api=has_config_value(settings.product_hunt_api_token),
            alpha_vantage_api=has_config_value(settings.alpha_vantage_api_key),
            chinese_rss_feeds=has_config_value(settings.chinese_rss_feeds),
        ),
    )


def has_config_value(value: str | None) -> bool:
    return bool(value and value.strip())

from fastapi import APIRouter

from app.core.config import Settings, get_settings
from app.schemas.health import HealthResponse, IntegrationStatus, SetupItem

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    settings = get_settings()
    integrations = IntegrationStatus(
        kimi_coding_api=has_config_value(settings.moonshot_api_key),
        product_hunt_api=has_config_value(settings.product_hunt_api_token),
        alpha_vantage_api=has_config_value(settings.alpha_vantage_api_key),
        chinese_rss_feeds=has_config_value(settings.chinese_rss_feeds),
    )
    return HealthResponse(
        status="ok",
        service="signallens-api",
        environment=settings.environment,
        llm_provider=settings.llm_provider,
        llm_model=settings.moonshot_model,
        llm_configured=has_config_value(settings.moonshot_api_key),
        integrations=integrations,
        setup_items=build_setup_items(settings=settings, integrations=integrations),
    )


def has_config_value(value: str | None) -> bool:
    return bool(value and value.strip())


def build_setup_items(settings: Settings, integrations: IntegrationStatus) -> list[SetupItem]:
    return [
        SetupItem(
            key="kimi_coding_api",
            label="Kimi Coding API",
            configured=integrations.kimi_coding_api,
            required_for="LLM summarization, classification, and digest enrichment",
            env_var="MOONSHOT_API_KEY",
            setup_hint=(
                f"Set MOONSHOT_API_KEY in .env; current provider is "
                f"{settings.llm_provider} using {settings.moonshot_model}."
            ),
        ),
        SetupItem(
            key="alpha_vantage_api",
            label="Alpha Vantage",
            configured=integrations.alpha_vantage_api,
            required_for="watched-stock news and daily price snapshots",
            env_var="ALPHA_VANTAGE_API_KEY",
            setup_hint="Set ALPHA_VANTAGE_API_KEY in .env for stock news and prices.",
        ),
        SetupItem(
            key="product_hunt_api",
            label="Product Hunt",
            configured=integrations.product_hunt_api,
            required_for="AI product launch ingestion",
            env_var="PRODUCT_HUNT_API_TOKEN",
            setup_hint="Set PRODUCT_HUNT_API_TOKEN in .env to collect public launch metadata.",
        ),
        SetupItem(
            key="chinese_rss_feeds",
            label="Chinese RSS Feeds",
            configured=integrations.chinese_rss_feeds,
            required_for="Chinese-language AI trend ingestion from public feeds",
            env_var="CHINESE_RSS_FEEDS",
            setup_hint=(
                "Set CHINESE_RSS_FEEDS as comma-separated Name|URL entries; "
                "use public RSS/Atom feeds only."
            ),
        ),
    ]

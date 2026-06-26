import pytest

from app.api.routes.health import has_config_value, health_check
from app.core.config import Settings


def test_has_config_value_rejects_empty_strings() -> None:
    assert has_config_value(None) is False
    assert has_config_value("") is False
    assert has_config_value("   ") is False
    assert has_config_value("configured") is True


def fake_settings() -> Settings:
    return Settings(
        ENVIRONMENT="test",
        LLM_PROVIDER="kimi_coding",
        MOONSHOT_API_KEY="moonshot-key",
        MOONSHOT_MODEL="kimi-for-coding",
        PRODUCT_HUNT_API_TOKEN="",
        ALPHA_VANTAGE_API_KEY="alpha-key",
        CHINESE_RSS_FEEDS="https://example.com/feed.xml",
    )


@pytest.mark.anyio
async def test_health_check_reports_readiness_without_exposing_secrets(monkeypatch) -> None:
    settings = fake_settings()
    monkeypatch.setattr("app.api.routes.health.get_settings", lambda: settings)

    response = await health_check()

    assert response.status == "ok"
    assert response.environment == "test"
    assert response.llm_model == "kimi-for-coding"
    assert response.llm_configured is True
    assert response.integrations.kimi_coding_api is True
    assert response.integrations.product_hunt_api is False
    assert response.integrations.alpha_vantage_api is True
    assert response.integrations.chinese_rss_feeds is True
    assert "moonshot-key" not in response.model_dump_json()

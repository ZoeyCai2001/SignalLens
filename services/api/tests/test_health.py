import pytest

from app.api.routes.health import (
    build_missing_env_template,
    build_setup_summary,
    build_setup_items,
    has_custom_sec_user_agent,
    has_config_value,
    health_check,
)
from app.core.config import DEFAULT_SEC_USER_AGENT, Settings
from app.schemas.health import IntegrationStatus


def test_has_config_value_rejects_empty_strings() -> None:
    assert has_config_value(None) is False
    assert has_config_value("") is False
    assert has_config_value("   ") is False
    assert has_config_value("configured") is True


def test_has_custom_sec_user_agent_rejects_default_placeholder() -> None:
    assert has_custom_sec_user_agent(None) is False
    assert has_custom_sec_user_agent("") is False
    assert has_custom_sec_user_agent(DEFAULT_SEC_USER_AGENT) is False
    assert has_custom_sec_user_agent("SignalLens/0.1 zoey@example.com") is True


def fake_settings() -> Settings:
    return Settings(
        ENVIRONMENT="test",
        LLM_PROVIDER="kimi_coding",
        MOONSHOT_API_KEY="moonshot-key",
        MOONSHOT_MODEL="kimi-for-coding",
        GITHUB_TOKEN="github-key",
        PRODUCT_HUNT_API_TOKEN="",
        ALPHA_VANTAGE_API_KEY="alpha-key",
        SEC_USER_AGENT="SignalLens/0.1 zoey@example.com",
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
    assert response.integrations.github_api is True
    assert response.integrations.product_hunt_api is False
    assert response.integrations.alpha_vantage_api is True
    assert response.integrations.sec_user_agent is True
    assert response.integrations.chinese_rss_feeds is True
    assert {item.env_var for item in response.setup_items} == {
        "MOONSHOT_API_KEY",
        "GITHUB_TOKEN",
        "ALPHA_VANTAGE_API_KEY",
        "SEC_USER_AGENT",
        "PRODUCT_HUNT_API_TOKEN",
        "CHINESE_RSS_FEEDS",
    }
    assert next(
        item for item in response.setup_items if item.env_var == "PRODUCT_HUNT_API_TOKEN"
    ).configured is False
    assert response.setup_summary.total == 6
    assert response.setup_summary.configured == 5
    assert response.setup_summary.missing == 1
    assert response.setup_summary.core_missing == 0
    assert response.setup_summary.recommended_missing == 0
    assert response.setup_summary.optional_missing == 1
    assert response.setup_summary.core_ready is True
    assert "PRODUCT_HUNT_API_TOKEN=your-product-hunt-token" in response.missing_env_template
    assert "MOONSHOT_API_KEY" not in response.missing_env_template
    assert next(item for item in response.setup_items if item.key == "kimi_coding_api").importance == "core"
    assert next(item for item in response.setup_items if item.key == "product_hunt_api").importance == "optional"
    assert "moonshot-key" not in response.model_dump_json()
    assert "github-key" not in response.model_dump_json()


def test_build_setup_items_reports_safe_env_hints_without_values() -> None:
    items = build_setup_items(
        settings=fake_settings(),
        integrations=IntegrationStatus(
            kimi_coding_api=True,
            github_api=True,
            product_hunt_api=False,
            alpha_vantage_api=True,
            sec_user_agent=True,
            chinese_rss_feeds=True,
        ),
    )

    assert [item.key for item in items] == [
        "kimi_coding_api",
        "github_api",
        "alpha_vantage_api",
        "sec_user_agent",
        "product_hunt_api",
        "chinese_rss_feeds",
    ]
    assert items[0].configured is True
    assert items[0].importance == "core"
    assert items[4].configured is False
    assert items[4].importance == "optional"
    assert "moonshot-key" not in " ".join(item.setup_hint for item in items)
    assert "github-key" not in " ".join(item.setup_hint for item in items)


def test_build_setup_summary_counts_missing_items_by_importance() -> None:
    items = build_setup_items(
        settings=fake_settings(),
        integrations=IntegrationStatus(
            kimi_coding_api=False,
            github_api=False,
            product_hunt_api=False,
            alpha_vantage_api=True,
            sec_user_agent=True,
            chinese_rss_feeds=True,
        ),
    )

    summary = build_setup_summary(items)

    assert summary.total == 6
    assert summary.configured == 3
    assert summary.missing == 3
    assert summary.core_missing == 1
    assert summary.recommended_missing == 1
    assert summary.optional_missing == 1
    assert summary.core_ready is False


def test_build_missing_env_template_uses_only_placeholders() -> None:
    items = build_setup_items(
        settings=fake_settings(),
        integrations=IntegrationStatus(
            kimi_coding_api=False,
            github_api=False,
            product_hunt_api=False,
            alpha_vantage_api=True,
            sec_user_agent=False,
            chinese_rss_feeds=True,
        ),
    )

    template = build_missing_env_template(items)

    assert "MOONSHOT_API_KEY=sk-..." in template
    assert "GITHUB_TOKEN=ghp_..." in template
    assert "SEC_USER_AGENT=SignalLens/0.1 your-email@example.com" in template
    assert "PRODUCT_HUNT_API_TOKEN=your-product-hunt-token" in template
    assert "ALPHA_VANTAGE_API_KEY" not in template
    assert "moonshot-key" not in template
    assert "github-key" not in template


def test_build_missing_env_template_returns_empty_when_ready() -> None:
    items = build_setup_items(
        settings=fake_settings(),
        integrations=IntegrationStatus(
            kimi_coding_api=True,
            github_api=True,
            product_hunt_api=True,
            alpha_vantage_api=True,
            sec_user_agent=True,
            chinese_rss_feeds=True,
        ),
    )

    assert build_missing_env_template(items) == ""

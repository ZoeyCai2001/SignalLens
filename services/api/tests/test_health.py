from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.routes.health import (
    build_quality_findings,
    build_missing_env_template,
    build_quality_metrics,
    build_setup_summary,
    build_setup_items,
    canonical_quality_url,
    duplicate_rate_for_items,
    digest_age_days,
    has_custom_sec_user_agent,
    has_config_value,
    health_check,
    normalize_quality_title,
)
from app.core.config import DEFAULT_SEC_USER_AGENT, Settings
from app.db.models import (
    Alert,
    AlertRule,
    Base,
    DailyDigestSnapshot,
    LlmUsageEvent,
    NormalizedItem,
    SourceRun,
    StockPricePoint,
    StockWatchlistItem,
    UserItemAction,
)
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


def test_build_quality_metrics_tracks_prd_quality_signals() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    now = datetime.now(UTC)

    with session_factory() as db:
        rule = AlertRule(
            id=1,
            user_id="local",
            name="High-impact stock signal",
            category="all",
            severity="high",
            min_importance_score=0.7,
            min_stock_impact_score=0,
            enabled=True,
        )
        db.add(rule)
        db.add_all(
            [
                make_quality_item(
                    1,
                    "OpenAI releases a new agent workflow",
                    url="https://example.com/agent?utm_source=newsletter",
                    published_at=now - timedelta(days=1),
                    relevance_score=0.9,
                    importance_score=0.8,
                    summary_short="Short summary",
                ),
                make_quality_item(
                    2,
                    "OpenAI releases a new agent workflow",
                    url="https://example.com/agent?utm_medium=social",
                    published_at=now - timedelta(days=1),
                    relevance_score=0.8,
                    importance_score=0.7,
                ),
                make_quality_item(
                    3,
                    "Low relevance market rumor",
                    url="https://example.com/rumor",
                    published_at=now - timedelta(days=2),
                    relevance_score=0.2,
                    importance_score=0.4,
                ),
                make_quality_item(
                    4,
                    "Hidden item should not count",
                    url="https://example.com/hidden",
                    published_at=now - timedelta(days=1),
                    relevance_score=1,
                    importance_score=1,
                ),
            ]
        )
        db.flush()
        db.add_all(
            [
                make_quality_alert(item_id=1, rule_id=rule.id, status="active"),
                make_quality_alert(item_id=2, rule_id=rule.id, status="dismissed"),
                UserItemAction(user_id="local", item_id=1, is_saved=True, is_read=True),
                UserItemAction(user_id="local", item_id=3, is_hidden=True),
                UserItemAction(user_id="local", item_id=4, is_hidden=True),
                SourceRun(
                    source_id=1,
                    status="success",
                    items_fetched=10,
                    items_stored=8,
                    started_at=now - timedelta(hours=2),
                ),
                SourceRun(
                    source_id=1,
                    status="failed",
                    items_fetched=0,
                    items_stored=0,
                    started_at=now - timedelta(hours=1),
                ),
                DailyDigestSnapshot(
                    user_id="local",
                    digest_date=now.date(),
                    generated_at=now - timedelta(hours=1),
                    headline="Digest",
                    total_items=2,
                    limit_per_section=5,
                    payload={
                        "digest_date": now.date().isoformat(),
                        "generated_at": now.isoformat(),
                        "headline": "Digest",
                        "total_items": 2,
                        "sections": [],
                        "source_coverage": [],
                        "disclaimer": "Informational only.",
                    },
                    markdown="# Digest\n",
                ),
                LlmUsageEvent(
                    user_id="local",
                    operation="summarize_item",
                    provider="kimi_coding",
                    model="kimi-for-coding",
                    item_id=1,
                    input_tokens=100,
                    output_tokens=20,
                    total_tokens=120,
                    created_at=now - timedelta(hours=1),
                ),
                LlmUsageEvent(
                    user_id="local",
                    operation="classify_item",
                    provider="kimi_coding",
                    model="kimi-for-coding",
                    item_id=2,
                    input_tokens=80,
                    output_tokens=10,
                    total_tokens=90,
                    created_at=now - timedelta(hours=1),
                ),
            ]
        )
        db.commit()

        metrics = build_quality_metrics(db=db, window_days=7)

    assert metrics.total_item_count == 2
    assert metrics.recent_item_count == 2
    assert metrics.recent_module_counts == {
        "trends": 2,
        "research": 0,
        "products": 0,
        "stocks": 0,
        "chinese": 0,
    }
    assert metrics.covered_module_count == 1
    assert metrics.high_value_item_count == 1
    assert metrics.high_value_unsummarized_count == 0
    assert metrics.classification_coverage == 1
    assert metrics.low_confidence_item_count == 0
    assert metrics.relevance_precision_proxy == 1
    assert metrics.duplicate_rate == 0.5
    assert metrics.summary_coverage == 0.5
    assert metrics.source_failure_rate == 0.5
    assert metrics.save_count == 1
    assert metrics.hide_count == 2
    assert metrics.saved_read_count == 1
    assert metrics.saved_read_later_count == 0
    assert metrics.save_hide_ratio == 0.5
    assert metrics.active_alert_count == 1
    assert metrics.dismissed_alert_count == 1
    assert metrics.alert_dismissal_rate == 0.5
    assert metrics.digest_snapshot_count == 1
    assert metrics.latest_digest_snapshot_date == now.date()
    assert metrics.latest_digest_age_days == 0
    assert metrics.latest_digest_snapshot_item_count == 2
    assert metrics.latest_stock_price_date is None
    assert metrics.latest_stock_price_age_days is None
    assert metrics.llm_call_count == 2
    assert metrics.llm_input_tokens == 180
    assert metrics.llm_output_tokens == 30
    assert metrics.llm_total_tokens == 210
    assert metrics.llm_calls_per_recent_item == 1
    assert [operation.operation for operation in metrics.llm_operation_usage] == [
        "summarize_item",
        "classify_item",
    ]
    assert metrics.llm_operation_usage[0].call_count == 1
    assert metrics.llm_operation_usage[0].total_tokens == 120
    assert metrics.llm_operation_usage[1].total_tokens == 90
    assert [finding.title for finding in metrics.quality_findings] == [
        "Duplicate pressure",
        "Source failures need review",
    ]
    assert metrics.quality_findings[0].action_module == "sources"
    assert metrics.quality_findings[0].action_source_filter == "attention"
    assert metrics.quality_findings[1].action_label == "Show Failed Runs"
    assert metrics.quality_findings[1].action_source_filter == "failed"


def test_build_quality_findings_recommends_local_actions() -> None:
    findings = build_quality_findings(
        recent_item_count=0,
        high_value_item_count=0,
        relevance_precision_proxy=0,
        duplicate_rate=0,
        summary_coverage=0,
        high_value_unsummarized_count=0,
        source_failure_rate=0,
        saved_read_later_count=0,
        save_count=0,
        active_alert_count=0,
        dismissed_alert_count=0,
        alert_dismissal_rate=0,
        digest_snapshot_count=0,
        latest_digest_snapshot_date=None,
        latest_digest_snapshot_item_count=None,
        llm_calls_per_recent_item=0,
    )

    assert [finding.title for finding in findings] == [
        "No recent items",
        "No saved digest snapshot",
    ]
    assert findings[0].severity == "warning"
    assert findings[0].action_label == "Run Full Cycle"
    assert findings[0].action_operation == "cycle"
    assert findings[0].action_source_filter == "attention"
    assert findings[1].action_module == "digest"
    assert findings[1].action_label == "Save Digest"
    assert findings[1].action_operation == "digest:save-snapshot"

    findings = build_quality_findings(
        recent_item_count=10,
        high_value_item_count=0,
        relevance_precision_proxy=0.5,
        duplicate_rate=0.3,
        summary_coverage=0.4,
        high_value_unsummarized_count=2,
        source_failure_rate=0.25,
        saved_read_later_count=5,
        save_count=6,
        active_alert_count=1,
        dismissed_alert_count=5,
        alert_dismissal_rate=0.833,
        digest_snapshot_count=1,
        latest_digest_snapshot_date=date(2026, 6, 30),
        latest_digest_snapshot_item_count=5,
        llm_calls_per_recent_item=1.6,
    )

    assert [finding.title for finding in findings] == [
        "Low relevance precision",
        "Duplicate pressure",
        "Summary coverage is thin",
        "High-value summaries missing",
        "Read-later backlog is high",
        "Alerts may be noisy",
        "Source failures need review",
        "LLM spend is high",
    ]
    assert findings[0].metric == "50% relevant"
    assert findings[-1].metric == "1.60 calls per recent item"
    assert [finding.action_module for finding in findings] == [
        "settings",
        "sources",
        "dashboard",
        "dashboard",
        "digest",
        "settings",
        "sources",
        "settings",
    ]
    assert findings[2].action_label == "Run Summaries"
    assert findings[2].action_operation == "llm:summarize"
    assert findings[3].action_operation == "llm:summarize"


def test_build_quality_findings_flags_stale_digest_snapshot() -> None:
    findings = build_quality_findings(
        recent_item_count=5,
        high_value_item_count=0,
        relevance_precision_proxy=0.8,
        duplicate_rate=0,
        summary_coverage=0.8,
        high_value_unsummarized_count=0,
        source_failure_rate=0,
        saved_read_later_count=0,
        save_count=0,
        active_alert_count=0,
        dismissed_alert_count=0,
        alert_dismissal_rate=0,
        digest_snapshot_count=1,
        latest_digest_snapshot_date=date(2026, 6, 29),
        latest_digest_snapshot_item_count=5,
        llm_calls_per_recent_item=0,
        current_date=date(2026, 6, 30),
    )

    assert [finding.title for finding in findings] == ["Digest snapshot is stale"]
    assert findings[0].metric == "last saved 2026-06-29"
    assert findings[0].action_label == "Save Digest"
    assert findings[0].action_module == "digest"
    assert findings[0].action_operation == "digest:save-snapshot"


def test_build_quality_findings_flags_thin_module_coverage() -> None:
    findings = build_quality_findings(
        recent_item_count=8,
        high_value_item_count=0,
        relevance_precision_proxy=0.8,
        duplicate_rate=0,
        summary_coverage=0.8,
        high_value_unsummarized_count=0,
        source_failure_rate=0,
        saved_read_later_count=0,
        save_count=0,
        active_alert_count=1,
        dismissed_alert_count=0,
        alert_dismissal_rate=0,
        digest_snapshot_count=1,
        latest_digest_snapshot_date=date(2026, 6, 30),
        latest_digest_snapshot_item_count=5,
        llm_calls_per_recent_item=0,
        covered_module_count=1,
        total_module_count=5,
    )

    assert [finding.title for finding in findings] == ["Module coverage is thin"]
    assert findings[0].metric == "1/5 modules active"
    assert findings[0].action_label == "Run Full Cycle"
    assert findings[0].action_module == "sources"
    assert findings[0].action_operation == "cycle"
    assert findings[0].action_source_filter == "attention"


def test_build_quality_findings_flags_thin_digest_snapshot() -> None:
    findings = build_quality_findings(
        recent_item_count=8,
        high_value_item_count=0,
        relevance_precision_proxy=0.8,
        duplicate_rate=0,
        summary_coverage=0.8,
        high_value_unsummarized_count=0,
        source_failure_rate=0,
        saved_read_later_count=0,
        save_count=0,
        active_alert_count=1,
        dismissed_alert_count=0,
        alert_dismissal_rate=0,
        digest_snapshot_count=1,
        latest_digest_snapshot_date=date(2026, 6, 30),
        latest_digest_snapshot_item_count=1,
        llm_calls_per_recent_item=0,
        current_date=date(2026, 6, 30),
    )

    assert [finding.title for finding in findings] == ["Digest snapshot is thin"]
    assert findings[0].metric == "1 saved digest items"
    assert findings[0].action_label == "Save Digest"
    assert findings[0].action_module == "digest"
    assert findings[0].action_operation == "digest:save-snapshot"


def test_build_quality_findings_flags_low_classification_confidence() -> None:
    findings = build_quality_findings(
        recent_item_count=8,
        high_value_item_count=0,
        relevance_precision_proxy=0.8,
        duplicate_rate=0,
        summary_coverage=0.8,
        high_value_unsummarized_count=0,
        source_failure_rate=0,
        saved_read_later_count=0,
        save_count=0,
        active_alert_count=1,
        dismissed_alert_count=0,
        alert_dismissal_rate=0,
        digest_snapshot_count=1,
        latest_digest_snapshot_date=date(2026, 6, 30),
        latest_digest_snapshot_item_count=5,
        llm_calls_per_recent_item=0,
        classification_coverage=0.5,
        low_confidence_item_count=4,
    )

    assert [finding.title for finding in findings] == ["Classification confidence is thin"]
    assert findings[0].metric == "50% high-confidence"
    assert findings[0].action_label == "Run Classification"
    assert findings[0].action_module == "dashboard"
    assert findings[0].action_operation == "llm:classify"


def test_build_quality_metrics_flags_missing_stock_prices_for_watchlist() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add(make_stock_watchlist_item("MU"))
        db.commit()

        metrics = build_quality_metrics(db=db, window_days=7)

    assert metrics.latest_stock_price_date is None
    assert metrics.latest_stock_price_age_days is None
    assert [finding.title for finding in metrics.quality_findings] == [
        "No recent items",
        "Stock prices are missing",
        "No saved digest snapshot",
    ]
    assert metrics.quality_findings[1].metric == "1 watched tickers need price data"
    assert metrics.quality_findings[1].action_label == "Refresh Prices"
    assert metrics.quality_findings[1].action_module == "stocks"
    assert metrics.quality_findings[1].action_operation == "stock-prices:refresh"


def test_build_quality_findings_flags_stale_stock_prices() -> None:
    findings = build_quality_findings(
        recent_item_count=5,
        high_value_item_count=0,
        relevance_precision_proxy=0.8,
        duplicate_rate=0,
        summary_coverage=0.8,
        high_value_unsummarized_count=0,
        source_failure_rate=0,
        saved_read_later_count=0,
        save_count=0,
        active_alert_count=0,
        dismissed_alert_count=0,
        alert_dismissal_rate=0,
        digest_snapshot_count=1,
        latest_digest_snapshot_date=date(2026, 6, 30),
        latest_digest_snapshot_item_count=5,
        llm_calls_per_recent_item=0,
        latest_stock_price_date=date(2026, 6, 27),
        stock_watchlist_count=2,
        current_date=date(2026, 6, 30),
    )

    assert [finding.title for finding in findings] == ["Stock prices are stale"]
    assert findings[0].metric == "latest close 2026-06-27"
    assert findings[0].action_label == "Refresh Prices"
    assert findings[0].action_module == "stocks"
    assert findings[0].action_operation == "stock-prices:refresh"


def test_build_quality_metrics_tracks_latest_watched_stock_price_date() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    today = datetime.now(UTC).date()

    with session_factory() as db:
        db.add_all(
            [
                make_stock_watchlist_item("MU"),
                make_stock_price_point("MU", today - timedelta(days=1)),
                make_stock_price_point("UNWATCHED", today),
            ]
        )
        db.commit()

        metrics = build_quality_metrics(db=db, window_days=7)

    assert metrics.latest_stock_price_date == today - timedelta(days=1)
    assert metrics.latest_stock_price_age_days == 1
    assert "Stock prices are missing" not in [
        finding.title for finding in metrics.quality_findings
    ]
    assert "Stock prices are stale" not in [finding.title for finding in metrics.quality_findings]


def test_build_quality_metrics_tracks_recent_prd_module_coverage() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    now = datetime.now(UTC)

    with session_factory() as db:
        db.add_all(
            [
                make_quality_item(
                    1,
                    "Agent routing trend",
                    url="https://example.com/trend",
                    published_at=now,
                    category="technical_trend",
                ),
                make_quality_item(
                    2,
                    "New benchmark paper",
                    url="https://example.com/paper",
                    published_at=now,
                    category="research",
                ),
                make_quality_item(
                    3,
                    "New AI product launch",
                    url="https://example.com/product",
                    published_at=now,
                    category="technical_trend",
                    products=["Agent IDE"],
                ),
                make_quality_item(
                    4,
                    "MU AI demand update",
                    url="https://example.com/stock",
                    published_at=now,
                    category="technical_trend",
                    tickers=["MU"],
                ),
                make_quality_item(
                    5,
                    "Chinese social AI trend",
                    url="https://example.com/chinese",
                    published_at=now,
                    category="technical_trend",
                    language="zh",
                ),
            ]
        )
        db.commit()

        metrics = build_quality_metrics(db=db, window_days=7)

    assert metrics.recent_module_counts == {
        "trends": 4,
        "research": 1,
        "products": 1,
        "stocks": 1,
        "chinese": 1,
    }
    assert metrics.covered_module_count == 5
    assert "Module coverage is thin" not in [
        finding.title for finding in metrics.quality_findings
    ]


def test_digest_age_days_tracks_latest_saved_digest_freshness() -> None:
    assert digest_age_days(date(2026, 6, 30), date(2026, 6, 30)) == 0
    assert digest_age_days(date(2026, 6, 28), date(2026, 6, 30)) == 2
    assert digest_age_days(None, date(2026, 6, 30)) is None


def test_build_quality_findings_flags_high_value_summary_gap() -> None:
    findings = build_quality_findings(
        recent_item_count=5,
        high_value_item_count=0,
        relevance_precision_proxy=0.8,
        duplicate_rate=0,
        summary_coverage=0.8,
        high_value_unsummarized_count=3,
        source_failure_rate=0,
        saved_read_later_count=0,
        save_count=0,
        active_alert_count=0,
        dismissed_alert_count=0,
        alert_dismissal_rate=0,
        digest_snapshot_count=1,
        latest_digest_snapshot_date=date(2026, 6, 30),
        latest_digest_snapshot_item_count=5,
        llm_calls_per_recent_item=0,
    )

    assert [finding.title for finding in findings] == ["High-value summaries missing"]
    assert findings[0].metric == "3 high-value unsummarized"
    assert findings[0].action_label == "Run Summaries"
    assert findings[0].action_module == "dashboard"
    assert findings[0].action_operation == "llm:summarize"


def test_build_quality_findings_flags_read_later_backlog() -> None:
    findings = build_quality_findings(
        recent_item_count=10,
        high_value_item_count=0,
        relevance_precision_proxy=0.8,
        duplicate_rate=0,
        summary_coverage=0.8,
        high_value_unsummarized_count=0,
        source_failure_rate=0,
        saved_read_later_count=5,
        save_count=6,
        active_alert_count=0,
        dismissed_alert_count=0,
        alert_dismissal_rate=0,
        digest_snapshot_count=1,
        latest_digest_snapshot_date=date(2026, 6, 30),
        latest_digest_snapshot_item_count=5,
        llm_calls_per_recent_item=0,
    )

    assert [finding.title for finding in findings] == ["Read-later backlog is high"]
    assert findings[0].metric == "5 saved unread"
    assert findings[0].action_label == "Open Daily Digest"
    assert findings[0].action_module == "digest"


def test_build_quality_findings_ignores_small_read_later_queue() -> None:
    findings = build_quality_findings(
        recent_item_count=10,
        high_value_item_count=0,
        relevance_precision_proxy=0.8,
        duplicate_rate=0,
        summary_coverage=0.8,
        high_value_unsummarized_count=0,
        source_failure_rate=0,
        saved_read_later_count=4,
        save_count=4,
        active_alert_count=0,
        dismissed_alert_count=0,
        alert_dismissal_rate=0,
        digest_snapshot_count=1,
        latest_digest_snapshot_date=date(2026, 6, 30),
        latest_digest_snapshot_item_count=5,
        llm_calls_per_recent_item=0,
    )

    assert findings == []


def test_build_quality_findings_flags_empty_alert_coverage_for_high_value_items() -> None:
    findings = build_quality_findings(
        recent_item_count=10,
        high_value_item_count=3,
        relevance_precision_proxy=0.8,
        duplicate_rate=0,
        summary_coverage=0.8,
        high_value_unsummarized_count=0,
        source_failure_rate=0,
        saved_read_later_count=0,
        save_count=0,
        active_alert_count=0,
        dismissed_alert_count=0,
        alert_dismissal_rate=0,
        digest_snapshot_count=1,
        latest_digest_snapshot_date=date(2026, 6, 30),
        latest_digest_snapshot_item_count=5,
        llm_calls_per_recent_item=0,
    )

    assert [finding.title for finding in findings] == ["Alert coverage is empty"]
    assert findings[0].metric == "3 high-value recent signals"
    assert findings[0].action_label == "Generate Alerts"
    assert findings[0].action_module == "dashboard"
    assert findings[0].action_operation == "alerts:generate"


def test_build_quality_findings_flags_noisy_alert_rules() -> None:
    findings = build_quality_findings(
        recent_item_count=10,
        high_value_item_count=0,
        relevance_precision_proxy=0.8,
        duplicate_rate=0,
        summary_coverage=0.8,
        high_value_unsummarized_count=0,
        source_failure_rate=0,
        saved_read_later_count=0,
        save_count=0,
        active_alert_count=1,
        dismissed_alert_count=5,
        alert_dismissal_rate=0.833,
        digest_snapshot_count=1,
        latest_digest_snapshot_date=date(2026, 6, 30),
        latest_digest_snapshot_item_count=5,
        llm_calls_per_recent_item=0,
    )

    assert [finding.title for finding in findings] == ["Alerts may be noisy"]
    assert findings[0].metric == "83% dismissed across 6 alerts"
    assert findings[0].action_label == "Review Settings"
    assert findings[0].action_module == "settings"


def test_build_quality_findings_ignores_tiny_alert_samples() -> None:
    findings = build_quality_findings(
        recent_item_count=10,
        high_value_item_count=0,
        relevance_precision_proxy=0.8,
        duplicate_rate=0,
        summary_coverage=0.8,
        high_value_unsummarized_count=0,
        source_failure_rate=0,
        saved_read_later_count=0,
        save_count=0,
        active_alert_count=0,
        dismissed_alert_count=4,
        alert_dismissal_rate=1,
        digest_snapshot_count=1,
        latest_digest_snapshot_date=date(2026, 6, 30),
        latest_digest_snapshot_item_count=5,
        llm_calls_per_recent_item=0,
    )

    assert findings == []


def test_quality_duplicate_helpers_ignore_tracking_noise() -> None:
    assert (
        canonical_quality_url("https://Example.com/path/?utm_source=x&b=2&a=1#fragment")
        == "https://example.com/path?a=1&b=2"
    )
    assert normalize_quality_title("  OpenAI   releases   agent workflow  ") == (
        "openai releases agent workflow"
    )
    assert normalize_quality_title("Short") is None
    items = [
        make_quality_item(
            1,
            "OpenAI releases agent workflow",
            url="https://example.com/a?utm_source=x",
        ),
        make_quality_item(
            2,
            "OpenAI releases agent workflow",
            url="https://example.com/a?utm_medium=y",
        ),
        make_quality_item(3, "Different useful item", url="https://example.com/b"),
    ]
    assert duplicate_rate_for_items(items) == pytest.approx(1 / 3, abs=0.001)


def make_quality_item(
    item_id: int,
    title: str,
    url: str,
    published_at: datetime | None = None,
    relevance_score: float = 0.7,
    importance_score: float = 0.7,
    summary_short: str | None = None,
    category: str = "technical_trend",
    language: str = "en",
    source_name: str = "Test Source",
    products: list[str] | None = None,
    tickers: list[str] | None = None,
) -> NormalizedItem:
    return NormalizedItem(
        id=item_id,
        raw_item_id=item_id,
        title=title,
        url=url,
        source_name=source_name,
        language=language,
        published_at=published_at or datetime.now(UTC),
        text=title,
        category=category,
        tickers=tickers or [],
        companies=[],
        products=products or [],
        topics=["agent"],
        sentiment="neutral",
        relevance_score=relevance_score,
        classification_confidence=0.8,
        importance_score=importance_score,
        novelty_score=0.6,
        source_quality_score=0.7,
        stock_impact_score=0,
        summary_short=summary_short,
    )


def make_quality_alert(item_id: int, rule_id: int, status: str) -> Alert:
    return Alert(
        user_id="local",
        item_id=item_id,
        rule_id=rule_id,
        title=f"Alert {item_id}",
        reason="Test reason",
        severity="high",
        status=status,
    )


def make_stock_watchlist_item(ticker: str) -> StockWatchlistItem:
    return StockWatchlistItem(
        user_id="local",
        ticker=ticker,
        company_name=f"{ticker} Inc.",
        exchange="NASDAQ",
        sector="Technology",
        industry="Semiconductors",
    )


def make_stock_price_point(ticker: str, price_date: date) -> StockPricePoint:
    return StockPricePoint(
        ticker=ticker,
        price_date=price_date,
        open_price=100,
        high_price=101,
        low_price=99,
        close_price=100,
        adjusted_close=100,
        volume=1_000,
    )

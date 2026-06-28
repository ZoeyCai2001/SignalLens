from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Alert, AlertRule, Base, NormalizedItem, UserItemAction
from app.schemas.feed import FeedItem
from app.services.alerts import (
    CROSS_SOURCE_CLUSTER_CATEGORY,
    alert_reason,
    clean_terms,
    generate_alerts,
    list_alerts,
    cross_source_alert_reason,
    match_alert_rules,
    normalize_tickers,
)
from app.services.event_clustering import build_event_cluster


def test_alert_reason_matches_high_impact_stock_signal() -> None:
    item = make_item(
        category="stock_company_event",
        importance_score=0.8,
        stock_impact_score=0.5,
        tickers=["AVGO"],
    )
    rule = make_rule(
        category="stock_company_event",
        min_importance_score=0.68,
        min_stock_impact_score=0.35,
    )

    reason = alert_reason(item, rule)

    assert reason is not None
    assert "importance 80" in reason
    assert "confidence 72" in reason
    assert "source quality 80" in reason
    assert "stock impact 50" in reason
    assert "AVGO" in reason


def test_alert_reason_skips_low_importance_items() -> None:
    item = make_item(importance_score=0.4, stock_impact_score=0.8)
    rule = make_rule(min_importance_score=0.68, min_stock_impact_score=0.35)

    assert alert_reason(item, rule) is None


def test_alert_reason_skips_low_confidence_items() -> None:
    item = make_item(classification_confidence=0.5)
    rule = make_rule(min_importance_score=0.68)

    assert alert_reason(item, rule) is None


def test_alert_reason_skips_low_source_quality_items() -> None:
    item = make_item(source_quality_score=0.5)
    rule = make_rule(min_importance_score=0.68)

    assert alert_reason(item, rule) is None


def test_match_alert_rules_respects_topic_filters() -> None:
    item = make_item(topics=["inference", "open-source"])
    rules = [
        make_rule(name="Inference", topics=["inference"]),
        make_rule(name="Routing", topics=["model-routing"]),
    ]

    matches = match_alert_rules(item, rules)

    assert [match.rule.name for match in matches] == ["Inference"]


def test_match_alert_rules_skips_disabled_rules() -> None:
    item = make_item(topics=["inference"])
    rules = [
        make_rule(name="Disabled", topics=["inference"], enabled=False),
        make_rule(name="Enabled", topics=["inference"], enabled=True),
    ]

    matches = match_alert_rules(item, rules)

    assert [match.rule.name for match in matches] == ["Enabled"]


def test_match_alert_rules_skips_cross_source_rules_for_single_items() -> None:
    item = make_item(topics=["inference"])
    rules = [
        make_rule(
            name="Cross-source",
            category=CROSS_SOURCE_CLUSTER_CATEGORY,
            topics=["inference"],
        ),
    ]

    assert match_alert_rules(item, rules) == []


def test_cross_source_alert_reason_requires_multiple_source_cluster_match() -> None:
    cluster = build_event_cluster(
        "technical_trend|agent",
        [
            make_feed_item(1, "Agent harness launch", source_name="RSS"),
            make_feed_item(2, "Agent harness discussion", source_name="Hacker News"),
        ],
    )
    rule = make_rule(
        name="Cross-source confirmation",
        category=CROSS_SOURCE_CLUSTER_CATEGORY,
        min_importance_score=0.7,
        topics=["agent"],
    )

    reason = cross_source_alert_reason(cluster=cluster, rule=rule)

    assert reason is not None
    assert "2 related items" in reason
    assert "2 sources" in reason
    assert "confidence" in reason
    assert "topics agent" in reason


def test_cross_source_alert_reason_respects_rule_filters() -> None:
    cluster = build_event_cluster(
        "technical_trend|agent",
        [
            make_feed_item(1, "Agent harness launch", source_name="RSS"),
            make_feed_item(2, "Agent harness discussion", source_name="Hacker News"),
        ],
    )
    rule = make_rule(
        name="Cross-source confirmation",
        category=CROSS_SOURCE_CLUSTER_CATEGORY,
        min_importance_score=0.7,
        topics=["model-routing"],
    )

    assert cross_source_alert_reason(cluster=cluster, rule=rule) is None


def test_cross_source_alert_reason_requires_cluster_confidence() -> None:
    cluster = build_event_cluster(
        "technical_trend|agent",
        [
            make_feed_item(1, "Agent harness launch", source_name="RSS", confidence=0.45),
            make_feed_item(2, "Agent harness discussion", source_name="Hacker News", confidence=0.45),
        ],
    )
    rule = make_rule(
        name="Cross-source confirmation",
        category=CROSS_SOURCE_CLUSTER_CATEGORY,
        min_importance_score=0.7,
        topics=["agent"],
    )

    assert cross_source_alert_reason(cluster=cluster, rule=rule) is None


def test_alert_rule_input_helpers_clean_terms_and_tickers() -> None:
    assert clean_terms([" inference ", "Inference", "", "agents"]) == ["inference", "agents"]
    assert normalize_tickers([" mu ", "$avgo"]) == ["MU", "AVGO"]


def test_generate_alerts_excludes_blocked_and_hidden_items() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add(make_rule(category="all", min_importance_score=0.7))
        db.add_all(
            [
                make_item(item_id=1, title="Blocked source signal", source_name="Noisy Blog"),
                make_item(item_id=2, title="Hidden source signal", source_name="Trusted Blog"),
                make_item(item_id=3, title="Visible source signal", source_name="Trusted Blog"),
            ]
        )
        db.add(
            UserItemAction(
                user_id="local",
                item_id=2,
                is_hidden=True,
            )
        )
        db.commit()

        result = generate_alerts(db, blocked_sources=["Noisy Blog"])

        alerts = db.query(Alert).all()
        assert result.alerts_created == 2
        assert result.active_alerts == 2
        assert {alert.title for alert in alerts} == {"Visible source signal"}


def test_list_alerts_excludes_blocked_and_hidden_items() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        rule = make_rule(category="all", min_importance_score=0.7)
        db.add(rule)
        db.add_all(
            [
                make_item(item_id=1, title="Blocked source signal", source_name="Noisy Blog"),
                make_item(item_id=2, title="Hidden source signal", source_name="Trusted Blog"),
                make_item(item_id=3, title="Visible source signal", source_name="Trusted Blog"),
            ]
        )
        db.flush()
        db.add_all(
            [
                make_alert(item_id=1, rule_id=rule.id, title="Blocked source signal"),
                make_alert(item_id=2, rule_id=rule.id, title="Hidden source signal"),
                make_alert(item_id=3, rule_id=rule.id, title="Visible source signal"),
                UserItemAction(user_id="local", item_id=2, is_hidden=True),
            ]
        )
        db.commit()

        visible_alerts = list_alerts(db, include_dismissed=True, blocked_sources=["Noisy Blog"])

    assert [alert.title for alert in visible_alerts] == ["Visible source signal"]


def make_item(
    item_id: int = 1,
    title: str = "OpenAI and Broadcom inference chip signal",
    source_name: str = "Test Source",
    category: str = "technical_trend",
    importance_score: float = 0.9,
    stock_impact_score: float = 0,
    classification_confidence: float = 0.72,
    source_quality_score: float = 0.8,
    tickers: list[str] | None = None,
    topics: list[str] | None = None,
) -> NormalizedItem:
    return NormalizedItem(
        id=item_id,
        raw_item_id=item_id,
        title=title,
        url=f"https://example.com/{item_id}",
        source_name=source_name,
        language="en",
        category=category,
        tickers=tickers or [],
        companies=[],
        products=[],
        topics=topics or [],
        sentiment="neutral",
        relevance_score=0.8,
        classification_confidence=classification_confidence,
        importance_score=importance_score,
        novelty_score=0.7,
        source_quality_score=source_quality_score,
        stock_impact_score=stock_impact_score,
    )


def make_alert(item_id: int, rule_id: int, title: str) -> Alert:
    return Alert(
        user_id="local",
        item_id=item_id,
        rule_id=rule_id,
        title=title,
        reason="Test reason",
        severity="high",
        status="active",
    )


def make_rule(
    name: str = "High-impact stock signal",
    category: str = "all",
    severity: str = "high",
    min_importance_score: float = 0.7,
    min_stock_impact_score: float = 0,
    tickers: list[str] | None = None,
    topics: list[str] | None = None,
    enabled: bool = True,
) -> AlertRule:
    return AlertRule(
        id=1,
        user_id="local",
        name=name,
        category=category,
        severity=severity,
        min_importance_score=min_importance_score,
        min_stock_impact_score=min_stock_impact_score,
        tickers=tickers or [],
        topics=topics or [],
        enabled=enabled,
    )


def make_feed_item(
    item_id: int,
    title: str,
    source_name: str,
    confidence: float = 0.72,
) -> FeedItem:
    return FeedItem(
        id=item_id,
        title=title,
        url=f"https://example.com/{item_id}",
        source_name=source_name,
        author=None,
        language="en",
        published_at=datetime(2026, 6, 25, 12, item_id, tzinfo=UTC),
        category="technical_trend",
        subcategory=None,
        tickers=[],
        companies=[],
        products=[],
        topics=["agent"],
        sentiment="neutral",
        relevance_score=0.8,
        classification_confidence=confidence,
        importance_score=0.75,
        novelty_score=0.7,
        source_quality_score=0.7,
        stock_impact_score=0,
        summary_short=None,
        summary_detailed=None,
        why_it_matters=None,
    )

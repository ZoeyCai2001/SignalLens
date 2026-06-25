from app.db.models import AlertRule, NormalizedItem
from app.services.alerts import alert_reason, clean_terms, match_alert_rules, normalize_tickers


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
    assert "stock impact 50" in reason
    assert "AVGO" in reason


def test_alert_reason_skips_low_importance_items() -> None:
    item = make_item(importance_score=0.4, stock_impact_score=0.8)
    rule = make_rule(min_importance_score=0.68, min_stock_impact_score=0.35)

    assert alert_reason(item, rule) is None


def test_match_alert_rules_respects_topic_filters() -> None:
    item = make_item(topics=["inference", "open-source"])
    rules = [
        make_rule(name="Inference", topics=["inference"]),
        make_rule(name="Routing", topics=["model-routing"]),
    ]

    matches = match_alert_rules(item, rules)

    assert [match.rule.name for match in matches] == ["Inference"]


def test_alert_rule_input_helpers_clean_terms_and_tickers() -> None:
    assert clean_terms([" inference ", "Inference", "", "agents"]) == ["inference", "agents"]
    assert normalize_tickers([" mu ", "$avgo"]) == ["MU", "AVGO"]


def make_item(
    category: str = "technical_trend",
    importance_score: float = 0.9,
    stock_impact_score: float = 0,
    tickers: list[str] | None = None,
    topics: list[str] | None = None,
) -> NormalizedItem:
    return NormalizedItem(
        id=1,
        raw_item_id=1,
        title="OpenAI and Broadcom inference chip signal",
        url="https://example.com",
        source_name="Test Source",
        language="en",
        category=category,
        tickers=tickers or [],
        companies=[],
        products=[],
        topics=topics or [],
        sentiment="neutral",
        relevance_score=0.8,
        importance_score=importance_score,
        novelty_score=0.7,
        source_quality_score=0.8,
        stock_impact_score=stock_impact_score,
    )


def make_rule(
    name: str = "High-impact stock signal",
    category: str = "all",
    severity: str = "high",
    min_importance_score: float = 0.7,
    min_stock_impact_score: float = 0,
    tickers: list[str] | None = None,
    topics: list[str] | None = None,
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
        enabled=True,
    )

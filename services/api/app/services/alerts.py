from dataclasses import dataclass

from sqlalchemy.orm import Session, joinedload

from app.db.models import Alert, AlertRule, NormalizedItem
from app.schemas.alerts import AlertGenerationResult, AlertItem
from app.services.feed_actions import LOCAL_USER_ID, get_action, serialize_feed_item
from app.services.watchlist import NON_FINANCIAL_ADVICE_DISCLAIMER


@dataclass(frozen=True)
class AlertMatch:
    rule: AlertRule
    severity: str
    reason: str


DEFAULT_ALERT_RULES = [
    {
        "name": "High-impact stock signal",
        "description": "AI-related item with strong stock relevance for watched companies.",
        "category": "stock_company_event",
        "severity": "high",
        "min_importance_score": 0.68,
        "min_stock_impact_score": 0.35,
        "tickers": [],
        "topics": [],
    },
    {
        "name": "Important AI development",
        "description": "High-importance AI research, product, or infrastructure signal.",
        "category": "all",
        "severity": "medium",
        "min_importance_score": 0.82,
        "min_stock_impact_score": 0,
        "tickers": [],
        "topics": [],
    },
]


def seed_default_alert_rules(db: Session) -> int:
    existing = {
        rule.name
        for rule in db.query(AlertRule).filter(AlertRule.user_id == LOCAL_USER_ID).all()
    }
    created = 0
    for payload in DEFAULT_ALERT_RULES:
        if payload["name"] in existing:
            continue
        db.add(AlertRule(user_id=LOCAL_USER_ID, enabled=True, **payload))
        created += 1
    if created:
        db.commit()
    return created


def generate_alerts(db: Session, limit: int = 100) -> AlertGenerationResult:
    rules_seeded = seed_default_alert_rules(db)
    rules = (
        db.query(AlertRule)
        .filter(AlertRule.user_id == LOCAL_USER_ID, AlertRule.enabled.is_(True))
        .order_by(AlertRule.severity.desc(), AlertRule.id.asc())
        .all()
    )
    items = (
        db.query(NormalizedItem)
        .order_by(
            NormalizedItem.importance_score.desc(),
            NormalizedItem.stock_impact_score.desc(),
            NormalizedItem.published_at.desc().nullslast(),
            NormalizedItem.created_at.desc(),
        )
        .limit(limit)
        .all()
    )
    created = 0
    for item in items:
        for match in match_alert_rules(item, rules):
            existing = (
                db.query(Alert)
                .filter(
                    Alert.user_id == LOCAL_USER_ID,
                    Alert.item_id == item.id,
                    Alert.rule_id == match.rule.id,
                )
                .one_or_none()
            )
            if existing:
                continue
            db.add(
                Alert(
                    user_id=LOCAL_USER_ID,
                    item_id=item.id,
                    rule_id=match.rule.id,
                    title=item.title,
                    reason=match.reason,
                    severity=match.severity,
                    status="active",
                )
            )
            created += 1
    if created:
        db.commit()
    return AlertGenerationResult(
        rules_seeded=rules_seeded,
        alerts_created=created,
        active_alerts=count_active_alerts(db),
    )


def match_alert_rules(item: NormalizedItem, rules: list[AlertRule]) -> list[AlertMatch]:
    matches: list[AlertMatch] = []
    for rule in rules:
        reason = alert_reason(item, rule)
        if reason is None:
            continue
        matches.append(AlertMatch(rule=rule, severity=rule.severity, reason=reason))
    return matches


def alert_reason(item: NormalizedItem, rule: AlertRule) -> str | None:
    if rule.category != "all" and item.category != rule.category:
        return None
    if item.importance_score < rule.min_importance_score:
        return None
    if item.stock_impact_score < rule.min_stock_impact_score:
        return None
    if rule.tickers and not set(normalize_list(rule.tickers)).intersection(
        normalize_list(item.tickers)
    ):
        return None
    if rule.topics and not set(normalize_list(rule.topics)).intersection(
        normalize_list(item.topics)
    ):
        return None

    score_bits = [f"importance {round(item.importance_score * 100)}"]
    if item.stock_impact_score:
        score_bits.append(f"stock impact {round(item.stock_impact_score * 100)}")
    if item.tickers:
        score_bits.append(f"tickers {', '.join(item.tickers[:4])}")
    return f"{rule.name}: " + ", ".join(score_bits)


def list_alerts(
    db: Session,
    limit: int = 20,
    include_dismissed: bool = False,
) -> list[AlertItem]:
    query = (
        db.query(Alert)
        .options(joinedload(Alert.item), joinedload(Alert.rule))
        .filter(Alert.user_id == LOCAL_USER_ID)
    )
    if not include_dismissed:
        query = query.filter(Alert.status == "active")
    rows = (
        query.order_by(
            Alert.status.asc(),
            Alert.severity.desc(),
            Alert.created_at.desc(),
            Alert.id.desc(),
        )
        .limit(limit)
        .all()
    )
    return [serialize_alert(db, alert) for alert in rows]


def dismiss_alert(db: Session, alert_id: int) -> Alert | None:
    alert = (
        db.query(Alert)
        .filter(Alert.user_id == LOCAL_USER_ID, Alert.id == alert_id)
        .one_or_none()
    )
    if alert is None:
        return None
    alert.status = "dismissed"
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def count_active_alerts(db: Session) -> int:
    return (
        db.query(Alert)
        .filter(Alert.user_id == LOCAL_USER_ID, Alert.status == "active")
        .count()
    )


def serialize_alert(db: Session, alert: Alert) -> AlertItem:
    return AlertItem(
        id=alert.id,
        title=alert.title,
        reason=alert.reason,
        severity=alert.severity,
        status=alert.status,
        created_at=alert.created_at,
        rule=alert.rule,
        item=serialize_feed_item(alert.item, get_action(db, alert.item_id)),
        disclaimer=NON_FINANCIAL_ADVICE_DISCLAIMER,
    )


def normalize_list(values: list[str]) -> list[str]:
    return [value.strip().lower() for value in values if value.strip()]

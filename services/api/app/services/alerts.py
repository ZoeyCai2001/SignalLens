from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session, joinedload

from app.db.models import (
    Alert,
    AlertRule,
    NormalizedItem,
    StockPricePoint,
    StockWatchlistItem,
    UserItemAction,
)
from app.schemas.alerts import AlertGenerationResult, AlertItem, AlertRuleCreate, AlertRuleUpdate
from app.schemas.events import EventCluster
from app.schemas.feed import FeedItem
from app.services.event_clustering import build_event_clusters_from_items
from app.services.feed_actions import (
    LOCAL_USER_ID,
    get_action,
    normalize_source_names,
    serialize_feed_item,
    social_signal_score_for_item,
)
from app.services.preferences import get_user_preferences
from app.services.watchlist import NON_FINANCIAL_ADVICE_DISCLAIMER, format_product_use_case_label

CROSS_SOURCE_CLUSTER_CATEGORY = "cross_source_cluster"
STOCK_PRICE_MOVE_CATEGORY = "stock_price_move"
EARNINGS_GUIDANCE_CATEGORY = "earnings_guidance"
ANALYST_ACTION_CATEGORY = "analyst_action"
SUPPLY_CHAIN_SIGNAL_CATEGORY = "supply_chain_signal"
THEME_BREAKOUT_CATEGORY = "theme_breakout"
SOCIAL_TREND_CATEGORY = "social_trend"
MIN_ALERT_CLASSIFICATION_CONFIDENCE = 0.55
MIN_ALERT_SOURCE_QUALITY = 0.55
MIN_CROSS_SOURCE_CLUSTER_CONFIDENCE = 0.65
MIN_PRICE_MOVE_ALERT_PERCENT = 5
MIN_THEME_BREAKOUT_ITEMS = 2
MIN_THEME_BREAKOUT_SOURCES = 2
MIN_SOCIAL_TREND_SCORE = 0.45

SPECIAL_STOCK_EVENT_TERMS = {
    EARNINGS_GUIDANCE_CATEGORY: [
        "earnings",
        "guidance",
        "revenue guidance",
        "data center revenue",
        "ai demand",
        "capex",
        "forecast",
    ],
    ANALYST_ACTION_CATEGORY: [
        "analyst",
        "upgrade",
        "downgrade",
        "price target",
        "rating",
        "overweight",
        "underweight",
    ],
    SUPPLY_CHAIN_SIGNAL_CATEGORY: [
        "supply chain",
        "supplier",
        "customer",
        "competitor",
        "export control",
        "capacity",
        "inventory",
    ],
}


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
    {
        "name": "Cross-source confirmation",
        "description": "Related AI signals appearing across multiple sources.",
        "category": CROSS_SOURCE_CLUSTER_CATEGORY,
        "severity": "high",
        "min_importance_score": 0.7,
        "min_stock_impact_score": 0,
        "tickers": [],
        "topics": [],
    },
    {
        "name": "Large price move with AI news",
        "description": (
            "Watched or rule-matched ticker moved sharply while related AI news is present."
        ),
        "category": STOCK_PRICE_MOVE_CATEGORY,
        "severity": "high",
        "min_importance_score": 0.6,
        "min_stock_impact_score": 0.25,
        "tickers": [],
        "topics": [],
    },
    {
        "name": "Earnings or guidance mention",
        "description": (
            "Stock-linked item mentions earnings, guidance, AI demand, revenue, or capex."
        ),
        "category": EARNINGS_GUIDANCE_CATEGORY,
        "severity": "high",
        "min_importance_score": 0.62,
        "min_stock_impact_score": 0.25,
        "tickers": [],
        "topics": [],
    },
    {
        "name": "Analyst action",
        "description": (
            "Stock-linked item mentions analyst rating, upgrade, downgrade, or price target."
        ),
        "category": ANALYST_ACTION_CATEGORY,
        "severity": "medium",
        "min_importance_score": 0.6,
        "min_stock_impact_score": 0.2,
        "tickers": [],
        "topics": [],
    },
    {
        "name": "Supply chain signal",
        "description": (
            "Stock-linked item mentions suppliers, customers, competitors, export controls, "
            "or capacity."
        ),
        "category": SUPPLY_CHAIN_SIGNAL_CATEGORY,
        "severity": "medium",
        "min_importance_score": 0.62,
        "min_stock_impact_score": 0.25,
        "tickers": [],
        "topics": [],
    },
    {
        "name": "Theme breakout",
        "description": (
            "A watched AI theme appears across multiple sources in recent high-quality items."
        ),
        "category": THEME_BREAKOUT_CATEGORY,
        "severity": "medium",
        "min_importance_score": 0.65,
        "min_stock_impact_score": 0,
        "tickers": [],
        "topics": [],
    },
    {
        "name": "Viral AI product or social trend",
        "description": (
            "A social, community, or product signal shows strong engagement, novelty, or "
            "Chinese/social-platform traction."
        ),
        "category": SOCIAL_TREND_CATEGORY,
        "severity": "medium",
        "min_importance_score": 0.62,
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


def list_alert_rules(db: Session) -> list[AlertRule]:
    seed_default_alert_rules(db)
    return (
        db.query(AlertRule)
        .filter(AlertRule.user_id == LOCAL_USER_ID)
        .order_by(AlertRule.enabled.desc(), AlertRule.severity.desc(), AlertRule.name.asc())
        .all()
    )


def create_alert_rule(db: Session, payload: AlertRuleCreate) -> AlertRule:
    name = payload.name.strip()
    if not name:
        raise ValueError("Alert rule name is required.")
    if get_alert_rule_by_name(db, name):
        raise ValueError(f"{name} is already an alert rule.")

    rule = AlertRule(
        user_id=LOCAL_USER_ID,
        name=name,
        description=payload.description.strip() if payload.description else None,
        category=payload.category.strip() or "all",
        severity=payload.severity.strip() or "medium",
        min_importance_score=clamp_alert_score(payload.min_importance_score),
        min_stock_impact_score=clamp_alert_score(payload.min_stock_impact_score),
        tickers=normalize_tickers(payload.tickers),
        topics=clean_terms(payload.topics),
        enabled=payload.enabled,
        snoozed_until=payload.snoozed_until,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def update_alert_rule(db: Session, rule_id: int, payload: AlertRuleUpdate) -> AlertRule | None:
    rule = get_alert_rule(db, rule_id)
    if rule is None:
        return None

    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates and updates["name"] is not None:
        name = updates["name"].strip()
        if not name:
            raise ValueError("Alert rule name is required.")
        existing = get_alert_rule_by_name(db, name)
        if existing and existing.id != rule.id:
            raise ValueError(f"{name} is already an alert rule.")
        updates["name"] = name

    for field_name, value in updates.items():
        if field_name == "tickers" and value is not None:
            value = normalize_tickers(value)
        elif field_name == "topics" and value is not None:
            value = clean_terms(value)
        elif field_name in {"category", "severity"} and isinstance(value, str):
            normalized_text = value.strip()
            if not normalized_text:
                continue
            value = normalized_text
        elif field_name == "description" and isinstance(value, str):
            value = value.strip() or None
        elif field_name in {"min_importance_score", "min_stock_impact_score"} and value is not None:
            value = clamp_alert_score(value)
        elif isinstance(value, str):
            value = value.strip()
        setattr(rule, field_name, value)

    if updates.get("enabled") is False or (
        "snoozed_until" in updates and is_alert_rule_snoozed(rule)
    ):
        dismiss_active_alerts_for_rule(db=db, rule_id=rule.id)

    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def delete_alert_rule(db: Session, rule_id: int) -> bool:
    rule = get_alert_rule(db, rule_id)
    if rule is None:
        return False
    db.query(Alert).filter(Alert.user_id == LOCAL_USER_ID, Alert.rule_id == rule.id).delete()
    db.delete(rule)
    db.commit()
    return True


def clamp_alert_score(value: float) -> float:
    return min(max(float(value), 0), 1)


def get_alert_rule(db: Session, rule_id: int) -> AlertRule | None:
    return (
        db.query(AlertRule)
        .filter(AlertRule.user_id == LOCAL_USER_ID, AlertRule.id == rule_id)
        .one_or_none()
    )


def get_alert_rule_by_name(db: Session, name: str) -> AlertRule | None:
    return (
        db.query(AlertRule)
        .filter(AlertRule.user_id == LOCAL_USER_ID, AlertRule.name == name.strip())
        .one_or_none()
    )


def generate_alerts(
    db: Session,
    limit: int = 100,
    blocked_sources: list[str] | None = None,
) -> AlertGenerationResult:
    rules_seeded = seed_default_alert_rules(db)
    if blocked_sources is None:
        blocked_sources = get_user_preferences(db).blocked_sources
    blocked_source_names = normalize_source_names(blocked_sources)
    rules = (
        db.query(AlertRule)
        .filter(AlertRule.user_id == LOCAL_USER_ID, AlertRule.enabled.is_(True))
        .order_by(AlertRule.severity.desc(), AlertRule.id.asc())
        .all()
    )
    rules = [rule for rule in rules if not is_alert_rule_snoozed(rule)]
    query = (
        db.query(NormalizedItem, UserItemAction)
        .outerjoin(
            UserItemAction,
            (UserItemAction.item_id == NormalizedItem.id)
            & (UserItemAction.user_id == LOCAL_USER_ID),
        )
        .filter((UserItemAction.is_hidden.is_(False)) | (UserItemAction.id.is_(None)))
    )
    if blocked_source_names:
        query = query.filter(~NormalizedItem.source_name.in_(blocked_source_names))

    rows = (
        query
        .order_by(
            NormalizedItem.importance_score.desc(),
            NormalizedItem.stock_impact_score.desc(),
            NormalizedItem.published_at.desc().nullslast(),
            NormalizedItem.created_at.desc(),
        )
        .limit(limit)
        .all()
    )
    items = [item for item, _action in rows]
    created = 0
    pending_alert_keys: set[tuple[int, int]] = set()
    for item in items:
        for match in match_alert_rules(item, rules):
            alert_key = (item.id, match.rule.id)
            if alert_key in pending_alert_keys:
                continue
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
            pending_alert_keys.add(alert_key)
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
    created += generate_cross_source_alerts(
        db=db,
        rules=rules,
        items=[serialize_feed_item(item) for item in items],
    )
    created += generate_price_move_alerts(db=db, rules=rules, items=items)
    created += generate_theme_breakout_alerts(db=db, rules=rules, items=items)
    if created:
        db.commit()
    return AlertGenerationResult(
        rules_seeded=rules_seeded,
        alerts_created=created,
        active_alerts=count_active_alerts(db, blocked_sources=blocked_sources),
    )


def match_alert_rules(item: NormalizedItem, rules: list[AlertRule]) -> list[AlertMatch]:
    matches: list[AlertMatch] = []
    for rule in rules:
        if not rule.enabled or is_alert_rule_snoozed(rule):
            continue
        if rule.category in {
            CROSS_SOURCE_CLUSTER_CATEGORY,
            STOCK_PRICE_MOVE_CATEGORY,
            THEME_BREAKOUT_CATEGORY,
        }:
            continue
        if rule.category == SOCIAL_TREND_CATEGORY:
            reason = social_trend_alert_reason(item, rule)
        elif rule.category in SPECIAL_STOCK_EVENT_TERMS:
            reason = stock_event_alert_reason(item, rule)
        else:
            reason = alert_reason(item, rule)
        if reason is None:
            continue
        matches.append(AlertMatch(rule=rule, severity=rule.severity, reason=reason))
    return matches


def is_alert_rule_snoozed(rule: AlertRule, now: datetime | None = None) -> bool:
    if rule.snoozed_until is None:
        return False
    now = now or datetime.now(UTC)
    snoozed_until = rule.snoozed_until
    if snoozed_until.tzinfo is None:
        snoozed_until = snoozed_until.replace(tzinfo=UTC)
    return snoozed_until > now


def generate_cross_source_alerts(
    db: Session,
    rules: list[AlertRule],
    items: list[FeedItem],
) -> int:
    cluster_rules = [
        rule
        for rule in rules
        if rule.enabled and rule.category == CROSS_SOURCE_CLUSTER_CATEGORY
    ]
    if not cluster_rules:
        return 0

    clusters = build_event_clusters_from_items(items=items, limit=30, min_items=2)
    created = 0
    pending_alert_keys: set[tuple[int, int]] = set()
    for cluster in clusters:
        if len(cluster.sources) < 2:
            continue
        for rule in cluster_rules:
            reason = cross_source_alert_reason(cluster=cluster, rule=rule)
            if reason is None:
                continue
            alert_key = (cluster.representative_item.id, rule.id)
            if alert_key in pending_alert_keys:
                continue
            existing = (
                db.query(Alert)
                .filter(
                    Alert.user_id == LOCAL_USER_ID,
                    Alert.item_id == cluster.representative_item.id,
                    Alert.rule_id == rule.id,
                )
                .one_or_none()
            )
            if existing:
                continue
            pending_alert_keys.add(alert_key)
            db.add(
                Alert(
                    user_id=LOCAL_USER_ID,
                    item_id=cluster.representative_item.id,
                    rule_id=rule.id,
                    title=cluster.title,
                    reason=reason,
                    severity=rule.severity,
                    status="active",
                )
            )
            created += 1
    return created


def generate_price_move_alerts(
    db: Session,
    rules: list[AlertRule],
    items: list[NormalizedItem],
) -> int:
    price_move_rules = [
        rule
        for rule in rules
        if rule.enabled and rule.category == STOCK_PRICE_MOVE_CATEGORY
    ]
    if not price_move_rules:
        return 0

    created = 0
    price_moves: dict[str, float | None] = {}
    pending_alert_keys: set[tuple[int, int]] = set()
    for item in items:
        for rule in price_move_rules:
            reason = price_move_alert_reason(db=db, item=item, rule=rule, price_moves=price_moves)
            if reason is None:
                continue
            alert_key = (item.id, rule.id)
            if alert_key in pending_alert_keys:
                continue
            existing = (
                db.query(Alert)
                .filter(
                    Alert.user_id == LOCAL_USER_ID,
                    Alert.item_id == item.id,
                    Alert.rule_id == rule.id,
                )
                .one_or_none()
            )
            if existing:
                continue
            pending_alert_keys.add(alert_key)
            db.add(
                Alert(
                    user_id=LOCAL_USER_ID,
                    item_id=item.id,
                    rule_id=rule.id,
                    title=item.title,
                    reason=reason,
                    severity=rule.severity,
                    status="active",
                )
            )
            created += 1
    return created


def generate_theme_breakout_alerts(
    db: Session,
    rules: list[AlertRule],
    items: list[NormalizedItem],
) -> int:
    theme_rules = [
        rule
        for rule in rules
        if rule.enabled and rule.category == THEME_BREAKOUT_CATEGORY
    ]
    if not theme_rules:
        return 0

    created = 0
    buckets = build_theme_breakout_buckets(items)
    pending_alert_keys: set[tuple[int, int]] = set()
    for theme, theme_items in buckets.items():
        sources = {item.source_name for item in theme_items}
        if len(theme_items) < MIN_THEME_BREAKOUT_ITEMS:
            continue
        if len(sources) < MIN_THEME_BREAKOUT_SOURCES:
            continue
        representative = max(
            theme_items,
            key=lambda item: (
                item.importance_score,
                item.source_quality_score,
                alert_item_sort_time(item),
            ),
        )
        for rule in theme_rules:
            reason = theme_breakout_alert_reason(
                theme=theme,
                items=theme_items,
                sources=sources,
                representative=representative,
                rule=rule,
            )
            if reason is None:
                continue
            alert_key = (representative.id, rule.id)
            if alert_key in pending_alert_keys:
                continue
            existing = (
                db.query(Alert)
                .filter(
                    Alert.user_id == LOCAL_USER_ID,
                    Alert.item_id == representative.id,
                    Alert.rule_id == rule.id,
                )
                .one_or_none()
            )
            if existing:
                continue
            pending_alert_keys.add(alert_key)
            db.add(
                Alert(
                    user_id=LOCAL_USER_ID,
                    item_id=representative.id,
                    rule_id=rule.id,
                    title=f"{rule.name}: {theme}",
                    reason=reason,
                    severity=rule.severity,
                    status="active",
                )
            )
            created += 1
    return created


def build_theme_breakout_buckets(
    items: list[NormalizedItem],
) -> dict[str, list[NormalizedItem]]:
    buckets: dict[str, list[NormalizedItem]] = {}
    for item in items:
        if item.importance_score < 0.55:
            continue
        if item.classification_confidence < MIN_ALERT_CLASSIFICATION_CONFIDENCE:
            continue
        if item.source_quality_score < MIN_ALERT_SOURCE_QUALITY:
            continue
        for topic in normalize_list(item.topics):
            buckets.setdefault(topic, []).append(item)
    return buckets


def theme_breakout_alert_reason(
    theme: str,
    items: list[NormalizedItem],
    sources: set[str],
    representative: NormalizedItem,
    rule: AlertRule,
) -> str | None:
    if representative.importance_score < rule.min_importance_score:
        return None
    if representative.stock_impact_score < rule.min_stock_impact_score:
        return None
    if rule.topics and theme not in normalize_list(rule.topics):
        return None
    theme_tickers = sorted({ticker for item in items for ticker in normalize_tickers(item.tickers)})
    if rule.tickers and not set(normalize_tickers(rule.tickers)).intersection(theme_tickers):
        return None

    score_bits = [
        f"theme {theme}",
        f"{len(items)} related items",
        f"{len(sources)} sources",
        f"importance {round(representative.importance_score * 100)}",
    ]
    if theme_tickers:
        score_bits.append(f"tickers {', '.join(theme_tickers[:4])}")
    return f"{rule.name}: " + ", ".join(score_bits)


def price_move_alert_reason(
    db: Session,
    item: NormalizedItem,
    rule: AlertRule,
    price_moves: dict[str, float | None] | None = None,
) -> str | None:
    if item.importance_score < rule.min_importance_score:
        return None
    if item.classification_confidence < MIN_ALERT_CLASSIFICATION_CONFIDENCE:
        return None
    if item.source_quality_score < MIN_ALERT_SOURCE_QUALITY:
        return None
    if item.stock_impact_score < rule.min_stock_impact_score:
        return None
    item_tickers = normalize_tickers(item.tickers)
    if not item_tickers:
        return None
    rule_tickers = set(normalize_tickers(rule.tickers))
    if rule_tickers:
        eligible_tickers = set(item_tickers).intersection(rule_tickers)
    else:
        watched_tickers = {
            ticker
            for (ticker,) in db.query(StockWatchlistItem.ticker)
            .filter(StockWatchlistItem.user_id == LOCAL_USER_ID)
            .all()
        }
        eligible_tickers = set(item_tickers).intersection(normalize_tickers(watched_tickers))

    if not eligible_tickers:
        return None
    if rule.topics and not set(normalize_list(rule.topics)).intersection(
        normalize_list(item.topics)
    ):
        return None

    cache = price_moves if price_moves is not None else {}
    matched_moves: list[tuple[str, float]] = []
    for ticker in sorted(eligible_tickers):
        ticker_key = ticker.upper()
        if ticker_key not in cache:
            cache[ticker_key] = latest_price_change_percent(db=db, ticker=ticker_key)
        change_percent = cache[ticker_key]
        if change_percent is None or abs(change_percent) < MIN_PRICE_MOVE_ALERT_PERCENT:
            continue
        matched_moves.append((ticker_key, change_percent))

    if not matched_moves:
        return None

    move_bits = [
        f"{ticker} {format_signed_percent(change_percent)}"
        for ticker, change_percent in matched_moves[:4]
    ]
    score_bits = [
        f"price move {', '.join(move_bits)}",
        f"importance {round(item.importance_score * 100)}",
        f"stock impact {round(item.stock_impact_score * 100)}",
        f"confidence {round(item.classification_confidence * 100)}",
    ]
    return f"{rule.name}: " + ", ".join(score_bits)


def stock_event_alert_reason(item: NormalizedItem, rule: AlertRule) -> str | None:
    if item.importance_score < rule.min_importance_score:
        return None
    if item.classification_confidence < MIN_ALERT_CLASSIFICATION_CONFIDENCE:
        return None
    if item.source_quality_score < MIN_ALERT_SOURCE_QUALITY:
        return None
    if item.stock_impact_score < rule.min_stock_impact_score:
        return None
    if not item.tickers and item.category != "stock_company_event":
        return None
    if rule.tickers and not set(normalize_tickers(rule.tickers)).intersection(
        normalize_tickers(item.tickers)
    ):
        return None
    if rule.topics and not set(normalize_list(rule.topics)).intersection(
        normalize_list(item.topics)
    ):
        return None

    terms = SPECIAL_STOCK_EVENT_TERMS.get(rule.category)
    if not terms:
        return None
    text = build_alert_item_text(item)
    matched_terms = [term for term in terms if term in text]
    if not matched_terms:
        return None

    score_bits = [
        f"matched {', '.join(matched_terms[:3])}",
        f"importance {round(item.importance_score * 100)}",
        f"stock impact {round(item.stock_impact_score * 100)}",
        f"confidence {round(item.classification_confidence * 100)}",
    ]
    if item.tickers:
        score_bits.append(f"tickers {', '.join(item.tickers[:4])}")
    return f"{rule.name}: " + ", ".join(score_bits)


def social_trend_alert_reason(item: NormalizedItem, rule: AlertRule) -> str | None:
    if item.importance_score < rule.min_importance_score:
        return None
    if item.classification_confidence < MIN_ALERT_CLASSIFICATION_CONFIDENCE:
        return None
    if item.source_quality_score < MIN_ALERT_SOURCE_QUALITY:
        return None
    if item.stock_impact_score < rule.min_stock_impact_score:
        return None
    if rule.tickers and not set(normalize_tickers(rule.tickers)).intersection(
        normalize_tickers(item.tickers)
    ):
        return None
    if rule.topics and not set(normalize_list(rule.topics)).intersection(
        normalize_list(item.topics)
    ):
        return None

    social_score = social_signal_score_for_item(item)
    context_bits = social_trend_context_bits(item=item, social_score=social_score)
    if not context_bits:
        return None

    score_bits = [
        *context_bits,
        f"importance {round(item.importance_score * 100)}",
        f"novelty {round(item.novelty_score * 100)}",
        f"social signal {round(social_score * 100)}",
        f"confidence {round(item.classification_confidence * 100)}",
    ]
    if item.products:
        score_bits.append(f"products {', '.join(item.products[:4])}")
    if item.category == "product" and item.subcategory:
        score_bits.append(f"use case {format_product_use_case_label(item.subcategory)}")
    if item.topics:
        score_bits.append(f"topics {', '.join(item.topics[:4])}")
    return f"{rule.name}: " + ", ".join(score_bits)


def social_trend_context_bits(item: NormalizedItem, social_score: float) -> list[str]:
    source_name = item.source_name.lower()
    subcategory = (item.subcategory or "").lower()
    category = item.category.lower()
    bits: list[str] = []

    if social_score >= MIN_SOCIAL_TREND_SCORE:
        bits.append("strong engagement")
    if item.novelty_score >= 0.72 and (item.products or category == "product"):
        bits.append("new product signal")
    if category == SOCIAL_TREND_CATEGORY or "social" in subcategory:
        bits.append("social trend source")
    if item.language.lower().startswith("zh") or "chinese" in source_name:
        bits.append("Chinese-language signal")
    if "product hunt" in source_name and item.products:
        bits.append("product-launch traction")

    return clean_terms(bits)


def build_alert_item_text(item: NormalizedItem) -> str:
    parts = [
        item.title,
        item.summary_short or "",
        item.summary_detailed or "",
        item.why_it_matters or "",
        " ".join(item.topics or []),
    ]
    return " ".join(parts).lower()


def alert_item_sort_time(item: NormalizedItem):
    timestamp = item.published_at or item.created_at
    return timestamp.timestamp() if timestamp else 0


def latest_price_change_percent(db: Session, ticker: str) -> float | None:
    rows = (
        db.query(StockPricePoint)
        .filter(StockPricePoint.ticker == ticker.upper())
        .order_by(StockPricePoint.price_date.desc())
        .limit(2)
        .all()
    )
    if len(rows) < 2:
        return None
    latest, previous = rows[0], rows[1]
    if not previous.close_price:
        return None
    return round(((latest.close_price - previous.close_price) / previous.close_price) * 100, 2)


def format_signed_percent(value: float) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def cross_source_alert_reason(cluster: EventCluster, rule: AlertRule) -> str | None:
    if cluster.importance_score < rule.min_importance_score:
        return None
    if cluster.confidence < MIN_CROSS_SOURCE_CLUSTER_CONFIDENCE:
        return None
    if rule.tickers and not set(normalize_list(rule.tickers)).intersection(
        normalize_list(cluster.tickers)
    ):
        return None
    if rule.topics and not set(normalize_list(rule.topics)).intersection(
        normalize_list(cluster.topics)
    ):
        return None

    score_bits = [
        f"{cluster.item_count} related items",
        f"{len(cluster.sources)} sources",
        f"importance {round(cluster.importance_score * 100)}",
        f"confidence {round(cluster.confidence * 100)}",
    ]
    if cluster.tickers:
        score_bits.append(f"tickers {', '.join(cluster.tickers[:4])}")
    if cluster.topics:
        score_bits.append(f"topics {', '.join(cluster.topics[:4])}")
    return f"{rule.name}: " + ", ".join(score_bits)


def alert_reason(item: NormalizedItem, rule: AlertRule) -> str | None:
    if rule.category != "all" and item.category != rule.category:
        return None
    if item.importance_score < rule.min_importance_score:
        return None
    if item.classification_confidence < MIN_ALERT_CLASSIFICATION_CONFIDENCE:
        return None
    if item.source_quality_score < MIN_ALERT_SOURCE_QUALITY:
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

    score_bits = [
        f"importance {round(item.importance_score * 100)}",
        f"confidence {round(item.classification_confidence * 100)}",
        f"source quality {round(item.source_quality_score * 100)}",
    ]
    if item.stock_impact_score:
        score_bits.append(f"stock impact {round(item.stock_impact_score * 100)}")
    if item.tickers:
        score_bits.append(f"tickers {', '.join(item.tickers[:4])}")
    return f"{rule.name}: " + ", ".join(score_bits)


def list_alerts(
    db: Session,
    limit: int = 20,
    include_dismissed: bool = False,
    blocked_sources: list[str] | None = None,
) -> list[AlertItem]:
    if blocked_sources is None:
        blocked_sources = get_user_preferences(db).blocked_sources
    blocked_source_names = normalize_source_names(blocked_sources)
    query = (
        db.query(Alert)
        .join(Alert.item)
        .outerjoin(
            UserItemAction,
            (UserItemAction.item_id == Alert.item_id)
            & (UserItemAction.user_id == LOCAL_USER_ID),
        )
        .options(joinedload(Alert.item), joinedload(Alert.rule))
        .filter(Alert.user_id == LOCAL_USER_ID)
        .filter((UserItemAction.is_hidden.is_(False)) | (UserItemAction.id.is_(None)))
    )
    if blocked_source_names:
        query = query.filter(~NormalizedItem.source_name.in_(blocked_source_names))
    if not include_dismissed:
        query = query.filter(
            Alert.status == "active",
            Alert.rule.has(AlertRule.enabled.is_(True)),
        )
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


def dismiss_active_alerts_for_rule(db: Session, rule_id: int) -> int:
    return (
        db.query(Alert)
        .filter(
            Alert.user_id == LOCAL_USER_ID,
            Alert.rule_id == rule_id,
            Alert.status == "active",
        )
        .update({"status": "dismissed"})
    )


def count_active_alerts(db: Session, blocked_sources: list[str] | None = None) -> int:
    blocked_source_names = normalize_source_names(blocked_sources)
    query = (
        db.query(Alert)
        .join(Alert.item)
        .outerjoin(
            UserItemAction,
            (UserItemAction.item_id == Alert.item_id)
            & (UserItemAction.user_id == LOCAL_USER_ID),
        )
        .filter(Alert.user_id == LOCAL_USER_ID, Alert.status == "active")
        .filter((UserItemAction.is_hidden.is_(False)) | (UserItemAction.id.is_(None)))
    )
    if blocked_source_names:
        query = query.filter(~NormalizedItem.source_name.in_(blocked_source_names))
    return query.count()


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


def normalize_tickers(values: list[str]) -> list[str]:
    return [value.upper().removeprefix("$") for value in clean_terms(values)]


def clean_terms(values: list[str]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized.lower() in seen:
            continue
        seen.add(normalized.lower())
        cleaned.append(normalized)
    return cleaned

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.models import (
    AlertRule,
    CompanyWatchlistItem,
    ProductWatchlistItem,
    Source,
    StockWatchlistItem,
    TopicWatchlistItem,
)
from app.schemas.alerts import AlertRuleCreate, AlertRuleUpdate
from app.schemas.preferences import UserPreferencesUpdate
from app.schemas.settings_backup import PersonalSettingsBackup, PersonalSettingsRestoreResult
from app.schemas.sources import SourceCreate, SourceUpdate
from app.schemas.watchlist import (
    CompanyWatchlistItemCreate,
    CompanyWatchlistItemUpdate,
    ProductWatchlistItemCreate,
    ProductWatchlistItemUpdate,
    StockWatchlistItemCreate,
    StockWatchlistItemUpdate,
    TopicWatchlistItemCreate,
    TopicWatchlistItemUpdate,
)
from app.services.alerts import create_alert_rule, get_alert_rule_by_name, update_alert_rule
from app.services.feed_actions import LOCAL_USER_ID
from app.services.preferences import get_user_preferences, update_user_preferences
from app.services.source_health import create_source, update_source
from app.services.watchlist import (
    create_company_watchlist_item,
    create_product_watchlist_item,
    create_stock_watchlist_item,
    create_topic_watchlist_item,
    get_company_watchlist_item,
    get_product_watchlist_item,
    get_stock_watchlist_item,
    get_topic_watchlist_item,
    normalize_company_key,
    normalize_product_category,
    normalize_ticker,
    normalize_topic,
    update_company_watchlist_item,
    update_product_watchlist_item,
    update_stock_watchlist_item,
    update_topic_watchlist_item,
)


def export_personal_settings_backup(db: Session) -> PersonalSettingsBackup:
    preferences = get_user_preferences(db)
    return PersonalSettingsBackup(
        exported_at=datetime.now(UTC),
        preferences=UserPreferencesUpdate(
            ranking_weights=preferences.ranking_weights,
            preferred_sources=preferences.preferred_sources,
            blocked_sources=preferences.blocked_sources,
            language_preferences=preferences.language_preferences,
        ),
        sources=[
            SourceCreate.model_validate(source, from_attributes=True)
            for source in db.query(Source).order_by(Source.priority.asc(), Source.name.asc()).all()
        ],
        alert_rules=[
            AlertRuleCreate.model_validate(rule, from_attributes=True)
            for rule in (
                db.query(AlertRule)
                .filter(AlertRule.user_id == LOCAL_USER_ID)
                .order_by(AlertRule.name.asc())
                .all()
            )
        ],
        stock_watchlist=[
            StockWatchlistItemCreate.model_validate(stock, from_attributes=True)
            for stock in (
                db.query(StockWatchlistItem)
                .filter(StockWatchlistItem.user_id == LOCAL_USER_ID)
                .order_by(StockWatchlistItem.display_order.asc(), StockWatchlistItem.ticker.asc())
                .all()
            )
        ],
        company_watchlist=[
            CompanyWatchlistItemCreate.model_validate(company, from_attributes=True)
            for company in (
                db.query(CompanyWatchlistItem)
                .filter(CompanyWatchlistItem.user_id == LOCAL_USER_ID)
                .order_by(CompanyWatchlistItem.company_name.asc())
                .all()
            )
        ],
        topic_watchlist=[
            TopicWatchlistItemCreate.model_validate(topic, from_attributes=True)
            for topic in (
                db.query(TopicWatchlistItem)
                .filter(TopicWatchlistItem.user_id == LOCAL_USER_ID)
                .order_by(TopicWatchlistItem.label.asc())
                .all()
            )
        ],
        product_watchlist=[
            ProductWatchlistItemCreate.model_validate(product, from_attributes=True)
            for product in (
                db.query(ProductWatchlistItem)
                .filter(ProductWatchlistItem.user_id == LOCAL_USER_ID)
                .order_by(ProductWatchlistItem.label.asc())
                .all()
            )
        ],
    )


def restore_personal_settings_backup(
    db: Session,
    backup: PersonalSettingsBackup,
) -> PersonalSettingsRestoreResult:
    result = PersonalSettingsRestoreResult(
        version=backup.version,
        restored_at=datetime.now(UTC),
    )
    if backup.version != 1:
        result.skipped_sections.append(f"Unsupported backup version {backup.version}.")
        return result

    if backup.preferences is not None:
        update_user_preferences(db, backup.preferences)
        result.preferences_updated = True

    for payload in backup.sources:
        upsert_source(db, payload)
        result.sources_upserted += 1

    for payload in backup.alert_rules:
        upsert_alert_rule(db, payload)
        result.alert_rules_upserted += 1

    for payload in backup.stock_watchlist:
        upsert_stock_watchlist_item(db, payload)
        result.stock_watchlist_upserted += 1

    for payload in backup.company_watchlist:
        upsert_company_watchlist_item(db, payload)
        result.company_watchlist_upserted += 1

    for payload in backup.topic_watchlist:
        upsert_topic_watchlist_item(db, payload)
        result.topic_watchlist_upserted += 1

    for payload in backup.product_watchlist:
        upsert_product_watchlist_item(db, payload)
        result.product_watchlist_upserted += 1

    return result


def upsert_source(db: Session, payload: SourceCreate) -> None:
    existing = db.query(Source).filter(Source.name == payload.name.strip()).one_or_none()
    if existing is None:
        create_source(db, payload)
        return
    update_source(db, existing.id, SourceUpdate(**payload.model_dump()))


def upsert_alert_rule(db: Session, payload: AlertRuleCreate) -> None:
    existing = get_alert_rule_by_name(db, payload.name)
    if existing is None:
        create_alert_rule(db, payload)
        return
    update_alert_rule(db, existing.id, AlertRuleUpdate(**payload.model_dump()))


def upsert_stock_watchlist_item(db: Session, payload: StockWatchlistItemCreate) -> None:
    ticker = normalize_ticker(payload.ticker or "")
    existing = get_stock_watchlist_item(db, ticker) if ticker else None
    if existing is None:
        create_stock_watchlist_item(db, payload)
        return
    update_stock_watchlist_item(db, ticker, StockWatchlistItemUpdate(**payload.model_dump()))


def upsert_company_watchlist_item(db: Session, payload: CompanyWatchlistItemCreate) -> None:
    company_key = normalize_company_key(payload.company_key or payload.company_name)
    existing = get_company_watchlist_item(db, company_key)
    if existing is None:
        create_company_watchlist_item(db, payload)
        return
    update_company_watchlist_item(
        db,
        company_key=company_key,
        payload=CompanyWatchlistItemUpdate(**payload.model_dump(exclude={"company_key"})),
    )


def upsert_topic_watchlist_item(db: Session, payload: TopicWatchlistItemCreate) -> None:
    topic = normalize_topic(payload.topic)
    existing = get_topic_watchlist_item(db, topic)
    if existing is None:
        create_topic_watchlist_item(db, payload)
        return
    update_topic_watchlist_item(
        db,
        topic=topic,
        payload=TopicWatchlistItemUpdate(**payload.model_dump(exclude={"topic"})),
    )


def upsert_product_watchlist_item(db: Session, payload: ProductWatchlistItemCreate) -> None:
    category = normalize_product_category(payload.category)
    existing = get_product_watchlist_item(db, category)
    if existing is None:
        create_product_watchlist_item(db, payload)
        return
    update_product_watchlist_item(
        db,
        category=category,
        payload=ProductWatchlistItemUpdate(**payload.model_dump(exclude={"category"})),
    )

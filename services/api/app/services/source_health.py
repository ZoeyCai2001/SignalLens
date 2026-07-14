from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import RawItem, Source, SourceRun
from app.schemas.ingestion import build_ingestion_recovery_hint
from app.schemas.sources import SourceCreate, SourceHealth, SourceRunHistoryItem, SourceUpdate
from app.services.polling_intervals import parse_polling_interval

SOURCE_ATTENTION_FAILURE_THRESHOLD = 2
SOURCE_HEALTH_RECENT_RUN_LIMIT = 5
SOURCE_FAILURE_STATUSES = {"failed"}
SOURCE_CONFIGURATION_HINTS = {
    "product_topic": "Set PRODUCT_HUNT_API_TOKEN in .env or disable this optional source.",
    "finance_news": "Set ALPHA_VANTAGE_API_KEY in .env or disable Alpha Vantage news.",
    "stock_prices": "Set ALPHA_VANTAGE_API_KEY in .env or disable Alpha Vantage prices.",
    "social_keyword": "Add a public RSS/Atom URL to the source or configure CHINESE_RSS_FEEDS.",
    "reddit_community": (
        "Add a public subreddit URL and set REDDIT_USER_AGENT to a descriptive contact string."
    ),
    "finance_filings": "Set SEC_USER_AGENT to a descriptive app/contact string for SEC requests.",
}


@dataclass(frozen=True)
class RecentSourceRunQuality:
    run_count: int = 0
    success_rate: float | None = None
    store_rate: float | None = None
    items_fetched: int = 0
    items_stored: int = 0


def list_source_health(db: Session) -> list[SourceHealth]:
    latest_run_subquery = (
        db.query(
            SourceRun.source_id,
            func.max(SourceRun.started_at).label("latest_started_at"),
        )
        .group_by(SourceRun.source_id)
        .subquery()
    )

    rows = (
        db.query(Source, SourceRun)
        .outerjoin(latest_run_subquery, Source.id == latest_run_subquery.c.source_id)
        .outerjoin(
            SourceRun,
            (SourceRun.source_id == Source.id)
            & (SourceRun.started_at == latest_run_subquery.c.latest_started_at),
        )
        .order_by(Source.priority.asc(), Source.name.asc())
        .all()
    )

    return [
        serialize_source_health(
            source,
            run,
            failure_count=count_recent_source_failures(db, source.id),
            last_success_at=get_latest_success_at(db, source.id),
            recent_quality=summarize_recent_source_runs(db, source.id),
        )
        for source, run in rows
    ]


def create_source(db: Session, payload: SourceCreate) -> Source:
    name = normalize_required_text(payload.name, "Source name")
    existing = db.query(Source).filter(Source.name == name).one_or_none()
    if existing is not None:
        raise ValueError(f"{name} is already registered.")

    source_type, access_method, base_url, auth_required, rate_limit, polling_interval = (
        normalize_source_configuration(
            source_type=payload.type,
            access_method=payload.access_method,
            base_url=payload.base_url,
            auth_required=payload.auth_required,
            rate_limit=payload.rate_limit,
            polling_interval=payload.polling_interval,
        )
    )

    source = Source(
        name=name,
        type=source_type,
        access_method=access_method,
        base_url=base_url,
        auth_required=auth_required,
        rate_limit=rate_limit,
        polling_interval=polling_interval,
        enabled=payload.enabled,
        priority=payload.priority,
        terms_notes=normalize_optional_text(payload.terms_notes),
        raw_content_policy=normalize_optional_text(payload.raw_content_policy),
    )
    if source.raw_content_policy is None:
        source.raw_content_policy = raw_content_policy_for_source(source)
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def update_source(db: Session, source_id: int, payload: SourceUpdate) -> Source | None:
    source = db.get(Source, source_id)
    if source is None:
        return None

    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates:
        name = normalize_optional_text(updates.pop("name"))
        if name:
            existing = (
                db.query(Source)
                .filter(Source.name == name, Source.id != source.id)
                .one_or_none()
            )
            if existing is not None:
                raise ValueError(f"{name} is already registered.")
            source.name = name

    source_type, access_method, base_url, auth_required, rate_limit, polling_interval = (
        normalize_source_configuration(
            source_type=updates.pop("type", source.type),
            access_method=updates.pop("access_method", source.access_method),
            base_url=updates.pop("base_url", source.base_url),
            auth_required=updates.pop("auth_required", source.auth_required),
            rate_limit=updates.pop("rate_limit", source.rate_limit),
            polling_interval=updates.pop("polling_interval", source.polling_interval),
        )
    )
    source.type = source_type
    source.access_method = access_method
    source.base_url = base_url
    source.auth_required = auth_required
    source.rate_limit = rate_limit
    source.polling_interval = polling_interval

    for field_name, value in updates.items():
        if field_name == "priority" and value is None:
            continue
        if isinstance(value, str):
            value = value.strip() or None
        setattr(source, field_name, value)

    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def delete_source(db: Session, source_id: int) -> bool:
    source = db.get(Source, source_id)
    if source is None:
        return False

    has_run_history = (
        db.query(SourceRun.id).filter(SourceRun.source_id == source.id).first() is not None
    )
    has_collected_items = (
        db.query(RawItem.id).filter(RawItem.source_id == source.id).first() is not None
    )
    if has_run_history or has_collected_items:
        raise ValueError(
            "Sources with run history or collected items cannot be deleted; "
            "disable the source instead."
        )

    db.delete(source)
    db.commit()
    return True


def normalize_required_text(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} is required.")
    return normalized


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


def normalize_source_configuration(
    *,
    source_type: str | None,
    access_method: str | None,
    base_url: str | None,
    auth_required: bool | None,
    rate_limit: str | None,
    polling_interval: str | None,
) -> tuple[str, str, str | None, bool, str | None, str | None]:
    normalized_type = normalize_optional_text(source_type) or "rss"
    normalized_access_method = normalize_optional_text(access_method) or "rss"
    normalized_base_url = normalize_optional_text(base_url)
    normalized_rate_limit = normalize_optional_text(rate_limit)
    normalized_polling_interval = normalize_optional_text(polling_interval)

    if normalized_type == "github_repository":
        normalized_access_method = "official_api"
    if normalized_type == "product_topic":
        normalized_access_method = "official_graphql_api"
    if normalized_type == "social_keyword" and normalized_base_url:
        normalized_access_method = "rss"

    normalized_auth_required = bool(auth_required) or normalized_type == "product_topic"
    normalized_rate_limit = (
        normalized_rate_limit
        or (
            "Product Hunt API token required; keep topic polling conservative."
            if normalized_type == "product_topic"
            else None
        )
        or (
            "Public RSS/Atom metadata only; no login-protected social scraping."
            if normalized_type == "social_keyword"
            else None
        )
    )
    normalized_polling_interval = normalized_polling_interval or (
        "6 hours" if normalized_type in {"product_topic", "social_keyword"} else None
    )

    return (
        normalized_type,
        normalized_access_method,
        normalized_base_url,
        normalized_auth_required,
        normalized_rate_limit,
        normalized_polling_interval,
    )


def list_source_run_history(
    db: Session,
    limit: int = 20,
    status: str | None = None,
    source_id: int | None = None,
) -> list[SourceRunHistoryItem]:
    query = (
        db.query(SourceRun, Source)
        .join(Source, Source.id == SourceRun.source_id)
        .order_by(SourceRun.started_at.desc(), SourceRun.id.desc())
    )
    normalized_status = normalize_optional_text(status)
    if normalized_status:
        query = query.filter(SourceRun.status == normalized_status)
    if source_id is not None:
        query = query.filter(SourceRun.source_id == source_id)
    rows = query.limit(limit).all()
    return [serialize_source_run_history_item(run=run, source=source) for run, source in rows]


def get_latest_source_run(db: Session, source_id: int) -> SourceRun | None:
    return (
        db.query(SourceRun)
        .filter(SourceRun.source_id == source_id)
        .order_by(SourceRun.started_at.desc())
        .first()
    )


def get_latest_success_at(db: Session, source_id: int) -> datetime | None:
    run = (
        db.query(SourceRun)
        .filter(SourceRun.source_id == source_id, SourceRun.status == "success")
        .order_by(SourceRun.started_at.desc(), SourceRun.id.desc())
        .first()
    )
    if run is None:
        return None
    return run.finished_at or run.started_at


def count_recent_source_failures(
    db: Session,
    source_id: int,
    limit: int = SOURCE_HEALTH_RECENT_RUN_LIMIT,
) -> int:
    rows = (
        db.query(SourceRun.status)
        .filter(SourceRun.source_id == source_id)
        .order_by(SourceRun.started_at.desc(), SourceRun.id.desc())
        .limit(limit)
        .all()
    )
    return sum(1 for row in rows if unwrap_status(row) in SOURCE_FAILURE_STATUSES)


def summarize_recent_source_runs(
    db: Session,
    source_id: int,
    limit: int = SOURCE_HEALTH_RECENT_RUN_LIMIT,
) -> RecentSourceRunQuality:
    rows = (
        db.query(SourceRun.status, SourceRun.items_fetched, SourceRun.items_stored)
        .filter(SourceRun.source_id == source_id)
        .order_by(SourceRun.started_at.desc(), SourceRun.id.desc())
        .limit(limit)
        .all()
    )
    if not rows:
        return RecentSourceRunQuality()

    items_fetched = sum(row.items_fetched or 0 for row in rows)
    items_stored = sum(row.items_stored or 0 for row in rows)
    success_count = sum(1 for row in rows if row.status == "success")
    return RecentSourceRunQuality(
        run_count=len(rows),
        success_rate=success_count / len(rows),
        store_rate=items_stored / items_fetched if items_fetched else None,
        items_fetched=items_fetched,
        items_stored=items_stored,
    )


def unwrap_status(row) -> str:
    if isinstance(row, str):
        return row
    if hasattr(row, "status"):
        return row.status
    if isinstance(row, tuple) and row:
        return row[0]
    return ""


def source_needs_attention(latest_status: str, failure_count: int, is_stale: bool = False) -> bool:
    return (
        latest_status in SOURCE_FAILURE_STATUSES
        or failure_count >= SOURCE_ATTENTION_FAILURE_THRESHOLD
        or is_stale
    )


def serialize_source_health(
    source: Source,
    run: SourceRun | None,
    failure_count: int = 0,
    last_success_at: datetime | None = None,
    recent_quality: RecentSourceRunQuality | None = None,
) -> SourceHealth:
    latest_status = run.status if run else "never_run"
    quality = recent_quality or RecentSourceRunQuality()
    next_run_due_at = source_next_run_due_at(
        source_retry_reference_at(run=run, last_success_at=last_success_at),
        source.polling_interval,
    )
    is_stale = bool(source.enabled) and source_is_stale(last_success_at, source.polling_interval)
    return SourceHealth(
        id=source.id,
        name=source.name,
        type=source.type,
        access_method=source.access_method,
        base_url=source.base_url,
        auth_required=bool(source.auth_required),
        rate_limit=source.rate_limit,
        polling_interval=source.polling_interval,
        enabled=bool(source.enabled),
        priority=source.priority if source.priority is not None else 100,
        terms_notes=source.terms_notes,
        raw_content_policy=raw_content_policy_for_source(source),
        failure_handling=failure_handling_for_source(source),
        recovery_hint=recovery_hint_for_source(source, run),
        latest_status=latest_status,
        latest_error=run.error_message if run else None,
        last_started_at=run.started_at if run else None,
        last_finished_at=run.finished_at if run else None,
        latest_duration_seconds=source_run_duration_seconds(run),
        last_success_at=last_success_at,
        next_run_due_at=next_run_due_at,
        is_stale=is_stale,
        items_fetched=run.items_fetched if run else 0,
        items_stored=run.items_stored if run else 0,
        failure_count=failure_count,
        needs_attention=source_needs_attention(latest_status, failure_count, is_stale),
        recent_run_count=quality.run_count,
        recent_success_rate=quality.success_rate,
        recent_store_rate=quality.store_rate,
        recent_items_fetched=quality.items_fetched,
        recent_items_stored=quality.items_stored,
    )


def raw_content_policy_for_source(source: Source) -> str:
    explicit_policy = normalize_optional_text(getattr(source, "raw_content_policy", None))
    if explicit_policy:
        return explicit_policy

    source_type = (source.type or "").strip().lower()
    access_method = (source.access_method or "").strip().lower()
    if source_type == "manual":
        return "Store the submitted URL, title, excerpt, and optional user-provided text."
    if source_type == "social_keyword":
        return "Store public RSS/Atom metadata and snippets only; avoid login-protected content."
    if source_type == "product_topic":
        return "Store Product Hunt launch metadata returned by the official GraphQL API."
    if source_type == "github_repository":
        return "Store public repository metadata and summaries; do not clone repository contents."
    if source_type == "research":
        return "Store public paper metadata, abstract text, source URL, and publication time."
    if access_method in {"rss", "atom"}:
        return "Store public feed metadata, title, excerpt, URL, and publication time."
    if "api" in access_method:
        return "Store public API metadata and snippets needed for ranking and summaries."
    return "Store minimal public metadata required for personal search, ranking, and attribution."


def failure_handling_for_source(source: Source) -> str:
    if source.auth_required:
        return "Record the failed run and latest error; update credentials or disable the source."
    if parse_polling_interval(source.polling_interval) is not None:
        return (
            "Record failures, preserve the last success time, and retry at the next polling "
            "window."
        )
    return "Record failures in run history; use a manual run after fixing source configuration."


def recovery_hint_for_source(source: Source, run: SourceRun | None) -> str | None:
    if run is None:
        if not source.enabled:
            return "Enable the source before running it."
        return None

    generic_hint = build_ingestion_recovery_hint(
        status=run.status,
        items_fetched=run.items_fetched or 0,
        items_stored=run.items_stored or 0,
        error_message=run.error_message,
    )
    if generic_hint is None:
        return None

    source_hint = source_configuration_hint_for_error(source, run.error_message)
    return source_hint or generic_hint


def source_configuration_hint_for_error(source: Source, error_message: str | None) -> str | None:
    normalized_error = (error_message or "").strip().lower()
    if not normalized_error:
        return None

    source_type = (source.type or "").strip().lower()
    source_name = (source.name or "").strip().lower()
    if "not configured" in normalized_error or "api key" in normalized_error:
        return (
            SOURCE_CONFIGURATION_HINTS.get(source_type)
            or configuration_hint_for_source_name(source_name)
        )
    if "rss/atom feed" in normalized_error or "public subreddit" in normalized_error:
        return SOURCE_CONFIGURATION_HINTS.get(source_type)
    if "rate limit" in normalized_error or "rate limited" in normalized_error:
        if source_type in {"reddit_community", "finance_filings"}:
            return SOURCE_CONFIGURATION_HINTS[source_type]
    return None


def configuration_hint_for_source_name(source_name: str) -> str | None:
    if "alpha vantage" in source_name:
        return "Set ALPHA_VANTAGE_API_KEY in .env or disable this optional stock source."
    if "product hunt" in source_name:
        return SOURCE_CONFIGURATION_HINTS["product_topic"]
    if "chinese rss" in source_name:
        return "Set CHINESE_RSS_FEEDS in .env or add a public RSS/Atom URL to the source."
    if "reddit" in source_name:
        return SOURCE_CONFIGURATION_HINTS["reddit_community"]
    if "sec" in source_name:
        return SOURCE_CONFIGURATION_HINTS["finance_filings"]
    return None


def source_next_run_due_at(
    last_success_at: datetime | None,
    polling_interval: str | None,
) -> datetime | None:
    interval = parse_polling_interval(polling_interval)
    if last_success_at is None or interval is None:
        return None
    return normalize_source_health_datetime(last_success_at) + interval


def source_retry_reference_at(
    run: SourceRun | None,
    last_success_at: datetime | None,
) -> datetime | None:
    if run is not None and run.status != "success":
        if run.started_at is not None:
            return run.started_at
        if run.finished_at is not None:
            return run.finished_at
    return last_success_at


def source_is_stale(
    last_success_at: datetime | None,
    polling_interval: str | None,
    now: datetime | None = None,
) -> bool:
    next_run_due_at = source_next_run_due_at(last_success_at, polling_interval)
    if next_run_due_at is None:
        return False
    reference_time = normalize_source_health_datetime(now or datetime.now(UTC))
    return reference_time >= next_run_due_at


def normalize_source_health_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def serialize_source_run_history_item(
    run: SourceRun,
    source: Source,
) -> SourceRunHistoryItem:
    return SourceRunHistoryItem(
        id=run.id,
        source_id=source.id,
        source_name=source.name,
        status=run.status,
        items_fetched=run.items_fetched,
        items_stored=run.items_stored,
        error_message=run.error_message,
        started_at=run.started_at,
        finished_at=run.finished_at,
        duration_seconds=source_run_duration_seconds(run),
    )


def source_run_duration_seconds(run: SourceRun | None) -> float | None:
    if run is None or run.started_at is None or run.finished_at is None:
        return None
    started_at = normalize_source_health_datetime(run.started_at)
    finished_at = normalize_source_health_datetime(run.finished_at)
    return round(max(0.0, (finished_at - started_at).total_seconds()), 3)

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import Source, SourceRun
from app.schemas.sources import SourceCreate, SourceHealth, SourceRunHistoryItem, SourceUpdate

SOURCE_ATTENTION_FAILURE_THRESHOLD = 2
SOURCE_HEALTH_RECENT_RUN_LIMIT = 5
SOURCE_FAILURE_STATUSES = {"failed"}


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
        )
        for source, run in rows
    ]


def create_source(db: Session, payload: SourceCreate) -> Source:
    name = normalize_required_text(payload.name, "Source name")
    existing = db.query(Source).filter(Source.name == name).one_or_none()
    if existing is not None:
        raise ValueError(f"{name} is already registered.")

    source = Source(
        name=name,
        type=normalize_optional_text(payload.type) or "rss",
        access_method=normalize_optional_text(payload.access_method) or "rss",
        base_url=normalize_optional_text(payload.base_url),
        auth_required=payload.auth_required,
        rate_limit=normalize_optional_text(payload.rate_limit),
        polling_interval=normalize_optional_text(payload.polling_interval),
        enabled=payload.enabled,
        priority=payload.priority,
        terms_notes=normalize_optional_text(payload.terms_notes),
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def update_source(db: Session, source_id: int, payload: SourceUpdate) -> Source | None:
    source = db.get(Source, source_id)
    if source is None:
        return None

    updates = payload.model_dump(exclude_unset=True)
    for field_name, value in updates.items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(source, field_name, value)

    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def normalize_required_text(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} is required.")
    return normalized


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


def list_source_run_history(db: Session, limit: int = 20) -> list[SourceRunHistoryItem]:
    rows = (
        db.query(SourceRun, Source)
        .join(Source, Source.id == SourceRun.source_id)
        .order_by(SourceRun.started_at.desc(), SourceRun.id.desc())
        .limit(limit)
        .all()
    )
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


def unwrap_status(row) -> str:
    if isinstance(row, str):
        return row
    if hasattr(row, "status"):
        return row.status
    if isinstance(row, tuple) and row:
        return row[0]
    return ""


def source_needs_attention(latest_status: str, failure_count: int) -> bool:
    return latest_status in SOURCE_FAILURE_STATUSES or failure_count >= SOURCE_ATTENTION_FAILURE_THRESHOLD


def serialize_source_health(
    source: Source,
    run: SourceRun | None,
    failure_count: int = 0,
    last_success_at: datetime | None = None,
) -> SourceHealth:
    latest_status = run.status if run else "never_run"
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
        latest_status=latest_status,
        latest_error=run.error_message if run else None,
        last_started_at=run.started_at if run else None,
        last_finished_at=run.finished_at if run else None,
        last_success_at=last_success_at,
        items_fetched=run.items_fetched if run else 0,
        items_stored=run.items_stored if run else 0,
        failure_count=failure_count,
        needs_attention=source_needs_attention(latest_status, failure_count),
    )


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
    )

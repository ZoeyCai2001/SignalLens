from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import Source, SourceRun
from app.schemas.sources import SourceHealth, SourceUpdate


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

    return [serialize_source_health(source, run) for source, run in rows]


def update_source(db: Session, source_id: int, payload: SourceUpdate) -> Source | None:
    source = db.get(Source, source_id)
    if source is None:
        return None

    updates = payload.model_dump(exclude_unset=True)
    for field_name, value in updates.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(source, field_name, value)

    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def get_latest_source_run(db: Session, source_id: int) -> SourceRun | None:
    return (
        db.query(SourceRun)
        .filter(SourceRun.source_id == source_id)
        .order_by(SourceRun.started_at.desc())
        .first()
    )


def serialize_source_health(source: Source, run: SourceRun | None) -> SourceHealth:
    return SourceHealth(
        id=source.id,
        name=source.name,
        type=source.type,
        access_method=source.access_method,
        enabled=source.enabled,
        latest_status=run.status if run else "never_run",
        latest_error=run.error_message if run else None,
        last_started_at=run.started_at if run else None,
        last_finished_at=run.finished_at if run else None,
        items_fetched=run.items_fetched if run else 0,
        items_stored=run.items_stored if run else 0,
    )

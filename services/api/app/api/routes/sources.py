from fastapi import APIRouter
from sqlalchemy import func

from app.api.deps import DbSession
from app.db.models import Source, SourceRun
from app.schemas.sources import SourceHealth

router = APIRouter()


@router.get("/health", response_model=list[SourceHealth])
async def list_source_health(db: DbSession) -> list[SourceHealth]:
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
        SourceHealth(
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
        for source, run in rows
    ]

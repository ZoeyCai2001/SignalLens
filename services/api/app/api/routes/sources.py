from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DbSession
from app.schemas.ingestion import IngestionRunResponse
from app.schemas.sources import SourceCreate, SourceHealth, SourceRunHistoryItem, SourceUpdate
from app.services.ingestion import (
    SourceNotFoundError,
    SourceRunnerNotFoundError,
    run_source_ingestion_by_id,
)
from app.services.source_health import (
    create_source,
    get_latest_source_run,
    list_source_run_history,
    serialize_source_health,
    update_source,
)
from app.services.source_health import (
    list_source_health as list_source_health_items,
)

router = APIRouter()


@router.get("/health", response_model=list[SourceHealth])
async def list_source_health(db: DbSession) -> list[SourceHealth]:
    return list_source_health_items(db)


@router.get("/runs", response_model=list[SourceRunHistoryItem])
async def list_source_runs(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[SourceRunHistoryItem]:
    return list_source_run_history(db=db, limit=limit)


@router.post("", response_model=SourceHealth, status_code=201)
async def create_followed_source(
    payload: SourceCreate,
    db: DbSession,
) -> SourceHealth:
    try:
        source = create_source(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_source_health(source, None)


@router.post("/{source_id}/run", response_model=IngestionRunResponse)
async def run_source_now(
    source_id: int,
    db: DbSession,
    limit: Annotated[int | None, Query(ge=1, le=100)] = None,
) -> IngestionRunResponse:
    try:
        result = await run_source_ingestion_by_id(db=db, source_id=source_id, limit=limit)
    except SourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Source not found.") from exc
    except SourceRunnerNotFoundError as exc:
        raise HTTPException(
            status_code=400,
            detail="No runnable connector is registered for this source.",
        ) from exc
    return IngestionRunResponse.model_validate(result)


@router.patch("/{source_id}", response_model=SourceHealth)
async def patch_source(
    source_id: int,
    payload: SourceUpdate,
    db: DbSession,
) -> SourceHealth:
    source = update_source(db, source_id=source_id, payload=payload)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found.")
    return serialize_source_health(source, get_latest_source_run(db, source_id=source.id))

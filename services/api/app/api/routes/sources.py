from fastapi import APIRouter, HTTPException

from app.api.deps import DbSession
from app.schemas.sources import SourceHealth, SourceUpdate
from app.services.source_health import (
    get_latest_source_run,
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

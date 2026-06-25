from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.schemas.events import EventCluster
from app.services.event_clustering import list_event_clusters

router = APIRouter()


@router.get("/clusters", response_model=list[EventCluster])
async def list_clusters(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=50)] = 12,
    min_items: Annotated[int, Query(ge=1, le=10)] = 1,
) -> list[EventCluster]:
    return list_event_clusters(db=db, limit=limit, min_items=min_items)

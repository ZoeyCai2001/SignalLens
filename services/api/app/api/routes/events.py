from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DbSession
from app.schemas.events import EventCluster
from app.services.event_clustering import get_event_cluster, list_event_clusters

router = APIRouter()


@router.get("/clusters", response_model=list[EventCluster])
async def list_clusters(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=50)] = 12,
    min_items: Annotated[int, Query(ge=1, le=10)] = 1,
) -> list[EventCluster]:
    return list_event_clusters(db=db, limit=limit, min_items=min_items)


@router.get("/clusters/{cluster_key}", response_model=EventCluster)
async def get_cluster(
    cluster_key: str,
    db: DbSession,
    min_items: Annotated[int, Query(ge=1, le=10)] = 1,
) -> EventCluster:
    cluster = get_event_cluster(db=db, cluster_key=cluster_key, min_items=min_items)
    if cluster is None:
        raise HTTPException(status_code=404, detail="Event cluster not found.")
    return cluster

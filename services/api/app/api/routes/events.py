from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DbSession
from app.core.config import get_settings
from app.llm.kimi_coding import KimiCodingClient, KimiCodingError
from app.schemas.events import EventCluster, EventClusterLlmExplanation
from app.services.event_clustering import (
    build_event_cluster_llm_prompt,
    get_event_cluster,
    list_event_clusters,
)
from app.services.llm_usage import record_llm_usage
from app.services.preferences import get_user_preferences

router = APIRouter()


@router.get("/clusters", response_model=list[EventCluster])
async def list_clusters(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=50)] = 12,
    min_items: Annotated[int, Query(ge=1, le=10)] = 1,
) -> list[EventCluster]:
    preferences = get_user_preferences(db)
    return list_event_clusters(
        db=db,
        limit=limit,
        min_items=min_items,
        ranking_weights=preferences.ranking_weights,
        preferred_sources=preferences.preferred_sources,
        blocked_sources=preferences.blocked_sources,
    )


@router.get("/clusters/{cluster_key}", response_model=EventCluster)
async def get_cluster(
    cluster_key: str,
    db: DbSession,
    min_items: Annotated[int, Query(ge=1, le=10)] = 1,
) -> EventCluster:
    preferences = get_user_preferences(db)
    cluster = get_event_cluster(
        db=db,
        cluster_key=cluster_key,
        min_items=min_items,
        ranking_weights=preferences.ranking_weights,
        preferred_sources=preferences.preferred_sources,
        blocked_sources=preferences.blocked_sources,
    )
    if cluster is None:
        raise HTTPException(status_code=404, detail="Event cluster not found.")
    return cluster


@router.post("/clusters/{cluster_key}/llm-explanation", response_model=EventClusterLlmExplanation)
async def explain_cluster_with_llm(
    cluster_key: str,
    db: DbSession,
    min_items: Annotated[int, Query(ge=1, le=10)] = 1,
) -> EventClusterLlmExplanation:
    settings = get_settings()
    if not settings.moonshot_api_key:
        raise HTTPException(status_code=400, detail="MOONSHOT_API_KEY is not configured.")

    preferences = get_user_preferences(db)
    cluster = get_event_cluster(
        db=db,
        cluster_key=cluster_key,
        min_items=min_items,
        ranking_weights=preferences.ranking_weights,
        preferred_sources=preferences.preferred_sources,
        blocked_sources=preferences.blocked_sources,
    )
    if cluster is None:
        raise HTTPException(status_code=404, detail="Event cluster not found.")

    client = KimiCodingClient(settings=settings)
    try:
        result = await client.create_message(
            prompt=build_event_cluster_llm_prompt(cluster),
            max_tokens=420,
        )
    except KimiCodingError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    record_llm_usage(
        db=db,
        operation="explain_event_cluster",
        provider=settings.llm_provider,
        result=result,
    )
    db.commit()

    return EventClusterLlmExplanation(
        cluster_key=cluster.cluster_key,
        model=result.model,
        explanation=result.text,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        total_tokens=result.total_tokens,
    )

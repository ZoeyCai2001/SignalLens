from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DbSession
from app.schemas.digest import (
    DailyDigest,
    DailyDigestMarkdown,
    DailyDigestSnapshot,
    DailyDigestSnapshotFeedback,
)
from app.services.daily_digest import (
    delete_daily_digest_snapshot,
    generate_daily_digest,
    list_daily_digest_snapshots,
    render_digest_markdown,
    save_daily_digest_snapshot,
    serialize_daily_digest_snapshot,
    update_daily_digest_snapshot_feedback,
)

router = APIRouter()


@router.get("/daily", response_model=DailyDigest)
async def get_daily_digest(
    db: DbSession,
    digest_date: Annotated[date | None, Query(alias="date")] = None,
    limit_per_section: Annotated[int, Query(ge=1, le=10)] = 5,
) -> DailyDigest:
    return generate_daily_digest(
        db=db,
        digest_date=digest_date,
        limit_per_section=limit_per_section,
    )


@router.post("/daily/generate", response_model=DailyDigest)
async def generate_daily_digest_now(
    db: DbSession,
    digest_date: Annotated[date | None, Query(alias="date")] = None,
    limit_per_section: Annotated[int, Query(ge=1, le=10)] = 5,
) -> DailyDigest:
    return generate_daily_digest(
        db=db,
        digest_date=digest_date,
        limit_per_section=limit_per_section,
    )


@router.get("/daily/markdown", response_model=DailyDigestMarkdown)
async def get_daily_digest_markdown(
    db: DbSession,
    digest_date: Annotated[date | None, Query(alias="date")] = None,
    limit_per_section: Annotated[int, Query(ge=1, le=10)] = 5,
) -> DailyDigestMarkdown:
    digest = generate_daily_digest(
        db=db,
        digest_date=digest_date,
        limit_per_section=limit_per_section,
    )
    return DailyDigestMarkdown(
        digest_date=digest.digest_date,
        generated_at=digest.generated_at,
        markdown=render_digest_markdown(digest),
    )


@router.post("/daily/snapshots", response_model=DailyDigestSnapshot, status_code=201)
async def create_daily_digest_snapshot(
    db: DbSession,
    digest_date: Annotated[date | None, Query(alias="date")] = None,
    limit_per_section: Annotated[int, Query(ge=1, le=10)] = 5,
) -> DailyDigestSnapshot:
    snapshot = save_daily_digest_snapshot(
        db=db,
        digest_date=digest_date,
        limit_per_section=limit_per_section,
    )
    return serialize_daily_digest_snapshot(snapshot)


@router.get("/daily/snapshots", response_model=list[DailyDigestSnapshot])
async def get_daily_digest_snapshots(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=30)] = 10,
) -> list[DailyDigestSnapshot]:
    return [
        serialize_daily_digest_snapshot(snapshot)
        for snapshot in list_daily_digest_snapshots(db=db, limit=limit)
    ]


@router.delete("/daily/snapshots/{snapshot_id}", status_code=204)
async def delete_saved_daily_digest_snapshot(snapshot_id: int, db: DbSession) -> None:
    deleted = delete_daily_digest_snapshot(db=db, snapshot_id=snapshot_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Digest snapshot not found.")


@router.patch("/daily/snapshots/{snapshot_id}/feedback", response_model=DailyDigestSnapshot)
async def update_saved_daily_digest_snapshot_feedback(
    snapshot_id: int,
    payload: DailyDigestSnapshotFeedback,
    db: DbSession,
) -> DailyDigestSnapshot:
    snapshot = update_daily_digest_snapshot_feedback(
        db=db,
        snapshot_id=snapshot_id,
        usefulness_feedback=payload.usefulness_feedback,
    )
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Digest snapshot not found.")
    return serialize_daily_digest_snapshot(snapshot)

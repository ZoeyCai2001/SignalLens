from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.schemas.digest import DailyDigest, DailyDigestMarkdown
from app.services.daily_digest import generate_daily_digest, render_digest_markdown

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

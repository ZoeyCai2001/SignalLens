from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.schemas.digest import DailyDigest
from app.services.daily_digest import generate_daily_digest

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

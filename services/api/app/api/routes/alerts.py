from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DbSession
from app.schemas.alerts import AlertGenerationResult, AlertItem
from app.services.alerts import dismiss_alert, generate_alerts, list_alerts, serialize_alert

router = APIRouter()


@router.get("", response_model=list[AlertItem])
async def get_alerts(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    include_dismissed: bool = False,
) -> list[AlertItem]:
    generate_alerts(db)
    return list_alerts(db=db, limit=limit, include_dismissed=include_dismissed)


@router.post("/generate", response_model=AlertGenerationResult)
async def generate_dashboard_alerts(db: DbSession) -> AlertGenerationResult:
    return generate_alerts(db)


@router.post("/{alert_id}/dismiss", response_model=AlertItem)
async def dismiss_dashboard_alert(alert_id: int, db: DbSession) -> AlertItem:
    alert = dismiss_alert(db, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return serialize_alert(db, alert)

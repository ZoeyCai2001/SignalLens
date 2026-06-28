from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DbSession
from app.schemas.alerts import (
    AlertGenerationResult,
    AlertItem,
    AlertRule,
    AlertRuleCreate,
    AlertRuleUpdate,
)
from app.services.alerts import (
    create_alert_rule,
    delete_alert_rule,
    dismiss_alert,
    generate_alerts,
    list_alert_rules,
    list_alerts,
    serialize_alert,
    update_alert_rule,
)
from app.services.preferences import get_user_preferences

router = APIRouter()


@router.get("", response_model=list[AlertItem])
async def get_alerts(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    include_dismissed: bool = False,
) -> list[AlertItem]:
    preferences = get_user_preferences(db)
    generate_alerts(db, blocked_sources=preferences.blocked_sources)
    return list_alerts(
        db=db,
        limit=limit,
        include_dismissed=include_dismissed,
        blocked_sources=preferences.blocked_sources,
    )


@router.post("/generate", response_model=AlertGenerationResult)
async def generate_dashboard_alerts(db: DbSession) -> AlertGenerationResult:
    preferences = get_user_preferences(db)
    return generate_alerts(db, blocked_sources=preferences.blocked_sources)


@router.get("/rules", response_model=list[AlertRule])
async def get_alert_rules(db: DbSession) -> list[AlertRule]:
    return [AlertRule.model_validate(rule) for rule in list_alert_rules(db)]


@router.post("/rules", response_model=AlertRule, status_code=201)
async def create_dashboard_alert_rule(
    payload: AlertRuleCreate,
    db: DbSession,
) -> AlertRule:
    try:
        rule = create_alert_rule(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return AlertRule.model_validate(rule)


@router.patch("/rules/{rule_id}", response_model=AlertRule)
async def update_dashboard_alert_rule(
    rule_id: int,
    payload: AlertRuleUpdate,
    db: DbSession,
) -> AlertRule:
    try:
        rule = update_alert_rule(db, rule_id=rule_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if rule is None:
        raise HTTPException(status_code=404, detail="Alert rule not found.")
    return AlertRule.model_validate(rule)


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_dashboard_alert_rule(rule_id: int, db: DbSession) -> None:
    deleted = delete_alert_rule(db, rule_id=rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Alert rule not found.")


@router.post("/{alert_id}/dismiss", response_model=AlertItem)
async def dismiss_dashboard_alert(alert_id: int, db: DbSession) -> AlertItem:
    alert = dismiss_alert(db, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return serialize_alert(db, alert)

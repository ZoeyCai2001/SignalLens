from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.settings_backup import PersonalSettingsBackup, PersonalSettingsRestoreResult
from app.services.settings_backup import (
    export_personal_settings_backup,
    restore_personal_settings_backup,
)

router = APIRouter()


@router.get("/backup", response_model=PersonalSettingsBackup)
async def export_settings_backup(db: DbSession) -> PersonalSettingsBackup:
    return export_personal_settings_backup(db)


@router.post("/restore", response_model=PersonalSettingsRestoreResult)
async def restore_settings_backup(
    payload: PersonalSettingsBackup,
    db: DbSession,
) -> PersonalSettingsRestoreResult:
    return restore_personal_settings_backup(db, payload)

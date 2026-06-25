from datetime import datetime

from pydantic import BaseModel


class SourceHealth(BaseModel):
    id: int
    name: str
    type: str
    access_method: str
    base_url: str | None
    auth_required: bool
    rate_limit: str | None
    polling_interval: str | None
    enabled: bool
    priority: int
    terms_notes: str | None
    latest_status: str
    latest_error: str | None
    last_started_at: datetime | None
    last_finished_at: datetime | None
    items_fetched: int
    items_stored: int


class SourceUpdate(BaseModel):
    enabled: bool | None = None
    priority: int | None = None
    rate_limit: str | None = None
    polling_interval: str | None = None
    terms_notes: str | None = None

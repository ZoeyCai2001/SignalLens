from datetime import datetime

from pydantic import BaseModel


class SourceHealth(BaseModel):
    id: int
    name: str
    type: str
    access_method: str
    enabled: bool
    latest_status: str
    latest_error: str | None
    last_started_at: datetime | None
    last_finished_at: datetime | None
    items_fetched: int
    items_stored: int


class SourceUpdate(BaseModel):
    enabled: bool | None = None
    priority: int | None = None
    polling_interval: str | None = None
    terms_notes: str | None = None

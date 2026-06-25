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

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
    raw_content_policy: str
    failure_handling: str
    latest_status: str
    latest_error: str | None
    last_started_at: datetime | None
    last_finished_at: datetime | None
    last_success_at: datetime | None
    next_run_due_at: datetime | None = None
    is_stale: bool = False
    items_fetched: int
    items_stored: int
    failure_count: int = 0
    needs_attention: bool = False
    recent_run_count: int = 0
    recent_success_rate: float | None = None
    recent_store_rate: float | None = None
    recent_items_fetched: int = 0
    recent_items_stored: int = 0


class SourceRunHistoryItem(BaseModel):
    id: int
    source_id: int
    source_name: str
    status: str
    items_fetched: int
    items_stored: int
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None


class SourceCreate(BaseModel):
    name: str
    type: str = "rss"
    access_method: str = "rss"
    base_url: str | None = None
    auth_required: bool = False
    rate_limit: str | None = None
    polling_interval: str | None = None
    enabled: bool = True
    priority: int = 100
    terms_notes: str | None = None


class SourceUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    access_method: str | None = None
    base_url: str | None = None
    auth_required: bool | None = None
    enabled: bool | None = None
    priority: int | None = None
    rate_limit: str | None = None
    polling_interval: str | None = None
    terms_notes: str | None = None

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class IngestionRunResponse(BaseModel):
    source_name: str
    status: str
    items_fetched: int
    items_stored: int
    error_message: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ScheduledCycleResponse(BaseModel):
    started_at: datetime
    finished_at: datetime
    seeded_stock_count: int
    seeded_company_count: int
    seeded_topic_count: int
    seeded_product_count: int
    generated_alert_count: int
    saved_digest_date: date | None = None
    ingestion_results: list[IngestionRunResponse]

    model_config = ConfigDict(from_attributes=True)

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, model_validator


class IngestionRunResponse(BaseModel):
    source_name: str
    status: str
    items_fetched: int
    items_stored: int
    error_message: str | None = None
    store_rate: float = 0
    needs_attention: bool = False
    recovery_hint: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def derive_operational_fields(self) -> "IngestionRunResponse":
        self.store_rate = compute_store_rate(
            items_fetched=self.items_fetched,
            items_stored=self.items_stored,
        )
        self.needs_attention = ingestion_run_needs_attention(
            status=self.status,
            items_fetched=self.items_fetched,
            items_stored=self.items_stored,
            error_message=self.error_message,
        )
        self.recovery_hint = build_ingestion_recovery_hint(
            status=self.status,
            items_fetched=self.items_fetched,
            items_stored=self.items_stored,
            error_message=self.error_message,
        )
        return self


def compute_store_rate(items_fetched: int, items_stored: int) -> float:
    if items_fetched <= 0:
        return 0
    return round(min(max(items_stored / items_fetched, 0), 1), 3)


def ingestion_run_needs_attention(
    status: str,
    items_fetched: int,
    items_stored: int,
    error_message: str | None,
) -> bool:
    normalized_status = status.strip().lower()
    if normalized_status == "failed":
        return True
    if normalized_status == "skipped" and error_message:
        return True
    return normalized_status == "success" and items_fetched > 0 and items_stored == 0


def build_ingestion_recovery_hint(
    status: str,
    items_fetched: int,
    items_stored: int,
    error_message: str | None,
) -> str | None:
    normalized_status = status.strip().lower()
    normalized_error = (error_message or "").strip().lower()
    if "not configured" in normalized_error or "api key" in normalized_error:
        return "Add the required API key in .env or disable this optional source."
    if "rate limit" in normalized_error or "rate limited" in normalized_error:
        return "Wait for the provider rate limit window or reduce the polling frequency."
    if "disabled" in normalized_error:
        return "Enable the source before running it again."
    if "no runnable connector" in normalized_error:
        return "Add a supported RSS, GitHub, Product Hunt, or social-source URL before rerunning."
    if normalized_status == "failed":
        return "Check credentials, network access, rate limits, or source configuration before rerunning."
    if normalized_status == "skipped" and error_message:
        return "Review the source configuration or schedule before rerunning."
    if normalized_status == "success" and items_fetched > 0 and items_stored == 0:
        return "Fetched items were filtered or deduplicated; review source relevance and canonical URLs."
    return None


class ScheduledCycleResponse(BaseModel):
    started_at: datetime
    finished_at: datetime
    duration_seconds: float
    seeded_stock_count: int
    seeded_company_count: int
    seeded_topic_count: int
    seeded_product_count: int
    generated_alert_count: int
    saved_digest_date: date | None = None
    successful_source_count: int = 0
    failed_source_count: int = 0
    skipped_source_count: int = 0
    ingestion_results: list[IngestionRunResponse]

    model_config = ConfigDict(from_attributes=True)

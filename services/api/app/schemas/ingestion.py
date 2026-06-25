from pydantic import BaseModel, ConfigDict


class IngestionRunResponse(BaseModel):
    source_name: str
    status: str
    items_fetched: int
    items_stored: int
    error_message: str | None = None

    model_config = ConfigDict(from_attributes=True)

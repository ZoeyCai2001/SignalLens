from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.alerts import AlertRuleCreate
from app.schemas.preferences import UserPreferencesUpdate
from app.schemas.sources import SourceCreate
from app.schemas.watchlist import (
    CompanyWatchlistItemCreate,
    ProductWatchlistItemCreate,
    StockWatchlistItemCreate,
    TopicWatchlistItemCreate,
)


class PersonalSettingsBackup(BaseModel):
    version: int = 1
    exported_at: datetime
    preferences: UserPreferencesUpdate | None = None
    sources: list[SourceCreate] = Field(default_factory=list)
    alert_rules: list[AlertRuleCreate] = Field(default_factory=list)
    stock_watchlist: list[StockWatchlistItemCreate] = Field(default_factory=list)
    company_watchlist: list[CompanyWatchlistItemCreate] = Field(default_factory=list)
    topic_watchlist: list[TopicWatchlistItemCreate] = Field(default_factory=list)
    product_watchlist: list[ProductWatchlistItemCreate] = Field(default_factory=list)


class PersonalSettingsRestoreResult(BaseModel):
    version: int
    restored_at: datetime
    preferences_updated: bool = False
    sources_upserted: int = 0
    alert_rules_upserted: int = 0
    stock_watchlist_upserted: int = 0
    company_watchlist_upserted: int = 0
    topic_watchlist_upserted: int = 0
    product_watchlist_upserted: int = 0
    skipped_sections: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

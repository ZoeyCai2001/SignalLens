from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class Source(Base, TimestampMixin):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(80), nullable=False)
    access_method: Mapped[str] = mapped_column(String(80), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(500))
    auth_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rate_limit: Mapped[str | None] = mapped_column(String(120))
    polling_interval: Mapped[str | None] = mapped_column(String(120))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    terms_notes: Mapped[str | None] = mapped_column(Text)
    raw_content_policy: Mapped[str | None] = mapped_column(Text)

    raw_items: Mapped[list["RawItem"]] = relationship(back_populates="source")
    runs: Mapped[list["SourceRun"]] = relationship(back_populates="source")


class SourceRun(Base):
    __tablename__ = "source_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    items_fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    items_stored: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    source: Mapped[Source] = relationship(back_populates="runs")


class RawItem(Base):
    __tablename__ = "raw_items"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_raw_items_source_external_id"),
        UniqueConstraint("content_hash", name="uq_raw_items_content_hash"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(240))
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    raw_title: Mapped[str] = mapped_column(Text, nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text)
    raw_author: Mapped[str | None] = mapped_column(String(240))
    raw_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source: Mapped[Source] = relationship(back_populates="raw_items")
    normalized_item: Mapped["NormalizedItem | None"] = relationship(back_populates="raw_item")


class NormalizedItem(Base):
    __tablename__ = "normalized_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_item_id: Mapped[int] = mapped_column(ForeignKey("raw_items.id"), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_name: Mapped[str] = mapped_column(String(120), nullable=False)
    author: Mapped[str | None] = mapped_column(String(240))
    language: Mapped[str] = mapped_column(String(20), default="en", nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    text: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(80), default="technical_trend", nullable=False)
    subcategory: Mapped[str | None] = mapped_column(String(120))
    tickers: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    companies: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    products: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    topics: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    sentiment: Mapped[str] = mapped_column(String(40), default="neutral", nullable=False)
    relevance_score: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    classification_confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    importance_score: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    novelty_score: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    source_quality_score: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    stock_impact_score: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    summary_short: Mapped[str | None] = mapped_column(Text)
    summary_detailed: Mapped[str | None] = mapped_column(Text)
    why_it_matters: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    raw_item: Mapped[RawItem] = relationship(back_populates="normalized_item")
    user_actions: Mapped[list["UserItemAction"]] = relationship(back_populates="item")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="item")


class UserItemAction(Base, TimestampMixin):
    __tablename__ = "user_item_actions"
    __table_args__ = (
        UniqueConstraint("user_id", "item_id", name="uq_user_item_actions_user_item"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(120), default="local", nullable=False)
    item_id: Mapped[int] = mapped_column(ForeignKey("normalized_items.id"), nullable=False)
    is_saved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_important: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    personal_note: Mapped[str | None] = mapped_column(Text)
    manual_tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    usefulness_feedback: Mapped[str | None] = mapped_column(String(20))
    usefulness_feedback_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    item: Mapped[NormalizedItem] = relationship(back_populates="user_actions")


class UserPreference(Base, TimestampMixin):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(120), unique=True, default="local", nullable=False)
    ranking_weights: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    preferred_sources: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    blocked_sources: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    language_preferences: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)


class DailyDigestSnapshot(Base, TimestampMixin):
    __tablename__ = "daily_digest_snapshots"
    __table_args__ = (
        UniqueConstraint("user_id", "digest_date", name="uq_daily_digest_snapshots_user_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(120), default="local", nullable=False)
    digest_date: Mapped[date] = mapped_column(Date, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    total_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    limit_per_section: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    markdown: Mapped[str] = mapped_column(Text, nullable=False)


class StockPricePoint(Base, TimestampMixin):
    __tablename__ = "stock_price_points"
    __table_args__ = (
        UniqueConstraint("ticker", "price_date", name="uq_stock_price_points_ticker_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    price_date: Mapped[date] = mapped_column(Date, nullable=False)
    open_price: Mapped[float] = mapped_column(Float, nullable=False)
    high_price: Mapped[float] = mapped_column(Float, nullable=False)
    low_price: Mapped[float] = mapped_column(Float, nullable=False)
    close_price: Mapped[float] = mapped_column(Float, nullable=False)
    adjusted_close: Mapped[float | None] = mapped_column(Float)
    volume: Mapped[int | None] = mapped_column(Integer)
    source_name: Mapped[str] = mapped_column(String(120), default="Alpha Vantage", nullable=False)


class StockWatchlistItem(Base, TimestampMixin):
    __tablename__ = "stock_watchlist_items"
    __table_args__ = (
        UniqueConstraint("user_id", "ticker", name="uq_stock_watchlist_user_ticker"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(120), default="local", nullable=False)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    company_name: Mapped[str] = mapped_column(String(240), nullable=False)
    exchange: Mapped[str] = mapped_column(String(80), nullable=False)
    sector: Mapped[str] = mapped_column(String(120), nullable=False)
    industry: Mapped[str] = mapped_column(String(160), nullable=False)
    market_cap_usd: Mapped[float | None] = mapped_column(Float)
    priority: Mapped[str] = mapped_column(String(40), default="Medium", nullable=False)
    group_name: Mapped[str] = mapped_column(String(120), default="Watch Only", nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_holding: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    shares: Mapped[float | None] = mapped_column(Float)
    average_cost: Mapped[float | None] = mapped_column(Float)
    related_keywords: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    related_companies: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    related_ai_themes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class CompanyWatchlistItem(Base, TimestampMixin):
    __tablename__ = "company_watchlist_items"
    __table_args__ = (
        UniqueConstraint("user_id", "company_key", name="uq_company_watchlist_user_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(120), default="local", nullable=False)
    company_key: Mapped[str] = mapped_column(String(160), nullable=False)
    company_name: Mapped[str] = mapped_column(String(240), nullable=False)
    ticker: Mapped[str | None] = mapped_column(String(20))
    category: Mapped[str] = mapped_column(String(80), default="ai_company", nullable=False)
    priority: Mapped[str] = mapped_column(String(40), default="Medium", nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    include_in_digest: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    related_terms: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class TopicWatchlistItem(Base, TimestampMixin):
    __tablename__ = "topic_watchlist_items"
    __table_args__ = (
        UniqueConstraint("user_id", "topic", name="uq_topic_watchlist_user_topic"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(120), default="local", nullable=False)
    topic: Mapped[str] = mapped_column(String(160), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(80), default="technical_trend", nullable=False)
    priority: Mapped[str] = mapped_column(String(40), default="Medium", nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    include_in_digest: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    related_terms: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class ProductWatchlistItem(Base, TimestampMixin):
    __tablename__ = "product_watchlist_items"
    __table_args__ = (
        UniqueConstraint("user_id", "category", name="uq_product_watchlist_user_category"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(120), default="local", nullable=False)
    category: Mapped[str] = mapped_column(String(160), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    priority: Mapped[str] = mapped_column(String(40), default="Medium", nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    include_in_digest: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    related_terms: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class AlertRule(Base, TimestampMixin):
    __tablename__ = "alert_rules"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_alert_rules_user_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(120), default="local", nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(80), default="all", nullable=False)
    severity: Mapped[str] = mapped_column(String(40), default="medium", nullable=False)
    min_importance_score: Mapped[float] = mapped_column(Float, default=0.75, nullable=False)
    min_stock_impact_score: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    tickers: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    topics: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    snoozed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    alerts: Mapped[list["Alert"]] = relationship(back_populates="rule")


class Alert(Base, TimestampMixin):
    __tablename__ = "alerts"
    __table_args__ = (
        UniqueConstraint("user_id", "item_id", "rule_id", name="uq_alerts_user_item_rule"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(120), default="local", nullable=False)
    item_id: Mapped[int] = mapped_column(ForeignKey("normalized_items.id"), nullable=False)
    rule_id: Mapped[int] = mapped_column(ForeignKey("alert_rules.id"), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(40), default="medium", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False)

    item: Mapped[NormalizedItem] = relationship(back_populates="alerts")
    rule: Mapped[AlertRule] = relationship(back_populates="alerts")


class LlmUsageEvent(Base):
    __tablename__ = "llm_usage_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(120), default="local", nullable=False)
    operation: Mapped[str] = mapped_column(String(80), nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(160), nullable=False)
    item_id: Mapped[int | None] = mapped_column(ForeignKey("normalized_items.id"), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

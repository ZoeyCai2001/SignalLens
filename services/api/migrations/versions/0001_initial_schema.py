"""Initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("type", sa.String(length=80), nullable=False),
        sa.Column("access_method", sa.String(length=80), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=True),
        sa.Column("auth_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("rate_limit", sa.String(length=120), nullable=True),
        sa.Column("polling_interval", sa.String(length=120), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("terms_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("name", name="uq_sources_name"),
    )

    op.create_table(
        "source_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("items_fetched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_stored", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "raw_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("external_id", sa.String(length=240), nullable=True),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("raw_title", sa.Text(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("raw_author", sa.String(length=240), nullable=True),
        sa.Column("raw_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("source_id", "external_id", name="uq_raw_items_source_external_id"),
        sa.UniqueConstraint("content_hash", name="uq_raw_items_content_hash"),
    )
    op.create_index("ix_raw_items_published_at", "raw_items", ["published_at"])

    op.create_table(
        "normalized_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("raw_item_id", sa.Integer(), sa.ForeignKey("raw_items.id"), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("source_name", sa.String(length=120), nullable=False),
        sa.Column("author", sa.String(length=240), nullable=True),
        sa.Column("language", sa.String(length=20), nullable=False, server_default="en"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column(
            "category",
            sa.String(length=80),
            nullable=False,
            server_default="technical_trend",
        ),
        sa.Column("subcategory", sa.String(length=120), nullable=True),
        sa.Column("tickers", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("companies", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("products", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("topics", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("sentiment", sa.String(length=40), nullable=False, server_default="neutral"),
        sa.Column("relevance_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("importance_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("novelty_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("source_quality_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("stock_impact_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("summary_short", sa.Text(), nullable=True),
        sa.Column("summary_detailed", sa.Text(), nullable=True),
        sa.Column("why_it_matters", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_normalized_items_published_at", "normalized_items", ["published_at"])
    op.create_index("ix_normalized_items_category", "normalized_items", ["category"])

    op.create_table(
        "stock_watchlist_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(length=120), nullable=False, server_default="local"),
        sa.Column("ticker", sa.String(length=20), nullable=False),
        sa.Column("company_name", sa.String(length=240), nullable=False),
        sa.Column("exchange", sa.String(length=80), nullable=False),
        sa.Column("sector", sa.String(length=120), nullable=False),
        sa.Column("industry", sa.String(length=160), nullable=False),
        sa.Column("priority", sa.String(length=40), nullable=False, server_default="Medium"),
        sa.Column("group_name", sa.String(length=120), nullable=False, server_default="Watch Only"),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_holding", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("shares", sa.Float(), nullable=True),
        sa.Column("average_cost", sa.Float(), nullable=True),
        sa.Column(
            "related_keywords",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
        sa.Column(
            "related_companies",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
        sa.Column(
            "related_ai_themes",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "ticker", name="uq_stock_watchlist_user_ticker"),
    )


def downgrade() -> None:
    op.drop_table("stock_watchlist_items")
    op.drop_index("ix_normalized_items_category", table_name="normalized_items")
    op.drop_index("ix_normalized_items_published_at", table_name="normalized_items")
    op.drop_table("normalized_items")
    op.drop_index("ix_raw_items_published_at", table_name="raw_items")
    op.drop_table("raw_items")
    op.drop_table("source_runs")
    op.drop_table("sources")

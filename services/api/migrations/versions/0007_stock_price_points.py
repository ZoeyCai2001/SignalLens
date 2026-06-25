"""Add stock price points

Revision ID: 0007_stock_price_points
Revises: 0006_daily_digest_snapshots
Create Date: 2026-06-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_stock_price_points"
down_revision: str | None = "0006_daily_digest_snapshots"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stock_price_points",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ticker", sa.String(length=20), nullable=False),
        sa.Column("price_date", sa.Date(), nullable=False),
        sa.Column("open_price", sa.Float(), nullable=False),
        sa.Column("high_price", sa.Float(), nullable=False),
        sa.Column("low_price", sa.Float(), nullable=False),
        sa.Column("close_price", sa.Float(), nullable=False),
        sa.Column("adjusted_close", sa.Float()),
        sa.Column("volume", sa.Integer()),
        sa.Column(
            "source_name",
            sa.String(length=120),
            nullable=False,
            server_default="Alpha Vantage",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("ticker", "price_date", name="uq_stock_price_points_ticker_date"),
    )


def downgrade() -> None:
    op.drop_table("stock_price_points")

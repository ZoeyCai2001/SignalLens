"""Add stock watchlist market cap

Revision ID: 0018_stock_market_cap
Revises: 0017_llm_usage_events
Create Date: 2026-07-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_stock_market_cap"
down_revision: str | None = "0017_llm_usage_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "stock_watchlist_items",
        sa.Column("market_cap_usd", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("stock_watchlist_items", "market_cap_usd")

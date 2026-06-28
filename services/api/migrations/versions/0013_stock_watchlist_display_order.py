"""Add stock watchlist display order

Revision ID: 0013_stock_order
Revises: 0012_language_preferences
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_stock_order"
down_revision: str | None = "0012_language_preferences"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "stock_watchlist_items",
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="100"),
    )


def downgrade() -> None:
    op.drop_column("stock_watchlist_items", "display_order")

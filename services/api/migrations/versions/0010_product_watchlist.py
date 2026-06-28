"""Add product watchlist

Revision ID: 0010_product_watchlist
Revises: 0009_source_preferences
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_product_watchlist"
down_revision: str | None = "0009_source_preferences"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_watchlist_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=160), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("priority", sa.String(length=40), nullable=False),
        sa.Column("is_pinned", sa.Boolean(), nullable=False),
        sa.Column("include_in_digest", sa.Boolean(), nullable=False),
        sa.Column("related_terms", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "category", name="uq_product_watchlist_user_category"),
    )


def downgrade() -> None:
    op.drop_table("product_watchlist_items")

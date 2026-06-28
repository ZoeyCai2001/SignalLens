"""Add company watchlist

Revision ID: 0011_company_watchlist
Revises: 0010_product_watchlist
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_company_watchlist"
down_revision: str | None = "0010_product_watchlist"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "company_watchlist_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=120), nullable=False),
        sa.Column("company_key", sa.String(length=160), nullable=False),
        sa.Column("company_name", sa.String(length=240), nullable=False),
        sa.Column("ticker", sa.String(length=20), nullable=True),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("priority", sa.String(length=40), nullable=False),
        sa.Column("is_pinned", sa.Boolean(), nullable=False),
        sa.Column("include_in_digest", sa.Boolean(), nullable=False),
        sa.Column("related_terms", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "company_key", name="uq_company_watchlist_user_key"),
    )


def downgrade() -> None:
    op.drop_table("company_watchlist_items")

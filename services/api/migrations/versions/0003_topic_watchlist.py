"""Add topic watchlist

Revision ID: 0003_topic_watchlist
Revises: 0002_user_item_actions
Create Date: 2026-06-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_topic_watchlist"
down_revision: str | None = "0002_user_item_actions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "topic_watchlist_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(length=120), nullable=False, server_default="local"),
        sa.Column("topic", sa.String(length=160), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column(
            "category",
            sa.String(length=80),
            nullable=False,
            server_default="technical_trend",
        ),
        sa.Column("priority", sa.String(length=40), nullable=False, server_default="Medium"),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("include_in_digest", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("related_terms", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "topic", name="uq_topic_watchlist_user_topic"),
    )


def downgrade() -> None:
    op.drop_table("topic_watchlist_items")

"""Add user item actions

Revision ID: 0002_user_item_actions
Revises: 0001_initial_schema
Create Date: 2026-06-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_user_item_actions"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_item_actions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(length=120), nullable=False, server_default="local"),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("normalized_items.id"), nullable=False),
        sa.Column("is_saved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_hidden", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_important", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "item_id", name="uq_user_item_actions_user_item"),
    )
    op.create_index("ix_user_item_actions_item_id", "user_item_actions", ["item_id"])


def downgrade() -> None:
    op.drop_index("ix_user_item_actions_item_id", table_name="user_item_actions")
    op.drop_table("user_item_actions")

"""Add user item notes and tags

Revision ID: 0014_user_item_notes
Revises: 0013_stock_order
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_user_item_notes"
down_revision: str | None = "0013_stock_order"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user_item_actions", sa.Column("personal_note", sa.Text(), nullable=True))
    op.add_column(
        "user_item_actions",
        sa.Column("manual_tags", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
    )


def downgrade() -> None:
    op.drop_column("user_item_actions", "manual_tags")
    op.drop_column("user_item_actions", "personal_note")

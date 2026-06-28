"""Add user item read state

Revision ID: 0015_user_item_read_state
Revises: 0014_user_item_notes
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_user_item_read_state"
down_revision: str | None = "0014_user_item_notes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_item_actions",
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "user_item_actions",
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_item_actions", "read_at")
    op.drop_column("user_item_actions", "is_read")

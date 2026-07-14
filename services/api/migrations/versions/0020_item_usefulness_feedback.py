"""Add per-item usefulness feedback

Revision ID: 0020_item_usefulness_feedback
Revises: 0019_source_raw_content_policy
Create Date: 2026-07-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_item_usefulness_feedback"
down_revision: str | None = "0019_source_raw_content_policy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_item_actions",
        sa.Column("usefulness_feedback", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "user_item_actions",
        sa.Column("usefulness_feedback_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_item_actions", "usefulness_feedback_at")
    op.drop_column("user_item_actions", "usefulness_feedback")

"""Add source preferences

Revision ID: 0009_source_preferences
Revises: 0008_classification_confidence
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_source_preferences"
down_revision: str | None = "0008_classification_confidence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_preferences",
        sa.Column(
            "preferred_sources",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
    )
    op.add_column(
        "user_preferences",
        sa.Column(
            "blocked_sources",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
    )


def downgrade() -> None:
    op.drop_column("user_preferences", "blocked_sources")
    op.drop_column("user_preferences", "preferred_sources")

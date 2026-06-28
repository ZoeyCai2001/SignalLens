"""Add classification confidence

Revision ID: 0008_classification_confidence
Revises: 0007_stock_price_points
Create Date: 2026-06-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_classification_confidence"
down_revision: str | None = "0007_stock_price_points"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "normalized_items",
        sa.Column(
            "classification_confidence",
            sa.Float(),
            nullable=False,
            server_default="0.5",
        ),
    )


def downgrade() -> None:
    op.drop_column("normalized_items", "classification_confidence")

"""Add source raw content policy

Revision ID: 0019_source_raw_content_policy
Revises: 0018_stock_market_cap
Create Date: 2026-07-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_source_raw_content_policy"
down_revision: str | None = "0018_stock_market_cap"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sources",
        sa.Column("raw_content_policy", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sources", "raw_content_policy")

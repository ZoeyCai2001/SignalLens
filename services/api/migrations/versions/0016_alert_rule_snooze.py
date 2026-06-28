"""Add alert rule snooze timestamp

Revision ID: 0016_alert_rule_snooze
Revises: 0015_user_item_read_state
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_alert_rule_snooze"
down_revision: str | None = "0015_user_item_read_state"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "alert_rules",
        sa.Column("snoozed_until", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("alert_rules", "snoozed_until")

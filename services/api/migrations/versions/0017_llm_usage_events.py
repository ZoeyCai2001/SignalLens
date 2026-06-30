"""Add LLM usage event ledger

Revision ID: 0017_llm_usage_events
Revises: 0016_alert_rule_snooze
Create Date: 2026-06-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_llm_usage_events"
down_revision: str | None = "0016_alert_rule_snooze"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_usage_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(length=120), nullable=False),
        sa.Column("operation", sa.String(length=80), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=160), nullable=False),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("normalized_items.id"), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_llm_usage_events_created_at", "llm_usage_events", ["created_at"])
    op.create_index("ix_llm_usage_events_user_operation", "llm_usage_events", ["user_id", "operation"])


def downgrade() -> None:
    op.drop_index("ix_llm_usage_events_user_operation", table_name="llm_usage_events")
    op.drop_index("ix_llm_usage_events_created_at", table_name="llm_usage_events")
    op.drop_table("llm_usage_events")

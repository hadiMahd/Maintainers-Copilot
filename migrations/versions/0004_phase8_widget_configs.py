"""Phase 8 widget configuration table.

Revision ID: 0004_phase8_widget_configs
Revises: 0003_phase6_auth_memory_audit
Create Date: 2026-05-21 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_phase8_widget_configs"
down_revision: Union[str, Sequence[str], None] = "0003_phase6_auth_memory_audit"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "widget_configs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("allowed_origins", sa.Text(), nullable=False),
        sa.Column("theme", sa.String(30), nullable=False, server_default="default"),
        sa.Column("welcome_message", sa.String(500), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_by_user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("updated_by_user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_widget_configs_name", "widget_configs", ["name"])


def downgrade() -> None:
    op.drop_index("ix_widget_configs_name", table_name="widget_configs")
    op.drop_table("widget_configs")

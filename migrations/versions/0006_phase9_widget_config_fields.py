"""Phase 9: add widget_id, greeting, position, enabled_tools to widget_configs.

greeting is a new column; welcome_message is kept for backward compatibility.
Services prefer greeting, falling back to welcome_message when greeting is null.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("widget_configs", sa.Column("widget_id", sa.String(36), nullable=True))
    op.add_column("widget_configs", sa.Column("greeting", sa.String(500), nullable=True))
    op.add_column(
        "widget_configs",
        sa.Column("position", sa.String(20), nullable=False, server_default="bottom-right"),
    )
    op.add_column(
        "widget_configs",
        sa.Column("enabled_tools", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )

    op.create_index("ix_widget_configs_widget_id", "widget_configs", ["widget_id"], unique=True)

    conn = op.get_bind()
    conn.execute(sa.text("""
            UPDATE widget_configs
            SET widget_id = gen_random_uuid()::text
            WHERE widget_id IS NULL
        """))
    op.alter_column("widget_configs", "widget_id", nullable=False)


def downgrade() -> None:
    op.drop_index("ix_widget_configs_widget_id", table_name="widget_configs")
    op.drop_column("widget_configs", "enabled_tools")
    op.drop_column("widget_configs", "position")
    op.drop_column("widget_configs", "greeting")
    op.drop_column("widget_configs", "widget_id")

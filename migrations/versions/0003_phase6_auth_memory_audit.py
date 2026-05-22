"""Phase 6 auth, memory, and audit tables.

Revision ID: 0003_phase6_auth_memory_audit
Revises: 0002_phase5_rag
Create Date: 2026-05-20 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0003_phase6_auth_memory_audit"
down_revision: Union[str, Sequence[str], None] = "0002_phase5_rag"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.String(10),
            nullable=False,
            server_default="user",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_check_constraint("ck_users_role", "users", "role IN ('user', 'admin')")

    op.create_table(
        "token_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("refresh_token_hash", sa.String(128), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reuse_detected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent_hash", sa.String(128), nullable=True),
        sa.Column("ip_hash", sa.String(128), nullable=True),
    )
    op.create_index("ix_token_sessions_user_id", "token_sessions", ["user_id"])
    op.create_index("ix_token_sessions_refresh_hash", "token_sessions", ["refresh_token_hash"])
    op.create_foreign_key(
        "fk_token_sessions_user",
        "token_sessions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_table(
        "admin_invitations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("invitee_email", sa.String(255), nullable=False),
        sa.Column("created_by_user_id", sa.String(36), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column(
            "status",
            sa.String(12),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_by_user_id", sa.String(36), nullable=True),
    )
    op.create_index("ix_admin_invitations_status", "admin_invitations", ["status"])
    op.create_check_constraint(
        "ck_admin_invitations_status",
        "admin_invitations",
        "status IN ('pending', 'accepted', 'revoked', 'expired')",
    )
    op.create_foreign_key(
        "fk_admin_inv_created_by",
        "admin_invitations",
        "users",
        ["created_by_user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_table(
        "long_term_memory",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_user_id", sa.String(36), nullable=False),
        sa.Column(
            "memory_type",
            sa.String(16),
            nullable=False,
            server_default="semantic",
        ),
        sa.Column("redacted_content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("embedding", Vector(384), nullable=True),
        sa.Column("source", sa.String(64), nullable=True),
        sa.Column("created_by_user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("extra_data", sa.JSON(), nullable=True),
    )
    op.create_index("ix_long_term_memory_owner", "long_term_memory", ["owner_user_id"])
    op.create_check_constraint(
        "ck_long_term_memory_type",
        "long_term_memory",
        "memory_type IN ('episodic', 'semantic', 'procedural')",
    )
    op.create_foreign_key(
        "fk_long_term_memory_owner",
        "long_term_memory",
        "users",
        ["owner_user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_user_id", sa.String(36), nullable=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("target_type", sa.String(64), nullable=True),
        sa.Column("target_id", sa.String(36), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("extra_data", sa.JSON(), nullable=True),
    )
    op.create_index("ix_audit_logs_actor", "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])
    op.create_foreign_key(
        "fk_audit_logs_actor",
        "audit_logs",
        "users",
        ["actor_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("long_term_memory")
    op.drop_table("admin_invitations")
    op.drop_table("token_sessions")
    op.drop_table("users")

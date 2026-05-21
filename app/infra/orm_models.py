"""SQLAlchemy ORM models for Phase 6 tables."""

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, JSON, String, Text, func
from sqlalchemy.orm import DeclarativeBase, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email", "email"),
        CheckConstraint("role IN ('user', 'admin')", name="ck_users_role"),
    )

    id = Column(String(36), primary_key=True)
    email = Column(String(255), nullable=False, unique=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(10), nullable=False, server_default="user")
    is_active = Column(Boolean(), nullable=False, server_default="true")
    is_verified = Column(Boolean(), nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


class TokenSession(Base):
    __tablename__ = "token_sessions"
    __table_args__ = (
        Index("ix_token_sessions_user_id", "user_id"),
        Index("ix_token_sessions_refresh_hash", "refresh_token_hash"),
    )

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    refresh_token_hash = Column(String(128), nullable=False)
    issued_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    rotated_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    reuse_detected_at = Column(DateTime(timezone=True), nullable=True)
    user_agent_hash = Column(String(128), nullable=True)
    ip_hash = Column(String(128), nullable=True)


class AdminInvitation(Base):
    __tablename__ = "admin_invitations"
    __table_args__ = (
        Index("ix_admin_invitations_status", "status"),
        CheckConstraint(
            "status IN ('pending', 'accepted', 'revoked', 'expired')",
            name="ck_admin_invitations_status",
        ),
    )

    id = Column(String(36), primary_key=True)
    invitee_email = Column(String(255), nullable=False)
    created_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(128), nullable=False)
    status = Column(String(12), nullable=False, server_default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    accepted_by_user_id = Column(String(36), nullable=True)


class LongTermMemory(Base):
    __tablename__ = "long_term_memory"
    __table_args__ = (
        Index("ix_long_term_memory_owner", "owner_user_id"),
        CheckConstraint(
            "memory_type IN ('episodic', 'semantic', 'procedural')",
            name="ck_long_term_memory_type",
        ),
    )

    id = Column(String(36), primary_key=True)
    owner_user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    memory_type = Column(String(16), nullable=False, server_default="semantic")
    redacted_content = Column(Text(), nullable=False)
    content_hash = Column(String(64), nullable=False)
    embedding = Column(Vector(384), nullable=True)
    source = Column(String(64), nullable=True)
    created_by_user_id = Column(String(36), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    extra_data = Column(JSON(), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_actor", "actor_user_id"),
        Index("ix_audit_logs_timestamp", "timestamp"),
    )

    id = Column(String(36), primary_key=True)
    actor_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(64), nullable=False)
    target_type = Column(String(64), nullable=True)
    target_id = Column(String(36), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    extra_data = Column(JSON(), nullable=True)


class WidgetConfig(Base):
    __tablename__ = "widget_configs"
    __table_args__ = (
        Index("ix_widget_configs_name", "name"),
    )

    id = Column(String(36), primary_key=True)
    name = Column(String(120), nullable=False)
    allowed_origins = Column(Text(), nullable=False)
    theme = Column(String(30), nullable=False, server_default="default")
    welcome_message = Column(String(500), nullable=True)
    is_enabled = Column(Boolean(), nullable=False, server_default="true")
    created_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    updated_by_user_id = Column(String(36), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

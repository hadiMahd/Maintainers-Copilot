"""Align long-term memory embeddings with Azure embedding dimensionality.

Revision ID: 0005_mem_embed_dim
Revises: 0004_phase8_widget_configs
Create Date: 2026-05-21
"""

from __future__ import annotations

from alembic import op

revision = "0005_mem_embed_dim"
down_revision = "0004_phase8_widget_configs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE long_term_memory
        ALTER COLUMN embedding TYPE vector(1536)
        USING NULL::vector(1536)
        """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE long_term_memory
        ALTER COLUMN embedding TYPE vector(384)
        USING NULL::vector(384)
        """)

"""Phase 5 RAG tables.

Revision ID: 0002_phase5_rag
Revises: 0001_baseline
Create Date: 2026-05-20 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0002_phase5_rag"
down_revision: Union[str, Sequence[str], None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rag_sources",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_id", sa.String(64), nullable=False, unique=True),
        sa.Column("source_type", sa.String(16), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_rag_sources_source_id", "rag_sources", ["source_id"])
    op.create_index("ix_rag_sources_source_type", "rag_sources", ["source_type"])

    op.create_table(
        "rag_chunks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chunk_id", sa.String(64), nullable=False, unique=True),
        sa.Column("parent_id", sa.String(64), nullable=False),
        sa.Column("source_type", sa.String(16), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=True),
        sa.Column("issue_number", sa.Integer(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("labels", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False, default=0),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("row_created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_rag_chunks_chunk_id", "rag_chunks", ["chunk_id"])
    op.create_index("ix_rag_chunks_parent_id", "rag_chunks", ["parent_id"])
    op.create_index("ix_rag_chunks_source_type", "rag_chunks", ["source_type"])
    op.create_index("ix_rag_chunks_content_hash", "rag_chunks", ["content_hash"])

    op.create_table(
        "rag_embeddings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("embedding_id", sa.String(64), nullable=False, unique=True),
        sa.Column("chunk_id", sa.String(64), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("embedding_model", sa.String(64), nullable=False),
        sa.Column("embedding_dim", sa.Integer(), nullable=False),
        sa.Column("vector", Vector(1536), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_rag_embeddings_embedding_id", "rag_embeddings", ["embedding_id"])
    op.create_index("ix_rag_embeddings_chunk_id", "rag_embeddings", ["chunk_id"])
    op.create_index(
        "ix_rag_embeddings_content_hash_model",
        "rag_embeddings",
        ["content_hash", "embedding_model"],
    )

    op.create_table(
        "rag_sparse_search",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chunk_id", sa.String(64), nullable=False),
        sa.Column("search_text", sa.Text(), nullable=False),
        sa.Column("title_terms", sa.Text(), nullable=True),
        sa.Column("metadata_terms", sa.Text(), nullable=True),
        sa.Column("search_vector", sa.dialects.postgresql.TSVECTOR(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_rag_sparse_search_chunk_id",
        "rag_sparse_search",
        ["chunk_id"],
        unique=True,
    )

    op.create_table(
        "rag_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("snapshot_id", sa.String(64), nullable=False, unique=True),
        sa.Column("conversation_id", sa.String(64), nullable=False),
        sa.Column("message_id", sa.String(64), nullable=False),
        sa.Column("trace_id", sa.String(64), nullable=True),
        sa.Column("query", sa.Text(), nullable=True),
        sa.Column("chunk_ids", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("scores", sa.ARRAY(sa.Float()), nullable=True),
        sa.Column("metadata_preview", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_rag_snapshots_conversation_id", "rag_snapshots", ["conversation_id"])
    op.create_index("ix_rag_snapshots_created_at", "rag_snapshots", ["created_at"])


def downgrade() -> None:
    op.drop_table("rag_snapshots")
    op.drop_table("rag_sparse_search")
    op.drop_table("rag_embeddings")
    op.drop_table("rag_chunks")
    op.drop_table("rag_sources")

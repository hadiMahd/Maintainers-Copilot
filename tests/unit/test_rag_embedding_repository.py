"""Unit tests for RAG embedding repository row mapping."""

from __future__ import annotations

from datetime import datetime, timezone

from app.repositories.rag_embedding_repository import _row_to_embedding


def test_row_to_embedding_parses_pgvector_text() -> None:
    row = {
        "embedding_id": "emb-1",
        "chunk_id": "chunk-1",
        "content_hash": "hash-1",
        "embedding_model": "text-embedding-3-small",
        "embedding_dim": 3,
        "vector": "[0.1,-0.2,3]",
        "created_at": datetime.now(timezone.utc),
    }

    embedding = _row_to_embedding(row)

    assert embedding.vector == [0.1, -0.2, 3.0]


def test_row_to_embedding_keeps_sequence_vectors() -> None:
    row = {
        "embedding_id": "emb-1",
        "chunk_id": "chunk-1",
        "content_hash": "hash-1",
        "embedding_model": "text-embedding-3-small",
        "embedding_dim": 3,
        "vector": (0.1, -0.2, 3),
        "created_at": datetime.now(timezone.utc),
    }

    embedding = _row_to_embedding(row)

    assert embedding.vector == [0.1, -0.2, 3.0]

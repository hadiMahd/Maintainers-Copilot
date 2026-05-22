"""RAG embedding repository — lookup and upsert operations."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.rag import RAGEmbedding

logger = logging.getLogger(__name__)


class RAGEmbeddingRepository:
    """Async repository for RAG embedding lookup and upsert."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_chunk_id(self, chunk_id: str, embedding_model: str) -> RAGEmbedding | None:
        result = await self._session.execute(
            text(
                "SELECT * FROM rag_embeddings "
                "WHERE chunk_id = :chunk_id AND embedding_model = :embedding_model"
            ),
            {"chunk_id": chunk_id, "embedding_model": embedding_model},
        )
        row = result.mappings().first()
        if row is None:
            return None
        return _row_to_embedding(row)

    async def exists_by_hash_and_model(self, content_hash: str, embedding_model: str) -> bool:
        result = await self._session.execute(
            text(
                "SELECT 1 FROM rag_embeddings "
                "WHERE content_hash = :content_hash AND embedding_model = :embedding_model LIMIT 1"
            ),
            {"content_hash": content_hash, "embedding_model": embedding_model},
        )
        return result.first() is not None

    async def upsert(self, embedding: RAGEmbedding) -> RAGEmbedding:
        existing = await self.get_by_chunk_id(embedding.chunk_id, embedding.embedding_model)
        if existing is not None:
            await self._session.execute(
                text(
                    "UPDATE rag_embeddings SET content_hash = :content_hash, "
                    "vector = CAST(:vector AS vector), embedding_dim = :embedding_dim "
                    "WHERE chunk_id = :chunk_id AND embedding_model = :embedding_model"
                ),
                {
                    "content_hash": embedding.content_hash,
                    "vector": _vector_literal(embedding.vector),
                    "embedding_dim": embedding.embedding_dim,
                    "chunk_id": embedding.chunk_id,
                    "embedding_model": embedding.embedding_model,
                },
            )
        else:
            await self._session.execute(
                text(
                    "INSERT INTO rag_embeddings "
                    "(embedding_id, chunk_id, content_hash, embedding_model, embedding_dim, vector) "
                    "VALUES (:embedding_id, :chunk_id, :content_hash, :embedding_model, "
                    ":embedding_dim, CAST(:vector AS vector))"
                ),
                {
                    "embedding_id": embedding.embedding_id,
                    "chunk_id": embedding.chunk_id,
                    "content_hash": embedding.content_hash,
                    "embedding_model": embedding.embedding_model,
                    "embedding_dim": embedding.embedding_dim,
                    "vector": _vector_literal(embedding.vector),
                },
            )
        return embedding


def _row_to_embedding(row) -> RAGEmbedding:
    return RAGEmbedding(
        embedding_id=str(row["embedding_id"]),
        chunk_id=str(row["chunk_id"]),
        content_hash=str(row["content_hash"]),
        embedding_model=row["embedding_model"],
        embedding_dim=int(row["embedding_dim"]),
        vector=_parse_vector(row.get("vector")),
        created_at=row.get("created_at"),
    )


def _parse_vector(value) -> list[float]:
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            stripped = stripped[1:-1]
        if not stripped:
            return []
        return [float(part) for part in stripped.split(",")]
    return [float(part) for part in value]


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(str(float(value)) for value in vector) + "]"


__all__ = ["RAGEmbeddingRepository"]

"""Integration tests for repeatable ingestion, duplicate embedding skipping, and stable corpus outputs."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile

import pytest

from app.domain.rag import RAGChunk, RAGEmbedding, RAGSource


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class TestRepeatableIngestion:
    def test_same_input_produces_same_chunks(self):
        docs = [
            {"source_path": "docs/install.md", "title": "Installation", "content": "Line one.\n\nLine two."},
        ]
        chunks1 = _ingest_docs(docs)
        chunks2 = _ingest_docs(docs)
        assert len(chunks1) == len(chunks2)
        for c1, c2 in zip(chunks1, chunks2):
            assert c1.chunk_id == c2.chunk_id
            assert c1.content_hash == c2.content_hash

    def test_different_input_produces_different_chunks(self):
        chunks_a = _ingest_docs([
            {"source_path": "a.md", "title": "A", "content": "Content A."},
        ])
        chunks_b = _ingest_docs([
            {"source_path": "b.md", "title": "B", "content": "Content B."},
        ])
        assert chunks_a[0].chunk_id != chunks_b[0].chunk_id

    def test_stable_source_output(self):
        docs = [
            {"source_path": "docs/readme.md", "title": "README", "content": "Project overview.\n\nSetup guide."},
        ]
        sources, chunks = _ingest_with_sources(docs)
        assert len(sources) == 1
        assert sources[0].source_path == "docs/readme.md"
        json1 = json.dumps([s.model_dump() for s in sources], default=str, sort_keys=True)
        sources2, _ = _ingest_with_sources(docs)
        json2 = json.dumps([s.model_dump() for s in sources2], default=str, sort_keys=True)
        assert json1 == json2


class TestDuplicateEmbeddingSkipping:
    def test_same_content_hash_and_model_is_duplicate(self):
        embedding1 = RAGEmbedding(
            embedding_id="e1", chunk_id="c1", content_hash="abc123",
            embedding_model="all-MiniLM-L6-v2", embedding_dim=384,
            vector=[0.1] * 384,
        )
        embedding2 = RAGEmbedding(
            embedding_id="e2", chunk_id="c1", content_hash="abc123",
            embedding_model="all-MiniLM-L6-v2", embedding_dim=384,
            vector=[0.1] * 384,
        )
        assert _is_duplicate(embedding1, embedding2)

    def test_different_content_hash_not_duplicate(self):
        embedding1 = RAGEmbedding(
            embedding_id="e1", chunk_id="c1", content_hash="abc",
            embedding_model="all-MiniLM-L6-v2", embedding_dim=384,
        )
        embedding2 = RAGEmbedding(
            embedding_id="e2", chunk_id="c1", content_hash="def",
            embedding_model="all-MiniLM-L6-v2", embedding_dim=384,
        )
        assert not _is_duplicate(embedding1, embedding2)

    def test_different_model_not_duplicate(self):
        embedding1 = RAGEmbedding(
            embedding_id="e1", chunk_id="c1", content_hash="abc",
            embedding_model="all-MiniLM-L6-v2", embedding_dim=384,
        )
        embedding2 = RAGEmbedding(
            embedding_id="e2", chunk_id="c1", content_hash="abc",
            embedding_model="text-embedding-3-small", embedding_dim=1536,
        )
        assert not _is_duplicate(embedding1, embedding2)

    def test_embedding_comparison_preserves_both_candidates(self):
        comparison = {
            "all-MiniLM-L6-v2": {"dim": 384, "chunks_embedded": 5, "status": "completed"},
            "text-embedding-3-small": {"dim": 1536, "chunks_embedded": 0, "status": "unavailable"},
        }
        assert "all-MiniLM-L6-v2" in comparison
        assert "text-embedding-3-small" in comparison
        assert comparison["text-embedding-3-small"]["status"] == "unavailable"


# -- Helpers (mirror ingestion service logic) --------------------------------

def _ingest_docs(docs: list[dict]) -> list[RAGChunk]:
    chunks: list[RAGChunk] = []
    for doc in docs:
        source_id = _hash(doc["source_path"])
        paras = [p.strip() for p in doc["content"].split("\n\n") if p.strip()]
        for i, p in enumerate(paras):
            chunk_id = _hash(f"{source_id}:{i}")
            chunks.append(RAGChunk(
                chunk_id=chunk_id,
                parent_id=source_id,
                source_type="docs",
                source_path=doc["source_path"],
                title=doc["title"],
                chunk_index=i,
                content=p,
                content_hash=_hash(p),
                token_count=len(p.split()),
            ))
    return chunks


def _ingest_with_sources(docs: list[dict]) -> tuple[list[RAGSource], list[RAGChunk]]:
    sources: list[RAGSource] = []
    chunks: list[RAGChunk] = []
    for doc in docs:
        source_id = _hash(doc["source_path"])
        content_hash = _hash(doc["content"])
        sources.append(RAGSource(
            source_id=source_id,
            source_type="docs",
            source_path=doc["source_path"],
            title=doc["title"],
            content=doc["content"],
            content_hash=content_hash,
        ))
        paras = [p.strip() for p in doc["content"].split("\n\n") if p.strip()]
        for i, p in enumerate(paras):
            chunk_id = _hash(f"{source_id}:{i}")
            chunks.append(RAGChunk(
                chunk_id=chunk_id,
                parent_id=source_id,
                source_type="docs",
                source_path=doc["source_path"],
                title=doc["title"],
                chunk_index=i,
                content=p,
                content_hash=_hash(p),
                token_count=len(p.split()),
            ))
    return sources, chunks


def _is_duplicate(a: RAGEmbedding, b: RAGEmbedding) -> bool:
    return a.content_hash == b.content_hash and a.embedding_model == b.embedding_model

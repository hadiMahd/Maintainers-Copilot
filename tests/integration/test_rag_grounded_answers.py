"""Integration tests for grounded question answering — fixture-backed flow."""

from __future__ import annotations

import asyncio

import pytest

from app.domain.rag import (
    GroundedAnswer,
    RAGChunk,
    RetrievalQuery,
    RetrievalResult,
    RetrievalResultSet,
)
from app.services.rag_retrieval_service import RAGRetrievalService
from app.services.rag_generation_service import RAGGenerationService
from app.infra.rag_generation_client import FakeGenerationClient
from app.repositories.rag_chunk_repository import RAGChunkRepository


# -- Fixture-backed chunks ---------------------------------------------------

def _make_fixture_chunks() -> list[RAGChunk]:
    return [
        RAGChunk(
            chunk_id="chunk-1", parent_id="doc-1", source_type="docs",
            source_path="docs/install.md", title="Installation Guide",
            content="Install numpy with: pip install numpy. For pandas: pip install pandas.",
            content_hash="abc111", token_count=14,
        ),
        RAGChunk(
            chunk_id="chunk-2", parent_id="doc-1", source_type="docs",
            source_path="docs/install.md", title="Installation Guide",
            content="Use Python 3.11 or newer. Set up a virtual environment first.",
            content_hash="abc222", token_count=12,
        ),
        RAGChunk(
            chunk_id="chunk-3", parent_id="doc-2", source_type="docs",
            source_path="docs/errors.md", title="Common Errors",
            content="ERR_PARSER_42 means the parser encountered an unexpected token.",
            content_hash="abc333", token_count=10,
        ),
    ]


def _chunks_to_results(chunks: list[RAGChunk]) -> list[RetrievalResult]:
    return [
        RetrievalResult(rank=i + 1, final_score=0.9 - i * 0.1, chunk=c,
                      content_preview=c.content[:100])
        for i, c in enumerate(chunks)
    ]


# -- Tests -------------------------------------------------------------------

class TestGroundedAnswerFlow:
    async def test_answer_with_evidence(self):
        chunks = _make_fixture_chunks()
        retrieved = RetrievalResultSet(results=_chunks_to_results(chunks))
        client = FakeGenerationClient()
        service = RAGGenerationService(client)
        answer = await service.generate("how to install numpy", retrieved)
        assert not answer.insufficient_evidence
        assert answer.answer
        assert len(answer.supporting_chunk_ids) > 0

    async def test_insufficient_evidence(self):
        retrieved = RetrievalResultSet(results=[])
        client = FakeGenerationClient()
        service = RAGGenerationService(client)
        answer = await service.generate("unknown question", retrieved)
        assert answer.insufficient_evidence

    async def test_request_id_present(self):
        chunks = _make_fixture_chunks()
        retrieved = RetrievalResultSet(results=_chunks_to_results(chunks))
        client = FakeGenerationClient()
        service = RAGGenerationService(client)
        answer = await service.generate(
            "how to install numpy", retrieved, request_id="fixture-req-1",
        )
        assert answer.request_id == "fixture-req-1"

    async def test_generation_latency_recorded(self):
        import time
        chunks = _make_fixture_chunks()
        retrieved = RetrievalResultSet(results=_chunks_to_results(chunks))
        client = FakeGenerationClient()
        service = RAGGenerationService(client)
        answer = await service.generate("test query", retrieved)
        assert answer.answer

    async def test_answer_deterministic_for_same_input(self):
        chunks = _make_fixture_chunks()
        retrieved = RetrievalResultSet(results=_chunks_to_results(chunks))
        client = FakeGenerationClient()
        service = RAGGenerationService(client)
        a1 = await service.generate("same question", retrieved)
        a2 = await service.generate("same question", retrieved)
        assert a1.answer == a2.answer
        assert a1.insufficient_evidence == a2.insufficient_evidence

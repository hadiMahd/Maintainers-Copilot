"""Unit tests for grounded-generation service shaping and redacted prompt handling."""

from __future__ import annotations

import pytest

from app.domain.rag import (
    RAGChunk,
    RetrievalResult,
    RetrievalResultSet,
)
from app.infra.rag_generation_client import FakeGenerationClient
from app.services.rag_generation_service import RAGGenerationService


@pytest.fixture
def client() -> FakeGenerationClient:
    return FakeGenerationClient()


@pytest.fixture
def service(client) -> RAGGenerationService:
    return RAGGenerationService(client)


def _make_result_set() -> RetrievalResultSet:
    chunk = RAGChunk(
        chunk_id="c1",
        parent_id="p1",
        source_type="docs",
        content="pip install numpy installs the numpy package",
        content_hash="abc",
        token_count=8,
    )
    return RetrievalResultSet(
        results=[
            RetrievalResult(
                rank=1, final_score=0.95, chunk=chunk, content_preview="pip install numpy..."
            ),
        ],
    )


class TestGroundedAnswerShaping:
    async def test_generate_returns_answer_with_chunks(self, service):
        result_set = _make_result_set()
        answer = await service.generate("how to install numpy", result_set)
        assert answer.answer
        assert not answer.insufficient_evidence
        assert len(answer.supporting_chunk_ids) > 0

    async def test_generate_insufficient_evidence_without_chunks(self, service):
        result_set = RetrievalResultSet(results=[])
        answer = await service.generate("how to install numpy", result_set)
        assert answer.insufficient_evidence
        assert len(answer.supporting_chunk_ids) == 0

    async def test_generate_sets_request_id(self, service):
        result_set = _make_result_set()
        answer = await service.generate(
            "question",
            result_set,
            request_id="req-test-1",
        )
        assert answer.request_id == "req-test-1"


class TestRedactedPromptHandling:
    async def test_service_logs_safely(self, service):
        from app.infra.redaction import redact_rag_prompt

        payload = {
            "question": "test question",
            "content": "secret chunk content with sk-abcdefghijklmnopqrstuvwxyzxtoken",
        }
        redacted = redact_rag_prompt(payload)
        assert "content" not in redacted
        assert "content_len" in redacted
        assert "sk-" not in str(redacted)

    async def test_service_preserves_safe_metadata(self, service):
        from app.infra.redaction import redact_rag_prompt

        payload = {
            "chunk_id": "c1",
            "top_k": 5,
            "insufficient_evidence": False,
            "content": "large text content to be stripped",
        }
        redacted = redact_rag_prompt(payload)
        assert redacted["chunk_id"] == "c1"
        assert redacted["top_k"] == 5
        assert "content" not in redacted
        assert redacted["content_len"] == len(payload["content"])

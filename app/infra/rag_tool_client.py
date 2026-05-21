"""Project-owned RAG tool client seam."""

from __future__ import annotations

from app.domain.chat_tools import AnswerProjectQuestionInput, RAGToolClientResponse


class BaseRAGToolClient:
    """Abstract RAG tool seam used by chat orchestration."""

    async def answer_project_question(
        self,
        payload: AnswerProjectQuestionInput,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> RAGToolClientResponse:
        raise NotImplementedError


class FakeRAGToolClient(BaseRAGToolClient):
    """Deterministic RAG tool fake for tests."""

    def __init__(self, result: RAGToolClientResponse | None = None) -> None:
        self._result = result or RAGToolClientResponse(
            answer="Grounded answer from fake retrieval.",
            supporting_sources=[],
            limitations=[],
            retrieval_trace_id="rag-trace-001",
            retrieved_chunks=[],
        )

    async def answer_project_question(
        self,
        payload: AnswerProjectQuestionInput,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> RAGToolClientResponse:
        _ = (payload, request_id, trace_id)
        return self._result

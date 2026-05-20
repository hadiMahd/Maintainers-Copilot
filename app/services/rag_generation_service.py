"""RAG generation service — grounded answer generation from retrieved evidence."""

from __future__ import annotations

import logging
import uuid

from app.domain.rag import (
    GroundedAnswer,
    RAGGenerationError,
    RetrievalQuery,
    RetrievalResultSet,
)
from app.infra.rag_generation_client import BaseGenerationClient
from app.infra.redaction import redact_rag_prompt

logger = logging.getLogger(__name__)


class RAGGenerationService:
    def __init__(self, client: BaseGenerationClient) -> None:
        self._client = client

    async def generate(
        self,
        question: str,
        retrieved: RetrievalResultSet,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> GroundedAnswer:
        rid = request_id or uuid.uuid4().hex
        tid = trace_id or uuid.uuid4().hex
        try:
            answer = await self._client.generate(
                question=question,
                retrieved=retrieved.results,
            )
            answer.request_id = rid
            _log_safe(rid, tid, answer)
            return answer
        except RAGGenerationError:
            raise
        except Exception as exc:
            logger.warning("Generation failed", extra={"request_id": rid, "trace_id": tid})
            raise RAGGenerationError(f"Generation failed: {exc}") from exc


def _log_safe(request_id: str, trace_id: str, answer: GroundedAnswer) -> None:
    logger.info(
        "Grounded answer generated",
        extra={
            "request_id": request_id,
            "trace_id": trace_id,
            "insufficient_evidence": answer.insufficient_evidence,
            "chunks_cited": len(answer.supporting_chunk_ids),
            "answer_len": len(answer.answer),
        },
    )


__all__ = ["RAGGenerationService"]

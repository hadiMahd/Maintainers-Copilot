"""Reranker client — cross-encoder config seam and fake adapter.

Real cross-encoder calls are synchronous CPU work. When wired into async
paths (US4+), wrap with ``asyncio.to_thread(reranker.rank, pairs)``.

This pass (US1) provides only the config seam and fake adapter.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from app.domain.rag import RetrievalResult

logger = logging.getLogger(__name__)

# Default: lightweight cross-encoder for local development.
# Documented in DECISIONS.md — configurable via RAGSettings.reranker_model_name.
_DEFAULT_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class BaseRerankerClient(ABC):
    """Abstract reranker for top-k candidate reordering."""

    @property
    @abstractmethod
    def model_name(self) -> str: ...

    @abstractmethod
    def rerank(
        self,
        query: str,
        candidates: list[RetrievalResult],
        top_k: int,
    ) -> list[RetrievalResult]: ...


class FakeRerankerClient(BaseRerankerClient):
    """Fake reranker — returns candidates unchanged (identity pass)."""

    def __init__(self, model_name: str = "fake-reranker") -> None:
        self._model_name = model_name

    @property
    def model_name(self) -> str:
        return self._model_name

    def rerank(
        self,
        query: str,
        candidates: list[RetrievalResult],
        top_k: int,
    ) -> list[RetrievalResult]:
        for idx, r in enumerate(candidates[:top_k], start=1):
            r.rank = idx
            r.rerank_score = r.final_score
        return candidates[:top_k]


class CrossEncoderRerankerStub(BaseRerankerClient):
    """Cross-encoder reranker config seam.

    Actual model calls are wired in US4. This stub holds the model name
    and raises NotImplementedError if called directly.
    """

    def __init__(self, model_name: str = _DEFAULT_RERANKER_MODEL) -> None:
        self._model_name = model_name

    @property
    def model_name(self) -> str:
        return self._model_name

    def rerank(
        self,
        query: str,
        candidates: list[RetrievalResult],
        top_k: int,
    ) -> list[RetrievalResult]:
        raise NotImplementedError("CrossEncoder reranker calls are not implemented in this pass")


def resolve_reranker(settings) -> BaseRerankerClient:
    return FakeRerankerClient()


__all__ = [
    "BaseRerankerClient",
    "FakeRerankerClient",
    "CrossEncoderRerankerStub",
    "resolve_reranker",
    "_DEFAULT_RERANKER_MODEL",
]

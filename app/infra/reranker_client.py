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


class CrossEncoderReranker(BaseRerankerClient):
    """Cross-encoder reranker using ``sentence_transformers.CrossEncoder``.

    .. note::

        ``CrossEncoder.predict()`` is synchronous CPU work.
        When this reranker is wired into an async request path,
        wrap the call with ``asyncio.to_thread(reranker.rerank, ...)``
        to avoid blocking the event loop.

        Example::

            ranked = await asyncio.to_thread(reranker.rerank, query, candidates, top_k)
    """

    def __init__(self, model_name: str = _DEFAULT_RERANKER_MODEL) -> None:
        self._model_name = model_name
        self._encoder: object | None = None

    @property
    def model_name(self) -> str:
        return self._model_name

    def _ensure_encoder(self) -> None:
        if self._encoder is not None:
            return
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:
            raise RuntimeError(
                "CrossEncoder reranker requires the rag optional dependencies "
                "(install with: uv sync --extra rag)"
            ) from exc
        self._encoder = CrossEncoder(self._model_name)

    def rerank(
        self,
        query: str,
        candidates: list[RetrievalResult],
        top_k: int,
    ) -> list[RetrievalResult]:
        if not candidates:
            return []
        self._ensure_encoder()
        pairs = [(query, c.chunk.content[:500]) for c in candidates]
        scores = self._encoder.predict(pairs).tolist()
        for r, s in zip(candidates, scores):
            r.rerank_score = float(s)
        ranked = sorted(candidates, key=lambda r: r.rerank_score or 0.0, reverse=True)
        for idx, r in enumerate(ranked[:top_k], start=1):
            r.rank = idx
        return ranked[:top_k]


def resolve_reranker(settings, *, force_fake: bool = False) -> BaseRerankerClient:
    if force_fake or getattr(settings, "environment", "") == "test":
        return FakeRerankerClient()
    try:
        return CrossEncoderReranker(model_name=settings.rag_reranker_model_name)
    except Exception as exc:
        logger.warning("CrossEncoderReranker unavailable, falling back to fake: %s", exc)
        return FakeRerankerClient()


__all__ = [
    "BaseRerankerClient",
    "FakeRerankerClient",
    "CrossEncoderReranker",
    "resolve_reranker",
    "_DEFAULT_RERANKER_MODEL",
]

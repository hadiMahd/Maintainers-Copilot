"""Embedding client — local sentence-transformers and Azure OpenAI embedding seams.

.. note::

    ``SentenceTransformer.encode()`` and ``CrossEncoder.predict()`` are
    synchronous CPU work.  When this client is wired into an async request
    path, wrap the call with ``asyncio.to_thread(encode, texts)`` to avoid
    blocking the event loop.

    Example::

        embeddings = await asyncio.to_thread(encoder.encode, texts)
"""

from __future__ import annotations

import hashlib
import logging
from abc import ABC, abstractmethod

from app.core.config import AppSettings

logger = logging.getLogger(__name__)

_DEFAULT_DIM = 384


class BaseEmbeddingClient(ABC):
    """Abstract embedding client for local and Azure embedding models."""

    @property
    @abstractmethod
    def model_name(self) -> str: ...

    @property
    @abstractmethod
    def dim(self) -> int: ...

    @abstractmethod
    def encode(self, texts: list[str]) -> list[list[float]]: ...


class LocalEmbeddingClient(BaseEmbeddingClient):
    """Local ``all-MiniLM-L6-v2`` embedding client (CPU-safe).

    Wraps ``sentence_transformers.SentenceTransformer``.
    Call ``encode()`` via ``asyncio.to_thread`` in async paths.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model_name = model_name
        self._dim = _DEFAULT_DIM
        self._encoder: object | None = None

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dim(self) -> int:
        return self._dim

    def _ensure_encoder(self) -> None:
        if self._encoder is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "Local embedding requires the rag optional dependencies "
                "(install with: uv sync --extra rag)"
            ) from exc
        self._encoder = SentenceTransformer(self._model_name)
        self._dim = self._encoder.get_sentence_embedding_dimension()

    def encode(self, texts: list[str]) -> list[list[float]]:
        self._ensure_encoder()
        embeddings = self._encoder.encode(texts, normalize_embeddings=True)
        return [emb.tolist() for emb in embeddings]


class FakeEmbeddingClient(BaseEmbeddingClient):
    """Deterministic fake embedding client for tests.

    Produces fixed-dimension embeddings derived from a text hash so that
    the same text always maps to the same vector.
    """

    def __init__(self, model_name: str = "fake-embedding", dim: int = _DEFAULT_DIM) -> None:
        self._model_name = model_name
        self._dim = dim

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dim(self) -> int:
        return self._dim

    def encode(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float]] = []
        for text in texts:
            seed = int(hashlib.sha256(text.encode()).hexdigest(), 16)
            vec = [_fake_component(seed, i) for i in range(self._dim)]
            norm = sum(v * v for v in vec) ** 0.5
            if norm > 0:
                vec = [v / norm for v in vec]
            results.append(vec)
        return results


def _fake_component(seed: int, idx: int) -> float:
    return ((seed * (idx + 1) * 2654435761) & 0xFFFFFFFF) / 0xFFFFFFFF * 2.0 - 1.0


class AzureEmbeddingStub(BaseEmbeddingClient):
    """Azure OpenAI text-embedding-3-small stub.

    Config seam only — wired when ``rag_azure_embedding_endpoint`` is set.
    Actual Azure calls are out of scope for the US1 pass.
    """

    def __init__(self, model_name: str = "text-embedding-3-small", dim: int = 1536) -> None:
        self._model_name = model_name
        self._dim = dim

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dim(self) -> int:
        return self._dim

    def encode(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("Azure embedding calls are not implemented in this pass")


def resolve_embedding_client(settings: AppSettings) -> BaseEmbeddingClient:
    """Return the embedding client based on runtime settings.

    Uses local ``all-MiniLM-L6-v2`` when Azure credentials are absent.
    """
    if settings.rag_azure_embedding_endpoint and settings.rag_azure_embedding_api_key:
        return AzureEmbeddingStub()
    return LocalEmbeddingClient(model_name=settings.rag_embedding_model)


__all__ = [
    "BaseEmbeddingClient",
    "LocalEmbeddingClient",
    "FakeEmbeddingClient",
    "AzureEmbeddingStub",
    "resolve_embedding_client",
]

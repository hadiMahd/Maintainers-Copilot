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
import os
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


class AzureEmbeddingClient(BaseEmbeddingClient):
    """Azure OpenAI embedding client for RAG query/corpus embeddings."""

    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str,
        model_name: str = "text-embedding-3-small",
        api_version: str = "2024-02-01",
        dim: int = 1536,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._api_key = api_key
        self._model_name = model_name
        self._api_version = api_version
        self._dim = dim

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dim(self) -> int:
        return self._dim

    def encode(self, texts: list[str]) -> list[list[float]]:
        try:
            import httpx
        except ImportError as exc:
            raise RuntimeError("Azure embeddings require httpx") from exc

        url = (
            f"{self._endpoint}/openai/deployments/{self._model_name}/embeddings"
            f"?api-version={self._api_version}"
        )
        headers = {"api-key": self._api_key, "Content-Type": "application/json"}
        vectors: list[list[float]] = []
        with httpx.Client(timeout=30.0) as client:
            for text in texts:
                response = client.post(url, json={"input": text}, headers=headers)
                response.raise_for_status()
                data = response.json()
                embedding = data["data"][0]["embedding"]
                self._dim = len(embedding)
                vectors.append([float(value) for value in embedding])
        return vectors


def resolve_embedding_client(settings: AppSettings) -> BaseEmbeddingClient:
    """Return the embedding client based on runtime settings.

    Uses local ``all-MiniLM-L6-v2`` when Azure credentials are absent.
    """
    if settings.rag_azure_embedding_endpoint and settings.rag_azure_embedding_api_key:
        return AzureEmbeddingClient(
            endpoint=settings.rag_azure_embedding_endpoint,
            api_key=settings.rag_azure_embedding_api_key,
            model_name=(
                settings.azure_openai_embedding_model
                or os.environ.get("AZURE_EMBEDDING_MODEL")
                or "text-embedding-3-small"
            ),
        )
    return LocalEmbeddingClient(model_name=settings.rag_embedding_model)


__all__ = [
    "BaseEmbeddingClient",
    "LocalEmbeddingClient",
    "FakeEmbeddingClient",
    "AzureEmbeddingClient",
    "resolve_embedding_client",
]

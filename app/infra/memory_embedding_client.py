"""Semantic memory embedding adapter.

Provides a deterministic local embedding client and a real Azure OpenAI
embedding client. The Azure path is used automatically when credentials are
available; otherwise the deterministic client ensures the service is always
operable.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os

logger = logging.getLogger(__name__)

_AZURE_API_VERSION = "2024-02-01"
DEFAULT_MEMORY_EMBEDDING_DIM = 1536


class MemoryEmbeddingClient:
    """Deterministic embedding adapter for semantic memory writes.

    Produces hash-derived vectors that are consistent for the same text.
    Used as the default when no Azure credentials are configured.
    """

    def __init__(self, vector_size: int = DEFAULT_MEMORY_EMBEDDING_DIM) -> None:
        self._vector_size = vector_size

    def _embed_sync(self, text: str) -> list[float]:
        seed = hashlib.sha256(text.encode()).digest()
        vector: list[float] = []
        state = seed
        while len(vector) < self._vector_size:
            state = hashlib.sha256(state).digest()
            for byte in state:
                vector.append((byte / 255.0) * 2.0 - 1.0)
                if len(vector) == self._vector_size:
                    break
        return vector

    async def embed(self, text: str) -> list[float]:
        return await asyncio.to_thread(self._embed_sync, text)


class AzureMemoryEmbeddingClient:
    """Azure OpenAI text-embedding-3-small client for semantic memory.

    Uses httpx to call the Azure OpenAI embeddings endpoint directly.
    Falls back to deterministic embeddings if Azure is unavailable.
    """

    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str,
        deployment_name: str = "text-embedding-3-small",
        api_version: str = _AZURE_API_VERSION,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._api_key = api_key
        self._deployment_name = deployment_name
        self._api_version = api_version
        self._dim: int = DEFAULT_MEMORY_EMBEDDING_DIM
        self._configured = True

    @property
    def vector_size(self) -> int:
        return self._dim

    async def embed(self, text: str) -> list[float]:
        try:
            import httpx
        except ImportError:
            logger.warning("httpx not available for Azure embeddings, using fallback")
            fallback = MemoryEmbeddingClient()
            return await fallback.embed(text)

        url = (
            f"{self._endpoint}/openai/deployments/"
            f"{self._deployment_name}/embeddings"
            f"?api-version={self._api_version}"
        )
        headers = {
            "api-key": self._api_key,
            "Content-Type": "application/json",
        }
        body = {"input": text, "model": self._deployment_name}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=body, headers=headers)
                response.raise_for_status()
                data = response.json()
                embedding = data["data"][0]["embedding"]
                return embedding
        except Exception as exc:
            logger.warning(
                "Azure embedding failed, falling back to deterministic: %s", exc
            )
            fallback = MemoryEmbeddingClient()
            return await fallback.embed(text)


def resolve_memory_embedding_client() -> MemoryEmbeddingClient | AzureMemoryEmbeddingClient:
    """Return the best available embedding client for memory operations."""
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT") or os.environ.get(
        "RAG_AZURE_EMBEDDING_ENDPOINT"
    )
    api_key = os.environ.get("AZURE_OPENAI_API_KEY") or os.environ.get(
        "RAG_AZURE_EMBEDDING_API_KEY"
    )
    if endpoint and api_key:
        model = os.environ.get("AZURE_EMBEDDING_MODEL", "text-embedding-3-small")
        logger.info(
            "Using Azure embeddings for semantic memory: model=%s", model,
        )
        return AzureMemoryEmbeddingClient(
            endpoint=endpoint,
            api_key=api_key,
            deployment_name=model,
        )
    logger.info("Using deterministic embeddings for semantic memory (no Azure creds)")
    return MemoryEmbeddingClient()

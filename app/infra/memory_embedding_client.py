"""Semantic memory embedding adapter.

Implements a deterministic local embedding client and offloads the
blocking vector generation path via ``asyncio.to_thread``.
"""

from __future__ import annotations

import asyncio
import hashlib


class MemoryEmbeddingClient:
    """Deterministic embedding adapter for semantic memory writes."""

    def __init__(self, vector_size: int = 384) -> None:
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

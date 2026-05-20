"""Semantic memory embedding adapter.

Stub for Phase 6 US4.  When implemented, embedding generation MUST use
``asyncio.to_thread`` or an async-safe provider so that write-memory
request paths do not block the event loop.
"""


class MemoryEmbeddingClient:
    """Stub for US4.  Do not use before US4 implementation."""

    async def embed(self, *args, **kwargs):
        raise NotImplementedError(
            "MemoryEmbeddingClient: US4 not implemented yet"
        )

"""Regression checks for semantic memory embedding dimensionality."""

from __future__ import annotations


async def test_default_memory_embedding_client_matches_long_term_memory_schema():
    from app.infra.memory_embedding_client import (
        DEFAULT_MEMORY_EMBEDDING_DIM,
        MemoryEmbeddingClient,
    )
    from app.infra.orm_models import LongTermMemory

    client = MemoryEmbeddingClient()
    vector = await client.embed("remember this preference")

    assert len(vector) == DEFAULT_MEMORY_EMBEDDING_DIM
    assert LongTermMemory.__table__.c.embedding.type.dim == DEFAULT_MEMORY_EMBEDDING_DIM


def test_azure_memory_embedding_client_reports_schema_dimension():
    from app.infra.memory_embedding_client import (
        DEFAULT_MEMORY_EMBEDDING_DIM,
        AzureMemoryEmbeddingClient,
    )

    client = AzureMemoryEmbeddingClient(
        endpoint="https://example.openai.azure.com",
        api_key="test-key",
    )

    assert client.vector_size == DEFAULT_MEMORY_EMBEDDING_DIM

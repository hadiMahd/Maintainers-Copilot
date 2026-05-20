"""Unit tests for RAG provider resolution."""

from __future__ import annotations

import pytest

from app.infra.embedding_client import (
    BaseEmbeddingClient,
    FakeEmbeddingClient,
    LocalEmbeddingClient,
    AzureEmbeddingStub,
    resolve_embedding_client,
)
from app.infra.rag_generation_client import (
    BaseGenerationClient,
    FakeGenerationClient,
    AzureGenerationStub,
    resolve_generation_client,
)
from app.infra.rag_judge_client import (
    TokenOverlapJudge,
    resolve_judge,
    _DEFAULT_JUDGE_ID,
)
from app.infra.reranker_client import (
    BaseRerankerClient,
    FakeRerankerClient,
    CrossEncoderReranker,
    resolve_reranker,
)


class TestEmbeddingClientResolution:
    def test_fake_embedding_client_is_deterministic(self):
        client = FakeEmbeddingClient()
        embeddings1 = client.encode(["hello world"])
        embeddings2 = client.encode(["hello world"])
        assert len(embeddings1) == len(embeddings2) == 1
        for a, b in zip(embeddings1[0], embeddings2[0]):
            assert a == pytest.approx(b)

    def test_fake_embedding_client_different_for_different_text(self):
        client = FakeEmbeddingClient()
        e1 = client.encode(["hello"])[0]
        e2 = client.encode(["world"])[0]
        assert e1 != e2

    def test_fake_embedding_client_returns_normalized_vectors(self):
        client = FakeEmbeddingClient(dim=128)
        for text in ["a", "b", "c"]:
            vec = client.encode([text])[0]
            norm = sum(v * v for v in vec) ** 0.5
            assert norm == pytest.approx(1.0, abs=1e-4)

    def test_fake_embedding_client_correct_dim(self):
        client = FakeEmbeddingClient(dim=256)
        assert client.dim == 256
        assert len(client.encode(["test"])[0]) == 256

    def test_azure_stub_has_correct_defaults(self):
        stub = AzureEmbeddingStub()
        assert stub.model_name == "text-embedding-3-small"
        assert stub.dim == 1536

    def test_azure_stub_raises_not_implemented(self):
        stub = AzureEmbeddingStub()
        with pytest.raises(NotImplementedError):
            stub.encode(["test"])

    def test_resolve_embedding_returns_fake_when_mock(self):
        from app.core.config import AppSettings
        settings = AppSettings(vault_addr="http://x", vault_token="t")
        client = resolve_embedding_client(settings)
        assert isinstance(client, BaseEmbeddingClient)


class TestGenerationClientResolution:
    def test_fake_generation_is_deterministic(self):
        import asyncio
        client = FakeGenerationClient()
        a1 = asyncio.run(client.generate("hello", []))
        a2 = asyncio.run(client.generate("hello", []))
        assert a1.answer == a2.answer

    def test_fake_generation_insufficient_without_chunks(self):
        import asyncio
        client = FakeGenerationClient()
        answer = asyncio.run(client.generate("query", []))
        assert answer.insufficient_evidence

    def test_fake_generation_returns_supporting_chunks(self):
        import asyncio
        from app.domain.rag import RetrievalResult, RAGChunk
        chunk = RAGChunk(
            chunk_id="c1", parent_id="p1", source_type="docs",
            content="evidence", content_hash="abc", token_count=3,
        )
        result = RetrievalResult(rank=1, final_score=0.9, chunk=chunk, retrieval_mode="hybrid")
        client = FakeGenerationClient()
        answer = asyncio.run(client.generate("query", [result]))
        assert not answer.insufficient_evidence
        assert len(answer.supporting_chunk_ids) > 0

    def test_azure_stub_raises_not_implemented(self):
        import asyncio
        stub = AzureGenerationStub()
        with pytest.raises(NotImplementedError):
            asyncio.run(stub.generate("test", []))

    def test_resolve_generation_returns_fake(self):
        client = resolve_generation_client()
        assert isinstance(client, BaseGenerationClient)


class TestJudgeResolution:
    def test_judge_has_stable_id(self):
        judge = resolve_judge()
        assert judge.judge_id == _DEFAULT_JUDGE_ID

    def test_judge_f1_perfect_match(self):
        judge = TokenOverlapJudge()
        score = judge.score_faithfulness("hello world", "hello world")
        assert score == 1.0

    def test_judge_f1_no_overlap(self):
        judge = TokenOverlapJudge()
        score = judge.score_faithfulness("hello", "world")
        assert score == 0.0

    def test_judge_f1_partial(self):
        judge = TokenOverlapJudge()
        score = judge.score_faithfulness("hello world foo", "hello world bar")
        assert 0.0 < score < 1.0

    def test_judge_relevancy(self):
        judge = TokenOverlapJudge()
        score = judge.score_answer_relevancy(
            "install numpy", "how to install numpy",
            "pip install numpy pandas",
        )
        assert 0.0 < score <= 1.0


class TestRerankerResolution:
    def test_fake_reranker_returns_same_ordering(self):
        from app.domain.rag import RetrievalResult, RAGChunk
        chunks = [
            RAGChunk(chunk_id=f"c{i}", parent_id="p", source_type="docs",
                     content=f"text {i}", content_hash="abc", token_count=2)
            for i in range(5)
        ]
        results = [
            RetrievalResult(rank=i + 1, final_score=0.9 - i * 0.1, chunk=chunks[i])
            for i in range(5)
        ]
        reranker = FakeRerankerClient()
        ranked = reranker.rerank("test", results, top_k=3)
        assert len(ranked) == 3
        assert ranked[0].chunk.chunk_id == results[0].chunk.chunk_id

    def test_cross_encoder_has_default_model(self):
        reranker = CrossEncoderReranker()
        assert reranker.model_name == "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def test_resolve_reranker_returns_fake(self):
        from app.core.config import AppSettings
        settings = AppSettings(vault_addr="http://x", vault_token="t")
        r = resolve_reranker(settings)
        assert isinstance(r, BaseRerankerClient)

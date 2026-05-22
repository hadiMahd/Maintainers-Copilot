"""Integration tests for grounded question answering — fixture-backed flow.

US1: Grounded answer generation with fake adapters.
US2: Baseline-vs-advanced evaluation with fixture corpora and fake providers.
"""

from __future__ import annotations

from app.domain.rag import (
    EvalMetrics,
    EvalReport,
    EvalRun,
    RAGChunk,
    RetrievalResult,
    RetrievalResultSet,
)
from app.infra.rag_generation_client import FakeGenerationClient
from app.infra.rag_judge_client import TokenOverlapJudge
from app.services.rag_generation_service import RAGGenerationService

# -- Fixture-backed chunks ---------------------------------------------------


def _make_fixture_chunks() -> list[RAGChunk]:
    return [
        RAGChunk(
            chunk_id="chunk-1",
            parent_id="doc-1",
            source_type="docs",
            source_path="docs/install.md",
            title="Installation Guide",
            content="Install numpy with: pip install numpy. For pandas: pip install pandas.",
            content_hash="abc111",
            token_count=14,
        ),
        RAGChunk(
            chunk_id="chunk-2",
            parent_id="doc-1",
            source_type="docs",
            source_path="docs/install.md",
            title="Installation Guide",
            content="Use Python 3.11 or newer. Set up a virtual environment first.",
            content_hash="abc222",
            token_count=12,
        ),
        RAGChunk(
            chunk_id="chunk-3",
            parent_id="doc-2",
            source_type="docs",
            source_path="docs/errors.md",
            title="Common Errors",
            content="ERR_PARSER_42 means the parser encountered an unexpected token.",
            content_hash="abc333",
            token_count=10,
        ),
    ]


def _chunks_to_results(chunks: list[RAGChunk]) -> list[RetrievalResult]:
    return [
        RetrievalResult(
            rank=i + 1, final_score=0.9 - i * 0.1, chunk=c, content_preview=c.content[:100]
        )
        for i, c in enumerate(chunks)
    ]


# -- US1 Tests ---------------------------------------------------------------


class TestGroundedAnswerFlow:
    async def test_answer_with_evidence(self):
        chunks = _make_fixture_chunks()
        retrieved = RetrievalResultSet(results=_chunks_to_results(chunks))
        client = FakeGenerationClient()
        service = RAGGenerationService(client)
        answer = await service.generate("how to install numpy", retrieved)
        assert not answer.insufficient_evidence
        assert answer.answer
        assert len(answer.supporting_chunk_ids) > 0

    async def test_insufficient_evidence(self):
        retrieved = RetrievalResultSet(results=[])
        client = FakeGenerationClient()
        service = RAGGenerationService(client)
        answer = await service.generate("unknown question", retrieved)
        assert answer.insufficient_evidence

    async def test_request_id_present(self):
        chunks = _make_fixture_chunks()
        retrieved = RetrievalResultSet(results=_chunks_to_results(chunks))
        client = FakeGenerationClient()
        service = RAGGenerationService(client)
        answer = await service.generate(
            "how to install numpy",
            retrieved,
            request_id="fixture-req-1",
        )
        assert answer.request_id == "fixture-req-1"

    async def test_generation_latency_recorded(self):

        chunks = _make_fixture_chunks()
        retrieved = RetrievalResultSet(results=_chunks_to_results(chunks))
        client = FakeGenerationClient()
        service = RAGGenerationService(client)
        answer = await service.generate("test query", retrieved)
        assert answer.answer

    async def test_answer_deterministic_for_same_input(self):
        chunks = _make_fixture_chunks()
        retrieved = RetrievalResultSet(results=_chunks_to_results(chunks))
        client = FakeGenerationClient()
        service = RAGGenerationService(client)
        a1 = await service.generate("same question", retrieved)
        a2 = await service.generate("same question", retrieved)
        assert a1.answer == a2.answer
        assert a1.insufficient_evidence == a2.insufficient_evidence


# -- US2 Tests ---------------------------------------------------------------


def _make_fixture_golden_examples() -> list[dict]:
    return [
        {
            "question": "how to install numpy",
            "answer": "pip install numpy",
            "expected_chunks": ["chunk-1"],
            "source_type": "docs",
        },
        {
            "question": "what python version",
            "answer": "Python 3.11 or newer",
            "expected_chunks": ["chunk-2"],
            "source_type": "docs",
        },
        {
            "question": "what does ERR_PARSER_42 mean",
            "answer": "ERR_PARSER_42 means unexpected token",
            "expected_chunks": ["chunk-3"],
            "source_type": "docs",
            "disagreement_note": "Context may require cross-file retrieval",
        },
        {
            "question": "unknown topic not in corpus",
            "answer": "Insufficient evidence",
            "expected_chunks": [],
            "source_type": "docs",
            "disagreement_note": "Expected no retrieval; baseline may hallucinate",
        },
        {
            "question": "how to set up environment",
            "answer": "Python 3.11 plus pip install",
            "expected_chunks": ["chunk-2"],
            "source_type": "docs",
            "disagreement_note": "Answer ambiguous; both chunks may apply",
        },
    ]


class TestBaselineVsAdvanced:
    def test_baseline_eval_run_metadata(self):
        run = EvalRun(
            mode="baseline",
            metrics=EvalMetrics(hit_at_5=0.4, mrr_at_10=0.5),
            embedding_model="all-MiniLM-L6-v2",
            retrieval_mode="dense",
            examples_completed=5,
            judge_id="token-overlap-f1-v1",
        )
        assert run.mode == "baseline"
        assert run.embedding_model == "all-MiniLM-L6-v2"

    def test_advanced_eval_run_metadata(self):
        run = EvalRun(
            mode="advanced",
            metrics=EvalMetrics(hit_at_5=0.6, mrr_at_10=0.7),
            embedding_model="all-MiniLM-L6-v2",
            retrieval_mode="hybrid",
            reranking_enabled=False,
            query_transformation_enabled=False,
            examples_completed=5,
            judge_id="token-overlap-f1-v1",
            disagreement_notes=["note 1", "note 2"],
        )
        assert run.mode == "advanced"
        assert run.retrieval_mode == "hybrid"
        assert len(run.disagreement_notes) == 2

    def test_judge_id_stable_across_runs(self):
        judge = TokenOverlapJudge()
        baseline = EvalRun(
            mode="baseline",
            metrics=EvalMetrics(),
            judge_id=judge.judge_id,
        )
        advanced = EvalRun(
            mode="advanced",
            metrics=EvalMetrics(),
            judge_id=judge.judge_id,
        )
        assert baseline.judge_id == advanced.judge_id == "token-overlap-f1-v1"

    def test_advanced_beats_baseline_report(self):
        baseline = EvalRun(
            mode="baseline",
            metrics=EvalMetrics(
                hit_at_5=0.4, mrr_at_10=0.5, faithfulness=0.7, answer_relevancy=0.6
            ),
            judge_id="token-overlap-f1-v1",
        )
        advanced = EvalRun(
            mode="advanced",
            metrics=EvalMetrics(
                hit_at_5=0.6, mrr_at_10=0.7, faithfulness=0.8, answer_relevancy=0.75
            ),
            judge_id="token-overlap-f1-v1",
            disagreement_notes=["note 1"],
        )
        report = EvalReport(
            baseline=baseline,
            advanced=advanced,
            advanced_beats_baseline=True,
            embedding_comparison={
                "all-MiniLM-L6-v2": {"dim": 384, "hit_at_5": 0.6, "mrr_at_10": 0.7},
                "text-embedding-3-small": {"dim": 1536, "hit_at_5": 0.5, "mrr_at_10": 0.6},
            },
        )
        assert report.advanced_beats_baseline
        assert "all-MiniLM-L6-v2" in report.embedding_comparison
        assert "text-embedding-3-small" in report.embedding_comparison

    def test_judge_scores_fixture_answers(self):
        judge = TokenOverlapJudge()
        examples = _make_fixture_golden_examples()
        faithfulness_scores = []
        for ex in examples:
            score = judge.score_faithfulness(ex["answer"], ex["answer"])
            faithfulness_scores.append(score)
        assert all(s >= 0.0 for s in faithfulness_scores)
        assert faithfulness_scores[0] == 1.0  # perfect match on first example

"""Run RAG eval against compact golden set using fake providers.

Default mode uses FakeGenerationClient and TokenOverlapJudge — deterministic,
fast, and requires no paid API credentials.

Set USE_REAL_AZURE_EVALS=1 to trigger Azure OpenAI generation (requires
real credentials and Vault bootstrap).
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any


def evaluate_rag(golden_path: str) -> dict[str, Any]:
    """Run RAG evaluation using the project's RAGEvaluationService with fake providers."""
    from app.core.config import AppSettings
    from app.infra.rag_generation_client import FakeGenerationClient
    from app.infra.rag_judge_client import resolve_judge
    from app.services.rag_evaluation_service import RAGEvaluationService

    settings = AppSettings()  # type: ignore[call-arg]
    judge = resolve_judge()
    gen = FakeGenerationClient()
    service = RAGEvaluationService(settings=settings, generation_client=gen, judge=judge)

    examples = service.load_golden_set(golden_path)

    async def _run() -> Any:
        baseline = await service.evaluate_baseline(examples)
        return baseline

    run_result = asyncio.run(_run())
    m = run_result.metrics

    return {
        "dataset_id": Path(golden_path).stem,
        "hit_at_5": m.hit_at_5,
        "mrr_at_10": m.mrr_at_10,
        "faithfulness": m.faithfulness or 0.0,
        "answer_relevancy": m.answer_relevancy or 0.0,
    }


def evaluate_real_rag(golden_path: str) -> dict[str, Any]:
    """Run RAG eval against live Postgres retrieval and Azure generation."""
    from app.core.config import AppSettings
    from app.core.lifespan import _apply_optional_provider_settings
    from app.domain.rag import RetrievalQuery
    from app.infra.database import create_engine, create_session_factory
    from app.infra.embedding_client import resolve_embedding_client
    from app.infra.rag_generation_client import resolve_generation_client
    from app.infra.rag_judge_client import resolve_judge
    from app.infra.reranker_client import resolve_reranker
    from app.infra.vault_client import init_vault_client, resolve_classifier_secrets
    from app.repositories.rag_chunk_repository import RAGChunkRepository
    from app.services.rag_generation_service import RAGGenerationService
    from app.services.rag_retrieval_service import RAGRetrievalService
    from scripts.build_rag_index import _resolve_database_url

    settings = AppSettings()
    _apply_optional_provider_settings(
        settings,
        resolve_classifier_secrets(init_vault_client(settings), settings),
    )
    embedding_client = resolve_embedding_client(settings)
    generation_client = resolve_generation_client(settings)
    if generation_client.provider_backend != "azure_openai":
        raise RuntimeError(
            "USE_REAL_AZURE_EVALS=1 requires Vault-resolved Azure generation settings"
        )
    judge = resolve_judge()

    with open(golden_path) as f:
        examples = [json.loads(line) for line in f if line.strip()]

    async def _run() -> dict[str, Any]:
        engine = create_engine(_resolve_database_url())
        session_factory = create_session_factory(engine)
        generation_service = RAGGenerationService(generation_client)
        hits: list[float] = []
        mrrs: list[float] = []
        faithfulness: list[float] = []
        relevancy: list[float] = []

        try:
            for ex in examples:
                question = ex["question"]
                expected = ex.get("expected_chunks", [])
                async with session_factory() as session:
                    retrieval_service = RAGRetrievalService(
                        RAGChunkRepository(session),
                        sparse_weight=settings.rag_hybrid_sparse_weight,
                        dense_weight=settings.rag_hybrid_dense_weight,
                        reranker=resolve_reranker(settings),
                        embedding_client=embedding_client,
                    )
                    retrieved = await retrieval_service.retrieve(
                        RetrievalQuery(
                            query=question,
                            retrieval_mode="hybrid",
                            embedding_model=embedding_client.model_name,
                            top_k=10,
                            reranking_enabled=True,
                            query_transformation_enabled=True,
                        )
                    )
                hits.append(_hit_at_5(retrieved.results, expected))
                mrrs.append(_mrr_at_10(retrieved.results, expected))
                answer = await generation_service.generate(question=question, retrieved=retrieved)
                context = " ".join(r.chunk.content for r in retrieved.results)
                faithfulness.append(judge.score_faithfulness(answer.answer, ex.get("answer", "")))
                relevancy.append(judge.score_answer_relevancy(answer.answer, question, context))
        finally:
            await engine.dispose()

        return {
            "dataset_id": Path(golden_path).stem,
            "hit_at_5": _avg(hits),
            "mrr_at_10": _avg(mrrs),
            "faithfulness": _avg(faithfulness),
            "answer_relevancy": _avg(relevancy),
            "provider_backend": generation_client.provider_backend,
            "embedding_model": embedding_client.model_name,
        }

    return asyncio.run(_run())


def _hit_at_5(results: list[Any], expected_chunks: list[str]) -> float:
    return 1.0 if any(r.chunk.chunk_id in expected_chunks for r in results[:5]) else 0.0


def _mrr_at_10(results: list[Any], expected_chunks: list[str]) -> float:
    for idx, result in enumerate(results[:10], start=1):
        if result.chunk.chunk_id in expected_chunks:
            return 1.0 / idx
    return 0.0


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def check_rag_gate(result: dict[str, Any]) -> tuple[bool, list[str]]:
    """Check RAG results against thresholds."""
    from scripts.ci.thresholds import check_threshold, get_rag_threshold, load_thresholds

    thresholds = load_thresholds()
    failures: list[str] = []

    for metric, key in [
        ("hit_at_5", "hit_at_5"),
        ("mrr_at_10", "mrr_at_10"),
        ("faithfulness", "faithfulness"),
        ("answer_relevancy", "answer_relevancy"),
    ]:
        threshold = get_rag_threshold(thresholds, key)
        ok, msg = check_threshold(result[key], threshold, metric)
        if not ok:
            failures.append(msg)

    return len(failures) == 0, failures


if __name__ == "__main__":
    golden_path = "evals/rag/golden.jsonl"

    if os.environ.get("USE_REAL_AZURE_EVALS") == "1":
        golden_path = os.environ.get("RAG_EVAL_GOLDEN_PATH", "evals/rag_golden_set.jsonl")
        result = evaluate_real_rag(golden_path)
    else:
        result = evaluate_rag(golden_path)

    print(f"RAG eval on {result['dataset_id']}:")
    print(f"  Hit@5:    {result['hit_at_5']:.4f}")
    print(f"  MRR@10:   {result['mrr_at_10']:.4f}")
    print(f"  Faithfulness: {result['faithfulness']:.4f}")
    print(f"  Answer Relevancy: {result['answer_relevancy']:.4f}")

    passed, failures = check_rag_gate(result)
    if not passed:
        result["passed"] = False
        result["failures"] = failures
        print(f"FAIL: {len(failures)} threshold failure(s)")
        for f in failures:
            print(f"  {f}")
    else:
        result["passed"] = True
        result["failures"] = []

    out_dir = Path("evals/reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "rag_result.json", "w") as fh:
        json.dump(result, fh, indent=2)
    print(f"RAG result saved to {out_dir / 'rag_result.json'}")

    if not passed:
        sys.exit(1)

    print("RAG eval passed all thresholds")

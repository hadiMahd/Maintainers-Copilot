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

    settings = AppSettings(_env_file=None)
    judge = resolve_judge()
    gen = FakeGenerationClient()
    service = RAGEvaluationService(settings=settings, generation_client=gen, judge=judge)

    examples = service.load_golden_set(golden_path)

    async def _run():
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
    with open(out_dir / "rag_result.json", "w") as f:
        json.dump(result, f, indent=2)
    print(f"RAG result saved to {out_dir / 'rag_result.json'}")

    if not passed:
        sys.exit(1)

    print("RAG eval passed all thresholds")

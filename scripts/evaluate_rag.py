"""RAG evaluation command.

Evaluates the naive baseline and advanced RAG pipeline on the same
25-example golden set using fixture-backed retrieval and fake generation.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys

from app.core.config import AppSettings
from app.domain.rag import EvalReport
from app.infra.rag_generation_client import FakeGenerationClient
from app.infra.rag_judge_client import resolve_judge
from app.infra.redaction import redact_eval_report
from app.services.rag_evaluation_service import RAGEvaluationService

logger = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate RAG pipeline")
    parser.add_argument(
        "--golden-set",
        default="evals/rag_golden_set.jsonl",
        help="Path to golden set JSONL (default: evals/rag_golden_set.jsonl)",
    )
    parser.add_argument(
        "--output",
        default="evals/rag_eval_report.json",
        help="Path to output report JSON (default: evals/rag_eval_report.json)",
    )
    parser.add_argument(
        "--exploratory",
        action="store_true",
        help="Bypass threshold gate (allow advanced to be worse than baseline)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    settings = AppSettings(_env_file=None)
    judge = resolve_judge()
    generation_client = FakeGenerationClient()
    service = RAGEvaluationService(
        settings=settings,
        generation_client=generation_client,
        judge=judge,
    )

    try:
        examples = service.load_golden_set(args.golden_set)
    except FileNotFoundError:
        logger.error("Golden set not found: %s", args.golden_set)
        return 1
    except ValueError as exc:
        logger.error("Golden set error: %s", exc)
        return 1

    async def _run() -> EvalReport:
        logger.info("Running baseline evaluation (%d examples)...", len(examples))
        baseline = await service.evaluate_baseline(examples)
        logger.info(
            "Baseline: hit@5=%.4f mrr@10=%.4f faith=%.4f relevancy=%.4f",
            baseline.metrics.hit_at_5,
            baseline.metrics.mrr_at_10,
            baseline.metrics.faithfulness or 0.0,
            baseline.metrics.answer_relevancy or 0.0,
        )

        logger.info("Running advanced evaluation (%d examples)...", len(examples))
        advanced = await service.evaluate_advanced(examples)
        logger.info(
            "Advanced: hit@5=%.4f mrr@10=%.4f faith=%.4f relevancy=%.4f",
            advanced.metrics.hit_at_5,
            advanced.metrics.mrr_at_10,
            advanced.metrics.faithfulness or 0.0,
            advanced.metrics.answer_relevancy or 0.0,
        )

        report = service.generate_report(baseline, advanced)
        logger.info(
            "Judge ID: %s | Embedding candidates: %s",
            service.judge_id,
            list(report.embedding_comparison.keys()),
        )
        return report

    report = asyncio.run(_run())

    try:
        service.apply_threshold_gate(report, exploratory=args.exploratory)
    except SystemExit:
        logger.info("Threshold gate: FAILED (run with --exploratory to bypass)")
        raise

    redacted = redact_eval_report(json.loads(json.dumps(report.model_dump(), default=str)))
    with open(args.output, "w") as f:
        json.dump(redacted, f, indent=2, default=str)

    logger.info("Report saved to %s", args.output)
    logger.info(
        "Advanced beats baseline: %s",
        report.advanced_beats_baseline,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

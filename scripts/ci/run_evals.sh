#!/usr/bin/env bash
set -euo pipefail
MODE="${1:-all}"

echo "=== Eval gate (mode: $MODE) ==="

run_classifier() {
    echo "--- Classifier eval ---"
    uv run python scripts/ci/run_classifier_eval.py
}

run_rag() {
    echo "--- RAG eval ---"
    uv run python scripts/ci/run_rag_eval.py
}

case "$MODE" in
    classifier)
        run_classifier
        ;;
    rag)
        run_rag
        ;;
    all)
        run_classifier
        run_rag
        ;;
    *)
        echo "Usage: run_evals.sh [classifier|rag|all]"
        exit 1
        ;;
esac

echo "Gate: eval PASSED"

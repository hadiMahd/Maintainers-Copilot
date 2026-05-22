#!/usr/bin/env bash
set -euo pipefail

FAILED=()
PASSED=()

run_gate() {
    local name="$1"
    local cmd="$2"
    echo ""
    echo "=== Gate: $name ==="
    if eval "$cmd"; then
        PASSED+=("$name")
        echo "PASS: $name"
    else
        FAILED+=("$name")
        echo "FAIL: $name (exit code $?)"
        return 1
    fi
}

echo "========================================="
echo "  Maintainer Copilot Validation Workflow "
echo "========================================="
echo ""

# Gate 1: Dependencies
echo "=== Gate: dependency-install ==="
uv sync --all-extras --dev
echo "PASS: dependency-install"

# Gate 2-6: Quality gates
run_gate "lint" "uv run flake8 ." || true
run_gate "format-check" "uv run black --check ." || true
run_gate "import-check" "uv run isort --check-only ." || true
run_gate "type-check" "scripts/ci/run_type_check.sh" || true
run_gate "tests" "uv run pytest" || true

# Gate 7: Threshold validation
run_gate "threshold-validation" "uv run python scripts/ci/check_eval_thresholds.py" || true

# Gate 8-9: Eval gates
run_gate "classifier-eval" "scripts/ci/run_evals.sh classifier" || true
run_gate "rag-eval" "scripts/ci/run_evals.sh rag" || true

# Gate 10-14: Security gates
run_gate "redaction-leak" "uv run python scripts/ci/check_redaction_leaks.py" || true
run_gate "static-secret-grep" "uv run python scripts/ci/check_static_secret_patterns.py" || true
run_gate "model-artifacts" "uv run python scripts/ci/check_model_artifacts.py" || true
run_gate "startup-failures" "uv run python scripts/ci/check_startup_failures.py" || true
run_gate "tracing-config" "uv run python scripts/ci/validate_tracing.py" || true

# Gate 15: Docker build
run_gate "docker-build" "docker compose build" || true

# Gate 16: Smoke
run_gate "stack-smoke" "scripts/ci/smoke_stack.sh" || true

# Gate 17-19: Report gates
run_gate "eval-report" "uv run python scripts/ci/build_eval_report.py" || true
run_gate "previous-green-diff" "uv run python scripts/ci/compare_previous_green_report.py" || true
run_gate "report-storage" "uv run python scripts/ci/store_eval_report.py" || true

# Gate 20: Docs
run_gate "docs-validation" "uv run python scripts/ci/validate_docs.py" || true

# Summary
echo ""
echo "========================================="
echo "  Validation Summary"
echo "========================================="
echo "Passed: ${#PASSED[@]}"
for g in "${PASSED[@]}"; do
    echo "  [PASS] $g"
done
echo "Failed: ${#FAILED[@]}"
for g in "${FAILED[@]}"; do
    echo "  [FAIL] $g"
done

if [ ${#FAILED[@]} -gt 0 ]; then
    echo "Validation FAILED: ${#FAILED[@]} gate(s) failed"
    exit 1
fi

echo "Validation PASSED: all ${#PASSED[@]} gates passed"

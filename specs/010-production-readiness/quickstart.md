# Quickstart: Production Readiness

## Prerequisites

- Python 3.11 or newer.
- uv installed.
- Docker and Docker Compose available for build and smoke-test gates.
- Local fake provider configuration available for tests and evals.
- Compact classifier and RAG golden sets committed under `evals/`.
- Required local model artifacts or test fixtures available for hash checks.

## Run Full Local Validation

```bash
make validate
```

Expected result: lint, format, type-check, tests, evals, redaction leak checks,
static secret grep checks, model artifact checks, startup failure checks,
tracing validation, Docker build, stack smoke test, eval report generation,
previous-green diffing, MinIO storage, and documentation validation all pass
without real paid API credentials.

## Run Individual Gates

```bash
uv sync --all-extras --dev
make lint
make format-check
make import-check
make type-check
make test
uv run python scripts/ci/check_eval_thresholds.py
scripts/ci/run_evals.sh classifier
scripts/ci/run_evals.sh rag
uv run python scripts/ci/check_redaction_leaks.py
uv run python scripts/ci/check_static_secret_patterns.py
uv run python scripts/ci/check_model_artifacts.py
uv run python scripts/ci/check_startup_failures.py
uv run python scripts/ci/validate_tracing.py
docker compose build
scripts/ci/smoke_stack.sh
uv run python scripts/ci/build_eval_report.py
uv run python scripts/ci/compare_previous_green_report.py
uv run python scripts/ci/store_eval_report.py
uv run python scripts/ci/validate_docs.py
```

Expected result: each command has a clear pass/fail signal and safe failure
summary.

## Verify Eval Gate Failures

Temporarily use test fixtures that set thresholds to zero or force below-
threshold metrics.

Expected result: threshold validation fails for zero thresholds, classifier eval
fails below classifier thresholds, RAG eval fails below RAG thresholds, and
disabled thresholds fail both workflow validation and startup validation.

## Verify Previous-Green Regression Failure

Run report comparison with a previous green fixture that has better metrics than
the current report beyond allowed tolerance.

Expected result: previous-green diffing fails with a safe metric comparison
summary and records regression metadata.

## Verify Redaction Leak Failure

Run the redaction leak gate with a test fixture that intentionally bypasses
redaction.

Expected result: the gate fails, reports the leak target, and does not reprint
the raw fake secret in failure output.

## Verify Static Secret Grep Failure

Run the static secret pattern gate with fixtures containing unsafe `sk-` and
`password` patterns.

Expected result: the gate fails, reports the path and pattern class, and does
not expose real secret values.

## Verify Startup Negative Cases

Run startup checks with Vault unreachable, required model artifacts missing,
model hash mismatch, tracing backend misconfigured, and eval thresholds zero or
disabled.

Expected result: app startup fails closed with structured, explainable errors in
all required negative cases.

## Verify Eval Report Storage

After a successful eval run, inspect:

```text
evals/reports/eval_report.json
artifacts/evals/
```

Expected result: the report matches `contracts/eval-report.schema.json` and is
stored in MinIO for CI. Local-compatible destinations are used only for dev/test
adapter runs.

## Verify Final Documentation

Review:

```text
README.md
docs/architecture.md
docs/decisions.md
docs/evals.md
docs/runbook.md
docs/security.md
```

Expected result: setup, architecture, commands, demo, decisions with numbers,
eval methodology, redaction patterns, secret policy, and common debugging paths
are documented.

## GitHub Actions

Push the branch or open a pull request.

Expected result: the CI workflow runs the same required gates using uv, flake8,
black, isort, mypy, pytest, compact eval fixtures, fake providers, Docker build
validation, and a full production-functional stack smoke test including the
model server where practical.

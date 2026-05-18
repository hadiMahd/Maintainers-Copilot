# Contract: Production Readiness Validation Workflow

## Workflow Provider

- Provider: GitHub Actions unless the repository already has a committed CI
  provider before implementation.
- Dependency installation: `uv`.
- Python quality checks: `ruff check` and `ruff format --check`.
- Python tests: `pytest`.
- Smoke testing: Docker Compose where practical.
- Provider calls: fake providers, local fixtures, or mocked calls only.

## Required Gate Order

| Order | Gate | Command Shape | Required Outcome |
|-------|------|---------------|------------------|
| 1 | Dependency install | `uv sync --all-extras --dev` | Dependencies install without real paid API credentials. |
| 2 | Lint | `uv run ruff check .` | No lint failures. |
| 3 | Format check | `uv run ruff format --check .` | No formatting drift. |
| 4 | Type check | `scripts/ci/run_type_check.sh` | Type-check passes. |
| 5 | Tests | `uv run pytest` | Test suite passes. |
| 6 | Threshold validation | `uv run python scripts/ci/check_eval_thresholds.py` | Thresholds exist, are enabled, and are greater than zero. |
| 7 | Classifier eval | `uv run python scripts/ci/run_evals.sh classifier` | Metrics meet thresholds. |
| 8 | RAG eval | `uv run python scripts/ci/run_evals.sh rag` | Metrics meet thresholds. |
| 9 | Redaction leak | `uv run python scripts/ci/check_redaction_leaks.py` | Fake secret is absent from logs, traces, memory, audit records, and captured outputs. |
| 10 | Static secret grep | `uv run python scripts/ci/check_static_secret_patterns.py` | Unsafe `sk-` and `password` patterns are absent or safely allowlisted. |
| 11 | Model artifacts | `uv run python scripts/ci/check_model_artifacts.py` | Required artifacts exist and hashes match model cards. |
| 12 | Startup failures | `uv run python scripts/ci/check_startup_failures.py` | Vault, model, tracing, and eval-threshold negative cases fail closed. |
| 13 | Tracing config | `uv run python scripts/ci/validate_tracing.py` | Tracing config is valid for the test profile. |
| 14 | Docker build | `docker compose build` | Core images build. |
| 15 | Stack smoke | `scripts/ci/smoke_stack.sh` | Core stack starts and health endpoint responds. |
| 16 | Eval report | `uv run python scripts/ci/build_eval_report.py` | Combined report is valid JSON. |
| 17 | Previous green diff | `uv run python scripts/ci/compare_previous_green_report.py` | Current report does not regress beyond configured tolerances. |
| 18 | Report storage | `uv run python scripts/ci/store_eval_report.py` | CI report is stored in MinIO. |
| 19 | Docs completeness | `uv run python scripts/ci/validate_docs.py` | Required docs and sections exist. |

## Failure Contract

- Any required gate failure fails the workflow.
- Required gates cannot be silently skipped.
- Failure output must include the gate ID and a safe summary.
- Failure output must not include raw fake secrets, provider keys, prompts,
  memory values, or sensitive payloads.
- Gates that intentionally test failure behavior must pass only when the
  expected failure occurs.

## Eval Threshold Contract

- Threshold file path: `evals/eval_thresholds.yaml`.
- All thresholds must be enabled, present, numeric, finite, and greater than
  zero.
- Classifier gate must compare accuracy and macro-F1 at minimum.
- RAG gate must compare hit@5 and MRR@10 at minimum.
- Faithfulness and answer relevancy are required when the RAG eval output
  contains those metrics.
- Below-threshold results fail the workflow and appear in `eval_report.json`.

## Previous Green Diff Contract

- Current `eval_report.json` must be compared with the previous green report
  from MinIO when one exists.
- The first successful CI run may record that no previous green report exists.
- Malformed or unavailable previous green reports fail the diff gate after at
  least one green report has been stored.
- Regressions beyond configured tolerances fail the workflow and are recorded in
  `eval_report.json`.

## Redaction Leak Contract

- Leak probes use fake secret-like values only.
- Targets checked include logs, traces, memory, audit records, and captured
  command output.
- Any raw probe value found in a target fails the workflow.
- Redacted replacement values may appear.

## Static Secret Grep Contract

- Static grep checks scan committed files and generated review artifacts for
  unsafe `sk-` and `password` patterns.
- Allowlisted false positives require a safe reason and must not expose real
  secrets.
- Failure output identifies path and pattern class without printing secret
  values.

## Startup Failure Contract

- Vault unreachable case must fail app startup.
- Missing required Vault value case must fail app startup.
- Missing required model artifact case must fail app or model-server startup.
- Model artifact hash mismatch must fail app or model-server startup.
- Tracing backend misconfiguration must fail app startup when tracing is
  required.
- Zero or disabled committed eval thresholds must fail app startup.
- Failure must be structured enough for the runbook to map it to a debugging
  path.

## Documentation Contract

- `README.md` explains setup, architecture overview, commands, and demo.
- `docs/ARCH.md` explains layers, runtime services, and request flow.
- `docs/DECISIONS.md` includes numeric evidence for classifier, embedding,
  chunking, retrieval weighting, reranking, memory type, and tracing backend.
- `docs/EVALS.md` explains golden sets, thresholds, commands, reports, and
  previous-green diff interpretation.
- `docs/SECURITY.md` explains secret policy, static secret grep checks, and
  redaction patterns.
- `docs/RUNBOOK.md` explains common failure paths and debugging steps.

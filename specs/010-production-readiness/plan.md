# Implementation Plan: Production Readiness

**Branch**: `010-production-readiness` | **Date**: 2026-05-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/010-production-readiness/spec.md`

## Summary

Build the final Phase 10 release-readiness layer: GitHub Actions CI, local
validation commands, uv dependency installation, ruff lint and format checks,
type-checking, pytest tests, classifier and RAG eval gates, redaction leak
checks, static secret grep checks, Docker build validation, Docker Compose smoke
tests, eval report generation, MinIO storage, previous-green report diffing,
model artifact hash validation, Vault/model-artifact/tracing/eval-threshold
startup failure checks, tracing configuration validation, and final review
documentation. The workflow must run without real paid API credentials by using
fake providers, committed small golden sets, and local artifacts.

## Technical Context

**Language/Version**: Python 3.11 or newer; GitHub Actions workflow YAML; Bash
or Python scripts for local validation orchestration  
**Primary Dependencies**: uv, ruff, pytest, httpx, Docker Compose, existing
classifier and RAG eval scripts, existing redaction/tracing/model artifact
helpers, type checker such as pyright when no project checker exists, MinIO
storage adapter with local-compatible dev/test fallback, fake provider clients
or mocked provider calls  
**Storage**: Generated `eval_report.json` written to a local artifact path and
stored in MinIO for CI; MinIO-compatible local paths are dev/test adapters only;
committed non-zero and enabled `eval_thresholds.yaml`; previous-green report
metadata; no real secrets or paid-provider credentials in CI  
**Testing**: pytest for gate behavior, redaction leaks, threshold failure,
static grep failures, previous-green regressions, artifact hash mismatch,
Vault/model/tracing/eval-threshold startup failures, tracing validation,
documentation completeness, and CI script behavior; Docker Compose smoke test
for core stack health  
**Target Platform**: GitHub Actions on Linux plus local Linux/container
development environment  
**Project Type**: Release validation, security/eval gate, smoke-test, and
documentation completion feature  
**Performance Goals**: Normal CI validation completes within a bootcamp-friendly
time budget using compact committed golden sets and local artifacts; smoke test
starts only the core stack required for health validation  
**Constraints**: Phase 10 only; no new product behavior, model behavior, RAG
behavior, chatbot behavior, widget behavior, or heavy infrastructure; CI must
not depend on real paid APIs; every release gate fails closed with a clear
reason; eval thresholds must be non-zero and not disabled  
**Scale/Scope**: One CI workflow, local validation scripts, eval report schema
and MinIO storage, previous-green diffing, security/startup/artifact/tracing
checks, stack smoke test, and final README, ARCH, DECISIONS, RUNBOOK, EVALS, and
SECURITY documentation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Phase Scope**: PASS. This plan only adds production readiness gates,
  observability/security validation, smoke tests, eval reporting, and final
  documentation. It does not change application product behavior or implement
  new AI, RAG, chatbot, widget, or auth features.
- **Layered Architecture**: PASS. CI and scripts orchestrate checks around the
  existing app. They do not introduce route-level SQL, route-level external
  clients, or new persistence shortcuts. Any validation helpers for Vault,
  tracing, redaction, MinIO, or model artifacts live in scripts/tests or existing
  infra/service boundaries.
- **FastAPI Resource Management**: PASS. Startup failure checks validate the
  existing app factory and lifespan behavior for Vault and model artifacts; the
  plan does not create expensive resources at import time or per request.
- **Async Safety**: PASS. CI checks and evals run as scripts/jobs. Smoke tests
  call health endpoints through HTTP with bounded waits. No blocking work is
  added to async request paths.
- **Secrets And Redaction**: PASS. CI uses fakes and local fixtures, never real
  paid-provider credentials. Redaction leak tests prove fake secret-like values
  do not appear unredacted in logs, traces, memory, audit records, or captured
  outputs.
- **Observability And Errors**: PASS. Tracing configuration is validated, smoke
  tests preserve enough diagnostic output, and startup failures must be
  structured and explainable without leaking sensitive payloads.
- **AI Evidence And Eval Gates**: PASS. Classifier and RAG evals run against
  committed small golden sets/local artifacts, compare results to non-zero
  enabled thresholds, write `eval_report.json`, store it in MinIO, diff it
  against the previous green build, and feed final `DECISIONS.md` and `EVALS.md`
  numbers.
- **Critical Tests And CI**: PASS. Tests cover zero thresholds, below-threshold
  classifier/RAG results, previous-green regressions, fake secret leaks, static
  secret grep failures, model hash mismatch, missing model artifacts, Vault
  unreachable startup failure, tracing config failure, disabled-threshold startup
  failure, smoke test health, MinIO eval report storage, and documentation
  completeness.
- **Simplicity**: PASS. The plan uses GitHub Actions, uv, ruff, pytest, Docker
  Compose, local fakes, and small committed eval assets. It does not add Kafka,
  Kubernetes, Celery, or additional datastores.

## Project Structure

### Documentation (this feature)

```text
specs/010-production-readiness/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── eval-report.schema.json
│   └── validation-workflow.md
└── tasks.md
```

### Source Code (repository root)

```text
.github/
└── workflows/
    └── ci.yml

scripts/
└── ci/
    ├── run_all.sh
    ├── run_lint.sh
    ├── run_format_check.sh
    ├── run_type_check.sh
    ├── run_tests.sh
    ├── run_evals.sh
    ├── build_eval_report.py
    ├── check_eval_thresholds.py
    ├── compare_previous_green_report.py
    ├── check_model_artifacts.py
    ├── check_redaction_leaks.py
    ├── check_static_secret_patterns.py
    ├── check_startup_failures.py
    ├── validate_tracing.py
    ├── validate_docs.py
    ├── store_eval_report.py
    └── smoke_stack.sh

evals/
├── eval_thresholds.yaml
├── classification/
│   └── golden.jsonl
├── rag/
│   └── golden.jsonl
└── reports/
    └── eval_report.json

artifacts/
└── evals/

docs/
├── ARCH.md
├── DECISIONS.md
├── EVALS.md
├── RUNBOOK.md
└── SECURITY.md

README.md

tests/
├── ci/
│   ├── test_eval_threshold_gate.py
│   ├── test_eval_report_schema.py
│   ├── test_previous_green_report_diff.py
│   ├── test_model_artifact_hash_gate.py
│   ├── test_redaction_leak_gate.py
│   ├── test_static_secret_pattern_gate.py
│   ├── test_startup_failure_gates.py
│   ├── test_tracing_config_gate.py
│   └── test_docs_completeness.py
└── integration/
    └── test_stack_smoke_health.py
```

**Structure Decision**: Keep CI orchestration in `.github/workflows/ci.yml` and
small reusable scripts under `scripts/ci/`. Store committed thresholds and small
golden sets under `evals/`, generated reports under `evals/reports/` and
MinIO artifact storage for CI reports with local-compatible storage only as a
dev/test adapter, final docs in `README.md` and `docs/`, and
gate tests under `tests/ci/` plus smoke tests under `tests/integration/`.

## Complexity Tracking

No constitution violations are planned.

## Post-Design Constitution Check

- **Phase Scope**: PASS. Generated artifacts cover only final validation,
  security/observability gates, eval reporting, smoke testing, and docs.
- **Layered Architecture**: PASS. Contracts define scripts and CI gates without
  changing app-layer ownership.
- **FastAPI Resource Management**: PASS. Startup gates validate lifespan-owned
  dependencies instead of bypassing them.
- **Async Safety**: PASS. Long-running eval, Docker, and smoke work stays in CI
  scripts/jobs.
- **Secrets And Redaction**: PASS. Fake-provider CI and redaction leak contracts
  are explicit.
- **Observability And Errors**: PASS. Tracing and startup failure contracts
  require clear diagnostics without sensitive payloads.
- **AI Evidence And Eval Gates**: PASS. Non-zero thresholds, compact evals,
  previous-green diffing, report schema, MinIO report storage, and final
  decision docs are planned.
- **Critical Tests And CI**: PASS. All release blockers have targeted tests or
  CI gates.
- **Simplicity**: PASS. The plan uses existing tooling and avoids additional
  production infrastructure.

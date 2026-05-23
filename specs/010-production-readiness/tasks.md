# Tasks: Production Readiness

**Input**: Design documents from `/specs/010-production-readiness/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Required for all release gates, security checks, eval behavior, startup refusal behavior, smoke checks, and documentation validation.

**Organization**: Tasks are grouped by user story so each story is independently implementable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish Phase 10 quality-gate tooling, local command entry points, and CI folder layout.

- [X] T001 Add `flake8` and `black` to the dev dependency group in `pyproject.toml`
- [X] T002 [P] Add `tool.black` configuration aligned to line length 100 in `pyproject.toml`
- [X] T003 [P] Add `flake8` configuration file `.flake8` with repo-appropriate ignores and max line length
- [X] T004 Create `scripts/ci/` directory with executable helper scripts tracked by `.gitkeep` or concrete script files in `scripts/ci/`
- [X] T005 Create `Makefile` targets `validate`, `lint`, `format-check`, `import-check`, `type-check`, `test`, `evals`, `security`, `smoke`, and `docs`
- [X] T006 Create `.github/workflows/ci.yml` workflow skeleton that installs with uv and calls the Phase 10 gate commands
- [X] T007 [P] Add CI fixture directories `tests/fixtures/ci/`, `evals/classification/`, `evals/rag/`, and `evals/reports/` with placeholder `.gitkeep` files
- [X] T008 [P] Add compact classification golden fixture `evals/classification/golden.jsonl` derived from existing safe test data
- [X] T009 [P] Add compact RAG golden fixture `evals/rag/golden.jsonl` derived from existing safe test data
- [X] T010 Update `evals/eval_thresholds.yaml` to non-zero enabled Phase 10 classifier and RAG thresholds

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared CI modules and gate helpers that all user stories depend on.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T011 [P] Create reusable command runner and safe output helpers in `scripts/ci/common.py`
- [X] T012 [P] Create validation workflow domain models in `scripts/ci/models.py`
- [X] T013 [P] Create eval report builder primitives matching `contracts/eval-report.schema.json` in `scripts/ci/eval_report.py`
- [X] T014 [P] Create threshold loading and validation helpers in `scripts/ci/thresholds.py`
- [X] T015 [P] Create MinIO/local-compatible report storage adapter in `scripts/ci/report_storage.py`
- [X] T016 [P] Create static secret pattern scanner helpers in `scripts/ci/secret_scan.py`
- [X] T017 [P] Create model artifact hash helper functions in `scripts/ci/model_artifacts.py`
- [X] T018 [P] Create startup negative-case harness helpers in `scripts/ci/startup_checks.py`
- [X] T019 [P] Create tracing config validation helpers in `scripts/ci/tracing_checks.py`
- [X] T020 [P] Create documentation completeness helper in `scripts/ci/docs_check.py`
- [X] T021 Create `scripts/ci/run_lint.sh` wrapper for `uv run flake8 .`
- [X] T022 Create `scripts/ci/run_format_check.sh` wrapper for `uv run black --check .` and `uv run isort --check-only .`
- [X] T023 Create `scripts/ci/run_type_check.sh` wrapper for `uv run mypy .`
- [X] T024 Create `scripts/ci/run_tests.sh` wrapper for `uv run pytest`
- [X] T025 Create `scripts/ci/run_all.sh` orchestration script that executes all required gates in contract order
- [X] T026 [P] Add unit tests for threshold helper validation in `tests/ci/test_eval_threshold_gate.py`
- [X] T027 [P] Add unit tests for eval report schema validation in `tests/ci/test_eval_report_schema.py`
- [X] T028 [P] Add unit tests for safe command output redaction in `tests/ci/test_ci_common.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in priority order.

---

## Phase 3: User Story 1 - Prove The Validation Workflow Is Wired (Priority: P1) MVP

**Goal**: A reviewer can run one local or CI validation command surface that invokes every required gate in order and fails fast with safe output.

**Independent Test**: Run `make validate` and the GitHub Actions command sequence against fixture gates; verify lint, format, type-check, tests, Docker build, smoke, eval, security, and docs gates are invoked in order, fail fast on errors, and do not require paid-provider credentials.

### Tests for User Story 1

- [X] T029 [P] [US1] Add Makefile target behavior tests in `tests/ci/test_makefile_targets.py`
- [X] T030 [P] [US1] Add CI workflow structure tests proving Docker build is a required non-skippable gate in `tests/ci/test_github_actions_workflow.py`
- [X] T031 [P] [US1] Add quality gate wrapper tests in `tests/ci/test_quality_gate_scripts.py`
- [X] T032 [P] [US1] Add full validation orchestration and no-paid-credentials tests in `tests/ci/test_validation_workflow_order.py`
- [X] T033 [P] [US1] Add Docker smoke script integration test in `tests/integration/test_stack_smoke_health.py`

### Implementation for User Story 1

- [X] T034 [US1] Wire `Makefile` targets to `scripts/ci/run_lint.sh`, `scripts/ci/run_format_check.sh`, `scripts/ci/run_type_check.sh`, `scripts/ci/run_tests.sh`, and `scripts/ci/run_all.sh`
- [X] T035 [US1] Implement `.github/workflows/ci.yml` jobs for dependency install, quality gates, tests, evals, security, Docker build, smoke, report storage, and docs validation
- [X] T036 [US1] Implement `scripts/ci/run_all.sh` fail-fast orchestration with safe gate summaries
- [X] T037 [US1] Implement `scripts/ci/smoke_stack.sh` to start the production-functional Docker Compose stack including `model_server`
- [X] T038 [US1] Implement `scripts/ci/validate_stack_health.py` backend health polling and safe log collection for smoke failures
- [X] T039 [US1] Update `README.md` with `make validate`, individual gate commands, and full-stack smoke-test command
- [X] T040 [US1] Verify US1 focused suite with `uv run pytest tests/ci/test_makefile_targets.py tests/ci/test_github_actions_workflow.py tests/ci/test_quality_gate_scripts.py tests/ci/test_validation_workflow_order.py tests/integration/test_stack_smoke_health.py`

**Checkpoint**: User Story 1 is independently functional and proves the clean-repo validation workflow.

---

## Phase 4: User Story 2 - Fail Fast On Eval Or Threshold Regression (Priority: P2)

**Goal**: Classifier and RAG quality cannot silently regress because thresholds, eval reports, storage, and previous-green diffing are enforced.

**Independent Test**: Set thresholds to zero or feed below-threshold/current-vs-previous regression fixtures and verify the workflow fails with safe metric summaries.

### Tests for User Story 2

- [X] T041 [P] [US2] Add classifier eval gate tests in `tests/ci/test_classifier_eval_gate.py`
- [X] T042 [P] [US2] Add RAG eval gate tests in `tests/ci/test_rag_eval_gate.py`
- [X] T043 [P] [US2] Add zero, missing, negative, disabled, and malformed threshold tests in `tests/ci/test_eval_threshold_gate.py`
- [X] T044 [P] [US2] Add eval report builder and schema tests in `tests/ci/test_eval_report_schema.py`
- [X] T045 [P] [US2] Add previous-green comparison tests in `tests/ci/test_previous_green_report_diff.py`
- [X] T046 [P] [US2] Add report storage adapter tests in `tests/ci/test_eval_report_storage.py`

### Implementation for User Story 2

- [X] T047 [US2] Implement `scripts/ci/check_eval_thresholds.py` using `scripts/ci/thresholds.py`
- [X] T048 [US2] Implement `scripts/ci/run_evals.sh` to run classifier and RAG compact golden-set evals
- [X] T049 [US2] Implement classifier eval adapter in `scripts/ci/run_classifier_eval.py` that runs the existing classifier eval path against `evals/classification/golden.jsonl` and normalizes fresh results
- [X] T050 [US2] Implement RAG eval adapter in `scripts/ci/run_rag_eval.py` that runs the existing RAG eval path against `evals/rag/golden.jsonl` and normalizes fresh results
- [X] T051 [US2] Implement `scripts/ci/build_eval_report.py` to emit `evals/reports/eval_report.json` with `run_id`, `timestamp`, `classifier`, `rag`, `storage.bucket`, `storage.key`, and `passed`
- [X] T052 [US2] Implement `scripts/ci/compare_previous_green_report.py` with 2 absolute percentage point regression failure logic
- [X] T053 [US2] Implement `scripts/ci/store_eval_report.py` with MinIO CI storage and local-compatible dev/test adapter
- [X] T054 [US2] Update `docs/evals.md` with threshold values, compact golden sets, report schema, MinIO storage, and previous-green diffing behavior
- [X] T055 [US2] Update `docs/decisions.md` with numeric classifier, embedding, chunking, retrieval weighting, reranking, memory type, and tracing evidence references
- [X] T056 [US2] Verify US2 focused suite with `uv run pytest tests/ci/test_classifier_eval_gate.py tests/ci/test_rag_eval_gate.py tests/ci/test_eval_threshold_gate.py tests/ci/test_eval_report_schema.py tests/ci/test_previous_green_report_diff.py tests/ci/test_eval_report_storage.py`

**Checkpoint**: User Story 2 is independently functional and fails on eval, threshold, storage, or previous-green regressions.

---

## Phase 5: User Story 3 - Prove Security And Startup Failure Gates (Priority: P3)

**Goal**: Secret leaks, model artifact problems, Vault failure, tracing misconfiguration, and disabled thresholds fail safely.

**Independent Test**: Run targeted security/startup fixtures that inject fake secrets, break Vault, corrupt artifacts, misconfigure tracing, and disable thresholds; verify each case fails cleanly without leaking raw values.

### Tests for User Story 3

- [X] T057 [P] [US3] Add redaction leak gate tests covering logs, traces, memory, audit, and captured output in `tests/ci/test_redaction_leak_gate.py`
- [X] T058 [P] [US3] Add static secret pattern gate tests for unsafe `sk-` and `password` fixtures in `tests/ci/test_static_secret_pattern_gate.py`
- [X] T059 [P] [US3] Add model artifact hash gate tests in `tests/ci/test_model_artifact_hash_gate.py`
- [X] T060 [P] [US3] Add startup negative-case tests for Vault, missing secrets, model artifacts, tracing, and thresholds in `tests/ci/test_startup_failure_gates.py`
- [X] T061 [P] [US3] Add tracing config gate tests in `tests/ci/test_tracing_config_gate.py`

### Implementation for User Story 3

- [X] T062 [US3] Implement `scripts/ci/check_redaction_leaks.py` with fake secret probes and safe failure output
- [X] T063 [US3] Implement `scripts/ci/check_static_secret_patterns.py` with allowlisted static scanning for `sk-` and `password` patterns
- [X] T064 [US3] Implement `scripts/ci/check_model_artifacts.py` to compare SHA-256 values from model cards against required artifacts
- [X] T065 [US3] Implement `scripts/ci/check_startup_failures.py` negative startup checks for Vault, missing secrets, missing artifacts, hash mismatch, tracing, and disabled thresholds
- [X] T066 [US3] Implement `scripts/ci/validate_tracing.py` request_id/trace_id and backend-sink validation for the test profile
- [X] T067 [US3] Add safe failure fixtures under `tests/fixtures/ci/security/` for fake secret, static grep, and redaction tests
- [X] T068 [US3] Add model artifact failure fixtures under `tests/fixtures/ci/model_artifacts/`
- [X] T069 [US3] Update `docs/security.md` with Phase 10 redaction, static grep, fake secret, artifact integrity, and startup failure policies
- [X] T070 [US3] Verify US3 focused suite with `uv run pytest tests/ci/test_redaction_leak_gate.py tests/ci/test_static_secret_pattern_gate.py tests/ci/test_model_artifact_hash_gate.py tests/ci/test_startup_failure_gates.py tests/ci/test_tracing_config_gate.py`

**Checkpoint**: User Story 3 is independently functional and proves security/startup gates fail closed.

---

## Phase 6: User Story 4 - Review Final Documentation And Runbook (Priority: P4)

**Goal**: Final docs explain setup, architecture, commands, decisions, evals, security policy, and runbook failure paths.

**Independent Test**: Run documentation completeness validation and manually follow the README/runbook commands on a clean checkout.

### Tests for User Story 4

- [X] T071 [P] [US4] Add documentation completeness tests for README and required docs in `tests/ci/test_docs_completeness.py`
- [X] T072 [P] [US4] Add README command coverage tests in `tests/ci/test_readme_commands.py`
- [X] T073 [P] [US4] Add runbook failure-path coverage tests in `tests/ci/test_runbook_failure_paths.py`

### Implementation for User Story 4

- [X] T074 [US4] Implement `scripts/ci/validate_docs.py` required-doc and required-section validation
- [X] T075 [US4] Update `README.md` with setup, architecture overview, common commands, demo flow, CI gates, and expected results
- [X] T076 [US4] Update `docs/architecture.md` with final runtime service map, validation workflow, and request/eval/report flow
- [X] T077 [US4] Update `docs/runbook.md` with CI failure debugging for lint, type-check, eval, MinIO, Vault, model artifact, tracing, smoke, and docs gates
- [X] T078 [US4] Update `docs/evals.md` with previous-green report diff interpretation and regression review process
- [X] T079 [US4] Update `docs/security.md` with static secret grep, redaction leak probes, and secret policy
- [X] T080 [US4] Update `docs/decisions.md` with final numeric evidence references and Phase 10 release-gate decisions
- [X] T081 [US4] Verify US4 focused suite with `uv run pytest tests/ci/test_docs_completeness.py tests/ci/test_readme_commands.py tests/ci/test_runbook_failure_paths.py`

**Checkpoint**: User Story 4 is independently functional and final documentation is review-ready.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, cleanup, and artifact consistency checks across Phase 10.

- [X] T082 [P] Run JSON schema syntax validation for `specs/010-production-readiness/contracts/eval-report.schema.json`
- [X] T083 [P] Run YAML syntax validation for `.github/workflows/ci.yml` and `evals/eval_thresholds.yaml`
- [X] T084 [P] Run shell syntax checks for `scripts/ci/run_all.sh`, `scripts/ci/run_lint.sh`, `scripts/ci/run_format_check.sh`, `scripts/ci/run_type_check.sh`, `scripts/ci/run_tests.sh`, `scripts/ci/run_evals.sh`, and `scripts/ci/smoke_stack.sh`
- [X] T085 Run `make validate` locally and capture safe summary output in `evals/reports/local_validation_summary.txt`
- [X] T086 Run full regression with `uv run pytest -q` and document the known pre-existing flaky test if it remains in `docs/runbook.md`
- [X] T087 Run `docker compose build` and `scripts/ci/smoke_stack.sh` against the full production-functional stack including `model_server`
- [X] T088 Run `/speckit-analyze` against `specs/010-production-readiness/tasks.md` after all Phase 10 tasks are marked complete and resolve any reported drift
- [X] T089 Update `specs/010-production-readiness/tasks.md` to mark T001-T089 complete after implementation and verification

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies.
- **Phase 2 Foundational**: Depends on Phase 1 and blocks all user stories.
- **Phase 3 US1**: Depends on Phase 2; delivers MVP validation workflow.
- **Phase 4 US2**: Depends on Phase 2; can run after or alongside US1 once shared workflow scripts exist, but final CI wiring depends on US1.
- **Phase 5 US3**: Depends on Phase 2; can run after or alongside US2, but final workflow aggregation depends on US1.
- **Phase 6 US4**: Depends on Phase 2 and should incorporate final behavior from US1-US3.
- **Phase 7 Polish**: Depends on desired user stories being complete.

### User Story Dependencies

- **US1 (P1)**: MVP. Needed for the complete validation command and CI surface.
- **US2 (P2)**: Uses foundational report/threshold/storage helpers and plugs into US1 workflow.
- **US3 (P3)**: Uses foundational safety helpers and plugs into US1 workflow.
- **US4 (P4)**: Can start after Phase 2, but final docs should be completed after US1-US3 behavior is stable.

### Within Each User Story

- Tests come first and should fail before implementation.
- Helper modules before scripts.
- Scripts before Makefile/CI aggregation.
- Gate implementation before documentation claims completion.

### Parallel Opportunities

- Setup: T002, T003, T007, T008, T009 can run in parallel.
- Foundational: T011-T020 can run in parallel after Phase 1.
- US1 tests: T029-T033 can run in parallel.
- US2 tests: T041-T046 can run in parallel.
- US3 tests: T057-T061 can run in parallel.
- US4 tests: T071-T073 can run in parallel.
- Polish syntax checks: T082-T084 can run in parallel.

## Parallel Execution Examples

### US1

```text
Task: T029 Add Makefile target behavior tests in tests/ci/test_makefile_targets.py
Task: T030 Add CI workflow structure tests in tests/ci/test_github_actions_workflow.py
Task: T031 Add quality gate wrapper tests in tests/ci/test_quality_gate_scripts.py
Task: T033 Add Docker smoke script integration test in tests/integration/test_stack_smoke_health.py
```

### US2

```text
Task: T041 Add classifier eval gate tests in tests/ci/test_classifier_eval_gate.py
Task: T042 Add RAG eval gate tests in tests/ci/test_rag_eval_gate.py
Task: T045 Add previous-green comparison tests in tests/ci/test_previous_green_report_diff.py
Task: T046 Add report storage adapter tests in tests/ci/test_eval_report_storage.py
```

### US3

```text
Task: T057 Add redaction leak gate tests in tests/ci/test_redaction_leak_gate.py
Task: T058 Add static secret pattern gate tests in tests/ci/test_static_secret_pattern_gate.py
Task: T059 Add model artifact hash gate tests in tests/ci/test_model_artifact_hash_gate.py
Task: T061 Add tracing config gate tests in tests/ci/test_tracing_config_gate.py
```

### US4

```text
Task: T071 Add documentation completeness tests for README and required docs in tests/ci/test_docs_completeness.py
Task: T072 Add README command coverage tests in tests/ci/test_readme_commands.py
Task: T073 Add runbook failure-path coverage tests in tests/ci/test_runbook_failure_paths.py
```

## Implementation Strategy

### MVP First

Complete Phase 1, Phase 2, and Phase 3 (US1) to deliver a working local and CI validation shell that can run from a clean checkout.

### Incremental Delivery

1. Add eval and previous-green enforcement with US2.
2. Add security, artifact, startup, and tracing failure gates with US3.
3. Complete final docs and docs validation with US4.
4. Run Phase 7 full validation and analyze before merge.

### Final Validation

Run:

```bash
make validate
uv run pytest -q
docker compose build
scripts/ci/smoke_stack.sh
```

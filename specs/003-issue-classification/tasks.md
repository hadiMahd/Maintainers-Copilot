# Tasks: Issue Classification Track

**Input**: Design documents from `/specs/003-issue-classification/`
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Tests are REQUIRED for critical behavior in this phase. That includes
metric calculation, fake-provider LLM evaluation behavior, Vault-backed secret
resolution, redaction before telemetry/artifact persistence, artifact
hash/model-card/run metadata validation, classifier endpoint schema, oversized
input validation, unavailable-model errors, lifespan loading, latency
measurement support, and no committed real secrets.

**Organization**: Tasks are grouped by user story to keep each increment
independently implementable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel after dependencies are met
- **[Story]**: User story label (`[US1]`, `[US2]`, `[US3]`)
- Every task includes the exact file path to change

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add the Phase 3 dependencies, bootstrap configuration, and local
services needed by training and artifact logging.

- [ ] T001 Add Phase 3 runtime and dev dependencies for scikit-learn, Transformers, safetensors, MLflow, LangChain Azure OpenAI, and LangSmith in `pyproject.toml`
- [ ] T002 [P] Add Phase 3 bootstrap environment variables for classifier artifacts, MLflow, MinIO, Vault-backed Azure OpenAI, and Vault-backed LangSmith settings in `.env.example`
- [ ] T003 [P] Add a self-hosted `mlflow` service wired to `minio` for local Phase 3 runs in `docker-compose.yml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the shared schemas, fixtures, settings, secret-resolution, and
redaction helpers that all Phase 3 user stories depend on.

**⚠️ CRITICAL**: No user story implementation should start before this phase is complete.

- [ ] T004 Create classifier label, prediction, report, artifact, and error schemas in `app/domain/classifier.py` and update exports in `app/domain/__init__.py`
- [ ] T005 [P] Extend Phase 3 dataset, prediction, artifact, and endpoint fixtures in `tests/conftest.py`
- [ ] T006 [P] Create foundational Vault secret-resolution and bootstrap-setting tests in `tests/test_config.py` and `tests/test_no_secrets.py`
- [ ] T007 [P] Create telemetry and artifact redaction tests in `tests/unit/test_classifier_redaction.py`
- [ ] T008 Extend Phase 3 Vault secret-resolution helpers for Azure OpenAI and LangSmith in `app/infra/vault_client.py`
- [ ] T009 Create the infra redaction helper for MLflow, LangSmith, model cards, and manifests in `app/infra/redaction.py` and update exports in `app/infra/__init__.py`
- [ ] T010 [P] Create MLflow tracking helpers in `app/infra/mlflow/tracking.py` and package exports in `app/infra/mlflow/__init__.py`
- [ ] T011 [P] Create MinIO classifier artifact and manifest helpers in `app/infra/storage/classifier_artifacts.py` and package exports in `app/infra/storage/__init__.py`
- [ ] T012 [P] Create the Azure OpenAI / fake-provider classifier baseline adapter in `app/infra/llm/classifier_baseline.py` and package exports in `app/infra/llm/__init__.py`
- [ ] T013 Extend typed bootstrap and runtime Phase 3 settings in `app/core/config.py`
- [ ] T014 Create shared metric, hashing, and evaluation report builders in `app/services/classifier_evaluation.py`

**Checkpoint**: Foundation ready. Shared schemas, fixtures, Vault resolution,
redaction, and adapters exist for classifier training, artifact evidence, and
model-server work.

---

## Phase 3: User Story 1 - Compare Classification Approaches (Priority: P1) 🎯 MVP

**Goal**: Train or run the classical baseline, fine-tuned transformer, and LLM
baseline on the same dataset split and compare them in one shared evaluation
report.

**Independent Test**: Run `python scripts/train_classical_classifier.py`,
`python scripts/train_transformer_classifier.py`,
`python scripts/run_llm_classifier_baseline.py`, and
`python scripts/evaluate_classifiers.py`, then verify
`evals/classifier_eval_report.json` contains accuracy, macro-F1, per-class F1,
confusion matrix, latency, and cost/skip data for the completed approaches.

### Tests for User Story 1 (REQUIRED) ⚠️

- [ ] T015 [P] [US1] Create metric and shared-report unit tests in `tests/unit/test_classifier_metrics.py`
- [ ] T016 [P] [US1] Create fake-provider, Vault-backed provider-config, and LangSmith-toggle integration tests in `tests/integration/test_llm_classifier_fake_provider.py`

### Implementation for User Story 1

- [ ] T017 [P] [US1] Create the 25-example golden set in `evals/classification_golden_set.jsonl`
- [ ] T018 [P] [US1] Implement the classical baseline training command in `scripts/train_classical_classifier.py`
- [ ] T019 [P] [US1] Implement the transformer training command shell with shared evaluation and Vault-aware MLflow wiring in `scripts/train_transformer_classifier.py`
- [ ] T020 [P] [US1] Implement the Azure OpenAI / fake-provider baseline command with redacted tracing metadata in `scripts/run_llm_classifier_baseline.py`
- [ ] T021 [US1] Implement the shared evaluation command and report writer in `scripts/evaluate_classifiers.py`
- [ ] T022 [US1] Document classifier metrics, fake-provider mode, Vault/LangSmith rules, and Phase 3 evaluation commands in `docs/evals.md`

**Checkpoint**: User Story 1 is independently testable. All three approaches can
produce or report comparable outputs on the same test split.

---

## Phase 4: User Story 2 - Preserve Model Artifacts and Evidence (Priority: P2)

**Goal**: Make the transformer artifact deployable and reviewable through model
cards, hashes, plots, MLflow run metadata, MinIO references, and classifier
decision documentation.

**Independent Test**: Train the transformer, inspect
`artifacts/classifiers/transformer/`, run
`python scripts/upload_classifier_artifact_manifest.py`, and verify the saved
artifact includes model weights, tokenizer files, `metrics.json`,
`model_card.json`, artifact SHA-256, training-data hash, run metadata, plot
references, and a MinIO artifact or manifest reference.

### Tests for User Story 2 (REQUIRED) ⚠️

- [ ] T023 [P] [US2] Create artifact-hash and model-card validation tests in `tests/unit/test_classifier_artifact_hash.py` and `tests/unit/test_classifier_model_card.py`
- [ ] T024 [P] [US2] Create MLflow run metadata, MinIO manifest, and redacted-telemetry tests in `tests/unit/test_classifier_run_metadata.py` and `tests/unit/test_classifier_redaction.py`

### Implementation for User Story 2

- [ ] T025 [US2] Extend transformer artifact generation with model card, metrics, plots, hashes, redacted metadata, and deployable-status rules in `scripts/train_transformer_classifier.py`
- [ ] T026 [US2] Implement the selected-artifact upload or manifest command in `scripts/upload_classifier_artifact_manifest.py`
- [ ] T027 [US2] Finalize MLflow completion, redaction, and MinIO artifact enforcement in `app/infra/mlflow/tracking.py` and `app/infra/storage/classifier_artifacts.py`
- [ ] T028 [US2] Record classifier comparison evidence, selected approach, and artifact references in `docs/decisions.md`

**Checkpoint**: User Story 2 is independently testable. The selected classifier
artifact is hash-validated, traceable, redacted safely, and documented for review.

---

## Phase 5: User Story 3 - Serve Classifier Predictions Safely (Priority: P3)

**Goal**: Expose a model-server classifier endpoint that loads the selected
artifact during lifespan and returns typed predictions or structured
unavailable-model errors.

**Independent Test**: Start the model server with a valid selected artifact and
call the classifier endpoint to verify a typed label, optional confidence, and
semantic `model_version`. Start without a valid artifact and verify a structured
`503` unavailable-model response with no stack trace.

### Tests for User Story 3 (REQUIRED) ⚠️

- [ ] T029 [P] [US3] Create classifier schema and endpoint contract tests including semantic version and unavailable reasons in `tests/unit/test_classifier_schemas.py` and `tests/contract/test_classifier_endpoint_contract.py`
- [ ] T030 [P] [US3] Create oversized-input and structured-`422` validation tests in `tests/integration/test_classifier_request_validation.py`
- [ ] T031 [P] [US3] Create classifier lifespan, hash-mismatch, and import-side-effect tests in `tests/integration/test_classifier_model_lifecycle.py` and `tests/test_import_side_effects.py`

### Implementation for User Story 3

- [ ] T032 [P] [US3] Create model-server classifier request, response, and error models in `model_server/domain/classifier.py` and `model_server/domain/__init__.py`
- [ ] T033 [P] [US3] Implement artifact loading, hash validation, and Vault-backed runtime setup in `model_server/infra/classifier_loader.py` and `model_server/infra/__init__.py`
- [ ] T034 [US3] Implement classifier inference orchestration with input-size checks, confidence omission, and redacted logging in `model_server/services/classifier_service.py` and `model_server/services/__init__.py`
- [ ] T035 [US3] Implement the thin classifier route in `model_server/api/classifier.py` and `model_server/api/__init__.py`
- [ ] T036 [US3] Replace the model-server stub with a FastAPI lifespan app and Phase 3 startup wiring in `model_server/main.py` and `model_server/Dockerfile`
- [ ] T037 [US3] Add the latency measurement command for 30 warm sequential representative requests in `scripts/measure_classifier_latency.py`
- [ ] T038 [US3] Document classifier endpoint startup, input limits, latency method, and unavailable-model behavior in `docs/architecture.md` and `docs/runbook.md`

**Checkpoint**: User Story 3 is independently testable. Later phases can call
the classifier endpoint without per-request model loading or ambiguous failures.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finish docs, ignore rules, and final validation across the full
Phase 3 surface.

- [ ] T039 [P] Update classifier artifact, plot, and eval-output ignore rules in `.gitignore`
- [ ] T040 [P] Sync Phase 3 usage and security notes in `README.md` and `docs/security.md`
- [ ] T041 [P] Sync Phase 3 command examples and expected outputs in `specs/003-issue-classification/quickstart.md`
- [ ] T042 Run the full Phase 3 validation suite referenced by `tests/`, `scripts/`, and `specs/003-issue-classification/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies. Start immediately.
- **Foundational (Phase 2)**: Depends on Setup. Blocks all story work.
- **User Story 1 (Phase 3)**: Depends on Foundational only. This is the MVP.
- **User Story 2 (Phase 4)**: Depends on Foundational and the transformer
  training flow from User Story 1.
- **User Story 3 (Phase 5)**: Depends on Foundational and the selected,
  hash-validated artifact from User Story 2.
- **Polish (Phase 6)**: Depends on the stories you want to ship being complete.

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2. No dependency on later stories.
- **US2 (P2)**: Builds on the transformer artifact produced in US1, but remains
  independently verifiable through artifact inspection and manifest upload.
- **US3 (P3)**: Builds on the selected artifact from US2, but remains
  independently verifiable through model-server startup and endpoint calls.

### Within Each User Story

- Write the required tests first and confirm they fail before implementing.
- Shared schemas, Vault resolution, and redaction before command or endpoint wiring.
- Artifact generation before artifact upload or manifesting.
- Loader and service work before the route and FastAPI startup wiring.
- Finish the story’s docs before marking the story complete.

### Parallel Opportunities

- **Phase 1**: `T002` and `T003` can run in parallel after `T001`.
- **Phase 2**: `T005`, `T006`, `T007`, `T010`, `T011`, and `T012` can run in
  parallel after `T004`; `T008`, `T009`, `T013`, and `T014` then consolidate
  shared behavior.
- **US1**: `T015`, `T016`, and `T017` can run in parallel; after that `T018`,
  `T019`, and `T020` can run in parallel before `T021`.
- **US2**: `T023` and `T024` can run in parallel before `T025` and `T026`.
- **US3**: `T029`, `T030`, and `T031` can run in parallel; `T032` and `T033`
  can run in parallel before `T034`.

---

## Parallel Example: User Story 1

```bash
# Launch User Story 1 tests together
Task: "Create metric and shared-report unit tests in tests/unit/test_classifier_metrics.py"
Task: "Create fake-provider, Vault-backed provider-config, and LangSmith-toggle integration tests in tests/integration/test_llm_classifier_fake_provider.py"

# Launch User Story 1 implementation work together after foundational tasks
Task: "Implement the classical baseline training command in scripts/train_classical_classifier.py"
Task: "Implement the transformer training command shell with shared evaluation and Vault-aware MLflow wiring in scripts/train_transformer_classifier.py"
Task: "Implement the Azure OpenAI / fake-provider baseline command with redacted tracing metadata in scripts/run_llm_classifier_baseline.py"
```

## Parallel Example: User Story 2

```bash
# Launch User Story 2 evidence tests together
Task: "Create artifact-hash and model-card validation tests in tests/unit/test_classifier_artifact_hash.py and tests/unit/test_classifier_model_card.py"
Task: "Create MLflow run metadata, MinIO manifest, and redacted-telemetry tests in tests/unit/test_classifier_run_metadata.py and tests/unit/test_classifier_redaction.py"
```

## Parallel Example: User Story 3

```bash
# Launch User Story 3 boundary tests together
Task: "Create classifier schema and endpoint contract tests including semantic version and unavailable reasons in tests/unit/test_classifier_schemas.py and tests/contract/test_classifier_endpoint_contract.py"
Task: "Create oversized-input and structured-422 validation tests in tests/integration/test_classifier_request_validation.py"
Task: "Create classifier lifespan, hash-mismatch, and import-side-effect tests in tests/integration/test_classifier_model_lifecycle.py and tests/test_import_side_effects.py"

# Launch User Story 3 lower-level implementation together
Task: "Create model-server classifier request, response, and error models in model_server/domain/classifier.py and model_server/domain/__init__.py"
Task: "Implement artifact loading, hash validation, and Vault-backed runtime setup in model_server/infra/classifier_loader.py and model_server/infra/__init__.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate `evals/classifier_eval_report.json` and the 25-example golden set
5. Stop and review classifier comparison results before moving on

### Incremental Delivery

1. Setup + Foundational → training/evaluation foundation ready
2. Add US1 → compare approaches and review the shared report
3. Add US2 → promote one artifact to reviewable, deployable status
4. Add US3 → expose safe model-server inference on top of the selected artifact
5. Finish Polish → docs and validation aligned with the delivered behavior

### Suggested MVP Scope

Implement **User Story 1 only** after Setup and Foundational work. It answers
the main phase question: which classifier approaches perform best on the shared
test split.

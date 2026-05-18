# Feature Specification: Issue Classification Track

**Feature Branch**: `003-issue-classification`  
**Created**: 2026-05-18  
**Status**: Draft  
**Input**: User description: "Phase 3, Build the issue classification track."

## Clarifications

### Session 2026-05-18

- Q: Which run logger backend should transformer fine-tuning use? → A: MLflow — self-hosted, MinIO-compatible artifact store, no external account required.
- Q: Which transformer base model should be used for fine-tuning? → A: `distilbert-base-uncased` — 66M params, CPU-feasible, fast enough for a bootcamp environment.
- Q: Which LLM provider should the LLM baseline use? → A: Azure OpenAI via LangChain with LangSmith tracing — consistent with Phases 3/4/5; LangChain fake adapter in automated tests.
- Q: What format should the model version field use in classifier prediction responses? → A: Semantic version string from the model card (e.g., `"1.0.0"`).
- Q: What is the maximum acceptable inference latency for the classifier endpoint? → A: 500ms p95 for a single classification request.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compare Classification Approaches (Priority: P1)

A developer can train or run three issue classification approaches on the same
dataset split and produce comparable results for `bug`, `feature`, `docs`, and
`question`.

**Why this priority**: The project must choose a classifier based on evidence.
Comparable results on the same held-out data are the minimum requirement before
any model can be served.

**Independent Test**: Run the classical baseline, fine-tuned transformer, and LLM
baseline against the same test split, then verify that a single evaluation report
contains all required metrics for all three approaches.

**Acceptance Scenarios**:

1. **Given** the Phase 2 dataset splits exist, **When** the developer evaluates
   all three classification approaches, **Then** each approach reports accuracy,
   macro-F1, per-class F1, confusion matrix, latency, and cost where applicable.
2. **Given** multiple approaches produce predictions, **When** the shared
   evaluator runs, **Then** all metrics are calculated from the same test split
   and are comparable in one report.
3. **Given** one optional external baseline cannot run because credentials are
   absent, **When** evaluation runs in local test mode, **Then** the pipeline
   reports the skipped or fake-provider baseline clearly without blocking tests
   that do not require real credentials.

---

### User Story 2 - Preserve Model Artifacts and Evidence (Priority: P2)

A reviewer can inspect saved model artifacts, model cards, hashes, training data
hashes, training run logs, training plots, MinIO artifact references, and
decisions to confirm that the selected deployment candidate is traceable and
evidence-based.

**Why this priority**: The transformer artifact and deployment choice must be
defensible. Without artifact metadata and hashes, future serving and CI gates
cannot prove what model is being used.

**Independent Test**: Train the transformer on the configured training data,
inspect the saved artifact directory, verify required files and hashes, and
confirm `DECISIONS.md` compares the three approaches with final metrics.

**Acceptance Scenarios**:

1. **Given** training completes for the transformer approach, **When** the
   artifact is inspected, **Then** model weights, tokenizer files,
   `model_card.json`, `metrics.json`, artifact SHA-256, training data hash,
   architecture name, hyperparameters, freeze policy, training run ID, run
   logger backend, training plot references, MinIO artifact or manifest
   reference, and final metrics are present.
2. **Given** an artifact hash is recorded, **When** the artifact is checked,
   **Then** the computed hash matches the model card.
3. **Given** all approach metrics exist, **When** a reviewer opens
   `DECISIONS.md`, **Then** the classifier comparison records the selected
   approach, alternatives, metrics, latency, cost where applicable, and known
   limitations.

---

### User Story 3 - Serve Classifier Predictions Safely (Priority: P3)

A maintainer or downstream chatbot phase can call the model-server classifier
endpoint with issue text and receive a typed prediction or a structured
unavailable-model error.

**Why this priority**: The selected classifier must be usable by later product
phases without loading models inside request handling or exposing unclear errors.

**Independent Test**: Start the model server with a valid classifier artifact,
call the classifier endpoint with test issue text, and verify the response
contains a valid label, optional confidence, and model version. Start without a
valid artifact and verify the structured unavailable error.

**Acceptance Scenarios**:

1. **Given** a valid classifier artifact is configured, **When** the model server
   starts, **Then** the classifier model loads during service lifespan and not at
   import time or per request.
2. **Given** issue text is submitted to the classifier endpoint, **When** the
   model is available, **Then** the response contains one project label,
   confidence if available, and model version.
3. **Given** the classifier artifact is missing or invalid, **When** the endpoint
   is called, **Then** the server returns a structured error instead of a stack
   trace or untyped failure.

### Edge Cases

- The dataset split files are missing, malformed, or have labels outside
  `bug`, `feature`, `docs`, and `question`: training and evaluation fail clearly
  before producing misleading metrics.
- A class is absent or rare in the test split: the report records the issue and
  still handles per-class metrics deterministically.
- The Azure OpenAI endpoint is unavailable, rate-limited, or credentials are absent locally: the baseline reports a controlled failure; automated tests always use a LangChain fake/mock provider and never require real credentials.
- Transformer training is interrupted or produces a partial artifact: partial
  artifacts are not treated as deployable and hash validation fails.
- A model artifact exists but hash verification fails: the model server refuses
  to serve it and reports a structured unavailable-model error.
- A classifier cannot produce confidence: the endpoint still returns a valid
  label and model version with confidence omitted or marked unavailable.
- Input text is empty, too large, or malformed: the endpoint returns a structured
  validation error.
- Training or evaluation is rerun on unchanged data: metrics and artifact
  metadata remain reproducible except for explicitly recorded timing fields.
- The run logger is unavailable: transformer training fails clearly before
  producing a deployable artifact instead of silently omitting run evidence.
- Training plots cannot be generated: the artifact is marked incomplete and is
  not deployable until the model card records plot references.
- MinIO artifact storage is unavailable in final-review mode: the artifact
  manifest upload fails clearly and the artifact is not marked final.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The classification track MUST use the same Phase 2 test split for
  the classical baseline, fine-tuned transformer, and LLM baseline.
- **FR-002**: The system MUST provide a command to train a classical ML baseline.
- **FR-003**: The system MUST provide a command to train a fine-tuned transformer
  classifier using `distilbert-base-uncased` as the base model. The architecture
  name `distilbert-base-uncased` MUST be recorded in the model card and MLflow
  run parameters.
- **FR-004**: The system MUST provide a command to run an LLM baseline evaluation
  on the same test split. The LLM baseline MUST use Azure OpenAI via the LangChain
  `AzureChatOpenAI` interface. LangSmith MUST be configured as the tracing backend
  for all LLM calls when a LangSmith API key is present in typed settings. In
  automated tests, a LangChain fake/mock provider MUST be used so no real Azure
  OpenAI credentials are required.
- **FR-005**: The system MUST provide one shared classifier evaluation module used
  to compare prediction outputs from all three approaches.
- **FR-006**: The evaluation report MUST include accuracy, macro-F1, per-class
  F1, confusion matrix, latency, and cost where applicable.
- **FR-007**: The project MUST include a 25-example classification golden set
  covering the four project labels.
- **FR-008**: Training and evaluation outputs MUST be saved as artifacts with
  stable, inspectable metadata.
- **FR-009**: The fine-tuned transformer artifact MUST include model weights,
  tokenizer files, `model_card.json`, `metrics.json`, artifact SHA-256, training
  data hash, architecture name, hyperparameters, freeze policy, and final metrics.
- **FR-009a**: Transformer fine-tuning MUST use MLflow as the run logger. MLflow
  MUST record a run ID, the `mlflow` backend name, safe hyperparameters, metrics,
  artifact references, and final run status. The MLflow tracking server MUST be
  included in the local Compose stack and MUST use MinIO as its artifact store.
- **FR-009b**: Transformer training MUST save training plots and record plot
  artifact references in the model card.
- **FR-009c**: The selected classifier artifact or a manifest for it MUST be
  stored in MinIO for final review and startup validation.
- **FR-010**: The model artifact hash MUST be computable and MUST match the value
  recorded in the model card before the artifact is considered deployable.
- **FR-011**: `DECISIONS.md` MUST compare the classical baseline, fine-tuned
  transformer, and LLM baseline using the required metrics, latency, cost where
  applicable, limitations, and selected deployment candidate.
- **FR-012**: The model server MUST expose a classifier inference endpoint.
- **FR-013**: The model server MUST load the selected classifier during service
  lifespan and MUST NOT load it at import time or per request.
- **FR-014**: Classifier responses MUST return a typed prediction containing a
  label, confidence when available, and model version. The model version MUST be
  a semantic version string (e.g., `"1.0.0"`) read from the `model_card.json`
  of the loaded artifact and returned verbatim in every prediction response.
- **FR-015**: The only valid prediction labels are `bug`, `feature`, `docs`, and
  `question`.
- **FR-016**: The model server MUST return a structured error when the model is
  unavailable, missing, invalid, or fails hash verification.
- **FR-017**: Tests MUST cover evaluation metric calculation, required report
  shape, model artifact hash validation, run-log/model-card fields, MinIO
  manifest metadata, and model-server response schema.
- **FR-018**: This phase MUST NOT implement RAG, chatbot orchestration, widget
  behavior, or production auth flows.

### Constitution Alignment *(mandatory)*

- **Phase Scope**: This is `PLAN.md` Phase 3 only. It compares issue
  classification approaches, creates classifier artifacts, records evidence, and
  exposes the classifier model-server endpoint. RAG, chatbot orchestration,
  widget work, and unrelated product features are out of scope.
- **Architecture Boundaries**: Training and evaluation belong in scripts and
  shared evaluation modules. Runtime serving belongs in the model server. API
  routes must stay thin and must not load models, train models, or calculate
  metrics directly.
- **Security And Redaction**: Azure OpenAI endpoint, API key, and LangSmith API
  key are optional local secrets loaded through typed settings only. Tests MUST
  use LangChain fake/mock providers so no real credentials are required. Reports,
  logs, and LangSmith traces must not contain raw secret values or unnecessary
  full issue payload dumps.
- **Observability And Errors**: Training/evaluation commands must produce clear
  progress and failure messages. Model-server prediction requests must use
  structured errors and include request correlation where the foundation supports
  it.
- **Evidence And Evals**: This phase is governed by evidence. Classifier choice
  must be backed by comparable metrics, final artifacts, hashes, training data
  hash, run logs, training plots, MinIO artifact references, a golden set, and
  `DECISIONS.md`.
- **Critical Tests**: Critical tests must cover metric calculations, prediction
  schema, unavailable-model error schema, artifact hash validation, model loading
  lifecycle rules, and no committed real secrets.

### Key Entities *(include if feature involves data)*

- **Classifier Training Dataset**: The Phase 2 train/validation/test records used
  to train and compare approaches.
- **Classification Golden Set**: A 25-example labeled set used as a stable
  sanity/evaluation fixture across the four project labels.
- **Classifier Approach**: One of classical baseline, fine-tuned transformer, or
  LLM baseline, with configuration, predictions, metrics, latency, and cost where
  applicable.
- **Prediction Record**: One classifier output for one issue, including record
  identifier, predicted label, optional confidence, model version, latency, and
  source approach.
- **Evaluation Report**: Comparable metrics for all approaches, including
  accuracy, macro-F1, per-class F1, confusion matrix, latency, and cost where
  applicable.
- **Transformer Artifact**: Saved model package containing weights, tokenizer
  files, model card, metrics, artifact hash, training data hash, architecture
  name, hyperparameters, freeze policy, run logger metadata, training plot
  references, MinIO reference, and final metrics.
- **Training Run Record**: MLflow run record for transformer fine-tuning,
  including MLflow run ID, `mlflow` as the logger backend, parameters, metrics,
  status, and artifact references stored in MinIO via the MLflow artifact store.
- **Model Card**: Artifact metadata document that identifies the transformer
  model, data used, hash values, metrics, intended use, limitations, and serving
  version.
- **Classifier Inference Request**: Input payload for issue classification,
  including title/body/comments text as available.
- **Classifier Prediction Response**: Typed model-server response containing one
  project label, optional confidence, and model version as a semantic version
  string (e.g., `"1.0.0"`) sourced from the loaded artifact's `model_card.json`.
- **Classifier Decision Record**: `DECISIONS.md` section comparing approaches and
  selecting the deployment candidate.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The classical baseline, fine-tuned transformer, and LLM baseline
  each produce predictions for the same test split or a documented controlled
  skip for an unavailable optional external provider.
- **SC-002**: One evaluation report contains 100% of required metrics for each
  completed approach.
- **SC-003**: The 25-example golden set contains at least one example for each of
  the four project labels and exactly 25 labeled examples.
- **SC-004**: The fine-tuned transformer artifact contains all required files and
  metadata fields, including run logger metadata and training plot references.
- **SC-005**: Artifact hash verification succeeds for the deployable transformer
  artifact and fails for a deliberately modified artifact in tests.
- **SC-005a**: The selected classifier artifact or manifest is stored in MinIO
  and referenced by the model card before final review.
- **SC-006**: `DECISIONS.md` records the selected classifier approach with metrics,
  latency, cost where applicable, limitations, and rejected alternatives.
- **SC-007**: The classifier endpoint returns a valid project label and model
  version for a valid test input when a deployable model is configured. End-to-end
  inference latency (request received to response sent) MUST be ≤ 500ms at p95
  for a single classification request under normal load.
- **SC-008**: The classifier endpoint returns a structured unavailable-model error
  when no valid model artifact is configured.
- **SC-009**: Automated tests cover metric calculation and model-server response
  schemas without requiring real LLM provider credentials.

## Assumptions

- Phase 2 has produced compatible dataset splits before classifier training and
  evaluation are treated as complete.
- The fine-tuned transformer uses `distilbert-base-uncased` (66M parameters), which is CPU-feasible for a bootcamp environment. Specific hyperparameters (learning rate, batch size, epochs, freeze policy) will be finalized during planning.
- LLM baseline evaluation may use a fake provider in automated tests and a real
  provider only when local credentials are available.
- Latency values are measured as part of evaluation and reported with enough
  context to compare approaches fairly.
- Cost is required for the LLM baseline and may be recorded as zero or not
  applicable for local classical and transformer approaches.

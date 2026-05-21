# Command Contracts: Issue Classification Track

## Shared Requirements

- Commands run from the repository root.
- Commands consume Phase 2 dataset splits and preserve the shared test split.
- Commands write JSON/JSONL predictions, metrics, reports, model cards, or
  artifact metadata.
- Commands fail non-zero for missing required datasets, invalid labels,
  malformed prediction files, MLflow logging failures, or hash mismatches.
- Commands must not print or persist real provider credentials.
- Commands must redact provider secrets and oversized raw issue payloads before
  MLflow metadata, LangSmith traces, model cards, manifests, or reports are
  written.
- Deployable transformer runs require a completed MLflow run, training plots,
  model-card references to those plots, and a MinIO artifact or manifest
  reference.

## `python scripts/train_classical_classifier.py`

**Purpose**: Train the classical TF-IDF + Logistic Regression baseline.

**Inputs**:
- Phase 2 train and validation split files.
- Safe classifier configuration.

**Outputs**:
- Classical artifact directory under `artifacts/classifiers/classical/`.
- Prediction and metrics JSON artifacts.

**Contract**:
- Uses only labels `bug`, `feature`, `docs`, and `question`.
- Saves enough metadata to reproduce the run.
- Does not train inside any request path.

## `python scripts/train_transformer_classifier.py`

**Purpose**: Fine-tune the `distilbert-base-uncased` transformer classifier.

**Inputs**:
- Phase 2 train and validation split files.
- Safe transformer training configuration.
- Reachable MLflow tracking configuration.
- Reachable MinIO artifact-store configuration.

**Outputs**:
- Transformer artifact directory under `artifacts/classifiers/transformer/`.
- `model_card.json`.
- `metrics.json`.
- tokenizer files.
- model weights, preferably safetensors.
- MLflow run record with run ID and final status.
- training plots.
- MinIO artifact or manifest reference for the selected artifact.

**Contract**:
- Records architecture name, hyperparameters, freeze policy, training-data hash,
  final metrics, artifact SHA-256, MLflow run ID, `mlflow` backend name,
  training-plot references, and MinIO reference.
- Produces a deployable artifact only when all required files are present and
  hash validation succeeds.
- Fails clearly if MLflow tracking cannot record run metadata or if required
  MinIO artifact persistence is unavailable for final-review status.

## `python scripts/run_llm_classifier_baseline.py`

**Purpose**: Run the LLM baseline against the shared test split.

**Inputs**:
- Phase 2 test split.
- Prompt/configuration for four-label issue classification.
- Optional local Azure OpenAI credentials.
- Optional LangSmith API key for tracing.
- Fake/mock provider mode for tests.

**Outputs**:
- LLM baseline predictions under `artifacts/classifiers/llm_baseline/`.
- Latency and cost summary where applicable.

**Contract**:
- Uses Azure OpenAI through LangChain `AzureChatOpenAI` for real provider runs.
- Resolves real Azure OpenAI and LangSmith credentials through Vault-backed
  runtime settings, not committed `.env` secrets.
- Uses a fake/mock LangChain provider in automated tests and credential-less
  local runs.
- Uses the same test records as the other approaches.
- Records skipped-provider status explicitly when a real provider run is not
  available.

## `python scripts/evaluate_classifiers.py`

**Purpose**: Compare all approaches with one shared evaluator.

**Inputs**:
- Shared test split.
- Prediction files from classical, transformer, and LLM baseline approaches.
- Optional golden set.

**Outputs**:
- `evals/classifier_eval_report.json`

**Report Contract**:
- Includes accuracy, macro-F1, per-class F1, confusion matrix, latency, and
  cost where applicable.
- Uses a stable label order: `bug`, `feature`, `docs`, `question`.
- Records dataset test hash, controlled skips, and limitations.

**Failure Behavior**:
- Unknown labels, missing test records, or mismatched test hashes fail
  validation.
- A controlled skipped approach remains visible in the report and does not get
  silently dropped.

## `python scripts/upload_classifier_artifact_manifest.py`

**Purpose**: Store the selected classifier artifact or a manifest in MinIO for
final review and later startup validation.

**Inputs**:
- Selected classifier artifact directory.
- Model card and computed artifact hash.
- MinIO bucket/settings from typed configuration.

**Outputs**:
- MinIO object or manifest reference recorded back into the model card or safe
  artifact metadata.

**Contract**:
- Uploads or manifests only hash-validated deployable artifacts.
- Never uploads secrets, provider credentials, or incomplete run state.
- Fails non-zero when MinIO is required for final review and unavailable.

## `python scripts/measure_classifier_latency.py`

**Purpose**: Measure classifier endpoint latency for the Phase 3 success
criterion.

**Inputs**:
- Running model-server with a preloaded deployable classifier artifact.
- Representative request payloads drawn from the Phase 2 classifier text shape.

**Outputs**:
- Latency summary including p50 and p95 for 30 sequential warm requests.

**Contract**:
- Measures request-received to response-sent latency only after model startup is
  complete.
- Uses a warm, single-process model-server and documents that assumption in the
  output.
- Fails non-zero when the model-server is unavailable or returns unexpected
  response shapes.

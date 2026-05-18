# Command Contracts: Issue Classification Track

## Shared Requirements

- Commands run from the repository root.
- Commands consume Phase 2 dataset splits.
- Commands write JSON predictions, metrics, reports, model cards, or artifacts.
- Commands fail non-zero for missing required datasets, invalid labels, malformed
  prediction files, or hash mismatches.
- Commands must not print or write real provider credentials.
- Deployable transformer runs must include a completed run-log record, training
  plots, model-card references to those artifacts, and a MinIO artifact or
  manifest reference.

## `python scripts/train_classical_classifier.py`

**Purpose**: Train the classical baseline.

**Inputs**:
- Phase 2 train and validation split files.
- Classifier configuration.

**Outputs**:
- Classical model artifact directory under `artifacts/classifiers/classical/`.
- Prediction and metrics JSON artifacts.

**Contract**:
- Uses only labels `bug`, `feature`, `docs`, and `question`.
- Saves enough metadata to reproduce the run.
- Does not train in any request path.

## `python scripts/train_transformer_classifier.py`

**Purpose**: Fine-tune the lightweight transformer classifier.

**Inputs**:
- Phase 2 train and validation split files.
- Transformer training configuration.

**Outputs**:
- Transformer artifact directory under `artifacts/classifiers/transformer/`.
- `model_card.json`
- `metrics.json`
- run logger record with run ID and backend
- training plots
- MinIO artifact manifest or uploaded artifact reference
- tokenizer files
- model weights, preferably safetensors

**Contract**:
- Records architecture name, hyperparameters, freeze policy, training data hash,
  final metrics, artifact SHA-256, run ID, run logger backend, training plot
  references, and MinIO reference.
- Produces a deployable artifact only when all required files are present and hash
  validation succeeds.
- Fails clearly if the configured run logger cannot write run metadata or if
  final-review MinIO manifest storage is unavailable.

## `python scripts/upload_classifier_artifact_manifest.py`

**Purpose**: Store the selected classifier artifact or manifest in MinIO for
final review and startup validation.

**Inputs**:
- Selected classifier artifact directory.
- Model card and computed artifact hash.
- MinIO bucket/settings from typed configuration.

**Outputs**:
- MinIO object or manifest reference recorded back into the model card or a
  safe artifact metadata file.

**Contract**:
- Uploads or manifests only hash-validated deployable artifacts.
- Does not upload raw secrets or provider credentials.
- Fails non-zero when MinIO is required for final review and unavailable.

## `python scripts/run_llm_classifier_baseline.py`

**Purpose**: Run the LLM baseline against the same test split.

**Inputs**:
- Phase 2 test split.
- Prompt/configuration for four-label issue classification.
- Optional local provider credentials or fake provider mode.

**Outputs**:
- LLM baseline predictions under `artifacts/classifiers/llm_baseline/`.
- Latency and cost summary where applicable.

**Contract**:
- Uses the same test records as the other approaches.
- Does not require real credentials in automated tests.
- Records skipped-provider status explicitly when real provider mode is
  unavailable.

## `python scripts/evaluate_classifiers.py`

**Purpose**: Compare all approaches with one shared evaluator.

**Inputs**:
- Test split.
- Prediction files from classical, transformer, and LLM baseline approaches.
- Optional golden set.

**Outputs**:
- `evals/classifier_eval_report.json`

**Report Contract**:
- Includes accuracy, macro-F1, per-class F1, confusion matrix, latency, and cost
  where applicable.
- Uses a stable label order: `bug`, `feature`, `docs`, `question`.
- Records dataset test hash and limitations.

**Failure Behavior**:
- Prediction files with unknown labels, missing test records, or mismatched test
  hashes fail validation.

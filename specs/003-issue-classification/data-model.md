# Data Model: Issue Classification Track

## Classifier Training Dataset

**Purpose**: Phase 2 train, validation, and test records consumed by all three
classification approaches.

**Fields**:
- `record_id`: stable issue record identifier.
- `split`: `train`, `validation`, or `test`.
- `text_for_classifier`: normalized issue text used for training or inference.
- `label_mapped`: one of `bug`, `feature`, `docs`, `question`.
- `source_url`: issue source URL.

**Validation Rules**:
- Every approach must use the same `test` split.
- Labels outside the four project labels fail validation.
- Missing or empty `text_for_classifier` is rejected before training/eval.

## Classification Golden Set

**Purpose**: Stable 25-example sanity and regression fixture across the four
project labels.

**Fields**:
- `id`: stable example identifier.
- `title`: issue title.
- `body`: issue body.
- `comments`: optional comments text.
- `label`: expected project label.
- `source_url`: optional source traceability link.

**Validation Rules**:
- Exactly 25 examples.
- At least one example for each label.
- Labels must be one of `bug`, `feature`, `docs`, `question`.

## Classifier Approach

**Purpose**: One comparable classifier approach included in the report.

**Fields**:
- `name`: `classical`, `transformer`, or `llm_baseline`.
- `version`: model version, prompt version, or baseline config version.
- `status`: `completed`, `skipped`, or `failed`.
- `config`: safe run configuration with no secrets.
- `provider_backend`: optional provider identifier such as `sklearn`,
  `transformers`, or `azure_openai`.
- `tracing_backend`: optional trace backend label such as `langsmith`.
- `secret_source`: optional safe label such as `vault` or `fake_provider`.
- `artifact_path`: optional local artifact directory.
- `predictions_path`: prediction JSONL path.
- `metrics_path`: metrics JSON path.
- `latency_summary`: aggregate latency values.
- `cost_summary`: cost values where applicable.
- `run_id`: optional training/eval run identifier.
- `run_logger_backend`: optional run logger backend label.
- `minio_reference`: optional artifact or manifest URI for final review.

**Validation Rules**:
- Approach names are fixed for comparison.
- `status=completed` requires predictions, metrics, and latency summary.
- `status=skipped` requires a documented skip reason.
- Deployable trained approaches require run metadata and MinIO evidence.
- Real provider runs require `secret_source=vault` or an equivalent safe
  Vault-resolved marker, never raw secrets in config.

## Prediction Record

**Purpose**: One prediction for one dataset record.

**Fields**:
- `record_id`: source test record identifier.
- `approach`: classifier approach name.
- `label_true`: expected label.
- `label_predicted`: predicted project label.
- `confidence`: optional confidence score.
- `model_version`: model or prompt/config version.
- `latency_ms`: prediction latency in milliseconds.
- `cost_usd`: optional per-record or amortized LLM cost contribution.

**Validation Rules**:
- `label_predicted` must be one of the four project labels.
- `record_id` must exist in the shared test split.
- `cost_usd` is required only for real LLM provider runs.

## Evaluation Report

**Purpose**: One comparable report spanning all approaches.

**Fields**:
- `dataset_test_hash`: hash of the shared test split.
- `label_order`: stable label order for all matrices and per-class metrics.
- `approaches`: per-approach metric blocks.
- `skipped_approaches`: optional array of skipped approach records.
- `accuracy`: per-approach accuracy.
- `macro_f1`: per-approach macro-F1.
- `per_class_f1`: per-label F1 values for each approach.
- `confusion_matrix`: matrix for each approach using the stable label order.
- `latency`: per-approach latency summary including p50 and p95 where measured.
- `cost`: per-approach cost where applicable.
- `generated_at`: report timestamp.
- `limitations`: known limitations or controlled skips.

**Validation Rules**:
- All completed approaches must share the same `dataset_test_hash`.
- `label_order` must remain `bug`, `feature`, `docs`, `question`.
- Skipped approaches must be recorded explicitly, not silently omitted.

## Transformer Artifact

**Purpose**: Deployable fine-tuned transformer package.

**Fields**:
- `artifact_dir`: local artifact directory.
- `model_weights`: safetensors or documented fallback.
- `tokenizer_files`: tokenizer files required for inference.
- `model_card_path`: `model_card.json`.
- `metrics_path`: `metrics.json`.
- `artifact_sha256`: hash over deployable artifact contents.
- `training_data_hash`: hash of the training split used.
- `architecture_name`: `distilbert-base-uncased`.
- `hyperparameters`: safe training configuration.
- `freeze_policy`: frozen/unfrozen layer policy.
- `final_metrics`: final validation/test metrics.
- `training_run_id`: MLflow run identifier.
- `run_logger_backend`: `mlflow`.
- `training_plot_paths`: references to saved training plots.
- `minio_reference`: MinIO artifact or manifest URI.

**Validation Rules**:
- Artifact hash must match the model card before the artifact is deployable.
- Partial artifacts are never deployable.
- MLflow run metadata, plot references, and MinIO reference are required for
  final-review status.

## Training Run Record

**Purpose**: Evidence record emitted by the transformer training run logger.

**Fields**:
- `run_id`: MLflow run identifier.
- `backend`: fixed logger backend label `mlflow`.
- `tracking_uri`: safe MLflow tracking URI or logical backend reference.
- `artifact_uri`: MLflow artifact URI pointing to MinIO-backed artifacts.
- `started_at`: run start timestamp.
- `completed_at`: run completion timestamp when available.
- `status`: `completed`, `failed`, or `interrupted`.
- `parameters`: safe hyperparameters and freeze policy.
- `metrics`: training and validation metrics by epoch or step.
- `artifact_references`: model, metrics, plots, and manifest references.
- `redaction_applied`: boolean showing telemetry/artifact metadata was redacted
  before persistence.

**Validation Rules**:
- Run records must not contain secrets or full issue payloads.
- Deployable transformer artifacts require a completed MLflow run.
- Failed or interrupted runs cannot be promoted.
- `redaction_applied` must be true for persisted telemetry records.

## Classifier Artifact Manifest

**Purpose**: Portable record stored in MinIO for the selected classifier.

**Fields**:
- `model_version`: semantic version from `model_card.json`.
- `approach`: selected classifier approach.
- `artifact_sha256`: verified artifact hash.
- `training_data_hash`: verified training-data hash.
- `source_artifact_path`: local artifact directory used to build the manifest.
- `minio_object_key`: MinIO object path or URI.
- `uploaded_at`: upload timestamp.

**Validation Rules**:
- Manifest creation requires a hash-validated artifact.
- Manifest contents must agree with the model card.
- Manifest must not contain secrets.

## Model Card

**Purpose**: Metadata record for the deployable transformer artifact.

**Fields**:
- `model_version`: semantic version string.
- `architecture_name`: model architecture.
- `training_data_hash`: training split hash.
- `artifact_sha256`: artifact hash.
- `hyperparameters`: training settings.
- `freeze_policy`: layer freeze policy.
- `metrics`: final metrics.
- `training_run_id`: MLflow run identifier.
- `run_logger_backend`: `mlflow`.
- `training_plot_paths`: saved plot references.
- `minio_reference`: MinIO artifact or manifest reference.
- `intended_use`: issue classification.
- `limitations`: known limitations.
- `redaction_applied`: boolean indicating metadata was redacted before write.

**Validation Rules**:
- Must match the saved artifact contents.
- Must not contain secrets.
- Must exist before the artifact is considered deployable.
- `redaction_applied` must be true for deployable artifacts.

## Classifier Inference Request

**Purpose**: Input payload for the model-server classifier endpoint.

**Fields**:
- `title`: issue title.
- `body`: issue body.
- `comments`: optional issue comments.

**Validation Rules**:
- At least one text field must be non-empty.
- `title` must be `<= 512` characters.
- `body` must be `<= 16,000` characters.
- `comments` may contain at most `100` items.
- Each comment item must be `<= 4,000` characters.
- Oversized or malformed inputs return a structured validation error.
- Full raw text is not logged.

## Classifier Prediction Response

**Purpose**: Typed classifier inference result returned by the model server.

**Fields**:
- `label`: one of `bug`, `feature`, `docs`, `question`.
- `confidence`: optional confidence score.
- `model_version`: semantic version from the loaded model card.
- `request_id`: request identifier when available.

**Validation Rules**:
- `label` must be valid.
- `model_version` is required for every successful response.
- Confidence may be omitted when the chosen approach cannot produce it.

## Classifier Unavailable Error

**Purpose**: Structured error returned when inference cannot use a valid model.

**Fields**:
- `code`: stable error code such as `classifier_model_unavailable`.
- `message`: human-readable summary.
- `request_id`: request identifier when available.
- `details.reason`: one of `missing_artifact`, `invalid_artifact`,
  `hash_mismatch`, or `startup_load_failed`.

**Validation Rules**:
- Error payload must not leak filesystem secrets or stack traces.
- Hash mismatch and missing artifact remain 503-class unavailable errors, not
  raw runtime failures.

## Classifier Decision Record

**Purpose**: `DECISIONS.md` section selecting the deployment candidate.

**Fields**:
- `selected_approach`: chosen classifier approach.
- `metrics_comparison`: required metrics for all completed approaches.
- `latency_comparison`: latency summary including endpoint p95 evidence.
- `cost_comparison`: cost where applicable.
- `artifact_reference`: selected artifact path, hash, and MinIO reference.
- `limitations`: known limitations.
- `alternatives_considered`: rejected approaches and rationale.

**Validation Rules**:
- Must cite the shared evaluation report.
- Must explain why the selected approach is acceptable.
- Must be updated before the phase is complete.

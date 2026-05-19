# Data Model: Issue Classification Track

## Classifier Training Dataset

**Purpose**: Phase 2 train, validation, and test records consumed by the
classification track.

**Fields**:
- `record_id`: stable issue record identifier.
- `split`: `train`, `validation`, or `test`.
- `text_for_classifier`: issue text used for classification.
- `label_mapped`: one of `bug`, `feature`, `docs`, `question`.
- `source_url`: issue source URL.

**Validation Rules**:
- All approaches must use the same test split.
- Labels outside the four project labels fail validation.
- Empty or missing classifier text is rejected or reported before training.

## Classification Golden Set

**Purpose**: Stable 25-example sanity set for classifier behavior.

**Fields**:
- `id`: stable example identifier.
- `title`: issue title.
- `body`: issue body.
- `comments`: optional comments text.
- `label`: expected project label.
- `source_url`: optional source traceability.

**Validation Rules**:
- Exactly 25 examples.
- At least one example per project label.
- Labels must be one of `bug`, `feature`, `docs`, `question`.

## Classifier Approach

**Purpose**: One comparable classifier approach.

**Fields**:
- `name`: `classical`, `transformer`, or `llm_baseline`.
- `version`: model or prompt/config version.
- `config`: safe run configuration.
- `artifact_path`: optional artifact directory.
- `predictions_path`: prediction JSONL path.
- `metrics_path`: metrics JSON path.
- `latency_summary`: aggregate latency values.
- `cost_summary`: cost values where applicable.
- `run_id`: optional run logger identifier for trained approaches.
- `run_logger_backend`: optional safe label for the logger used.
- `minio_reference`: optional artifact or manifest reference for final review.

**Validation Rules**:
- Approach names are fixed for comparison.
- Configuration must not contain secrets.
- Predictions must reference the same test records.
- Deployable trained approaches must include run logger metadata and MinIO
  artifact or manifest references.

## Prediction Record

**Purpose**: One classifier output for one dataset record.

**Fields**:
- `record_id`: source test record identifier.
- `approach`: classifier approach name.
- `label_true`: expected label.
- `label_predicted`: predicted project label.
- `confidence`: optional confidence score.
- `model_version`: model or baseline version.
- `latency_ms`: prediction latency.
- `cost_usd`: optional LLM cost.

**Validation Rules**:
- Predicted labels must be one of the four project labels.
- `record_id` must exist in the selected test split.
- Cost is required for real LLM baseline runs and omitted or zero for local
  approaches.

## Evaluation Report

**Purpose**: Comparable metrics for all approaches.

**Fields**:
- `dataset_test_hash`: hash of the shared test split.
- `approaches`: metrics grouped by approach.
- `accuracy`: per-approach accuracy.
- `macro_f1`: per-approach macro-F1.
- `per_class_f1`: per-label F1 values.
- `confusion_matrix`: matrix with label ordering.
- `latency`: per-approach latency summary.
- `cost`: per-approach cost where applicable.
- `generated_at`: report timestamp.
- `limitations`: known limitations.

**Validation Rules**:
- All completed approaches must use the same `dataset_test_hash`.
- Label order for confusion matrices must be stable.
- Missing optional real LLM credentials must be represented as a controlled skip
  or fake-provider test mode, not silent omission.

## Transformer Artifact

**Purpose**: Deployable fine-tuned transformer package.

**Fields**:
- `model_weights`: safetensors or documented alternative.
- `tokenizer_files`: tokenizer files required for inference.
- `model_card`: `model_card.json`.
- `metrics`: `metrics.json`.
- `artifact_sha256`: hash over deployable artifact contents.
- `training_data_hash`: hash of training data used.
- `architecture_name`: model architecture identifier.
- `hyperparameters`: training configuration.
- `freeze_policy`: frozen/unfrozen layer policy.
- `final_metrics`: final evaluation metrics.
- `training_run_id`: run logger identifier.
- `run_logger_backend`: safe run logger backend label.
- `training_plot_paths`: references to saved training plots.
- `minio_reference`: MinIO artifact or manifest reference.

**Validation Rules**:
- Artifact hash must match the model card.
- Partial artifacts are not deployable.
- Training data hash must be present before serving.
- Run logger metadata, training plot references, and MinIO reference are required
  before final review.

## Training Run Record

**Purpose**: Evidence record produced by the transformer training run logger.

**Fields**:
- `run_id`: stable run logger identifier.
- `backend`: safe logger backend label, such as local MLflow-compatible files or
  structured JSONL run logs.
- `started_at`: run start timestamp.
- `completed_at`: run completion timestamp when available.
- `status`: `completed`, `failed`, or `interrupted`.
- `parameters`: safe hyperparameters and freeze policy.
- `metrics`: training and validation metrics by step or epoch.
- `artifact_references`: saved model, metrics, plots, and manifest references.

**Validation Rules**:
- Run records must not contain secrets or raw issue payloads.
- A deployable transformer artifact requires a completed run record.
- Failed or interrupted runs cannot be marked deployable.

## Model Card

**Purpose**: Metadata record for the transformer artifact.

**Fields**:
- `model_version`: serving version.
- `architecture_name`: model architecture.
- `training_data_hash`: training split hash.
- `artifact_sha256`: artifact hash.
- `hyperparameters`: training settings.
- `freeze_policy`: layer freeze policy.
- `metrics`: final metrics.
- `training_run_id`: run logger identifier.
- `run_logger_backend`: safe logger backend label.
- `training_plot_paths`: saved plot references.
- `minio_reference`: MinIO artifact or manifest reference.
- `intended_use`: issue classification.
- `limitations`: known limitations.

**Validation Rules**:
- Must match saved artifact contents.
- Must not contain secrets.
- Must be present for deployable transformer artifacts.

## Classifier Inference Request

**Purpose**: Input payload for the model-server classifier endpoint.

**Fields**:
- `title`: issue title.
- `body`: issue body.
- `comments`: optional issue comments.

**Validation Rules**:
- At least one text field must be non-empty.
- Oversized inputs return a structured validation error.
- Input is not logged wholesale.

## Classifier Prediction Response

**Purpose**: Typed classifier inference result.

**Fields**:
- `label`: one of `bug`, `feature`, `docs`, `question`.
- `confidence`: optional confidence score.
- `model_version`: loaded classifier version.
- `request_id`: request identifier when available.

**Validation Rules**:
- Label must be valid.
- Model version is required for successful predictions.
- Confidence may be omitted when unavailable.

## Classifier Decision Record

**Purpose**: `DECISIONS.md` section selecting the deployment candidate.

**Fields**:
- `selected_approach`: chosen classifier approach.
- `metrics_comparison`: required metrics for all completed approaches.
- `latency_comparison`: latency summary.
- `cost_comparison`: cost where applicable.
- `artifact_reference`: selected artifact path and hash.
- `limitations`: known limitations.
- `alternatives_considered`: rejected approaches and rationale.

**Validation Rules**:
- Must cite the evaluation report.
- Must explain why selected approach is acceptable.
- Must be updated before the phase is considered complete.

# Quickstart: Issue Classification Track

## Prerequisites

- Phase 2 dataset splits already exist and contain only `bug`, `feature`,
  `docs`, and `question`.
- The local environment is installed through `uv` or an equivalent Python 3.11+
  environment.
- Real Azure OpenAI or LangSmith credentials are optional and, when used, must
  resolve through Vault bootstrap settings. Automated tests must work with
  fake/mock providers only.

## Start Required Local Services

Start the services needed for artifact logging and storage before transformer
training:

```bash
docker compose up -d minio mlflow
```

Expected result: MinIO is reachable as the artifact store and the self-hosted
MLflow tracking server is reachable for transformer training runs.

## Train The Classical Baseline

Run:

```bash
python scripts/train_classical_classifier.py
```

Expected result: a classical model artifact, predictions, and metrics are
written under `artifacts/classifiers/classical/`.

## Train The Transformer Classifier

Run:

```bash
python scripts/train_transformer_classifier.py
```

Expected result: `artifacts/classifiers/transformer/` contains model weights,
tokenizer files, `model_card.json`, `metrics.json`, training-data hash, artifact
SHA-256, architecture name, hyperparameters, freeze policy, MLflow run ID,
`mlflow` as the logger backend, training plots, and final metrics. The MLflow
run references MinIO-backed artifacts.

## Run The LLM Baseline

Run:

```bash
python scripts/run_llm_classifier_baseline.py
```

Expected result: the baseline uses Azure OpenAI through LangChain
`AzureChatOpenAI` when local credentials are configured. In tests or local fake
mode it uses a fake/mock LangChain provider instead. Predictions, latency, and
cost shape are written under `artifacts/classifiers/llm_baseline/`. When a
Vault-resolved LangSmith key is available, tracing is enabled with redacted
metadata only.

## Compare Classifiers

Run:

```bash
python scripts/evaluate_classifiers.py
```

Expected result: `evals/classifier_eval_report.json` compares completed
approaches on the same test split using accuracy, macro-F1, per-class F1,
confusion matrix, latency, and cost where applicable. Controlled skips are
listed explicitly.

## Validate The Golden Set

Verify `evals/classification_golden_set.jsonl` contains exactly 25 examples and
at least one example per project label.

Expected result: golden-set validation passes and remains reusable in CI or
future regression checks.

## Upload The Selected Classifier Artifact Or Manifest

Run:

```bash
python scripts/upload_classifier_artifact_manifest.py
```

Expected result: only a hash-validated deployable artifact or manifest is
stored in MinIO, and the resulting MinIO reference is recorded in the selected
model card or safe artifact metadata.

## Validate The Transformer Artifact

Check the artifact hash, model-card fields, MLflow run metadata, plot
references, and MinIO reference.

Expected result: the computed SHA-256 matches the model card. Missing MLflow
evidence, missing plot references, or missing MinIO reference keeps the
artifact out of final-review/deployable status.

## Measure Endpoint Latency

Run:

```bash
python scripts/measure_classifier_latency.py
```

Expected result: the script measures request-received to response-sent latency
for 30 sequential representative requests against a warm, preloaded
single-process model-server and reports p50/p95 values used for `SC-007`.

## Serve Classifier Predictions

Start the model server with a valid selected classifier artifact, then call the
classifier endpoint with issue title/body/comments text.

Expected result: the endpoint returns a typed label from `bug`, `feature`,
`docs`, or `question`, optional confidence, and the semantic `model_version`
from `model_card.json`. Under normal load, p95 end-to-end latency for a single
request is 500ms or better using the measurement method above.

Start the model server without a valid artifact or with a hash mismatch.

Expected result: the endpoint returns a structured unavailable-model error and
no stack trace.

## Run The Critical Tests

Run:

```bash
pytest tests/unit/test_classifier_metrics.py \
  tests/unit/test_classifier_artifact_hash.py \
  tests/unit/test_classifier_model_card.py \
  tests/unit/test_classifier_run_metadata.py \
  tests/unit/test_classifier_redaction.py \
  tests/contract/test_classifier_endpoint_contract.py \
  tests/integration/test_llm_classifier_fake_provider.py \
  tests/integration/test_classifier_request_validation.py \
  tests/integration/test_classifier_model_lifecycle.py
```

Expected result: metric calculations, artifact hash validation, semantic model
version behavior, MLflow/MinIO metadata requirements, redaction requirements,
endpoint schema, and lifespan loading rules all pass without real provider
credentials.

## Update Decisions

Update `DECISIONS.md` with:

- classical baseline metrics
- transformer metrics and artifact hash
- MLflow run ID, run logger backend, and training-plot references
- MinIO artifact or manifest reference
- LLM baseline metrics, latency, and cost where applicable
- selected classifier approach and rationale
- known limitations and rejected alternatives

Expected result: a reviewer can verify that the deployment choice is
evidence-based and traceable.

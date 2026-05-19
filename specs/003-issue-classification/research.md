# Research: Issue Classification Track

## Decision: Use TF-IDF plus Logistic Regression for the classical baseline

**Rationale**: A TF-IDF text representation with a logistic regression classifier
is fast, explainable, strong enough as a baseline, and can expose class
probabilities for confidence-like outputs when needed. It is easy to train on a
bootcamp machine and simple to compare with transformer and LLM results.

**Alternatives considered**:
- Linear SVM: strong baseline, but confidence requires calibration.
- Naive Bayes: very fast, but often weaker for mixed issue text and less useful
  as the main classical comparison.

## Decision: Use `distilbert-base-uncased` as the default transformer encoder

**Rationale**: DistilBERT is lightweight enough for the project while still
representing a real transformer fine-tuning workflow. The implementation can
allow a config override for a similarly small encoder, but the default remains
explicit for reproducibility.

**Alternatives considered**:
- Larger BERT/RoBERTa models: rejected because they increase training cost and
  are harder to defend for a bootcamp project.
- Tiny random models only: useful for tests, but not a credible final
  transformer comparison.

## Decision: Save transformer weights with safetensors when practical

**Rationale**: Safetensors avoids pickle-style model loading risks and gives a
cleaner artifact story. If a dependency or model path cannot emit safetensors,
the reason must be documented in the model card.

**Alternatives considered**:
- Pickle-only model artifacts: rejected for the transformer deployment candidate
  because artifact safety and portability matter.
- No saved artifact: rejected because model-server inference requires a stable
  deployable package.

## Decision: Use sklearn metrics for all comparable classification metrics

**Rationale**: Accuracy, macro-F1, per-class F1, and confusion matrix should be
computed by one shared implementation so all approaches are compared the same
way.

**Alternatives considered**:
- Per-script metric calculations: rejected because small differences can make
  comparisons unreliable.
- Manual metric calculations: rejected because tested library behavior is less
  error-prone.

## Decision: Store predictions, metrics, model cards, and reports as JSON artifacts

**Rationale**: JSON artifacts are easy to inspect, diff, validate in tests, and
consume from future CI or model-serving checks.

**Alternatives considered**:
- Markdown-only reports: useful for humans, but harder to validate.
- Database-only metric storage: unnecessary for this phase and less portable.

## Decision: Make the LLM baseline optional for real providers and mandatory with a fake provider in tests

**Rationale**: A real LLM baseline needs local credentials and may have cost.
Automated tests must not depend on paid services or secrets, so fake-provider
mode validates prompt/output parsing, cost accounting shape, and report
integration.

**Alternatives considered**:
- Require real LLM credentials for all runs: rejected because tests and local
  setup must work without secrets.
- Omit LLM baseline when credentials are absent: rejected for tests because the
  code path still needs coverage.

## Decision: Load classifier artifact during model-server lifespan

**Rationale**: Lifespan loading follows the constitution and prevents model
loading at import time or per request. It also lets startup fail or mark the model
unavailable before prediction calls.

**Alternatives considered**:
- Load at module import: rejected because it creates hidden side effects.
- Load on each request: rejected because it is slow and wastes resources.

## Decision: Record model and training data hashes before serving

**Rationale**: Hashes tie a served model to a known training dataset and artifact
contents. Hash validation prevents accidental or partial artifacts from being
served.

**Alternatives considered**:
- Trust artifact paths alone: rejected because paths can point to changed
  contents.
- Hash only the model weights: rejected because tokenizer and metadata also
  affect behavior.

## Decision: Log transformer training with a real local run logger

**Rationale**: The project brief requires a real run logger. A local
MLflow-style file store or structured JSONL run-log backend is enough for the
bootcamp scope while still recording run ID, parameters, metrics, artifact
references, plots, and final status.

**Alternatives considered**:
- Print training metrics only: rejected because console output is not durable
  evidence.
- Require a hosted tracking service: rejected because CI and local review should
  not depend on paid or external credentials.

## Decision: Store selected classifier artifact or manifest in MinIO

**Rationale**: Final review needs blob-backed model artifacts or at least a
manifest. The selected classifier artifact must be hash-validated before a
MinIO object or manifest reference is recorded in the model card.

**Alternatives considered**:
- Keep artifacts only on local disk: rejected because the project brief requires
  MinIO/blob storage for model artifacts or a manifest.
- Upload all intermediate failed runs: rejected because partial or failed
  artifacts are not deployable evidence.

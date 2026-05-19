# Research: Issue Classification Track

## Decision: Use TF-IDF plus Logistic Regression for the classical baseline

**Rationale**: TF-IDF with Logistic Regression is fast, explainable, and
strong enough to act as a credible non-neural baseline on issue text. It also
provides class probabilities that can be surfaced as confidence scores.

**Alternatives considered**:
- Linear SVM: competitive baseline, but confidence requires extra calibration.
- Naive Bayes: simpler, but usually weaker on mixed issue-title/body/comment
  text.

## Decision: Fine-tune `distilbert-base-uncased` as the transformer candidate

**Rationale**: DistilBERT is small enough for a bootcamp environment while
still representing a real fine-tuning workflow and a deployable transformer
artifact.

**Alternatives considered**:
- Larger BERT or RoBERTa variants: stronger in some settings, but heavier to
  train and harder to justify for this scope.
- Tiny random-test models only: useful for tests, but not credible as the phase
  comparison target.

## Decision: Prefer safetensors for transformer weights

**Rationale**: Safetensors gives a cleaner and safer artifact story than
pickle-style weight loading. If a non-safetensors fallback is ever needed, that
exception must be documented in the model card.

**Alternatives considered**:
- Pickle-only weights: rejected because deployable artifact safety matters.
- No saved artifact: rejected because later serving depends on stable model
  files.

## Decision: Use one shared sklearn-based evaluator for comparable metrics

**Rationale**: Accuracy, macro-F1, per-class F1, and confusion matrix must be
computed the same way for every approach. A shared evaluator avoids drift
between scripts.

**Alternatives considered**:
- Per-script metric logic: rejected because comparison would become fragile.
- Manual metric calculations: rejected because library behavior is easier to
  test and trust.

## Decision: Keep predictions, metrics, model cards, and reports in JSON/JSONL

**Rationale**: JSON artifacts are easy to diff, validate in tests, and reuse in
later CI and serving gates. JSONL remains appropriate for per-record
predictions.

**Alternatives considered**:
- Markdown-only reporting: readable, but weak for automated validation.
- Database-only storage: unnecessary complexity for this phase.

## Decision: Use Azure OpenAI via LangChain `AzureChatOpenAI` for the LLM baseline

**Rationale**: The project already leans toward Azure/OpenAI-backed model usage
in later phases. Using LangChain keeps provider-specific code inside an adapter
and makes fake/mock providers straightforward in tests.

**Alternatives considered**:
- Direct provider SDK calls: workable, but less consistent with later
  tool-calling/chatbot phases.
- Require a different hosted LLM provider: rejected because it fragments the
  stack without adding value.

## Decision: Resolve real Azure OpenAI and LangSmith credentials through Vault bootstrap settings

**Rationale**: The constitution requires LLM and tracing secrets to resolve
from Vault or test fakes. Phase 3 should keep `.env` limited to bootstrap
settings and never require real provider keys in committed files or automated
tests.

**Alternatives considered**:
- Read Azure OpenAI or LangSmith keys directly from `.env`: rejected because it
  conflicts with the constitution secret policy.
- Make all real-provider runs impossible before the auth phase: rejected because
  local evaluator runs still need an escape hatch for real comparisons.

## Decision: Enable LangSmith tracing only when a Vault-resolved API key is configured

**Rationale**: LangSmith provides trace evidence for real LLM baseline runs, but
the phase must still work without external accounts. When the key is absent, the
baseline still runs locally without tracing.

**Alternatives considered**:
- Make LangSmith mandatory: rejected because local and CI runs must remain
  credential-optional.
- Skip LLM tracing entirely: rejected because real runs should still be
  inspectable.

## Decision: Redact telemetry and artifact metadata before persistence

**Rationale**: MLflow runs, LangSmith traces, model cards, manifests, and eval
logs can all accidentally capture secrets or oversized raw issue text. A single
infra-level redaction step keeps telemetry and artifact metadata safe and
consistent with the constitution.

**Alternatives considered**:
- Rely on individual scripts to remember redaction rules: rejected because that
  scatters security logic and is easy to miss.
- Store full raw payloads in MLflow or LangSmith for convenience: rejected
  because the constitution forbids unredacted persistence or telemetry.

## Decision: Use a self-hosted MLflow tracking server with MinIO artifact storage

**Rationale**: MLflow satisfies the project requirement for a real run logger,
works locally without external accounts, and pairs cleanly with MinIO for model
artifacts, plots, and run evidence. For bootcamp scope, the tracking server can
run in Docker Compose with a local persistent backend and MinIO as the artifact
store.

**Alternatives considered**:
- Structured JSONL logs only: rejected because the spec explicitly requires a
  real run logger.
- Hosted experiment-tracking services: rejected because CI and local review must
  not depend on paid or external accounts.
- Reusing the application database as the MLflow backend: rejected to keep ML
  tracking isolated from application persistence.

## Decision: Upload the selected classifier artifact or manifest to MinIO

**Rationale**: Final review and later startup validation need a stable blob
reference for the selected model. Uploading only the selected, hash-validated
artifact or a manifest keeps storage disciplined.

**Alternatives considered**:
- Local disk only: rejected because the project brief requires MinIO/blob-backed
  evidence.
- Upload every failed or partial run artifact: rejected because incomplete runs
  are not deployable evidence.

## Decision: Validate artifact hashes before the model can be served

**Rationale**: Hash validation ensures the served model matches its model card
and prevents partial or mutated artifacts from being treated as deployable.

**Alternatives considered**:
- Trust artifact paths alone: rejected because contents can drift.
- Hash only weights: rejected because tokenizer and metadata also affect
  behavior.

## Decision: Load the classifier artifact during model-server lifespan

**Rationale**: Lifespan loading matches the constitution, avoids import-time
side effects, and keeps request latency stable.

**Alternatives considered**:
- Load at import time: rejected because it creates hidden startup side effects.
- Load on every request: rejected because it is slow and wasteful.

## Decision: Measure endpoint latency on a warm, preloaded model-server over 30 sequential requests

**Rationale**: The Phase 3 latency target needs a repeatable measurement method
instead of a vague “normal load” claim. Warm-process sequential requests are
simple enough for the bootcamp scope and are consistent with the endpoint’s
single-request acceptance criterion.

**Alternatives considered**:
- Leave latency as a qualitative statement: rejected because the success
  criterion is numeric.
- Require heavy load-testing infrastructure in Phase 3: rejected because it is
  out of proportion to the scope and belongs in later production-readiness work.

## Decision: Treat model version as a semantic version stored in `model_card.json`

**Rationale**: A semantic version string is easy to inspect, stable for clients,
and can be returned directly by the classifier endpoint without recomputing any
runtime identifier.

**Alternatives considered**:
- Git SHA only: useful internally, but weaker as a client-facing model version.
- Timestamp-only versioning: easy to generate, but less readable and harder to
  manage semantically.

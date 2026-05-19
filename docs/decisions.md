# Decisions

## ADR-001: structlog for Structured Logging

**Decision**: Use structlog with JSON renderer for all application logging.

**Rationale**: Machine-parseable logs, contextvars support for automatic `request_id` binding, and explicit processor chains.

**Alternatives Rejected**:
- Standard `logging` module: no structured JSON output by default.
- loguru: less contextvars integration and custom binding support.

## ADR-002: Vault Dev Token for Secret Resolution

**Decision**: All secrets are read from Vault at lifespan startup using the Vault dev-mode bootstrap token.

**Rationale**: The project brief specifies Vault dev mode. Using only `VAULT_ADDR` and `VAULT_TOKEN` keeps bootstrap simple while all runtime secrets still live in Vault rather than `.env`.

**Alternatives Rejected**:
- Env-file secrets: risk of committing credentials.
- AWS Secrets Manager: vendor lock-in for local development.

## ADR-003: X-Request-ID Header Strategy

**Decision**: Middleware generates UUID4 if header absent, echoes it on response, binds it to structlog contextvars.

**Rationale**: End-to-end traceability visible to HTTP clients.

**Alternatives Rejected**:
- Trace headers only (not HTTP-visible to clients).

## Phase 2 Data Source Decision

**Decision**: Use `fastapi/fastapi` as the public repository for the Phase 2 dataset pipeline.

**Selection Criteria**:
- Public open-source repository with permissive license (MIT)
- Sufficient closed issues with useful labels
- Well-known labels: bug, feature, documentation, question

**Fetch Library**: httpx with explicit timeouts and pagination (not PyGithub).

**Rate-Limit Policy**: Fail fast, exit non-zero. No automatic retry to avoid hammering the API.

**Fetch Limit**: 1000 closed issues (configurable via `DatasetSettings.max_issues`).

**Alternatives Rejected**:
- `pytorch/pytorch`: rejected because labels are more complex and less consistent.
- PyGithub library: rejected to keep dependencies minimal and control pagination explicitly.

## Phase 2 Label Mapping Decision

**Chosen Repository Labels**: `fastapi/fastapi` uses labels such as `bug`, `feature`, `documentation`, `question`.

**Label Mapping**:
- `bug` → `bug` (exact match)
- `feature`, `enhancement` → `feature`
- `documentation`, `docs` → `docs`
- `question`, `help wanted`, `good first issue` → `question`

**Unmapped Policy**: `exclude` — records with no matching labels are dropped.

**Ambiguous Policy**: `first_match` — when a record has labels matching multiple classes, the first match in `priority_order` wins.

**Priority Order**: `[bug, feature, docs, question]`

**Excluded Labels**: Labels not in the mapping (e.g., `duplicate`, `wontfix`, `good first issue` when not explicitly mapped) are excluded.

## Phase 2 Split Policy Decision

**Ratios**: 70% train / 15% validation / 10% test / 5% held-out.

**Temporal Ordering**: Records are sorted by `closed_at` ascending. Test records are strictly newer than training records. This prevents future information from leaking into model training.

**Why Temporal Ordering Takes Precedence**: A model evaluated on older data than it was trained on would give an unrealistically optimistic score. Temporal ordering ensures the evaluation mimics real-world deployment where the model sees issues it has not been trained on.

**Class Balance**: Attempted within the temporal constraint. When classes are missing from the train split (e.g., very few `question` issues early in the repo history), a WARNING is logged and the limitation is recorded in the dataset report.

## Phase 3 Classification Approach Decisions

**Decision**: Use TF-IDF + Logistic Regression for the classical baseline, DistilBERT for the transformer, and Azure OpenAI via LangChain for the LLM baseline.

**Classical Baseline**: TF-IDF with Logistic Regression is fast, explainable, and provides class probabilities as confidence scores.

**Transformer**: DistilBERT is small enough for a bootcamp environment while representing a real fine-tuning workflow. Uses safetensors for weight serialization.

**LLM Baseline**: LangChain AzureChatOpenAI keeps provider-specific code in an adapter. Fake/mock providers are used in tests; real credentials resolve from Vault.

**Shared Evaluator**: A single evaluator computes accuracy, macro-F1, per-class F1, confusion matrix, latency, and cost for all approaches on the same test split.

**Redaction**: All telemetry, model cards, manifests, and run metadata are redacted before persistence using `app.infra.redaction`.

**MLflow**: Self-hosted MLflow with MinIO artifact storage. Run metadata is redacted before logging.

**Secret Resolution**: Azure OpenAI and LangSmith credentials resolve from Vault bootstrap settings only, never from .env files.

**Artifact Validation**: Only hash-validated artifacts can be marked deployable or uploaded to MinIO.

## Phase 3 Comparison Results

Three-way comparison on the same test split (178 pandas issues):

| Approach | Accuracy | Macro-F1 | Mean Latency | Status |
|----------|----------|----------|--------------|--------|
| Classical (TF-IDF + LogReg) | 0.629 | 0.629 | 0.13ms | ✅ Completed |
| Transformer (DistilBERT) | 0.663 | 0.665 | — | ✅ Completed |
| LLM Baseline (Azure OpenAI gpt-5.4-nano) | 0.624 | 0.609 | ~980ms | ✅ Completed |

## Deployment Choice (LOCKED)

**Decision: DistilBERT transformer is the deployed classifier.**

Runners-up and rationale:

| Approach | Accuracy | Macro-F1 | Latency | Kept? | Reason |
|----------|----------|----------|---------|-------|--------|
| Transformer (DistilBERT) | **0.663** | **0.665** | ~50ms inference | ✅ **DEPLOYED** | Highest accuracy, zero API dependency, no per-request cost |
| Classical (TF-IDF + LogReg) | 0.629 | 0.629 | 0.13ms | Discarded | Undercut by transformer on both metrics |
| LLM Baseline (Azure gpt-5.4-nano) | 0.624 | 0.609 | ~1s/request | Discarded | Slower, costlier, depends on external Azure API; highest **feature**-class F1 (0.851) but collapses on **question** (0.313) |

**Locked because:**
- Transformer leads on both accuracy (+0.034 vs classical, +0.039 vs LLM) and macro-F1 (+0.036 vs classical, +0.056 vs LLM).
- Self-contained artifact (267 MB `.safetensors` + tokenizer) — no network call, no API key, no rate limit.
- Repeatable offline inference with no per-request cost.
- Classical model remains loaded in the model server as a fallback; LLM baseline retains the fake provider for CI.

**LLM Baseline Details**: The LLM baseline was successfully run with real Azure OpenAI (`gpt-5.4-nano`, ~1s per request, 174s total for 178 samples). Credentials resolve from Vault at runtime (`secret/maintainer-copilot/azure-openai`). LangSmith tracing was enabled for this run (`tracing_backend: langsmith`, project `week-7-aie`). The fake provider remains available for CI/tests via `--provider fake_provider`.

**Alternatives Rejected**:
- Direct OpenAI SDK: less consistent with later tool-calling phases
- PyTorch-based CNN: too heavy for the scope
- Pickle-only weights: safetensors is safer

## Phase 2+ Decisions

To be added as phases progress.

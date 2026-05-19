# Decisions

## ADR-001: structlog for Structured Logging

**Decision**: Use structlog with JSON renderer for all application logging.

**Rationale**: Machine-parseable logs, contextvars support for automatic `request_id` binding, and explicit processor chains.

**Alternatives Rejected**:
- Standard `logging` module: no structured JSON output by default.
- loguru: less contextvars integration and custom binding support.

## ADR-002: Vault AppRole for Secret Resolution

**Decision**: All secrets are read from Vault at lifespan startup using AppRole authentication.

**Rationale**: No secrets in env vars or Docker images. Centralized secret management with audit trails.

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

## Phase 2+ Decisions

To be added as phases progress.

# Security

## Secret Handling Policy

- No secrets committed to git.
- `.env.example` contains only fake values.
- All real secrets resolved from Vault at startup.
- The local `.env` may hold developer-only seed values for Docker Compose, but
  the app runtime still reads Azure OpenAI, LangSmith, database, MinIO, and JWT
  secrets from Vault rather than directly from `.env`.

## Vault Dev Bootstrap Policy

- Docker Compose starts Vault in dev mode only.
- Local/dev bootstrap can run through the one-shot `vault_seed` Docker Compose
  service or manually with `uv run python scripts/seed_vault_from_env.py .env`.
- The seeding input is local developer configuration; the runtime source of
  truth remains Vault.
- Only `VAULT_ADDR` and `VAULT_TOKEN` are used as bootstrap settings.
- Azure OpenAI secrets stored at `secret/data/maintainer-copilot/azure-openai`.
- LangSmith API key stored at `secret/data/maintainer-copilot/langsmith`.

## Redaction Policy

- All MLflow run metadata, model cards, manifests, and telemetry data are redacted before persistence using `app.infra.redaction`.
- No raw secrets, full issue payloads, or provider credentials appear in logs, traces, model cards, or manifests.
- `redaction_applied: true` must be set on all persisted model cards and run metadata.
- Tests prove that fake secrets do not appear unredacted in logs, traces, or audit records.

### Phase 5 RAG Redaction Rules

- `redact_chunk_preview()` strips full `content` from chunk records; keeps only `chunk_id`, `parent_id`, score metadata.
- `redact_rag_prompt()` replaces `content`, `maintainer_answer`, `question_context` with length-only metadata. Safe keys (chunk_id, top_k, retrieval_mode, etc.) are preserved with `redact_string()` applied to string values.
- `redact_snapshot_row()` strips raw content and redacts queries; keeps only `snapshot_id`, `conversation_id`, `message_id`, `trace_id`, `chunk_ids`, `scores`.
- `redact_eval_report()` strips `content` fields from all nested chunk results and redacts secret patterns in string values.
- No raw source text, prompts, chunk content, provider responses, or secrets appear in logs, traces, snapshots, or eval reports.
- Request IDs and trace IDs are preserved for correlation without exposing payloads.

### Phase 6 Auth and Memory Redaction Rules

- JWT signing keys are resolved from Vault during lifespan startup and are never logged or persisted in repo files.
- `redact_short_term_memory_value()` runs before any Redis short-term memory write.
- `redact_long_term_memory_content()` runs before long-term embedding generation, long-term persistence, audit metadata, logs, and traces.
- `redact_audit_metadata()` bounds and redacts audit metadata before audit-row creation.
- Long-term memory rows store redacted content only; no raw secret-like values are persisted.
- Recall responses return previously stored redacted content only and never create new memory.
- `memory.write` audit rows store safe metadata fields (`memory_type`, `content_hash`, `content_length`, `redaction_applied`, `source`) and do not include raw content.
- Structured logs for auth failures, role changes, memory writes, and recall events must include `request_id` and `trace_id` while excluding raw passwords, tokens, signing keys, invitation tokens, or unredacted memory content.

- `redact_issue_analysis_metadata()` keeps only safe keys: `request_id`, `tool_name`, `combined_characters`, `entity_count`, `entity_types`, `status`, `code`, `trace_id`, `provider_backend`, `tracing_backend`, `timeout_seconds`, `limitations`, `error_code`. All other keys are stripped.
- `redact_log_payload()` replaces `title`, `body`, and `comments` fields with length-only metadata (`title_len`, `body_len`, `comments_len`, `comments_count`). Non-content fields are redacted for secret patterns before logging.
- No raw title, body, comment text, prompts, credentials, provider responses, or stack traces reach logs or traces.
- Request IDs and trace IDs are preserved in redacted metadata for correlation without exposing payloads.

### Phase 7 Chat Redaction Rules

- `redact_chat_message()` runs before short-term chat state persistence and before chat payloads are logged or traced.
- `redact_chat_prompt_payload()` and `redact_llm_payload()` replace full prompt text with bounded metadata in telemetry paths.
- `redact_tool_payload()` and `redact_sse_event()` remove or bound secret-like values before tool telemetry or SSE-event telemetry is logged.
- `redact_trace_metadata()` runs before chat roots, LLM spans, tool spans, and RAG spans are recorded.
- Chat SSE responses may contain assistant-visible content, but logs and traces must not persist raw user messages, raw tool payloads, raw LLM prompts, or full retrieved chunks.
- Retrieved RAG context is wrapped as untrusted evidence and snapshot persistence stores bounded references only.

## Model Artifact Security

- Only hash-validated classifier artifacts can be marked deployable or uploaded to MinIO.
- Artifact SHA-256 must match `model_card.json` before the model can be served.
- Partial or incomplete artifacts are never deployable.

## `.gitignore` Rules

Secret-related entries:
- `.env`
- `.env.local`
- `data/raw/`
- `data/processed/`
- `artifacts/`

Classifier-related entries:
- `evals/classifier_eval_report.json`
- `evals/classification_golden_set.jsonl`
- `*.safetensors`
- `*.bin`
- `*.joblib`
- `mlruns/`

## Phase 8 Streamlit Security Boundaries

### No Direct Persistence

The `streamlit_app/` package MUST NOT import `sqlalchemy`, `asyncpg`, `redis`, `hvac`, `minio`, ORM models, repository classes, or database sessions. All data access goes through `BackendAPIClient` calling the same FastAPI backend that the widget will use. Static tests in `tests/unit/test_streamlit_no_direct_db_or_secrets.py` enforce this at CI time.

### No Hardcoded Secrets

`streamlit_app/` MUST NOT contain real API keys, passwords, tokens, JWT signing keys, or privileged credentials. The backend base URL is non-secret configuration loaded from `MAINTAINER_COPILOT_UI_BASE_URL`. Static tests verify no string literals matching secret patterns appear in Streamlit code.

### Cookie Token Lifecycle

- **Store**: Auth token written to browser cookie (`mc_access_token`) via `streamlit-cookies-manager` on successful login.
- **Restore**: Token read from cookie on page refresh; validated via `GET /users/me`.
- **Clear on logout**: Cookie and `st.session_state` cleared on explicit logout.
- **Clear on auth failure**: Backend `401` invalidates the session, clears cookie and state, and returns the user to the login page.
- **Scope**: Token is sent only as an `Authorization: Bearer` header; never displayed in UI, written to logs, or included in error messages.

### Streamlit Redaction Rules

- Raw chat messages, memory contents, tokens, embed snippets, and backend error traces MUST NOT be written to Streamlit logs or displayed in raw form.
- `display_error()` renders only `UIErrorMessage.message` with mapped severity; stack traces and raw payloads are never shown.
- Memory inspector displays only `redacted_content` from backend responses; unredacted content is never reconstructed or stored.

### UI Error Boundaries

- `401`: Clears auth state and returns to login page.
- `403`: Shows a clean access-denied message; no admin API calls are retried.
- Timeouts: Show a retryable warning; UI does not hang.
- Backend validation errors: Show field-level feedback via `display_error()`.
- Server errors (5xx): Show a generic retryable message without stack traces.

## Phase 9 Widget Security Boundaries

### Origin Allowlisting

- All public widget endpoints (`/public/widgets/{id}/config`, `/public/widgets/{id}/session`, `/widget/frame/{id}`) validate the observed request `Origin` header against the widget's `allowed_origins` list.
- `Referer` header is used as a fallback when `Origin` is absent (e.g., same-origin navigation).
- Client-declared origin in request bodies is advisory only and never authoritative.
- If origin validation fails, the endpoint returns `403` with a clean error message — no stack traces, no config details.

### CSP Frame-Ancestors

- The `/widget/frame/{widget_id}` response includes `Content-Security-Policy: frame-ancestors <allowed_origins>` derived from the widget's allowed origins list.
- Browsers that honor CSP will refuse to render the iframe on unapproved origins.
- `X-Frame-Options` is intentionally not sent on this route because it would
  block approved cross-origin host pages; `frame-ancestors` is the source of
  truth for embed authorization.

### Anonymous Session Tokens

- Widget session tokens are UUID4 hex strings with 60-minute TTL.
- Tokens are scoped to a specific widget ID and issued only after origin validation.
- Tokens are passed via `?token=` query parameter on the SSE stream URL — never in request bodies or headers.
- Tokens are stateless (not stored server-side); validation checks format and origin alignment.

### No Streamlit Coupling

- Widget code (`widget/`), demo hosts (`demo/host/`), and public widget routes (`widget_public.py`, `widget_loader.py`) contain zero references to Streamlit.
- Static tests in `tests/unit/test_widget_no_streamlit.py` enforce this at CI time.
- The widget uses the same FastAPI backend as the Streamlit admin app but has no dependency on it.

### postMessage Restriction

- The widget uses `postMessage` exclusively for the `maintainer-copilot-widget:resize` channel.
- No other message types are sent or accepted.
- Static tests verify no unauthorized `postMessage` usage in widget or demo host code.

### Raw Message Content Never on SSE URL

- User message content is submitted via POST and stored server-side in a pending message map.
- The SSE stream URL (`GET /chat/stream?token=...&conversation_id=...`) contains only the session token and conversation ID.
- This prevents raw message content from appearing in browser history, proxy logs, or server access logs.

### Bundle Integrity

- Widget bundle size is measured after each build: loader < 5 KB gzip, initial bundle ≤ 150 KB gzip.
- Report is generated at `docs/widget-bundle-report.md`.
- Bundle tests in `tests/unit/test_widget_bundle.py` enforce size constraints at CI time.

## Phase 10 Production Readiness Security Gates

### Redaction Leak Gate

`scripts/ci/check_redaction_leaks.py` exercises the app's `app/infra/redaction`
layer with fake secret probes and verifies that no raw probe value appears
unredacted in any output target:

- **App redaction layer**: Calls `redact_string()` with fake probes and verifies `[REDACTED]` replaces raw values
- **Logs**: Scans simulated log output for fake probe leakage
- **Traces**: Scans JSON trace output for fake probes
- **Memory**: Scans memory write/output for fake probes
- **Audit records**: Scans JSON audit records for fake probes
- **Captured output**: Scans all captured command output for fake probes

Fake probes used:
- `sk-fake-test-key-12345` (simulates OpenAI API key prefix)
- `password=super_secret_test_value` (simulates hardcoded password)

Fixture files in `tests/fixtures/ci/security/` contain deliberate fake probes
for testing the leak scanner itself. These fixtures are flagged as expected
hits and do not cause gate failure.

### Static Secret Grep Gate

`scripts/ci/check_static_secret_patterns.py` scans the entire repository for
committed secret-like patterns using the `scripts/ci/secret_scan.py` helper.

Unsafe patterns detected:
- `sk-` (OpenAI-style API key prefix)
- `password=` (hardcoded password assignment)
- `passwd=` (hardcoded password variant)
- `SECRET_KEY=` (hardcoded secret key)

Allowlisted files (known-safe false positives):
- `scripts/ci/secret_scan.py` — defines the patterns to scan for
- `scripts/ci/common.py` — contains sanitization patterns
- `scripts/ci/check_static_secret_patterns.py` — the scanner itself
- `scripts/ci/check_redaction_leaks.py` — contains fake probe definitions
- `.flake8` — lint configuration
- `.github/workflows/ci.yml` — Docker Compose password env vars
- `AGENTS.md`, `constitution.md` — documentation mentioning patterns

Non-allowlisted hits cause gate failure with safe path/line reporting.
Secret values are never printed in failure output.

### Model Artifact Integrity Gate

`scripts/ci/check_model_artifacts.py` validates model artifact SHA-256 hashes
against model cards:

- Locates model card at `artifacts/evals/model_card.json`
- Computes SHA-256 for each referenced artifact
- Verifies hash matches `sha256` field in card
- Fails on missing artifacts, hash mismatches, or malformed cards
- Passes gracefully when no model card exists (CI without model artifacts)

Fixture files in `tests/fixtures/ci/model_artifacts/` include:
- Valid card with expected hash
- Card referencing nonexistent artifact
- Card with deliberately wrong hash

### Startup Failure Gate

`scripts/ci/check_startup_failures.py` performs negative-test assertions to
verify the system fails closed when any required dependency is unavailable:

| Check | Expected Behavior |
|---|---|
| vault-unreachable | App fails when Vault is unreachable (init_vault_client raises ConfigError) |
| vault-missing-secret | App fails when Vault is reachable but required secret is missing |
| missing-model-artifact | App fails when required model artifact is absent |
| model-hash-mismatch | App fails when model artifact hash does not match model card |
| tracing-misconfig | App fails when tracing configuration is invalid |
| disabled-thresholds | App fails when eval thresholds are zero or disabled |

Each check returns `(True, message)` when the system correctly fails closed.
A `(False, message)` means the system succeeded when it should have failed —
this is a gate failure.

### Tracing Configuration Gate

`scripts/ci/validate_tracing.py` validates LangSmith tracing configuration:

- Checks `LANGSMITH_API_KEY` is present and of reasonable length
- Checks `LANGSMITH_PROJECT` is set when `LANGSMITH_ENDPOINT` is set
- Detects obviously invalid key formats
- In CI without credentials: passes gracefully (non-fatal — tracing is optional in CI)
- In production with misconfigured tracing: fails the gate

### Gate Order in Security Pipeline

1. `check_redaction_leaks.py` — fake probe leak detection
2. `check_static_secret_patterns.py` — committed secret pattern scan
3. `check_model_artifacts.py` — artifact hash validation
4. `check_startup_failures.py` — negative-case startup checks
5. `validate_tracing.py` — tracing config validation

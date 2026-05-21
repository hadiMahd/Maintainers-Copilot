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
- Local/dev bootstrap then runs `uv run python scripts/seed_vault_from_env.py .env`
  from the host to seed the expected paths.
- The seeding input is the local `.env`; the runtime source of truth remains Vault.
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

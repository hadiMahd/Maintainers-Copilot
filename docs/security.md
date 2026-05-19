# Security

## Secret Handling Policy

- No secrets committed to git.
- `.env.example` contains only fake values.
- All real secrets resolved from Vault at startup.
- The local `.env` may hold developer-only seed values for Docker Compose, but
  the app runtime still reads Azure OpenAI, LangSmith, database, MinIO, and JWT
  secrets from Vault rather than directly from `.env`.

## Vault Dev Bootstrap Policy

- Docker Compose starts Vault in dev mode and seeds the expected paths on boot.
- The seeding entrypoint is `scripts/seed_vault_from_env.sh`, which reads local
  `.env` values and writes them to Vault.
- Only `VAULT_ADDR` and `VAULT_TOKEN` are used as bootstrap settings.
- Azure OpenAI secrets stored at `secret/data/maintainer-copilot/azure-openai`.
- LangSmith API key stored at `secret/data/maintainer-copilot/langsmith`.

## Redaction Policy

- All MLflow run metadata, model cards, manifests, and telemetry data are redacted before persistence using `app.infra.redaction`.
- No raw secrets, full issue payloads, or provider credentials appear in logs, traces, model cards, or manifests.
- `redaction_applied: true` must be set on all persisted model cards and run metadata.
- Tests prove that fake secrets do not appear unredacted in logs, traces, or audit records.

### Phase 4 Redaction Rules

- `redact_issue_analysis_metadata()` keeps only safe keys: `request_id`, `tool_name`, `combined_characters`, `entity_count`, `entity_types`, `status`, `code`, `trace_id`, `provider_backend`, `tracing_backend`, `timeout_seconds`, `limitations`, `error_code`. All other keys are stripped.
- `redact_log_payload()` replaces `title`, `body`, and `comments` fields with length-only metadata (`title_len`, `body_len`, `comments_len`, `comments_count`). Non-content fields are redacted for secret patterns before logging.
- No raw title, body, comment text, prompts, credentials, provider responses, or stack traces reach logs or traces.
- Request IDs and trace IDs are preserved in redacted metadata for correlation without exposing payloads.

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

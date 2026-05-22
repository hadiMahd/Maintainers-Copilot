# Runbook

## Start Stack

```bash
cp .env.example .env
docker compose up -d
```

`vault_seed` is a one-shot Compose service that seeds Vault from the local
environment before `backend` and `model_server` start. For manual bootstrap, run
`uv run python scripts/seed_vault_from_env.py .env`.

## Stop Stack

```bash
docker compose down -v
```

## Start pgAdmin

```bash
docker compose --profile dbadmin up -d pgadmin
```

Open `http://localhost:5050`.

Login with:

- email: `PGADMIN_DEFAULT_EMAIL` from `.env` or default `admin@example.com`
- password: `PGADMIN_DEFAULT_PASSWORD` from `.env` or default `admin`

Preconfigured server:

- name: `maintainer-postgres`
- host: `postgres`
- port: `5432`
- database: `maintainer`
- username: `maintainer`
- password: `POSTGRES_PASSWORD` from `.env`

## Run Tests

```bash
uv run pytest tests/ -v
```

## Run Migrations

```bash
DATABASE_URL=postgresql+asyncpg://maintainer:maintainer@localhost:5432/maintainer uv run alembic upgrade head
```

## Check Health

```bash
curl -s localhost:8000/health/live | jq .
curl -s localhost:8000/health/ready | jq .
```

## Bootstrap First Admin

```bash
uv run python scripts/seed_admin.py --email admin@example.com --password '<password>'
```

Expected: the first admin is created when none exists; repeated runs report an existing admin.

## Phase 6 Auth and Memory Validation

Critical slice:

```bash
uv run pytest tests/unit/test_auth_service.py tests/unit/test_authorization_service.py tests/unit/test_admin_invitation_service.py tests/unit/test_short_term_memory_service.py tests/unit/test_long_term_memory_service.py tests/unit/test_long_term_memory_recall.py tests/unit/test_audit_service.py tests/unit/test_audit_action_names.py tests/unit/test_memory_redaction.py tests/unit/test_repository_boundaries.py tests/contract/test_auth_memory_api_contract.py tests/integration/test_auth_lifecycle_vault_key.py tests/integration/test_refresh_token_flow.py tests/integration/test_admin_invitation_flow.py tests/integration/test_redis_memory_ttl.py tests/integration/test_memory_audit_transaction.py tests/integration/test_cross_conversation_recall.py -q
```

Full suite:

```bash
uv run pytest -q
```

Expected: current baseline after Phase 6 is 542 passed, 3 skipped.

## Phase 7 Chat Validation

Focused chat suite:

```bash
uv run pytest tests/contract/test_chat_endpoint_contract.py tests/unit/test_chatbot_graph.py tests/unit/test_chat_limits.py tests/unit/test_tool_execution_service.py tests/unit/test_write_memory_intent.py tests/unit/test_untrusted_rag_context.py tests/unit/test_retrieved_chunk_snapshots.py tests/unit/test_chat_tracing.py tests/unit/test_chat_redaction.py tests/integration/test_chat_successful_tool_call.py tests/integration/test_chat_redis_state.py tests/integration/test_chat_failed_tool_recovery.py tests/integration/test_chat_trace_log_correlation.py -q
```

Cross-cutting Phase 7 guardrails:

```bash
uv run pytest tests/test_config.py tests/test_import_side_effects.py tests/test_route_boundaries.py tests/test_no_secrets.py tests/test_errors.py -q
```

Expected: the focused chat slice and cross-cutting guardrails both pass before full regression. Full regression baseline after Phase 7: 597 passed, 3 skipped.

## Common Failures

- **Vault unreachable**: check `VAULT_ADDR`, run `docker compose ps vault`
- **Postgres unhealthy**: check `docker compose logs postgres`
- **pgvector not installed**: run `docker compose restart migrations`
- **Backend crash on startup**: secrets may not be seeded yet — re-run `uv run python scripts/seed_vault_from_env.py .env`, then `docker compose restart backend`

## Start Model Server

```bash
CLASSIFIER_ARTIFACT_DIR=artifacts/classifiers/classical \
CLASSIFIER_MODEL_VERSION=0.1.0 \
uv run uvicorn model_server.main:app --port 8001
```

## Check Model Server Health

```bash
curl -s localhost:8001/health | jq .
```

## Ingest RAG Corpus

```bash
uv run python scripts/ingest_docs.py
uv run python scripts/ingest_resolved_issues.py --input /path/to/issues.jsonl
```

Expected: `data/processed/rag_doc_sources.jsonl`, `rag_issue_answer_sources.jsonl`, and `rag_chunks.jsonl` created.

## Build RAG Index

```bash
uv run python scripts/build_rag_index.py --persist-db
```

For testing without real embeddings:
```bash
uv run python scripts/build_rag_index.py --fake
```

Expected: `artifacts/rag/embedding_comparison.json` created and chunks,
sparse rows, and embeddings persisted into Postgres. With Azure embedding
secrets in Vault, this uses `text-embedding-3-small`; otherwise it uses the
local embedding client.

## Evaluate RAG Pipeline

```bash
uv run python scripts/evaluate_rag.py --exploratory
```

Expected: `evals/rag_eval_report.json` created with baseline-vs-advanced comparison, judge_id, embedding comparison, and disagreement notes.

Real CI RAG eval against the live index:

```bash
USE_REAL_AZURE_EVALS=1 uv run python scripts/ci/run_rag_eval.py
```

## Measure Classifier Latency

```bash
uv run python scripts/measure_classifier_latency.py
```

Expected: P95 ≤ 500ms for 30 sequential warm requests.

## Classifier Endpoint Unavailable

If the model server returns 503 with `classifier_model_unavailable`:
- Check `CLASSIFIER_ARTIFACT_DIR` points to a valid artifact directory
- Verify `model_card.json` exists in the artifact directory
- Check artifact hash matches model card `artifact_sha256`
- Verify the model was loaded during startup (check startup logs)

## Phase 8 Streamlit Admin App

### Start Streamlit

```bash
MAINTAINER_COPILOT_UI_BASE_URL=http://localhost:8000 streamlit run streamlit_app/app.py
```

The backend URL must be running and accessible. The FastAPI backend must have the Phase 8 widget-config and memory-inspection routes registered (they are wired in `app/api/routes/__init__.py`).

To run the UI inside Docker Compose instead:

```bash
docker compose --profile ui up -d streamlit
```

The default `chatbot` service publishes Streamlit at `http://localhost:8501`.
The optional `streamlit` profile publishes at `http://localhost:8502` to avoid
a port clash. Both point at the backend service with
`MAINTAINER_COPILOT_UI_BASE_URL=http://backend:8000`.

### Verify Backend Endpoints

```bash
# Widget config list (requires admin token)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/admin/widget-configs/

# Create widget config
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"Test","allowed_origins":["http://localhost"]}' \
  http://localhost:8000/admin/widget-configs/

# Embed snippet
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/admin/widget-configs/{config_id}/embed-snippet

# Memory inspection
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/memory/long-term?limit=5"
```

### Verify Cookie Auth Lifecycle

- Log in through the Streamlit login page with valid backend credentials.
- Refresh the browser: session should restore without re-login.
- Click "Log out": cookie is cleared, login page appears.
- Send an expired/invalid token: UI returns to login page.

### Verify Admin Guard

- Log in as a regular user: "Widget Config" tab should not appear in the sidebar.
- Log in as an admin: "Widget Config" tab should appear.
- Manual URL navigation to an admin page by a regular user is blocked by `st.navigation()` role exclusion.

### Verify Chat

- Open the Chat page after login.
- Send a message: response streams in via SSE with `st.write_stream()`.
- The full response is never buffered before display.

### Verify Memory Inspector

- Open the Memory page after login.
- As a regular user: sees only own memory records (scope `own`).
- As an admin: sees all records (scope `admin`), with owner displayed.

### Streamlit Troubleshooting

| Symptom | Check |
|---------|-------|
| "Unable to reach the backend" on login | `MAINTAINER_COPILOT_UI_BASE_URL` is set and backend is running |
| Login succeeds but page redirects to login | Cookie not being stored; check browser cookie settings |
| Admin tabs not visible | Verify `GET /users/me` returns `role: "admin"` |
| Chat stuck on "pending" | Backend SSE endpoint timing out; check `sse_timeout_seconds` |
| Widget config save fails with 403 | User is not admin; verify role in `st.session_state` |

## Phase 9 Embeddable Widget

### Build Widget Assets

```bash
cd widget
npm install
npm run build
npm run size
```

Expected: `dist/assets/loader.js` (< 5 KB gzip) and `dist/assets/widget-*.js` (≤ 150 KB gzip). Report written to `docs/widget-bundle-report.md`.

### Start Widget Demo Hosts

```bash
docker compose up -d demo_host
```

The demo host publishes the same host app on `http://localhost:8080` and
`http://localhost:8081`; allow only `http://localhost:8080` in the widget config
to demo the blocked-origin path on port 8081.

### Verify Widget Embed

1. Create a widget config via the admin API with an allowed origin matching the demo host.
2. Get the embed snippet from `GET /admin/widget-configs/{id}/embed-snippet`.
3. Serve `demo/host/allowed/index.html` from the allowed origin with the snippet injected.
4. The widget bubble should appear in the configured position.

### Widget Troubleshooting

| Symptom | Check |
|---------|-------|
| Widget not appearing | Verify `data-widget-id` matches a valid, enabled widget config |
| 403 on config fetch | Origin not in allowed_origins list |
| Chat not streaming | Check `POST /chat/messages` returns conversation_id, then `GET /chat/stream` is called |
| Bundle too large | Run `npm run size`; review `docs/widget-bundle-report.md` |

## Phase 10 Full Regression Baseline

```bash
uv run pytest -q
```

Expected current release baseline: 1007 passed, 1 skipped.

### CI Quality Gate Status

The release quality gates are expected to pass on current `010-production-readiness`:

| Gate | Status | Scope |
|---|---|---|
| lint (flake8) | PASS | Repository Python files |
| format-check (black/isort) | PASS | Repository Python files |
| import-check (isort) | PASS | Repository Python files |
| type-check (mypy) | PASS | `scripts/ci/` validation code |
| tests (pytest) | PASS | Full test suite |

The app runtime is still dynamically typed in places where FastAPI, SQLAlchemy,
LangChain, and provider adapters cross framework boundaries. The release gate keeps
strict mypy coverage on the CI validation code and relies on tests plus boundary checks
for the dynamic app layer.

## Phase 10 CI Failure Debugging

### Lint Gate (flake8)

**Symptom**: `make lint` or CI `lint` job fails.

**Debug**:
```bash
uv run flake8 . 2>&1 | head -20
```
- Check `.flake8` for ignore rules and exclude patterns.
- Common causes: unused imports, long lines, `E203`/`W503` whitespace.

### Format Check Gate (black + isort)

**Symptom**: `make format-check` fails.

**Debug**:
```bash
uv run black --check . --diff
uv run isort --check-only . --diff
```
- Fix formatting with `uv run black .` and `uv run isort .`.

### Type Check Gate (mypy)

**Symptom**: `make type-check` fails.

**Debug**:
```bash
scripts/ci/run_type_check.sh
```
- Common causes: untyped CI helper functions, missing return types, incompatible overrides.
- Check `pyproject.toml` `[tool.mypy]` for ignore/disfollow settings.

### Test Gate (pytest)

**Symptom**: `make test` fails.

**Debug**:
```bash
uv run pytest -x --tb=long
```
- Common causes: fixture setup failures, missing environment variables.

### Eval Gate (classifier/RAG)

**Symptom**: `make evals` fails on classifier or RAG eval.

**Debug**:
```bash
uv run python scripts/ci/check_eval_thresholds.py
uv run python scripts/ci/run_classifier_eval.py
uv run python scripts/ci/run_rag_eval.py
```
- Check `evals/eval_thresholds.yaml` has non-zero thresholds.
- Verify golden sets exist: `evals/classification/golden.jsonl`, `evals/rag/golden.jsonl`.
- For real Azure evals: set `USE_REAL_AZURE_EVALS=1` and verify credentials.

### Redaction Leak Gate

**Symptom**: `make security` fails on redaction.

**Debug**:
```bash
uv run python scripts/ci/check_redaction_leaks.py
```
- Verifies `app.infra.redaction.redact_string()` sanitizes fake probes.
- Fake probe fixtures in `tests/fixtures/ci/security/` are expected hits.

### Static Secret Grep Gate

**Symptom**: `make security` fails on static grep.

**Debug**:
```bash
uv run python scripts/ci/check_static_secret_patterns.py
```
- Scans for `sk-`, `password=`, `passwd=`, `SECRET_KEY=` patterns.
- If a real file triggers: verify it's not actually a secret; add to allowlist in `scripts/ci/secret_scan.py` if it's a false positive.

### Model Artifact Gate

**Symptom**: `make security` fails on model artifacts.

**Debug**:
```bash
uv run python scripts/ci/check_model_artifacts.py
```
- Requires model card at `artifacts/evals/model_card.json`.
- Passes gracefully when no card exists (CI without model artifacts).
- Verify SHA-256 matches with `sha256sum artifacts/path/to/model.pt`.

### Startup Failure Gate

**Symptom**: `make security` fails on startup checks.

**Debug**:
```bash
uv run python scripts/ci/check_startup_failures.py
```
- Requires Vault to be reachable for the negative test.
- Each check verifies system fails closed, not succeeds.

### Tracing Config Gate

**Symptom**: `make security` fails on tracing.

**Debug**:
```bash
uv run python scripts/ci/validate_tracing.py
```
- In CI without LangSmith: passes gracefully (non-fatal).
- In production: verify `LANGSMITH_API_KEY` and `LANGSMITH_PROJECT` are set.

### Docker Build Gate

**Symptom**: `docker compose build` fails.

**Debug**:
```bash
docker compose build --no-cache 2>&1 | tail -30
```
- Check `Dockerfile` base image availability.
- Verify `.dockerignore` excludes unnecessary files.

### Smoke Stack Gate

**Symptom**: `make smoke` fails.

**Debug**:
```bash
docker compose up -d postgres redis minio vault
docker compose logs --tail 20 vault model_server backend
curl -v http://localhost:8000/health/live
```
- Wait for all health checks to pass before smoke test.
- Model server requires valid classifier artifacts.

### Docs Validation Gate

**Symptom**: `make docs` fails.

**Debug**:
```bash
uv run python scripts/ci/validate_docs.py
```
- Verifies all 6 required docs exist and have reasonable content.
- Checks README has setup, architecture, commands, and demo sections.

### MinIO Storage Gate

**Symptom**: Eval report storage fails.

**Debug**:
- CI: verify MinIO is running at expected endpoint.
- Local: falls back to `evals/reports/` — check directory permissions.

### Previous Green Diff Gate

**Symptom**: Regression diff fails.

**Debug**:
- First CI run: no previous report — normal.
- Subsequent runs: check recent green reports in `evals/reports/` or MinIO.
- Regression > 2 percentage points triggers failure with metric names.

### Report Diffing Gate

**Symptom**: `compare_previous_green_report.py` fails.

**Debug**:
```bash
uv run python scripts/ci/compare_previous_green_report.py
```
- Compares current `evals/reports/eval_report.json` against last green.
- Ignores when no previous report exists (first run).

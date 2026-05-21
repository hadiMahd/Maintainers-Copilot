# Runbook

## Start Stack

```bash
cp .env.example .env
docker compose up -d vault postgres redis minio
uv run python scripts/seed_vault_from_env.py .env
docker compose up -d migrations backend
```

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
uv run python scripts/build_rag_index.py
```

For testing without real embeddings:
```bash
uv run python scripts/build_rag_index.py --fake
```

Expected: `artifacts/rag/embedding_comparison.json` created with both embedding candidates recorded.

## Evaluate RAG Pipeline

```bash
uv run python scripts/evaluate_rag.py --exploratory
```

Expected: `evals/rag_eval_report.json` created with baseline-vs-advanced comparison, judge_id, embedding comparison, and disagreement notes.

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

This publishes the UI at `http://localhost:8501` and points it at the backend
service with `MAINTAINER_COPILOT_UI_BASE_URL=http://backend:8000`.

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

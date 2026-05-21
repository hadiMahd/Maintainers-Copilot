# Architecture

## Layer Ownership Table

| Layer | Directory | Owns | Forbidden From |
|---|---|---|---|
| api | `app/api/` | HTTP routing, dependency wiring, request parsing, response mapping | SQLAlchemy, Redis, hvac, minio, httpx direct calls |
| services | `app/services/` | Business workflows, transaction boundaries, cache invalidation | SQLAlchemy sessions, Redis clients, external HTTP calls |
| repositories | `app/repositories/` | SQL and persistence only | Business logic, workflow orchestration |
| domain | `app/domain/` | Pydantic domain models, errors | Imports from `app/infra/` or `app/core/` |
| infra | `app/infra/` | Adapters for Vault, MinIO, Redis, DB, external APIs, LLM, MLflow, redaction | Business logic, route handling |
| core | `app/core/` | Application factory, config, lifespan, logging, middleware | No forbidden targets; serves as cross-cutting layer |

## Dependency Flow

Allowed call directions:

- `api` → `services` → `repositories` → `domain`
- `infra` → `domain`
- `core` → all layers

Routes may not call SQLAlchemy, Redis, hvac, minio, or httpx directly. They must call `app/services/` functions only.

## Guardrails

1. **Route Isolation**: `app/api/` handlers must never import or call SQLAlchemy, Redis, hvac, minio, or httpx directly. They call `app/services/` functions only.
2. **Domain Purity**: `app/domain/` has no imports from `app/infra/` or `app/core/`.
3. **No Import Side Effects**: No module may make network connections at import time.
4. **Structured Logging**: All log output is JSON via structlog with `request_id` bound via contextvars.
5. **Error Shape**: Every error response is `{error_code, message, request_id}` with no stack traces.

## Model Server Architecture

The model server is a separate FastAPI application in `model_server/` that loads a classifier artifact during lifespan and serves predictions.

### Model Server Layers

| Layer | Directory | Owns | Forbidden From |
|---|---|---|---|
| api | `model_server/api/` | HTTP routing, request parsing, response mapping | Direct model loading, file I/O |
| services | `model_server/services/` | Inference orchestration, input-size checks | File I/O, direct adapter calls |
| infra | `model_server/infra/` | Artifact loading, hash validation | Route handling |
| domain | `model_server/domain/` | Prediction and error schemas | Imports from infra |

### Classifier Endpoint

- **POST /classifier/predict**: Accepts title, body, and/or comments. Returns a typed label (`bug`, `feature`, `docs`, `question`), optional confidence, and semantic `model_version`.
- **Model loading**: The classifier artifact is loaded once during FastAPI lifespan, never at import time or per request.
- **Unavailable model**: Returns 503 with `classifier_model_unavailable` error code and a structured reason (`missing_artifact`, `invalid_artifact`, `hash_mismatch`, `startup_load_failed`). No stack traces are exposed.
- **Input limits**: Title ≤ 512 chars, body ≤ 16,000 chars, comments ≤ 100 items, each comment ≤ 4,000 chars.
- **Latency target**: P95 ≤ 500ms for one request on a warm, preloaded, single-process model-server measured across 30 sequential representative requests.

## Extension Points

- New routes: add files under `app/api/routes/` and register them at the bottom of each route module by importing `app` from `app/core.application`.
- New services: add files under `app/services/`.
- New repositories: add files under `app/repositories/`.
- New infra adapters: add files under `app/infra/`.

## RAG Pipeline Architecture

### Layer Ownership

| Layer | Files | Owns | Key Classes |
|-------|-------|------|-------------|
| services | `app/services/rag_*.py` | Ingestion, chunking, indexing, retrieval, generation, evaluation, snapshot workflows | `RAGIngestionService`, `RAGRetrievalService`, `RAGGenerationService`, `RAGEvaluationService`, `RAGSnapshotService`, `RAGIndexService` |
| repositories | `app/repositories/rag_*.py` | PostgreSQL/pgvector persistence: chunk search, embedding upsert, snapshot storage | `RAGChunkRepository`, `RAGEmbeddingRepository`, `RAGSnapshotRepository` |
| infra | `app/infra/*_client.py` | Provider seams: embedding, reranker, generation, judge | `LocalEmbeddingClient`, `FakeEmbeddingClient`, `CrossEncoderReranker`, `FakeRerankerClient`, `FakeGenerationClient`, `TokenOverlapJudge` |
| domain | `app/domain/rag.py` | Pydantic models and domain exceptions only | `RAGChunk`, `RetrievalQuery`, `RetrievalResult`, `GroundedAnswer`, `EvalReport`, `SnapshotRecord` |
| core | `app/core/config.py` | `RAGSettings` — embedding candidates, hybrid weights, reranker model, eval thresholds | `AppSettings` |

### Data Flow

```
scripts/ingest_docs.py ──→ RAGIngestionService ──→ RAGSource + RAGChunk (JSONL)
scripts/ingest_resolved_issues.py ──→ RAGIngestionService ──→ ResolvedIssueAnswer + RAGChunk (JSONL)
scripts/build_rag_index.py ──→ RAGIndexService ──→ EmbeddingClient ──→ RAGEmbedding + embedding_comparison.json
scripts/evaluate_rag.py ──→ RAGEvaluationService ──→ (GenerationClient + TokenOverlapJudge) ──→ rag_eval_report.json
```

### Async Safety

- All database access uses `AsyncSession` via `sqlalchemy.ext.asyncio`
- CPU-bound `SentenceTransformer` and `CrossEncoder` calls are NOT called in async request paths
- When wired into async code (Phase 7+), wrap with `asyncio.to_thread()`
- Long-running ingestion, embedding, and evaluation stay in scripts/jobs

### Provider Seams

All external model calls use fake adapters by default:
- Embedding: `FakeEmbeddingClient` (hash-based deterministic)
- Reranker: `FakeRerankerClient` (identity pass)
- Generation: `FakeGenerationClient` (hash-based deterministic)
- Judge: `TokenOverlapJudge` (token-overlap F1, zero-dependency)

Azure/Vault-backed adapters exist as config seams, enabled when credentials are present in settings.

## Phase 6 Auth, Memory, and Audit Architecture

### Key Services

| Service | Responsibility |
|---|---|
| `AuthService` | Registration, login, refresh rotation, current-user lookup, transaction boundaries |
| `AdminInvitationService` | Invitation creation, acceptance, role-change hooks, invitation audit linkage |
| `ShortTermMemoryService` | Redis-backed short-term memory with TTL and pre-persistence redaction |
| `LongTermMemoryService` | Explicit semantic write-memory, same-user recall, embedding boundary, audit linkage |
| `AuditService` | Safe audit metadata shaping and audit-log listing |

### Key Repositories

| Repository | Responsibility |
|---|---|
| `UserRepository` | User persistence and role updates |
| `TokenSessionRepository` | Refresh-session create/rotate/revoke operations |
| `AdminInvitationRepository` | Invitation create, lookup, and acceptance state changes |
| `MemoryRepository` | Durable semantic memory create and same-user semantic search |
| `AuditLogRepository` | Audit row creation and ordered listing |

### Key Infra Adapters

| Adapter | Responsibility |
|---|---|
| `PasswordHasher` | Argon2id hashing and verification |
| `TokenSigner` | RS256 JWT signing and verification |
| `RedisMemoryAdapter` | User-scoped Redis TTL storage for short-term memory |
| `MemoryEmbeddingClient` | Async-safe deterministic embedding generation via `asyncio.to_thread` |
| `vault_client` helpers | Vault bootstrap and JWT signing-key resolution |
| `redaction` helpers | Secret-safe shaping before memory, audit, logs, and traces |

### Phase 6 Data Flow

```
POST /auth/register
  -> AuthService.register()
  -> UserRepository.create()
  -> session.commit()

POST /memory/short-term
  -> ShortTermMemoryService.write_memory()
  -> redact_short_term_memory_value()
  -> RedisMemoryAdapter.set()

POST /memory/long-term
  -> LongTermMemoryService.write_memory()
  -> redact_long_term_memory_content()
  -> MemoryEmbeddingClient.embed()  # asyncio.to_thread boundary
  -> MemoryRepository.create()
  -> AuditLogRepository.create(action="memory.write")
  -> session.commit()

POST /memory/long-term/recall
  -> LongTermMemoryService.recall_memory()
  -> MemoryEmbeddingClient.embed()
  -> MemoryRepository.search_same_user_semantic()
  -> safe redacted response items
```

### Boundary Notes

- Routes remain thin request/response mapping and dependency wiring only.
- Repositories never commit or roll back.
- Audit linkage for memory writes is stored as safe `audit_log_id` metadata on the memory row.
- Recall does not create memory and does not write audit rows in Phase 6.

## Phase 7 Chat Backend Architecture

### Phase 7 Ownership

| Layer | Files | Responsibility |
|---|---|---|
| api | `app/api/routes/chat.py` | Authenticated `/chat` HTTP boundary and SSE response creation only |
| domain | `app/domain/chat.py`, `app/domain/chat_tools.py` | Chat request/event state, tool schemas, safe tool/LLM contracts |
| services | `app/services/chatbot_service.py`, `app/services/chatbot_graph_service.py`, `app/services/tool_execution_service.py`, `app/services/conversation_state_service.py`, `app/services/chat_tracing_service.py`, `app/services/chat_rag_snapshot_coordinator.py` | Request validation, bounded context shaping, graph orchestration, tool execution, tracing, snapshot coordination |
| infra | `app/infra/llm_adapter.py`, `app/infra/chatbot_graph.py`, `app/infra/model_server_tools.py`, `app/infra/rag_tool_client.py`, `app/infra/memory_tool_client.py`, `app/infra/conversation_state_adapter.py`, `app/infra/prompt_registry.py`, `app/infra/tracing.py` | Provider seams, prompt loading, Redis conversation-state storage, LangGraph/fallback wrapper, tracing adapter seams |
| core | `app/core/config.py`, `app/core/lifespan.py` | Typed chat settings and startup wiring for prompts, adapters, and tool clients |

### Phase 7 Request Flow

```text
POST /chat
  -> get_current_user()
  -> ChatbotService.execute_chat()
    -> ConversationStateService.read_conversation()
    -> ChatTracingService.start_chat_trace()
    -> ChatbotGraphService.run()
      -> LLM adapter
      -> ToolExecutionService.execute()
      -> ChatRAGSnapshotCoordinator.store_snapshot() when RAG succeeds
    -> ConversationStateService.append_exchange()
  -> StreamingResponse(text/event-stream)
```

### Phase 7 Boundary Notes

- The chat route does not import `sqlalchemy`, `redis`, `hvac`, `minio`, or `httpx`.
- The graph contains one primary LLM node plus support nodes only: `llm`, `execute_tools`, `finalize`.
- Tool clients stay in `app/infra/`; service code depends on project-owned seams, not provider SDKs.
- Short-term chat state reuses Redis infrastructure through a chat-specific adapter instead of direct route-level Redis access.

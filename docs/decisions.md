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

## Phase 4 NER and Summarization Decisions

**NER Approach**: Deterministic code-shaped entity extraction via regex-based spaCy pipeline.

- **Method**: Custom regex patterns organized by entity type priority, matched sequentially with non-overlapping span exclusion. spaCy blank English pipeline provides the framework; all 10 entity types covered: `file_path`, `function_name`, `class_name`, `package_name`, `version_number`, `error_code`, `url`, `stack_trace_marker`, `environment_name`, `command_snippet`.
- **Priority Order**: Higher-specificity types (stack_trace_marker, url, file_path) matched before lower-specificity types (class_name, environment_name) to prevent greedy matches.
- **Duplicate Handling**: Entities with identical (text, type, source_field, start, end) tuples are collapsed. Different spans of the same text are preserved.
- **Confidence**: Optional field, not populated — EntityRuler matches are deterministic, not probabilistic. Future phases may add confidence if a model-based NER approach is adopted.
- **Alternatives Rejected**: Pure spaCy EntityRuler token patterns (tokenization breaks code paths), pretrained NER model (does not cover code-shaped entities).

**Summarization Approach**: Azure OpenAI via LangChain `AzureChatOpenAI` with fake adapter test seam.

- **Provider Stack**: `langchain-openai` + `langchain-core`, same Azure OpenAI credentials (endpoint, api_key, model) as Phase 3 LLM baseline.
- **Timeout**: Fixed 15-second hard timeout per the spec requirement. Exceeded timeout produces `summarizer_timeout` error, never fallback content.
- **Fake Adapter**: `FakeSummarizationAdapter` returns deterministic hash-based summaries for automated tests. Supports configurable failure modes (timeout, unavailable) for testing error paths.
- **LangSmith**: Tracing enabled when `LANGCHAIN_API_KEY` is present in environment. Disabled by default for test/dev without credentials.
- **Response Shape**: `summary`, `key_facts`, `unresolved_questions` always present. `suggested_next_step` optional — omitted when the adapter cannot produce one.

**Input Validation**:
- Combined character count (title + body + all comments) must not exceed 8,000. Exceeding returns `invalid_tool_input` (422).
- At least one non-blank field required. Empty comments (whitespace-only) are normalized and excluded before entity extraction and prompt assembly.

**Error Handling**:
- `invalid_tool_input` (422): Combined input over 8,000 chars or no non-blank content.
- `ner_extraction_failed` (500): Pipeline not initialized or execution error.
- `summarizer_unavailable` (503): Adapter not configured or explicitly set unavailable.
- `summarizer_timeout` (503): Request exceeded 15-second timeout.
- `tool_execution_failed` (500): Unexpected summarization adapter failure.
- `internal_error` (500): Unexpected NER pipeline failure.

**Redaction**:
- Full title/body/comments never logged — only length metadata.
- `redact_issue_analysis_metadata()` keeps only safe keys (request_id, tool_name, combined_characters, entity_count, entity_types, etc.).
- `redact_log_payload()` replaces title/body/comments with length-only fields.

**Tracing**:
- Each request receives a `request_id` (from `X-Request-ID` header or auto-generated UUID4) and a `trace_id` (always auto-generated UUID4).
- Both IDs are returned in response headers: `X-Request-ID`, `X-Trace-ID`.
- Redaction applied before any metadata reaches logs or trace spans.

**Alternatives Rejected**:
- Direct `httpx` to Azure OpenAI: rejected in favor of LangChain adapter pattern for test seam and consistency with Phase 3.
- Silent truncation of oversized input: rejected because callers wouldn't know output is incomplete.
- Fallback summary content when Azure unavailable: rejected per spec requirement — explicit errors prevent callers from treating synthetic text as real model output.
- spaCy `en_core_web_sm` model: rejected — blank English pipeline with regex patterns is sufficient and avoids 11MB model download.

## Phase 5 Advanced RAG Pipeline Decisions

### Chunking Strategy: Parent-Document Retriever

**Decision**: Use parent-document retriever chunking — small child chunks for embedding and retrieval, with `parent_id` linkage back to the full source document for generation context.

- **Rationale**: Documentation headings, code blocks, lists, and issue-answer boundaries carry structure that fixed-size naive chunking discards. The parent-document retriever preserves provenance while keeping embedded child units small enough for accurate similarity search.
- **Child chunk size**: ~300 tokens by default, split on paragraph boundaries with adjacent merging.
- **Stable IDs**: `chunk_id` derived from `hash(parent_id : chunk_index)`, ensuring repeatable identifiers across reruns.
- **Baseline comparison**: Naive fixed-size chunking + pure dense retrieval serves as the evaluation baseline.
- **Alternatives Rejected**: Fixed-size chunks only (used as baseline but rejected for advanced pipeline), LLM-generated chunking (adds cost and non-determinism).

### Retrieval Strategy: Sparse + Dense + Weighted Hybrid

**Decision**: Support all three retrieval modes (sparse, dense, hybrid) with the advanced pipeline defaulting to weighted hybrid.

- **Sparse**: PostgreSQL full-text search (`tsvector`/`tsquery`) over chunk text and title. Provides exact term matching for file paths, error codes, and maintainer terminology.
- **Dense**: pgvector cosine similarity (`<=>`) over chunk embeddings. Captures semantic similarity across paraphrased queries.
- **Hybrid**: Normalized score merging with configurable weights (default: 0.3 sparse + 0.7 dense). Each score family is min-max normalized independently before weighted combination.
- **Score normalization**: Sparse and dense raw scores are independently min-max normalized. Dense cosine values are not pre-transformed (cosine range -1..1 → 0..1 remapping optional).
- **Weights configurable** via `RAGSettings.hybrid_sparse_weight` / `hybrid_dense_weight`.
- **Alternatives Rejected**: Pure dense retrieval (used in baseline but rejected as default advanced), learned rank fusion (needs more training data).

### Reranking: Small Cross-Encoder

**Decision**: Apply a small cross-encoder reranker over top-k hybrid candidates for final relevance ordering.

- **Default model**: `cross-encoder/ms-marco-MiniLM-L-6-v2` (~80MB, sentence-transformers).
- **Configurable** via `RAGSettings.reranker_model_name`.
- **Async safety**: Cross-encoder calls are synchronous CPU work. When wired into async request paths, wrap with `asyncio.to_thread(reranker.rerank, ...)`.
- **Fake seam**: `FakeRerankerClient` returns candidates unchanged (identity pass) for tests.
- **Alternatives Rejected**: Large reranker models (add latency), LLM-based reranking (adds cost/non-determinism).

### Query Transformation: Optional and Toggleable

**Decision**: Optional query transformation expands maintainer questions with technical synonyms before retrieval. Toggleable per query/eval mode.

- **Method**: Keyword-based term expansion dictionary (not LLM-based). Adds domain-specific terms (e.g., "install" → "installation setup pip venv").
- **Toggle**: `RetrievalQuery.query_transformation_enabled` boolean.
- **Eval**: Evaluation records both modes so reviewers can measure transformation impact.
- **Alternatives Rejected**: LLM-based query rewriting (adds latency/cost), no transformation at all (loses domain context).

### Embedding Model Comparison

**Decision**: Compare at least two embedding candidates — local `all-MiniLM-L6-v2` (384-dim, CPU-feasible) and Azure `text-embedding-3-small` (1536-dim, optional).

- **Comparison output**: `artifacts/rag/embedding_comparison.json` records dimensions, chunks embedded, and status for both candidates.
- **Azure path**: Optional — defaults to `unavailable` status when credentials are absent.
- **Local model**: Loaded via `sentence_transformers.SentenceTransformer` with `asyncio.to_thread` annotation for async safety.
- **Alternatives Rejected**: Single embedding model (spec requires comparison), large models (too heavy for CI).

### Evaluation: Baseline vs Advanced

**Decision**: Evaluate the naive baseline and advanced pipeline on the same 25-example golden set using a frozen token-overlap judge for CI metrics.

- **Golden set**: `evals/rag_golden_set.jsonl` — 25 question-answer pairs with expected chunk IDs.
- **Disagreement notes**: 5 hand-labeled examples with disagreement annotations recorded in the report.
- **Metrics**: hit@5, MRR@10, faithfulness, answer relevancy, retrieval latency (p50/p95), generation latency (p50/p95).
- **Judge**: `TokenOverlapJudge` — frozen unigram-F1 scorer, zero-dependency, deterministic, records stable `judge_id` = `token-overlap-f1-v1`.
- **Optional RAGAS**: `NonCIJudgeStub` — config seam for RAGAS-style metrics, raises `NotImplementedError` in this pass.
- **Threshold gate**: Advanced must beat baseline on hit@5 and MRR@10. Gate bypassed with `--exploratory` flag.
- **Report**: `evals/rag_eval_report.json` — redacted before persistence.
- **Alternatives Rejected**: LLM judge (adds cost/non-determinism), no gate (constitution requires evals), single-mode evaluation (spec requires baseline comparison).

### Duplicate Embedding Prevention

**Decision**: Skip duplicate embeddings by `content_hash` + embedding model. Unchanged content across reruns produces the same hash and is not re-embedded.

- **Check**: `RAGEmbeddingRepository.exists_by_hash_and_model()` queries before embedding.
- **Filter**: `RAGIndexService.filter_duplicate_embeddings()` removes duplicates in batch.
- **Alternatives Rejected**: Deduplicate by chunk ID only (IDs can change across reruns), text prefix dedup (not collision-resistant).

### Classifier Data Leakage Prevention

**Decision**: Issue sources from classifier training data are excluded from the RAG corpus using explicit `classifier_source_ids` exclusion set.

- **Mechanism**: `RAGIngestionService` accepts a `classifier_source_ids` parameter and skips matching issues.
- **Command**: `scripts/ingest_resolved_issues.py --classifier-source-ids <path>` loads exclusion list.
- **Alternatives Rejected**: No leakage check (violates eval integrity), automatic overlap detection (less traceable).

### Snapshot Storage: Redacted + 50-Conversation Retention

**Decision**: Store redacted retrieved-chunk snapshots for chat-phase conversation replay, bounded to the last 50 conversations.

- **Redaction**: `redact_snapshot_row()` strips raw content, keeps only chunk IDs, scores, and safe metadata.
- **Retention**: `prune_oldest()` in `RAGSnapshotRepository` deletes snapshots beyond the 50-conversation window using `MAX(created_at)` subquery.
- **Metadata**: Each snapshot carries `conversation_id`, `message_id`, and `trace_id` for correlation.
- **Alternatives Rejected**: Full-chunk storage (violates redaction), unlimited retention (unbounded growth), no snapshots (chat debugging needs evidence).

### Run Configuration Summary

| Config Key | Default | Purpose |
|------------|---------|---------|
| `rag_embedding_model` | `all-MiniLM-L6-v2` | Local embedding model |
| `rag_embedding_dim` | 384 | Embedding vector dimension |
| `rag_embedding_candidates` | `[all-MiniLM-L6-v2, text-embedding-3-small]` | Models to compare |
| `rag_hybrid_sparse_weight` | 0.3 | Sparse score weight in hybrid merge |
| `rag_hybrid_dense_weight` | 0.7 | Dense score weight in hybrid merge |
| `rag_reranker_model_name` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Cross-encoder model |
| `rag_reranker_top_k` | 10 | Candidates passed to reranker |
| `rag_snapshot_retention_conversations` | 50 | Max conversations retained |
| `rag_generation_timeout_seconds` | 30 | Generation timeout |
| `rag_eval_hit_at_5_threshold` | 0.0 | Threshold gate (baseline-permissive) |
| `rag_eval_mrr_at_10_threshold` | 0.0 | Threshold gate (baseline-permissive) |

## Phase 6 Auth, Memory, and Audit Decisions

### Auth Implementation Strategy

**Decision**: Use project-owned authentication services and repositories instead of adopting FastAPI Users as the primary runtime abstraction.

- **Rationale**: Phase 6 requires service-owned transaction boundaries, Vault-resolved RS256 signing keys at startup, refresh-session rotation/revocation, first-admin bootstrap, role-change audit rows, and explicit memory/audit workflows. A project-owned implementation keeps those boundaries direct and testable.
- **What remains library-shaped**: Standard FastAPI dependency injection, pydantic validation, SQLAlchemy async sessions, and PyJWT/argon2 adapters.
- **Alternatives Rejected**: FastAPI Users end-to-end (would blur transaction ownership and persistence seams), fully stateless refresh flow (does not support rotation/revocation requirements).

### JWT and Bootstrap Policy

**Decision**: Use RS256 access tokens with the private/public key pair resolved from Vault during lifespan startup.

- **Private key**: Used only for signing, never persisted outside Vault or logs.
- **Public key**: Used for token verification.
- **Failure mode**: If the signing key is unavailable, token issuance fails safely with `signing_key_unavailable` and the first-admin bootstrap script fails loudly.
- **Bootstrap path**: `scripts/seed_admin.py` creates the initial admin only when no admin exists. After that, all additional admin access is granted through invitation acceptance.

### Short-Term Memory Decision

**Decision**: Use Redis-backed user-scoped short-term memory with a default TTL of 1,800 seconds (30 minutes).

- **Rationale**: Matches a single conversation session boundary while keeping reads/writes fast and naturally expiring.
- **Scope key**: `short_term_memory:{user_id}:{conversation_id}:{key}`
- **Isolation**: Same conversation/key pairs from different users never collide.
- **Expiry policy**: Expired values return a safe empty result (`value=None`, `expires_at=None`) rather than an error.

### Long-Term Memory Decision

**Decision**: Support only explicit semantic long-term memory writes in Phase 6.

- **Write boundary**: Only `POST /memory/long-term` creates durable memory.
- **No auto-write**: Normal authenticated requests and recall requests never create memory.
- **Stored payload**: Redacted semantic memory text, content hash, embedding vector, source label, and safe metadata.
- **Memory type restriction**: `semantic` only. `episodic` and `procedural` are rejected with structured validation errors.

### Embedding Strategy for Phase 6

**Decision**: Use a deterministic local embedding adapter for Phase 6 semantic memory writes and recall, with the blocking vector generation step wrapped in `asyncio.to_thread`.

- **Rationale**: Satisfies the semantic recall requirement without introducing a new external model dependency for this phase.
- **Async safety**: `MemoryEmbeddingClient.embed()` offloads the sync vector derivation path to `asyncio.to_thread`.
- **Scope note**: This embedding path is for Phase 6 explicit memory only, not a general RAG retrieval strategy.

### Redaction Before Persistence Decision

**Decision**: Redaction runs before short-term writes, long-term writes, embeddings, audit metadata, logs, and traces.

- **Short-term memory**: `redact_short_term_memory_value()` preserves safe labels like `password=` while redacting the secret value.
- **Long-term memory**: `redact_long_term_memory_content()` applies the same secret-safe shaping before embedding and persistence.
- **Audit metadata**: `build_memory_write_metadata()` records only bounded fields (`memory_type`, `content_hash`, `content_length`, `redaction_applied`, `source`) and never stores raw content.

### Audit Action Policy

**Decision**: Reserve stable action names up front and use them consistently for implemented Phase 6 workflows.

- **Implemented in Phase 6**: `memory.write`, `role.change`, `admin_invitation.create`
- **Reserved for later phases**: `widget_config.create`, `widget_config.update`, `widget_config.delete`, `conversation.delete`
- **Atomicity**: Successful long-term memory writes and invitation acceptance create exactly one corresponding audit row in the same transaction.

### Recall Policy

**Decision**: Cross-conversation recall is same-user only and returns only explicitly written semantic memory.

- **Same-user scope**: Repository recall queries filter strictly by `owner_user_id`.
- **No leakage**: Another user cannot recall someone else's memory even if the query text matches.
- **Empty result behavior**: No-match recall returns `{items: []}` safely.
- **Response shape**: Recalled items return redacted content plus `audit_log_id` linkage, never raw secret material.

## Phase 7 Single Tool-Calling Chat Decisions

### One Assistant, One Tool Loop

**Decision**: Build the chat backend around one primary tool-calling LLM loop with three graph nodes only: `llm`, `execute_tools`, and `finalize`.

**Rationale**:
- Preserves the constitution's single-LLM constraint.
- Keeps the graph observable without introducing planner, router, critic, or memory agents.
- Lets tests assert the graph shape directly.

**Alternatives Rejected**:
- Planner/router nodes: rejected because they create additional agent roles.
- Multi-agent orchestration: rejected as out of scope for Phase 7.

### Prompt Files Are Version-Controlled Runtime Inputs

**Decision**: Keep chatbot behavior prompts in `prompts/chatbot_system.md`, `prompts/chatbot_tool_policy.md`, and `prompts/chatbot_untrusted_context.md`, loaded through `PromptRegistry`.

**Rationale**:
- Makes prompt behavior reviewable and diffable.
- Keeps routes and services free of embedded prompt strings.
- Produces a stable prompt bundle version fingerprint for traces.

### Tool Execution Uses Typed Project-Owned Schemas

**Decision**: The assistant exposes five tools only: `classify_issue`, `extract_entities`, `summarize_issue`, `answer_project_question`, and `write_memory`.

**Rationale**:
- Matches the phase scope exactly.
- Keeps tool validation and timeout policy in one service.
- Allows deterministic fake tool clients in automated tests.

### Explicit Write-Memory Gating

**Decision**: `write_memory` remains unavailable unless explicit remember intent is detected from the current user message.

**Rationale**:
- Preserves the Phase 6 no-auto-write rule.
- Prevents ambiguous or implicit long-term memory creation.

### Untrusted RAG Context Wrapping

**Decision**: RAG results are returned to the LLM as explicitly wrapped untrusted context, and retrieved-chunk snapshots are created after successful RAG calls.

**Rationale**:
- Prevents retrieved text from overriding system or tool policy.
- Keeps trace/log review tied to a bounded snapshot ID instead of raw chunks.

### Tracing Backend and Run-ID Correlation

**Decision**: Use a project-owned tracing adapter with `fake` and LangSmith-shaped seams. Structured chat logs carry `trace_id` and `run_id` when available.

**Rationale**:
- Preserves testability without external credentials.
- Keeps Phase 7 logs and traces joinable.

## Phase 8 Streamlit Admin App Decisions

### Cookie-Backed Auth via streamlit-cookies-manager

**Decision**: Store the access token in a browser cookie using `streamlit-cookies-manager`. Restore from cookie on page refresh. Clear on explicit logout and on backend `401`. Limit `st.session_state` to non-secret UI/user state.

**Alternatives considered**:
- `st.session_state` only: rejected because state is lost on refresh.
- Local file storage: rejected because it creates persistent secret material outside the backend.
- Query parameters: rejected because URLs leak through history, logs, and screenshots.

### Admin Guard via Runtime st.navigation()

**Decision**: Use programmatic `st.navigation()` to build a role-based page list at runtime. Admin-only pages (`admin_widget_config`) are excluded from the page list for regular users, and no admin backend API calls are made for non-admin sessions.

**Alternatives considered**:
- Page-level `if role != admin: st.stop()`: rejected because the page entry is still visible in the sidebar.
- Hardcoded admin email allowlist: rejected because it bypasses backend authorization and drifts from backend roles.

### SSE Chat Streaming via httpx + st.write_stream()

**Decision**: The chat page uses `BackendAPIClient.chat_stream()` (httpx streaming client) and renders events via `st.write_stream()`. The full chat response is never buffered before display.

**Alternatives considered**:
- Polling: rejected because it adds latency and server load.
- Buffering full response before display: rejected because it defeats streaming UX.

### Typed Timeout Settings (30s REST, 70s SSE)

**Decision**: All backend calls use explicit `httpx.Timeout` values loaded from typed `StreamlitSettings` (30s REST, 70s SSE). Timeouts are not hardcoded in the client methods.

**Alternatives considered**:
- Default httpx timeouts: rejected because chat SSE needs a longer timeout than REST calls.
- Per-call timeout overrides: rejected because it scatters configuration across the codebase.

### Backend Widget Config and Memory Inspector Endpoints

**Decision**: Add minimal FastAPI routes, services, and repositories for widget configuration CRUD, embed snippet generation, and authorized memory inspection listing. These are added only where Phase 6/7 did not already provide them.

**Alternatives considered**:
- Direct database access from Streamlit: rejected because it violates architecture boundaries and bypasses backend authorization.
- Deferring to Phase 9: rejected because Phase 8 acceptance requires admin widget configuration and memory inspection through backend API calls.

### Embed Snippet Placeholder

**Decision**: The `WidgetConfigService.generate_embed_snippet()` returns a placeholder HTML snippet referencing the `widget_config_id`. Phase 9 will replace this with the actual embed `<script>` generation.

**Rationale**: The widget loader lives in Phase 9; Phase 8 needs only enough backend support to display a generated snippet in the admin UI.

## Phase 9 Embeddable Widget Decisions

### Loader Serving Strategy

**Decision**: The widget loader (`loader.js`) is served by the FastAPI backend at `GET /widget/loader.js` with `Cache-Control: no-cache` headers. The loader is a vanilla TypeScript file built by Vite as a separate entry point.

**Rationale**:
- Single origin for all widget assets simplifies CORS and CSP.
- Backend can inject dynamic configuration or feature flags in the future.
- Loader is tiny (< 5 KB gzip) so caching is less critical than correctness.

**Alternatives Rejected**:
- CDN-hosted loader: rejected because it adds an external dependency and complicates origin enforcement.
- Inline loader in the snippet: rejected because it prevents cache sharing across widget instances.

### Iframe Isolation

**Decision**: The widget runs inside an iframe served at `GET /widget/frame/{widget_id}`. The iframe shell sets `window.__WIDGET_ID__` and `window.__ORIGIN__` for the React app to read.

**Rationale**:
- Iframe provides CSS and JS isolation from the host page.
- CSP `frame-ancestors` header enforces origin allowlisting at the HTTP level.
- Bootstrap values avoid query-string exposure of widget IDs.

**Alternatives Rejected**:
- Shadow DOM only: rejected because CSS leakage and JS scope conflicts are harder to guarantee.
- Web Components: rejected because React integration is simpler with iframe + postMessage.

### Bundle Strategy

**Decision**: Vite builds two entry points — `loader` (vanilla TS, no React) and `main` (React app). The loader is named `assets/loader.js`; the React bundle is `assets/widget-[hash].js`. CSS is bundled with the React app.

**Rationale**:
- Loader must be tiny and framework-free for fast host-page injection.
- React bundle can be larger since it's loaded inside the iframe.
- Single build command (`npm run build`) produces both.

**Bundle Targets**:
- Loader: < 5 KB gzip
- Initial widget bundle: ≤ 150 KB gzip
- One standalone initial JS bundle (no code-split chunks)

### Origin Enforcement

**Decision**: Observed request `Origin` header is authoritative. `Referer` is used as fallback. Client-declared origin (e.g., in request body) is advisory only. All public widget endpoints fail closed if approved origin cannot be established.

**Rationale**:
- `Origin` header is set by the browser and cannot be spoofed by JavaScript.
- Fail-closed prevents accidental data leakage to unapproved hosts.
- Consistent enforcement across config, session, frame, and chat endpoints.

### Chat Message Separation from SSE URL

**Decision**: Raw user message content is submitted via `POST /public/widgets/{widget_id}/chat/messages` and stored server-side in a pending message map. The `GET /chat/stream` EventSource URL contains only `token` and `conversation_id` — never raw message content.

**Rationale**:
- SSE URLs appear in browser history, proxy logs, and server access logs.
- Raw message content in URLs violates privacy and security requirements.
- Server-side pending map ensures message-to-stream correlation without URL exposure.

### postMessage Channel Restriction

**Decision**: The widget uses `postMessage` exclusively for the resize channel (`maintainer-copilot-widget:resize`). No other message types are sent or accepted.

**Rationale**:
- Minimizes attack surface for cross-origin message injection.
- Resize is the only legitimate host↔widget communication needed.
- Static tests enforce this constraint in CI.

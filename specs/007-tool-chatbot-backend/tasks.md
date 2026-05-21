# Tasks: Single Tool-Calling Chatbot Backend

**Input**: Design documents from `/specs/007-tool-chatbot-backend/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED for critical behavior identified by the
constitution, plan.md, spec.md, and contracts. Write tests before or alongside
implementation and verify they fail before implementing the related behavior.

**Organization**: Tasks are grouped by user story to enable independent
implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files and has no
  dependency on incomplete tasks.
- **[Story]**: User story label for story phases only.
- Every task includes an exact file path.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add Phase 7 dependencies, prompt files, and module/test skeletons.

- [X] T001 Update Phase 7 runtime dependencies for LangGraph/LangChain tool calling in `pyproject.toml` and refresh `uv.lock`
- [X] T002 [P] Create version-controlled prompt files `prompts/chatbot_system.md`, `prompts/chatbot_tool_policy.md`, and `prompts/chatbot_untrusted_context.md`
- [X] T003 [P] Create Phase 7 source skeletons in `app/api/routes/chat.py`, `app/domain/chat.py`, `app/domain/chat_tools.py`, `app/services/chatbot_service.py`, `app/services/chatbot_graph_service.py`, `app/services/tool_execution_service.py`, `app/services/conversation_state_service.py`, `app/services/chat_tracing_service.py`, `app/services/chat_rag_snapshot_coordinator.py`, `app/infra/llm_adapter.py`, `app/infra/chatbot_graph.py`, `app/infra/model_server_tools.py`, `app/infra/rag_tool_client.py`, `app/infra/memory_tool_client.py`, `app/infra/conversation_state_adapter.py`, `app/infra/prompt_registry.py`, and `app/infra/tracing.py`
- [X] T004 [P] Create Phase 7 test skeletons in `tests/unit/test_chatbot_graph.py`, `tests/unit/test_tool_execution_service.py`, `tests/unit/test_chat_limits.py`, `tests/unit/test_write_memory_intent.py`, `tests/unit/test_untrusted_rag_context.py`, `tests/unit/test_retrieved_chunk_snapshots.py`, `tests/unit/test_chat_tracing.py`, `tests/unit/test_chat_redaction.py`, `tests/contract/test_chat_endpoint_contract.py`, `tests/integration/test_chat_successful_tool_call.py`, `tests/integration/test_chat_failed_tool_recovery.py`, `tests/integration/test_chat_trace_log_correlation.py`, and `tests/integration/test_chat_redis_state.py`
- [X] T005 [P] Add Phase 7 route-boundary placeholders for the chat route in `tests/test_route_boundaries.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared schemas, settings, adapters, and dependency wiring that
MUST be complete before user story work.

**CRITICAL**: No user story implementation should begin until this phase is
complete.

- [X] T006 [P] Add Phase 7 settings default and environment override tests for max tool calls, 60s full timeout, per-tool timeout, request/context limits, prompt paths, and tracing backend in `tests/test_config.py`
- [X] T007 Add chat settings for max tool calls, full timeout, per-tool timeout, request size, context size, recursion limit, prompt paths, and tracing backend in `app/core/config.py`
- [X] T008 [P] Implement chat request, stream event, graph state, limits, conversation state, trace root, and safe error Pydantic models in `app/domain/chat.py`
- [X] T009 [P] Implement tool definition, tool call, tool execution result, RAG tool result, retrieved snapshot reference, and memory-write intent models in `app/domain/chat_tools.py`
- [X] T010 [P] Add Phase 7 chat error classes and stable error codes in `app/domain/errors.py`
- [X] T011 Align chat structured error mapping with the existing top-level `error_code`/`request_id`/`trace_id` response shape in `app/api/error_handlers.py`
- [X] T012 [P] Add chat redaction helpers for user messages, prompts, tool payloads, LLM payloads, SSE events, and trace metadata in `app/infra/redaction.py`
- [X] T013 [P] Implement prompt registry loading and validation for `prompts/chatbot_system.md`, `prompts/chatbot_tool_policy.md`, and `prompts/chatbot_untrusted_context.md` in `app/infra/prompt_registry.py`
- [X] T014 [P] Define the project-owned tool-calling LLM adapter interface with fake and Azure LangChain seams in `app/infra/llm_adapter.py`
- [X] T015 [P] Define the LangSmith/fake tracing adapter interface and run/span metadata contracts in `app/infra/tracing.py`
- [X] T016 [P] Define async fake-compatible tool client seams in `app/infra/model_server_tools.py`, `app/infra/rag_tool_client.py`, and `app/infra/memory_tool_client.py`
- [X] T017 [P] Implement the chat conversation-state adapter seam that reuses Phase 6 Redis infrastructure in `app/infra/conversation_state_adapter.py`
- [X] T018 Implement FastAPI lifespan/dependency wiring for prompt registry, LLM adapter, tool clients, trace adapter, and conversation-state adapter in `app/core/lifespan.py`
- [X] T019 Register the `/chat` router without importing provider libraries in `app/api/routes/__init__.py`

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Chat With The Maintainer Copilot (Priority: P1) MVP

**Goal**: An authenticated maintainer can send a chat message and receive a safe
SSE stream from one assistant, with same-user short-term conversation state.

**Independent Test**: Authenticate as a user, POST `/chat`, receive ordered SSE
events, and verify conversation state is available only for that user.

### Tests for User Story 1

- [X] T020 [P] [US1] Add contract tests for authenticated `/chat`, unauthenticated rejection, request-size rejection, and SSE event shape in `tests/contract/test_chat_endpoint_contract.py`
- [X] T021 [P] [US1] Add integration tests for successful streamed chat response and same-user Redis conversation state in `tests/integration/test_chat_successful_tool_call.py` and `tests/integration/test_chat_redis_state.py`
- [X] T022 [P] [US1] Add integration tests for Redis-unavailable bounded degradation or structured failure with no automatic long-term memory writes in `tests/integration/test_chat_redis_state.py`
- [X] T023 [P] [US1] Add unit tests for single-LLM graph shape, no planner/router/critic/memory agents, and basic graph completion in `tests/unit/test_chatbot_graph.py`
- [X] T024 [P] [US1] Add unit tests for conversation state scoping, TTL use, and bounded context shaping in `tests/unit/test_chat_limits.py`

### Implementation for User Story 1

- [X] T025 [US1] Implement user-scoped short-term conversation state workflows in `app/services/conversation_state_service.py`
- [X] T026 [US1] Implement Redis-unavailable degraded/structured-failure behavior with no automatic long-term memory writes in `app/services/conversation_state_service.py`
- [X] T027 [US1] Implement the thin single-LLM LangGraph construction with one primary LLM node and support nodes only in `app/infra/chatbot_graph.py`
- [X] T028 [US1] Implement graph execution orchestration and bounded context assembly in `app/services/chatbot_graph_service.py`
- [X] T029 [US1] Implement authenticated SSE chat orchestration, event sequencing, and safe event shaping in `app/services/chatbot_service.py`
- [X] T030 [US1] Implement the `/chat` FastAPI route as a thin authenticated SSE boundary in `app/api/routes/chat.py`

**Checkpoint**: User Story 1 is independently functional and testable.

---

## Phase 4: User Story 2 - Use Maintainer Tools From One Assistant (Priority: P2)

**Goal**: The single assistant can call classifier, NER, summarization, RAG, and
explicit write_memory tools through typed schemas and safe tool results.

**Independent Test**: Send controlled messages that require each supported tool
and verify the expected tool schema is called and the safe result is included in
the response.

### Tests for User Story 2

- [X] T031 [P] [US2] Add unit tests for all five tool schemas, input validation, output validation, and unknown tool rejection in `tests/unit/test_tool_execution_service.py`
- [X] T032 [P] [US2] Add unit tests proving `write_memory` is called only for explicit remember intent and never for ambiguous requests in `tests/unit/test_write_memory_intent.py`
- [X] T033 [P] [US2] Add unit tests proving retrieved RAG context is marked untrusted and cannot override system/developer/tool policy in `tests/unit/test_untrusted_rag_context.py`
- [X] T034 [P] [US2] Add unit tests for redacted retrieved-chunk snapshot creation after RAG tool calls in `tests/unit/test_retrieved_chunk_snapshots.py`
- [X] T035 [P] [US2] Add integration tests for classifier, NER, summarization, RAG, and explicit write_memory tool calls in `tests/integration/test_chat_successful_tool_call.py`

### Implementation for User Story 2

- [X] T036 [US2] Implement classifier, entity extraction, summarization, RAG, and write_memory tool schemas in `app/domain/chat_tools.py`
- [X] T037 [US2] Implement model-server tool client calls for classifier, NER, and summarization in `app/infra/model_server_tools.py`
- [X] T038 [US2] Implement RAG answer tool client and safe RAG result mapping in `app/infra/rag_tool_client.py`
- [X] T039 [US2] Implement explicit write_memory tool client using Phase 6 memory services in `app/infra/memory_tool_client.py`
- [X] T040 [US2] Implement tool registry, tool validation, timeout execution, output validation, and structured tool results in `app/services/tool_execution_service.py`
- [X] T041 [US2] Implement RAG snapshot coordination that delegates to `app/services/rag_snapshot_service.py` in `app/services/chat_rag_snapshot_coordinator.py`
- [X] T042 [US2] Integrate tool-call execution, untrusted RAG context wrapping, and explicit memory-intent gating into `app/services/chatbot_graph_service.py`

**Checkpoint**: User Stories 1 and 2 both work independently.

---

## Phase 5: User Story 3 - Recover Gracefully From Tool Failures (Priority: P3)

**Goal**: A maintainer receives a safe partial response when a tool fails,
times out, returns invalid output, or a configured chat limit is reached.

**Independent Test**: Force one supported tool to fail during chat and verify
the stream returns a partial answer or safe failure response without a 500.

### Tests for User Story 3

- [X] T043 [P] [US3] Add integration tests for failed-tool recovery after a prior successful tool result in `tests/integration/test_chat_failed_tool_recovery.py`
- [X] T044 [P] [US3] Add unit tests for max tool calls, recursion limit, total timeout, per-tool timeout, request size, and context size behavior in `tests/unit/test_chat_limits.py`
- [X] T045 [P] [US3] Add contract tests for top-level `error_code` structured chat error responses and safe SSE error events in `tests/contract/test_chat_endpoint_contract.py`
- [X] T046 [P] [US3] Add unit tests for invalid, oversized, unsafe, and unknown tool output recovery in `tests/unit/test_tool_execution_service.py`

### Implementation for User Story 3

- [X] T047 [US3] Implement configured request-size and context-size validation before LLM/tool work in `app/services/chatbot_service.py`
- [X] T048 [US3] Implement max-tool-call and recursion-limit enforcement in `app/services/chatbot_graph_service.py`
- [X] T049 [US3] Implement total chat timeout and safe partial SSE completion behavior in `app/services/chatbot_service.py`
- [X] T050 [US3] Implement per-tool timeout, invalid output handling, unknown tool handling, and safe failed tool results in `app/services/tool_execution_service.py`

**Checkpoint**: User Stories 1, 2, and 3 are independently functional.

---

## Phase 6: User Story 4 - Trace And Redact Chat Activity (Priority: P4)

**Goal**: Operators can inspect LangSmith traces and structured logs for chat
runs without exposing raw user, tool, LLM, or RAG payloads.

**Independent Test**: Run chat with a tool and RAG retrieval, then verify one
trace root exists, LLM/tool/RAG spans exist, LangSmith run IDs appear in logs,
and all telemetry metadata is redacted.

### Tests for User Story 4

- [X] T051 [P] [US4] Add unit tests for trace root, LLM span, tool span, RAG retrieval span, fake tracing, and LangSmith run ID propagation in `tests/unit/test_chat_tracing.py`
- [X] T052 [P] [US4] Add unit tests for redaction of user messages, prompts, tool payloads, LLM payloads, SSE events, retrieved chunks, and trace metadata in `tests/unit/test_chat_redaction.py`
- [X] T053 [P] [US4] Add integration tests for successful and failed-tool trace/log correlation with LangSmith run IDs in `tests/integration/test_chat_trace_log_correlation.py`
- [X] T054 [P] [US4] Add tests for tracing adapter failure producing safe operational metadata without leaking internals in `tests/unit/test_chat_tracing.py` and `tests/integration/test_chat_trace_log_correlation.py`
- [X] T055 [P] [US4] Extend secret-leak tests to cover Phase 7 prompts, traces, logs, and spec artifacts in `tests/test_no_secrets.py`

### Implementation for User Story 4

- [X] T056 [US4] Implement chat tracing service for conversation roots, LLM spans, tool spans, RAG spans, and safe trace metadata in `app/services/chat_tracing_service.py`
- [X] T057 [US4] Implement LangSmith-enabled tracing adapter and fake test tracing adapter in `app/infra/tracing.py`
- [X] T058 [US4] Implement safe tracing-adapter failure handling that preserves chat response safety and redacted logs in `app/services/chat_tracing_service.py` and `app/infra/tracing.py`
- [X] T059 [US4] Integrate LangSmith run IDs and redacted structured log metadata into chat orchestration in `app/services/chatbot_service.py`
- [X] T060 [US4] Integrate LLM call trace metadata and redacted prompt/response metadata into `app/infra/llm_adapter.py`
- [X] T061 [US4] Ensure all chat stream, tool, RAG, and tracing payloads pass through redaction helpers in `app/infra/redaction.py`

**Checkpoint**: All user stories are independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, boundaries, and validation across Phase 7.

- [X] T062 [P] Update Phase 7 decisions for LangGraph, LangSmith tracing, tool calling, prompt files, untrusted RAG context, and explicit write_memory in `docs/decisions.md`
- [X] T063 [P] Update Phase 7 architecture ownership, request flow, and single-LLM constraint in `docs/architecture.md`
- [X] T064 [P] Update Phase 7 security/redaction rules for chat prompts, SSE events, tool payloads, RAG chunks, and LangSmith metadata in `docs/security.md`
- [X] T065 [P] Update Phase 7 runbook commands for chat startup, fake-provider testing, LangSmith verification, and failure recovery in `docs/runbook.md`
- [X] T066 [P] Update the Phase 7 quickstart with validated commands and final paths in `specs/007-tool-chatbot-backend/quickstart.md`
- [X] T067 Validate route boundaries and import side effects for Phase 7 in `tests/test_route_boundaries.py` and `tests/test_import_side_effects.py`
- [X] T068 Run the Phase 7 quickstart test matrix from `specs/007-tool-chatbot-backend/quickstart.md`
- [X] T069 Run full regression with `uv run pytest -q` and record the result in `specs/007-tool-chatbot-backend/tasks.md` (Result: 597 passed, 3 skipped, 81 warnings)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; can start immediately.
- **Foundational (Phase 2)**: Depends on Setup; blocks all user stories.
- **US1 (Phase 3)**: Depends on Foundation; MVP scope.
- **US2 (Phase 4)**: Depends on Foundation and can integrate with US1 graph/service seams.
- **US3 (Phase 5)**: Depends on US1/US2 because it validates recovery around chat and tool execution.
- **US4 (Phase 6)**: Depends on US1/US2/US3 behavior being observable, but its tests can be written once foundational tracing seams exist.
- **Polish (Phase 7)**: Depends on desired user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: MVP; no dependency on other stories after Foundation.
- **User Story 2 (P2)**: Adds tools to the US1 graph and remains independently testable through fake tool clients.
- **User Story 3 (P3)**: Adds failure/limit behavior around US1/US2 paths.
- **User Story 4 (P4)**: Adds observability/redaction coverage around all prior paths.

### Within Each User Story

- Required tests MUST be written and fail before implementation.
- Domain models before services.
- Infra adapters before service integration when provider/tool calls are needed.
- Services before routes.
- Core implementation before integration tests pass.
- Story complete before moving to the next priority unless staffed in parallel.

### Parallel Opportunities

- Setup tasks T002-T005 can run in parallel after T001 is understood.
- Foundational schema/adapter tasks T008-T010 and T012-T017 can run in parallel after T007 starts.
- US1 tests T020-T024 can run in parallel.
- US2 tests T031-T035 can run in parallel.
- US3 tests T043-T046 can run in parallel.
- US4 tests T051-T055 can run in parallel.
- Polish docs T062-T066 can run in parallel.

---

## Parallel Example: User Story 1

```bash
# Launch US1 tests together:
Task: "T020 [US1] tests/contract/test_chat_endpoint_contract.py"
Task: "T021 [US1] tests/integration/test_chat_successful_tool_call.py and tests/integration/test_chat_redis_state.py"
Task: "T023 [US1] tests/unit/test_chatbot_graph.py"
Task: "T024 [US1] tests/unit/test_chat_limits.py"

# Then implement the independent US1 components:
Task: "T025 [US1] app/services/conversation_state_service.py"
Task: "T027 [US1] app/infra/chatbot_graph.py"
```

## Parallel Example: User Story 2

```bash
# Launch US2 tests together:
Task: "T031 [US2] tests/unit/test_tool_execution_service.py"
Task: "T032 [US2] tests/unit/test_write_memory_intent.py"
Task: "T033 [US2] tests/unit/test_untrusted_rag_context.py"
Task: "T034 [US2] tests/unit/test_retrieved_chunk_snapshots.py"
Task: "T035 [US2] tests/integration/test_chat_successful_tool_call.py"

# Then implement tool adapters in parallel:
Task: "T037 [US2] app/infra/model_server_tools.py"
Task: "T038 [US2] app/infra/rag_tool_client.py"
Task: "T039 [US2] app/infra/memory_tool_client.py"
```

## Parallel Example: User Story 3

```bash
# Launch US3 tests together:
Task: "T043 [US3] tests/integration/test_chat_failed_tool_recovery.py"
Task: "T044 [US3] tests/unit/test_chat_limits.py"
Task: "T045 [US3] tests/contract/test_chat_endpoint_contract.py"
Task: "T046 [US3] tests/unit/test_tool_execution_service.py"
```

## Parallel Example: User Story 4

```bash
# Launch US4 tests together:
Task: "T051 [US4] tests/unit/test_chat_tracing.py"
Task: "T052 [US4] tests/unit/test_chat_redaction.py"
Task: "T053 [US4] tests/integration/test_chat_trace_log_correlation.py"
Task: "T055 [US4] tests/test_no_secrets.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational.
3. Complete Phase 3: User Story 1.
4. Stop and validate authenticated SSE chat plus same-user Redis state.
5. Demo the basic chat endpoint before adding tool complexity.

### Incremental Delivery

1. Setup + Foundation -> shared schemas, settings, prompt registry, fake seams.
2. US1 -> authenticated SSE chat and Redis conversation state.
3. US2 -> five typed tools and explicit memory intent.
4. US3 -> graceful tool failure and limit behavior.
5. US4 -> LangSmith tracing, log correlation, and redaction hardening.
6. Polish -> docs, quickstart, boundary checks, and full regression.

### Validation Commands

```bash
uv run pytest tests/contract/test_chat_endpoint_contract.py
uv run pytest tests/test_config.py
uv run pytest tests/unit/test_chatbot_graph.py tests/unit/test_tool_execution_service.py tests/unit/test_chat_limits.py
uv run pytest tests/unit/test_write_memory_intent.py tests/unit/test_untrusted_rag_context.py tests/unit/test_retrieved_chunk_snapshots.py
uv run pytest tests/unit/test_chat_tracing.py tests/unit/test_chat_redaction.py
uv run pytest tests/integration/test_chat_successful_tool_call.py tests/integration/test_chat_failed_tool_recovery.py tests/integration/test_chat_trace_log_correlation.py tests/integration/test_chat_redis_state.py
uv run pytest -q
```

## Notes

- Keep `/chat` route thin: authentication, request parsing, dependency lookup,
  and SSE response only.
- Keep provider-specific Azure OpenAI, LangSmith, Redis, model-server, RAG, and
  memory client details in `app/infra/`.
- Do not introduce planner, router, researcher, critic, memory, or specialist
  agents. LangGraph is only a thin state graph around one primary LLM node.
- Do not add UI, widget behavior, new model training, new RAG indexing, or
  automatic long-term memory writes in this phase.

# Feature Specification: Single Tool-Calling Chatbot Backend

**Feature Branch**: `007-tool-chatbot-backend`  
**Created**: 2026-05-18  
**Status**: Draft  
**Input**: User description: "Phase 7, Build the single tool-calling chatbot backend."

## Clarifications

### Session 2026-05-18

- Q: Which streaming transport should the chat endpoint use? → A: SSE (Server-Sent Events) — unidirectional, plain HTTP, standard for LLM streaming.
- Q: Which LLM should the chatbot use for tool-calling orchestration? → A: Azure OpenAI via LangChain with LangSmith tracing — consistent with Phases 3/4/5; LangChain fake adapter in automated tests.
- Q: What should the default maximum tool-call count per user message be? → A: 5 tool calls — covers all five supported tools; configurable via typed settings.
- Q: What should the default full chatbot response timeout be? → A: 60 seconds — covers worst-case 5-tool chain with Azure OpenAI latency; configurable via typed settings.
- Q: Which local tracing backend should the dev/demo stack use? → A: LangSmith — already integrated across all LLM phases; no Jaeger/Tempo service needed. LangSmith run IDs used for log correlation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Chat With The Maintainer Copilot (Priority: P1)

An authenticated maintainer can send a message to the Maintainer's Copilot and
receive a streamed response from one tool-calling assistant.

**Why this priority**: This phase creates the actual chat backend that connects
the earlier classifier, NER, summarization, RAG, and memory capabilities into a
single user-facing workflow.

**Independent Test**: Authenticate as a user, send a chat message, receive a
streamed response, and verify that the conversation state is saved as short-term
state for that user.

**Acceptance Scenarios**:

1. **Given** an authenticated user, **When** they send a valid chat message,
   **Then** the chatbot returns a streamed response.
2. **Given** an unauthenticated caller, **When** they attempt to use chat,
   **Then** the request is rejected with a structured authentication error.
3. **Given** the user sends multiple messages in a conversation, **When** the
   chatbot responds, **Then** short-term conversation state is available for the
   same authenticated user and not for other users.

---

### User Story 2 - Use Maintainer Tools From One Assistant (Priority: P2)

The chatbot can call available maintainer tools for issue classification, entity
extraction, summarization, RAG question answering, and explicit memory writes
without becoming a multi-agent system.

**Why this priority**: The assistant is only useful if it can perform maintainer
work through the tools built in earlier phases while preserving the project's
single-LLM scope.

**Independent Test**: Send user messages that require each supported tool and
verify that the chatbot calls the expected tool schema and incorporates the safe
tool result into the response.

**Acceptance Scenarios**:

1. **Given** a user asks for issue triage, **When** the chatbot responds, **Then**
   it can call the classifier tool and use the result.
2. **Given** a user asks about entities or a long issue thread, **When** the
   chatbot responds, **Then** it can call the NER or summarization tool as
   appropriate.
3. **Given** a user asks a project knowledge question, **When** the chatbot
   responds, **Then** it can call the RAG tool and ground the answer in retrieved
   evidence.
4. **Given** a user explicitly asks the assistant to remember something,
   **When** the chatbot responds, **Then** it may call write_memory; otherwise it
   does not write long-term memory.

---

### User Story 3 - Recover Gracefully From Tool Failures (Priority: P3)

A maintainer receives a useful partial answer when one tool fails instead of a
server error.

**Why this priority**: Tool-backed assistants must remain reliable even when a
model server, RAG path, or memory tool is unavailable.

**Independent Test**: Force one supported tool to fail during a chat request and
verify that the chatbot streams a partial answer, identifies the unavailable
capability safely, and does not return a generic server failure.

**Acceptance Scenarios**:

1. **Given** a tool call fails, **When** the chatbot can still answer partially,
   **Then** it returns a partial answer with safe failure context.
2. **Given** one tool fails after another tool succeeds, **When** the response is
   generated, **Then** successful tool results may still be used.
3. **Given** the full chatbot timeout or tool-call limit is reached, **When** the
   response is generated, **Then** the chatbot stops further tool calls and
   returns the best safe response available.

---

### User Story 4 - Trace And Redact Chat Activity (Priority: P4)

A reviewer or operator can inspect conversation traces with LLM call spans, tool
call spans, RAG retrieval spans, and safe metadata without exposing full
sensitive payloads.

**Why this priority**: The constitution requires traceable AI behavior and
redaction before telemetry, especially now that user messages, tool payloads,
retrieved chunks, and generated answers flow through one system.

**Independent Test**: Run a chat request that calls a tool and RAG retrieval,
then verify that a trace root exists for the user message, LangSmith run IDs
appear in structured logs, the conversation is visible in LangSmith, and LLM,
tool, and RAG spans contain safe redacted metadata only.

**Acceptance Scenarios**:

1. **Given** a user sends a chat message, **When** the chatbot starts processing,
   **Then** a conversation trace root is created for that user message.
2. **Given** the chatbot calls the LLM or a tool, **When** tracing is recorded,
   **Then** LLM call spans and tool call spans are created with redacted inputs
   and outputs.
3. **Given** the chatbot uses RAG, **When** retrieval runs, **Then** RAG
   retrieval spans are recorded with safe metadata and without full raw chunks.
4. **Given** a chat request succeeds or recovers from a failed tool, **When** the
   reviewer opens LangSmith, **Then** the trace tree is visible and can be
   correlated to structured logs through the LangSmith run ID.

### Edge Cases

- The user is unauthenticated: chat is rejected before model or tool work starts.
- The request is too large: the request is rejected with a structured validation
  error before LLM or tool calls.
- The conversation context is too large: older or lower-priority short-term
  context is bounded according to policy and the limitation is visible safely.
- The chatbot reaches the maximum tool-call limit: it stops calling tools and
  returns the best safe response available.
- The full chatbot response timeout is reached: streaming ends gracefully with a
  bounded partial response or safe timeout message.
- A tool returns invalid, oversized, or unsafe output: the output is rejected,
  redacted, or summarized safely before being used.
- A tool fails or times out: the chatbot does not return an unhandled server
  error and does not leak raw tool payloads.
- The LLM requests a tool that is not registered: the request is rejected by the
  tool execution service and the chatbot recovers safely.
- The user asks to remember something ambiguously: long-term memory is not
  written unless the intent is explicit.
- The user explicitly asks to remember sensitive-looking data: redaction runs
  before write_memory and unsafe values are not persisted.
- Redis short-term state is unavailable: the chatbot responds with bounded
  degradation or structured failure without writing long-term memory
  automatically.
- Trace/logging fails: the chat response does not expose raw internals, and the
  failure is reported through safe operational metadata.
- Retrieved-chunk snapshot storage fails after a RAG tool call: chat can still
  recover safely, the failure is logged with safe metadata, and raw chunks are
  not exposed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide an authenticated chat capability.
- **FR-002**: The chat capability MUST support streaming responses delivered via
  Server-Sent Events (SSE). The SSE stream MUST emit text chunk events, safe
  tool-status events, a completion event, and safe error events. Raw tool inputs,
  raw tool outputs, full retrieved chunks, and unredacted prompts MUST NOT be
  emitted as SSE events.
- **FR-003**: The chatbot MUST use Azure OpenAI via LangChain (`AzureChatOpenAI`)
  as the single tool-calling LLM and MUST NOT be a multi-agent system. LangSmith
  MUST be configured as the tracing backend for LLM calls when a LangSmith API
  key is present. Automated tests MUST use a LangChain fake/mock provider; no
  real Azure OpenAI credentials are required for tests.
- **FR-004**: The system MUST define tool schemas for issue classification,
  entity extraction, summarization, RAG question answering, and explicit
  write_memory.
- **FR-005**: The system MUST provide a tool execution service that validates
  tool names, tool inputs, tool outputs, timeouts, and failure results.
- **FR-006**: Prompt files for chatbot behavior MUST live under `prompts/`.
- **FR-007**: Each user chat message MUST create one conversation trace root.
- **FR-008**: Each LLM call MUST create an LLM call span.
- **FR-009**: Each tool call MUST create a tool call span.
- **FR-010**: Each RAG retrieval performed by the chatbot MUST create a RAG
  retrieval span.
- **FR-010a**: Each RAG tool call MUST create a redacted retrieved-chunk snapshot
  through the RAG snapshot service.
- **FR-010b**: Chat tracing MUST use LangSmith as the tracing backend for all
  LLM calls, tool calls, and RAG retrieval spans, consistent with Phases 3–6.
  LangSmith is configured when a LangSmith API key is present in typed settings.
  No Jaeger or Tempo service is added to the local stack.
- **FR-010c**: Structured logs for chat requests MUST include the LangSmith run
  ID when available so logs and LangSmith traces are joinable.
- **FR-011**: Tool inputs, tool outputs, user messages, retrieved chunks, and LLM
  payloads MUST be redacted or bounded before logs and traces.
- **FR-012**: The chatbot MUST recover gracefully from tool failure and return a
  partial answer when possible instead of an unhandled server error.
- **FR-013**: The chatbot MUST enforce a configurable maximum tool-call limit per
  user message with a default of 5. When the limit is reached, the chatbot MUST
  stop further tool calls and return the best safe response available. The limit
  MUST be loaded from typed settings.
- **FR-014**: The chatbot MUST enforce a configurable full-response timeout with
  a default of 60 seconds. When the timeout is reached, the SSE stream MUST end
  gracefully with a bounded partial response or safe timeout event. The timeout
  MUST be loaded from typed settings.
- **FR-015**: The chat capability MUST enforce request size limits before LLM or
  tool execution.
- **FR-016**: The chatbot MUST enforce context size limits before sending context
  to the LLM.
- **FR-017**: Short-term conversation state MUST be stored in Redis and scoped to
  the authenticated user.
- **FR-018**: Long-term memory MUST be written only when the explicit
  write_memory tool is called.
- **FR-019**: The chatbot MUST call write_memory only when user intent to
  remember is explicit.
- **FR-020**: The chatbot MUST be able to call the classifier tool.
- **FR-021**: The chatbot MUST be able to call the NER/entity extraction tool.
- **FR-022**: The chatbot MUST be able to call the summarization tool.
- **FR-023**: The chatbot MUST be able to call the RAG question-answering tool.
- **FR-024**: The chatbot MUST be able to call the explicit write_memory tool
  when the user intent is explicit.
- **FR-025**: Structured errors MUST be returned for authentication, validation,
  timeout, context-limit, LLM, tracing, and tool execution failures.
- **FR-026**: Tests MUST cover one successful tool call path, one failed tool
  recovery path, authenticated chat access, write_memory explicit-intent gating,
  short-term state behavior, retrieved-chunk snapshot creation, trace/log
  correlation, visible tracing UI export behavior where practical, and redaction
  of logs/traces.

### Constitution Alignment *(mandatory)*

- **Phase Scope**: This is `PLAN.md` Phase 7 only. It builds the single
  tool-calling chatbot backend. UI work, widget behavior, multi-agent systems,
  new model training, new RAG indexing, automatic long-term memory writes, and
  unrelated product features are out of scope.
- **Architecture Boundaries**: Chat routes remain request/response and streaming
  mapping only. Chat orchestration, tool selection, tool execution, memory
  coordination, timeout handling, and trace coordination belong in services.
  Model, tool, Redis, RAG, tracing, and redaction adapters belong in infra.
- **Security And Redaction**: User messages, tool inputs, tool outputs, retrieved
  chunks, LLM prompts/responses, short-term state, and memory-write requests may
  contain sensitive content. Redaction must run before logs, traces, and memory
  persistence. Long-term memory may be written only through explicit
  write_memory.
- **Observability And Errors**: Every user message needs a trace root. LLM calls,
  tool calls, and RAG retrievals need spans. Chat logs must include the LangSmith
  run ID for correlation. Tool failures, timeouts, and limit-exceeded cases must
  return structured errors or partial responses with safe metadata.
- **Evidence And Evals**: This phase uses already selected/evaluated classifier
  and RAG capabilities. It must not change model, embedding, retrieval, or memory
  decisions without updating `docs/decisions.md`.
- **Critical Tests**: Critical tests must cover authenticated chat, streaming
  behavior, successful tool execution, failed tool recovery, max tool-call limit,
  full-response timeout, request/context limits, trace span creation,
  write_memory explicit intent, Redis short-term state, and redaction of
  tool/LLM payloads.

### Key Entities *(include if feature involves data)*

- **Chat Request**: Authenticated user message, conversation identifier, optional
  safe context references, and streaming preference.
- **Chat Response Stream**: SSE stream of ordered events: assistant text chunks, safe tool-status events, a completion event, and safe error events. Delivered over a plain HTTP SSE connection.
- **Conversation State**: User-scoped short-term state used to maintain recent
  conversation context.
- **Tool Definition**: Registered tool name, description, input schema, output
  schema, timeout policy, and safe-use constraints.
- **Tool Call**: One validated tool invocation with name, redacted input,
  redacted output or structured failure, duration, and trace span reference.
- **Tool Execution Result**: Successful tool result or safe failure payload used
  by the chatbot to continue or recover.
- **LLM Call**: One call to Azure OpenAI via LangChain `AzureChatOpenAI`, including redacted prompt metadata, tool call requests, response metadata, latency, and a LangSmith trace when configured.
- **RAG Retrieval Span**: Trace record for a RAG retrieval performed during chat,
  including safe query metadata, result counts, source metadata, and latency.
- **Retrieved Chunk Snapshot**: Redacted bounded snapshot of chunk IDs, scores,
  source metadata, and previews stored after a RAG tool call.
- **Conversation Trace Root**: LangSmith run root created for each user message, linked to LLM call, tool call, and RAG retrieval child spans.
- **Memory Write Intent**: Explicit user intent marker that allows the chatbot to
  call write_memory.
- **Chat Limits**: Configured request size limit, context size limit, max tool-call count (default 5), per-tool timeout, and full-response timeout (default 60 seconds). All limits are loaded from typed settings.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An authenticated user can send a chat message and receive a
  streamed assistant response.
- **SC-002**: Unauthenticated chat requests are rejected in 100% of auth guard
  tests before model or tool work starts.
- **SC-003**: The chatbot successfully calls each supported tool in controlled
  tests: classifier, NER/entity extraction, summarization, RAG question
  answering, and explicit write_memory.
- **SC-004**: In failed-tool tests, the chatbot returns a partial answer or safe
  failure response instead of an unhandled server error.
- **SC-005**: Long-term memory is written in 0% of tested chat flows unless
  explicit write_memory intent is present.
- **SC-006**: Every tested user message creates one trace root and includes LLM
  and tool spans for calls made during that message.
- **SC-007**: RAG-backed chat tests include a RAG retrieval span for every
  retrieval performed.
- **SC-007a**: RAG-backed chat tests create redacted retrieved-chunk snapshots
  without storing full raw chunks.
- **SC-007b**: Successful and failed-tool chat runs are visible in LangSmith and include LangSmith run IDs that also appear in structured logs.
- **SC-008**: Request size, context size, tool-call limit, and full-response
  timeout tests all stop processing at the configured bounds.
- **SC-009**: Fake secret values in user messages, tool payloads, retrieved
  chunks, and LLM payloads do not appear unredacted in logs or traces.
- **SC-010**: Short-term conversation state is available to the same
  authenticated user for a continued conversation and unavailable to other
  users.

## Assumptions

- Phase 3 classifier, Phase 4 NER/summarization, Phase 5 RAG, and Phase 6
  explicit memory capabilities exist or are represented by compatible test fakes
  before this phase is implemented.
- The chatbot uses one configured tool-calling LLM for orchestration and does
  not spawn specialist agents or independent agent loops.
- Streaming may include text chunks and safe tool-status events, but it must not
  stream raw tool inputs, raw tool outputs, full retrieved chunks, or unredacted
  prompts.
- The write_memory tool remains the only path to long-term memory writes from
  chat.
- Short-term conversation state follows the Phase 6 TTL and user scoping
  decisions.

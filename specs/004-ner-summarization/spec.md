# Feature Specification: NER and Summarization Tools

**Feature Branch**: `004-ner-summarization`  
**Created**: 2026-05-18  
**Status**: Draft  
**Input**: User description: "Phase 4, Build NER and summarization tools for issue analysis."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Extract Code-Shaped Entities from Issues (Priority: P1)

A future chatbot backend or developer can send issue title, body, and comments to
the model server and receive typed code-shaped entities found in the issue text.

**Why this priority**: Entity extraction gives later tools structured facts about
files, commands, errors, versions, and stack traces before the chatbot phase is
implemented.

**Independent Test**: Submit issue text containing file paths, function names,
class names, package names, versions, error codes, URLs, stack trace markers,
environment names, and command snippets, then verify that the response contains
typed entity records with text, type, confidence when available, and source span
when practical.

**Acceptance Scenarios**:

1. **Given** an issue title, body, and comments containing code-shaped entities,
   **When** the NER tool is called, **Then** it returns a list of typed entities
   matching the supported entity types.
2. **Given** entity source location can be identified, **When** the NER tool
   returns an entity, **Then** the response includes source span information.
3. **Given** confidence is available from the extraction method, **When** the NER
   tool returns an entity, **Then** the response includes the confidence value.

---

### User Story 2 - Summarize Long Issue Threads (Priority: P2)

A maintainer or later chatbot backend can send a long issue thread and receive a
concise summary, key facts, unresolved questions, and a suggested next maintainer
step when supported.

**Why this priority**: Long issue threads are hard to triage manually. A bounded,
structured summary gives maintainers and later chatbot workflows a compact issue
understanding without building chatbot orchestration yet.

**Independent Test**: Submit a long issue thread with multiple comments, then
verify that the summary response contains concise summary text, key facts,
unresolved questions, and a suggested next step when the summarizer can provide
one.

**Acceptance Scenarios**:

1. **Given** a long issue thread, **When** the summarization tool is called,
   **Then** it returns a concise summary and key facts.
2. **Given** the thread contains unanswered maintainer-relevant questions,
   **When** the summarization tool is called, **Then** it lists unresolved
   questions.
3. **Given** the summarizer can infer a next maintainer action, **When** the tool
   returns a response, **Then** it includes a suggested next step.

---

### User Story 3 - Handle Tool Failures Safely (Priority: P3)

A caller can receive structured tool errors when extraction or summarization
fails, while the model server remains healthy and avoids logging full sensitive
issue payloads.

**Why this priority**: These tools will be called by later backend workflows, so
failure behavior must be predictable and safe before integration.

**Independent Test**: Trigger invalid input, adapter failure, timeout, and empty
content cases, then verify that each failure returns a structured tool error,
does not crash the model server, and does not log full issue payloads.

**Acceptance Scenarios**:

1. **Given** invalid or empty tool input, **When** the tool endpoint is called,
   **Then** it returns a structured validation error.
2. **Given** an external summarization adapter times out or fails, **When** the
   summarization endpoint is called, **Then** the tool returns a clear fallback or
   structured tool error without crashing the model server.
3. **Given** issue text contains sensitive-looking values, **When** a tool call
   succeeds or fails, **Then** logs do not include full raw issue payloads.

### Edge Cases

- Issue text is empty or only whitespace: the tool returns a structured
  validation error.
- Issue text is very long: the tool applies documented limits, truncation, or
  chunking behavior and reports the limitation safely.
- Comments are missing, duplicated, or empty: tools still process title/body and
  ignore duplicate or empty comments deterministically.
- One entity text matches multiple entity types: the extraction policy returns
  deterministic types or multiple typed entities according to documented rules.
- Source spans are impractical for a result: the entity is returned without span
  rather than inventing an inaccurate span.
- External summarization is unavailable, rate-limited, or times out: the endpoint
  returns a bounded fallback or structured tool error.
- Summarization cannot infer unresolved questions or next step: those fields are
  returned empty or marked unavailable without failing the whole response.
- Tool inputs contain secret-like text or full issue bodies: routine logs and
  traces avoid full raw payloads and use redacted or summarized context.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The model server MUST expose a NER/entity extraction tool endpoint.
- **FR-002**: The NER tool MUST accept issue title, body, and comments.
- **FR-003**: The NER tool MUST detect supported code-shaped entity types:
  file paths, function names, class names, package names, version numbers, error
  codes, URLs, stack trace markers, environment names, and command snippets when
  detectable.
- **FR-004**: NER responses MUST return typed entity records containing entity
  text, entity type, confidence when available, and source span when practical.
- **FR-005**: The model server MUST expose a summarization tool endpoint.
- **FR-006**: The summarization tool MUST accept issue thread content, including
  title, body, and comments.
- **FR-007**: Summarization responses MUST include concise summary, key facts,
  unresolved questions, and suggested maintainer next step when supported.
- **FR-008**: Both tool endpoints MUST use typed request and response models.
- **FR-009**: Both tool endpoints MUST return structured tool errors for invalid
  input, unavailable dependencies, timeouts, and tool failures.
- **FR-010**: Endpoint handlers MUST remain thin and delegate extraction,
  summarization, fallback, and error handling logic to services.
- **FR-011**: Model or client adapters MUST live in infra or model-server infra
  ownership areas, not in endpoint handlers.
- **FR-012**: Tool failures MUST NOT crash the model server.
- **FR-013**: External summarization, when used, MUST have an explicit timeout and
  clear fallback or structured failure behavior.
- **FR-014**: Full sensitive issue payloads MUST NOT be logged during successful
  or failed tool calls.
- **FR-015**: Tests MUST cover successful and failed NER calls, successful and
  failed summarization calls, structured error shapes, adapter failure behavior,
  and logging redaction expectations.
- **FR-016**: This phase MUST NOT implement chatbot orchestration, RAG retrieval,
  widget behavior, model training, or memory persistence.

### Constitution Alignment *(mandatory)*

- **Phase Scope**: This is `PLAN.md` Phase 4 only. It exposes NER and
  summarization tools over the model server. Chatbot orchestration, RAG
  retrieval, widget work, auth flows, memory persistence, and custom NER training
  are out of scope.
- **Architecture Boundaries**: Endpoint handlers remain request/response mapping
  only. Extraction and summarization behavior belongs in services. External model
  or client adapters belong in infra or model-server infra ownership areas.
- **Security And Redaction**: Tool inputs may contain issue text and
  secret-like values. Logs and traces must avoid full raw payloads and use
  redacted or bounded context for success and failure paths.
- **Observability And Errors**: Tool calls must produce structured errors for
  invalid input, timeouts, unavailable adapters, and unexpected failures. Failures
  must include request correlation where available and must not crash the model
  server.
- **Evidence And Evals**: This phase does not select classifier, embedding, or
  RAG approaches. It must document summarization adapter/fallback decisions when
  external summarization is used.
- **Critical Tests**: Critical tests must cover typed response schemas, supported
  entity types, success and failure paths, timeout/fallback behavior, no full
  sensitive payload logging, and endpoint thinness.

### Key Entities *(include if feature involves data)*

- **Issue Text Input**: Title, body, and comments submitted for NER or
  summarization.
- **Entity Type**: Supported code-shaped category: file path, function name,
  class name, package name, version number, error code, URL, stack trace marker,
  environment name, or command snippet.
- **Extracted Entity**: Entity text, entity type, optional confidence, optional
  source span, and source field.
- **Source Span**: Start/end location or equivalent trace to where an entity was
  found when practical.
- **Issue Summary**: Concise summary, key facts, unresolved questions, suggested
  next maintainer step, and limitations.
- **Tool Error**: Structured failure response with stable code, safe message,
  request identifier when available, and safe details.
- **Tool Adapter**: External or local model/client adapter used by extraction or
  summarization services.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The NER endpoint returns typed entities for at least one test input
  covering each supported entity type.
- **SC-002**: 100% of NER entity responses include text and entity type, and
  include confidence/span fields only when available or practical.
- **SC-003**: The summarization endpoint returns all required response fields for
  representative long issue-thread inputs.
- **SC-004**: Invalid input, adapter failure, and timeout tests return structured
  tool errors without crashing the model server.
- **SC-005**: External summarization calls, when configured, are bounded by an
  explicit timeout and have a tested fallback or structured failure path.
- **SC-006**: Logging tests confirm that full issue title/body/comment payloads
  and fake secret values do not appear unredacted in tool logs.
- **SC-007**: Endpoint tests confirm route handlers delegate behavior to services
  and do not contain adapter logic.

## Assumptions

- NER starts with deterministic, explainable extraction for code-shaped entities;
  custom NER training is not part of this phase.
- Summarization may use a local model, fake adapter, or external provider during
  implementation, but external providers must be optional for tests and bounded
  by timeouts.
- Source spans are best-effort because not every extraction strategy can produce
  reliable character offsets.
- The model server already has or will have the Phase 1 error and request
  correlation patterns available before implementation.
- Tool outputs are intended for later chatbot use, but this phase does not add
  chatbot orchestration or tool-calling LLM behavior.

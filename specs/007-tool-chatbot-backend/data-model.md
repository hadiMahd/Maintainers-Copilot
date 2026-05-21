# Data Model: Single Tool-Calling Chatbot Backend

## Chat Request

**Purpose**: Authenticated user message submitted to the chatbot.

**Fields**:
- `user_id`: authenticated user identifier.
- `conversation_id`: stable conversation identifier.
- `message_id`: stable user message identifier.
- `message`: user message text.
- `stream`: whether response streaming is requested.
- `metadata`: optional safe client metadata.

**Validation Rules**:
- User must be authenticated before processing starts.
- Message must be non-empty and within request size limits.
- Metadata must be bounded and safe.
- Request is rejected before LLM/tool work if authentication or size validation
  fails.

## Chat Response Stream

**Purpose**: Ordered events emitted to the caller during a chat response.

**Fields**:
- `event_type`: `message_delta`, `tool_status`, `warning`, `error`, or `done`.
- `conversation_id`: conversation identifier.
- `message_id`: user message identifier.
- `sequence`: monotonically increasing event sequence.
- `content`: streamed text or safe event summary.
- `trace_id`: trace identifier when available.

**Validation Rules**:
- Events must not include raw tool inputs, raw tool outputs, full retrieved
  chunks, provider payloads, or unredacted prompts.
- Error events use safe structured messages.
- Event ordering is deterministic per response.

## Chat Graph State

**Purpose**: State passed through the thin LangGraph workflow.

**Fields**:
- `messages`: bounded conversation messages sent to the LLM.
- `tool_calls`: validated tool call requests.
- `tool_results`: successful or failed tool execution results.
- `tool_call_count`: count of tool calls attempted for the current user message.
- `remaining_steps`: graph recursion/step budget when available.
- `limits`: request, context, tool-call, recursion, and timeout limits.
- `trace_root_id`: conversation trace root identifier.
- `final_response`: final response text or streaming completion state.

**Validation Rules**:
- State must be scoped to one authenticated user message.
- Tool call count cannot exceed configured maximum.
- Context sent to the LLM must be bounded.
- Retrieved documents in state are marked untrusted evidence.

## Tool Definition

**Purpose**: Registered chatbot tool contract exposed to the LLM.

**Fields**:
- `name`: stable tool name.
- `description`: safe tool description.
- `input_schema`: typed input schema.
- `output_schema`: typed output schema.
- `timeout_seconds`: per-tool timeout.
- `requires_explicit_intent`: whether explicit user intent is required.
- `redaction_policy`: input/output redaction policy.

**Validation Rules**:
- Tool names must be unique and registered before chat execution.
- Tool inputs and outputs must validate against schemas.
- `write_memory` requires explicit intent.
- Unknown tool requests are rejected safely.

## Tool Call

**Purpose**: One LLM-requested tool invocation.

**Fields**:
- `tool_call_id`: stable call identifier.
- `name`: registered tool name.
- `input`: validated tool input.
- `redacted_input`: input safe for logs/traces.
- `started_at`: start timestamp.
- `completed_at`: completion timestamp when available.
- `trace_span_id`: associated tool span.

**Validation Rules**:
- Tool call must reference a registered tool.
- Input must validate before execution.
- Tool call count and timeout limits apply.
- Inputs are redacted before telemetry.

## Tool Execution Result

**Purpose**: Safe result passed back into the chatbot after a tool call.

**Fields**:
- `tool_call_id`: associated tool call.
- `name`: tool name.
- `status`: `success` or `failed`.
- `output`: validated tool output when successful.
- `error`: structured safe error when failed.
- `redacted_output`: output safe for logs/traces.
- `duration_ms`: execution duration.

**Validation Rules**:
- Success outputs must validate against the tool output schema.
- Failed results must preserve safe error code/message.
- Raw tool payloads are not logged or traced.

## LLM Call

**Purpose**: One call to the single tool-calling LLM.

**Fields**:
- `llm_call_id`: stable call identifier.
- `model_version`: configured model/provider version label.
- `prompt_version`: loaded prompt version.
- `redacted_prompt_metadata`: safe prompt metadata.
- `requested_tool_calls`: tool calls requested by the LLM.
- `response_metadata`: safe response metadata.
- `latency_ms`: LLM latency.
- `trace_span_id`: associated LLM span.

**Validation Rules**:
- Provider-specific payloads stay inside infra.
- Prompt and response payloads are redacted or bounded before logs/traces.
- LLM call timeout applies.

## RAG Tool Result

**Purpose**: RAG tool output consumed by the chatbot.

**Fields**:
- `answer`: grounded answer or insufficient-evidence response.
- `supporting_sources`: bounded source references.
- `retrieval_span_id`: RAG retrieval span identifier.
- `snapshot_id`: redacted retrieved-chunk snapshot identifier when created.
- `untrusted_context_used`: boolean.
- `limitations`: safe limitations.

**Validation Rules**:
- Retrieved text is treated as untrusted context.
- Supporting sources are bounded references, not full raw chunks.
- Retrieved text cannot override system/developer instructions or tool policy.
- Snapshot IDs reference redacted bounded retrieval evidence, not full raw
  chunks.

## Retrieved Chunk Snapshot

**Purpose**: Redacted bounded record created after a RAG tool call.

**Fields**:
- `snapshot_id`: snapshot identifier from the RAG snapshot service.
- `conversation_id`: conversation identifier.
- `message_id`: user message identifier.
- `trace_id`: chat trace identifier when available.
- `chunk_refs`: chunk IDs and safe source metadata.
- `score_summary`: bounded retrieval score metadata.
- `redacted_previews`: bounded redacted previews when needed for review.

**Validation Rules**:
- Snapshot creation happens after RAG retrieval and before telemetry/reporting
  references the snapshot.
- Full raw chunks, full prompts, and raw secrets are never stored.
- Snapshot failures are structured and do not force a 500 if chat can otherwise
  recover safely.

## Conversation State

**Purpose**: Short-term state persisted between user messages.

**Fields**:
- `user_id`: owner user.
- `conversation_id`: conversation identifier.
- `messages`: bounded recent message summaries or redacted messages.
- `updated_at`: last update timestamp.
- `expires_at`: TTL expiry from Phase 6 memory policy.

**Validation Rules**:
- State is user-scoped and unavailable to other users.
- State respects configured TTL.
- State is bounded by context policy before LLM use.

## Conversation Trace Root

**Purpose**: Root trace for one user chat message.

**Fields**:
- `trace_root_id`: trace identifier.
- `user_id`: authenticated user.
- `conversation_id`: conversation identifier.
- `message_id`: user message identifier.
- `started_at`: start timestamp.
- `completed_at`: completion timestamp.
- `status`: `success`, `partial`, or `failed`.
- `safe_metadata`: bounded redacted metadata.
- `tracing_backend`: configured tracing backend label, `langsmith` when real
  tracing is enabled or `fake` in tests.

**Validation Rules**:
- One trace root is created for each tested user message.
- Trace root links to LLM, tool, and RAG spans.
- Raw user/tool/LLM/RAG payloads are not stored in trace metadata.
- Trace ID is included in structured logs for the same request when available.
- Successful and failed-tool conversations are reviewable in LangSmith when
  tracing credentials are configured.

## Memory Write Intent

**Purpose**: Explicit user intent that permits the write_memory tool.

**Fields**:
- `present`: whether explicit intent is detected.
- `evidence`: bounded safe explanation of the intent source.
- `target_content_reference`: reference to content intended for memory.

**Validation Rules**:
- Ambiguous intent is treated as not explicit.
- Long-term memory is not written unless intent is explicit and write_memory is
  called.
- Evidence does not include unredacted sensitive content.

## Chat Limits

**Purpose**: Runtime bounds for one chat request.

**Fields**:
- `request_size_limit`: maximum accepted request size.
- `context_size_limit`: maximum context sent to LLM.
- `max_tool_calls`: maximum tool calls per user message.
- `recursion_limit`: graph recursion/step limit.
- `total_timeout_seconds`: full chatbot response timeout.
- `per_tool_timeout_seconds`: default tool timeout.

**Validation Rules**:
- Limits are required and positive.
- Limit breaches stop further model/tool work and return safe partial/error
  behavior.
- Limit values are safe to log, but payloads are not.

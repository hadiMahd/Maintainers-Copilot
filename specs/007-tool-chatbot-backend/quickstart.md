# Quickstart: Single Tool-Calling Chatbot Backend

## Prerequisites

- Phase 3 classifier, Phase 4 NER/summarization, Phase 5 RAG, and Phase 6
  explicit write-memory/Redis state are implemented or available as compatible
  test fakes.
- One tool-calling LLM provider is configured through an infra adapter or fake
  provider for tests.
- Prompt files exist under `prompts/`.
- Authenticated user fixtures are available for chat endpoint tests.
- LangSmith is configured for trace review when real tracing credentials are
  available, and a fake tracing adapter is available for tests.

## Validate Prompt Files

Check that these files exist and are version controlled:

```text
prompts/chatbot_system.md
prompts/chatbot_tool_policy.md
prompts/chatbot_untrusted_context.md
```

Expected result: chat services load prompts through a prompt registry and do not
hard-code provider prompts in service code.

## Start Authenticated Chat

Authenticate as a user, then send a chat request to `/chat` with streaming
enabled.

Expected result: the response stream emits safe chat events and completes with a
trace identifier.

## Validate Tool Calls

Run controlled chat prompts that require:

- issue classification
- entity extraction
- issue summarization
- RAG question answering
- explicit write_memory

Expected result: each supported tool can be called by the single LLM loop and
returns a validated tool result. The write_memory tool is called only when the
user explicitly asks the assistant to remember something.

## Validate Failure Recovery

Configure one fake tool to fail or time out.

Expected result: the chatbot returns a partial answer or safe failure response
instead of a server error, and successful prior tool results may still be used.

## Validate Limits

Run tests for:

- request size limit
- context size limit
- maximum tool-call limit
- LangGraph recursion limit
- total chatbot timeout
- per-tool timeout

Expected result: processing stops at the configured bound and returns safe
partial/error behavior.

## Validate Tracing And Redaction

Run a chat request that calls the LLM, at least one tool, and the RAG tool.

Expected result: one trace root exists for the user message; LLM, tool, and RAG
spans are linked; LangSmith run IDs appear in structured logs when available;
the successful conversation is visible in LangSmith when configured; fake
secrets do not appear unredacted in logs or traces.

## Validate Failed-Tool Trace UI

Run a chat request where one fake tool fails after tracing has started.

Expected result: the chatbot returns a safe partial response, the failed tool
span appears in LangSmith when configured, and the LangSmith run ID is joinable
with structured logs.

## Validate Retrieved-Chunk Snapshots

Run a chat request that calls the RAG tool.

Expected result: the RAG tool returns a retrieval trace ID and redacted snapshot
ID. Stored snapshot data contains chunk IDs, scores, and redacted previews only,
not full raw chunks.

## Run Critical Tests

Run:

```bash
uv run pytest tests/contract/test_chat_endpoint_contract.py tests/unit/test_chatbot_graph.py tests/unit/test_chat_limits.py tests/unit/test_tool_execution_service.py tests/unit/test_write_memory_intent.py tests/unit/test_untrusted_rag_context.py tests/unit/test_retrieved_chunk_snapshots.py tests/unit/test_chat_tracing.py tests/unit/test_chat_redaction.py tests/integration/test_chat_successful_tool_call.py tests/integration/test_chat_redis_state.py tests/integration/test_chat_failed_tool_recovery.py tests/integration/test_chat_trace_log_correlation.py -q
uv run pytest tests/test_config.py tests/test_import_side_effects.py tests/test_route_boundaries.py tests/test_no_secrets.py tests/test_errors.py -q
```

Expected result: authenticated chat, streaming contract, tool success/failure,
limits, explicit memory gating, retrieved-chunk snapshots, Redis state, tracing,
trace/log correlation, and redaction behavior pass.

Validated result during implementation: the focused chat suite passed with `32 passed`, and the Phase 7 cross-cutting guardrails passed with `55 passed`.

## Validate Single-LLM Constraint

Inspect the graph and tests.

Expected result: the graph has one primary LLM node plus support nodes for tool
execution, timeout/error handling, tracing, and final formatting. There are no
planner, researcher, critic, memory, router, or specialist agent nodes.

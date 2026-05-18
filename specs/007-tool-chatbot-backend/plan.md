# Implementation Plan: Single Tool-Calling Chatbot Backend

**Branch**: `007-tool-chatbot-backend` | **Date**: 2026-05-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-tool-chatbot-backend/spec.md`

## Summary

Build the Phase 7 authenticated chat backend for Maintainer's Copilot using one
tool-calling LLM. LangGraph is used only as a thin, observable state graph around
one primary LLM node that can request tools, plus supporting nodes for tool
execution, timeout/error recovery, tracing, and final response formatting. The
chatbot streams responses, stores short-term conversation state in Redis, calls
typed tools for classifier, NER, summarization, RAG, and explicit write_memory,
enforces tool-call, recursion, request-size, context-size, and total-response
limits, writes redacted retrieved-chunk snapshots after RAG tool calls, and
redacts user/tool/LLM/RAG payloads before logs and traces. OpenTelemetry-
compatible tracing uses local Jaeger or Tempo for dev/demo and chat logs include
trace IDs. It does not create planner, researcher, critic, router, memory, or
other agents.

## Technical Context

**Language/Version**: Python 3.11 or newer  
**Primary Dependencies**: FastAPI streaming response support, pydantic for typed
chat/tool schemas, LangGraph as a thin single-LLM orchestration graph,
SQLAlchemy async/current auth dependencies from prior phases, Redis async client
for short-term conversation state, httpx or existing async model-server/RAG
clients for tools, infra LLM adapter for provider-specific calls, structured
tracing/logging, pytest and httpx for service/contract tests  
**Storage**: Redis short-term conversation state scoped by authenticated user and
conversation; redacted retrieved-chunk snapshots through the Phase 5 RAG
snapshot service; version-controlled prompt files under `prompts/`; no new
long-term memory path beyond the Phase 6 explicit write_memory service  
**Testing**: pytest unit tests for graph routing, tool-call limits, recursion
limits, timeout behavior, typed tool schema validation, failed-tool recovery,
write_memory explicit-intent gating, prompt loading, untrusted RAG context
handling, retrieved-chunk snapshot creation, redaction, trace/log correlation,
and trace span creation; httpx contract tests for authenticated streaming chat  
**Target Platform**: Local backend service and future CI with fake LLM/tool
providers; production-shaped async FastAPI runtime  
**Project Type**: Authenticated backend chat endpoint plus chatbot orchestration
services and infra adapters  
**Performance Goals**: Streaming starts without waiting for all tool work when
safe; every chat request is bounded by total timeout, max tool calls, graph
recursion limit, request size limit, and context size limit; async tool/LLM calls
have explicit timeouts  
**Constraints**: Phase 7 only; no UI, widget behavior, new model training, new
RAG indexing, automatic long-term memory writes, or multi-agent workflow;
retrieved documents are untrusted context and cannot override system/developer
instructions; provider-specific LLM code stays out of services; prompt files are
version controlled; LangGraph must not introduce separate planner, researcher,
critic, memory, router, or specialist agents  
**Scale/Scope**: One authenticated chat endpoint, one primary tool-calling LLM
node, one tool execution path, five typed tools, prompt files, Redis conversation
state, conversation trace root, LLM/tool/RAG spans, limit enforcement, graceful
tool failure recovery, retrieved-chunk snapshots, local tracing UI review, and
critical tests for success/failure paths

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Gate

- **Phase Scope**: PASS. This is `PLAN.md` Phase 7 only. It builds the single
  tool-calling chatbot backend and excludes UI, widget behavior, new model
  training, new RAG indexing, automatic long-term memory writes, and unrelated
  product behavior.
- **Layered Architecture**: PASS. Chat routes stay HTTP/streaming mapping only.
  Chat orchestration, graph execution, tool coordination, memory coordination,
  timeout handling, and trace coordination live in services. Provider-specific
  LLM/tool/model/RAG/Redis/tracing/redaction code lives in infra.
- **FastAPI Resource Management**: PASS. LLM adapters, tool clients, Redis
  clients, prompt registry, and graph/service dependencies are created through
  lifespan/dependency injection, not at import time or per request.
- **Async Safety**: PASS. Chat, LLM, tool, Redis, model-server, and RAG calls use
  async clients and explicit timeouts. Blocking work is not introduced in the
  request path.
- **Secrets And Redaction**: PASS. Provider credentials come from prior settings
  and Vault/test fakes. User messages, prompts, tool payloads, retrieved chunks,
  and LLM payloads are redacted or bounded before logs/traces.
- **Observability And Errors**: PASS. Each user message creates a trace root with
  LLM call spans, tool call spans, and RAG retrieval spans. OpenTelemetry-
  compatible traces are exported to local Jaeger or Tempo for dev/demo, and
  trace IDs are included in structured logs. Tool failures, recursion/limit
  errors, and timeouts recover to partial responses where possible.
- **AI Evidence And Eval Gates**: PASS. This phase uses already selected
  classifier/RAG/memory decisions and does not change model/retrieval choices.
  Any changes would require `DECISIONS.md` updates.
- **Critical Tests And CI**: PASS. Tests cover authenticated chat, streaming,
  successful tool execution, failed tool recovery, max tool-call limit,
  recursion limit, total timeout, request/context limits, trace spans,
  retrieved-chunk snapshots, write_memory explicit intent, Redis state, trace/log
  correlation, and redaction.
- **Simplicity**: PASS. LangGraph is restricted to one primary LLM node plus
  simple support nodes. No multi-agent workflow or specialist agents are
  introduced.

### Post-Design Recheck

- **Phase Scope**: PASS. Generated artifacts cover only Phase 7 chatbot backend
  behavior.
- **Layered Architecture**: PASS. Data model and contracts separate API,
  services, graph orchestration, tools, and infra adapters.
- **FastAPI Resource Management**: PASS. Contracts require injected LLM/tool
  clients, Redis state, prompt registry, and trace services.
- **Async Safety**: PASS. All API-facing LLM/tool/RAG/Redis operations are
  timeout-bound async calls.
- **Secrets And Redaction**: PASS. Contracts and quickstart require redaction of
  user, tool, LLM, and RAG payloads before logs/traces.
- **Observability And Errors**: PASS. Contracts define trace roots and spans,
  graceful failure recovery, and safe streaming error events.
- **AI Evidence And Eval Gates**: PASS. No new classifier/RAG/model decisions are
  introduced.
- **Critical Tests And CI**: PASS. Quickstart lists tests for success/failure
  tool paths, limits, traces, Redis state, and explicit memory gating.
- **Simplicity**: PASS. No complexity exceptions were introduced.

## Project Structure

### Documentation (this feature)

```text
specs/007-tool-chatbot-backend/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── chat.openapi.yaml
│   └── tool-schemas.md
└── tasks.md              # Created by /speckit.tasks, not by /speckit.plan
```

### Source Code (repository root)

```text
app/
├── api/
│   └── routes/
│       └── chat.py
├── services/
│   ├── chatbot_service.py
│   ├── chatbot_graph_service.py
│   ├── tool_execution_service.py
│   ├── conversation_state_service.py
│   ├── chat_tracing_service.py
│   └── retrieved_chunk_snapshot_service.py
├── domain/
│   ├── chat.py
│   └── chat_tools.py
└── infra/
    ├── llm_adapter.py
    ├── chatbot_graph.py
    ├── model_server_tools.py
    ├── rag_tool_client.py
    ├── memory_tool_client.py
    ├── redis_conversation_state.py
    └── tracing.py

prompts/
├── chatbot_system.md
├── chatbot_tool_policy.md
└── chatbot_untrusted_context.md

tests/
├── unit/
│   ├── test_chatbot_graph.py
│   ├── test_tool_execution_service.py
│   ├── test_chat_limits.py
│   ├── test_write_memory_intent.py
│   ├── test_untrusted_rag_context.py
│   ├── test_chat_tracing.py
│   └── test_chat_redaction.py
├── contract/
│   └── test_chat_endpoint_contract.py
└── integration/
    ├── test_chat_successful_tool_call.py
    ├── test_chat_failed_tool_recovery.py
    └── test_chat_redis_state.py
```

**Structure Decision**: Keep the chat endpoint in the main backend and preserve
existing ownership boundaries. Use `app/services/chatbot_graph_service.py` to
run the LangGraph state graph and `app/infra/chatbot_graph.py` to construct the
thin graph. Provider-specific LLM calls belong in `app/infra/llm_adapter.py`.
Typed tool models live in `app/domain/chat_tools.py`; tool orchestration and
validation live in services. Prompts are version-controlled under `prompts/`.
Tracing uses OpenTelemetry-compatible adapters with local Jaeger or Tempo for
dev/demo, and RAG tool calls delegate redacted snapshot storage to the RAG
snapshot service.

## Complexity Tracking

No constitution violations or complexity exceptions.

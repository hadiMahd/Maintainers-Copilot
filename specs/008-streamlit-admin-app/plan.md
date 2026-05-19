# Implementation Plan: Streamlit Internal Chatbot and Admin App

**Branch**: `008-streamlit-admin-app` | **Date**: 2026-05-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/008-streamlit-admin-app/spec.md`

## Summary

Build Phase 8 as an internal Streamlit UI for authenticated chat, admin widget
configuration, generated embed snippet viewing, and authorized memory
inspection. Add the minimal FastAPI backend support for widget configuration and
memory inspection when those endpoints do not already exist. Streamlit remains a
thin client: it stores auth state in `st.session_state`, calls the same FastAPI
backend that the widget will use, and uses an `httpx` backend API client with
explicit timeouts. Business logic, authorization, memory access, widget
configuration persistence, snippet generation, and chat execution remain owned
by the backend.

## Technical Context

**Language/Version**: Python 3.11 or newer  
**Primary Dependencies**: Streamlit, httpx with explicit timeouts, pydantic or
dataclasses for UI/client models, existing FastAPI backend contracts, FastAPI
backend app layers for missing widget and memory-inspection endpoints,
SQLAlchemy async for backend widget configuration persistence if not already
available, pytest, and test doubles such as `httpx.MockTransport`  
**Storage**: Streamlit `session_state` for current browser-session auth and UI
state only; backend PostgreSQL persistence for widget configuration and
authorized memory inspection; no direct database, Redis, Vault, MinIO, model, or
filesystem persistence from Streamlit  
**Testing**: pytest unit and integration-style tests for backend API client,
session token handling, admin UI guard, clean errors, timeout behavior, snippet
display, memory authorization handling, and static checks for no direct
persistence or secrets in Streamlit code  
**Target Platform**: Local/internal developer and admin workstation UI running
beside the FastAPI backend  
**Project Type**: Internal UI client plus minimal backend API support and
backend API client module  
**Performance Goals**: Every backend call is bounded by configured connect/read
timeouts; UI interactions fail cleanly instead of hanging; chat rendering streams
or incrementally displays backend events when the backend supports streaming  
**Constraints**: Phase 8 only; no public widget loader, iframe, or host demo
implementation; backend additions are limited to widget configuration,
generated snippet retrieval, and authorized memory inspection needed by the
internal UI; no direct DB/Redis/Vault/model access from Streamlit; no real
secrets or hardcoded privileged credentials; token state is scoped to Streamlit
session and cleared on logout or invalid session  
**Scale/Scope**: One internal Streamlit app with login, chat, admin widget
configuration, embed snippet display, memory inspector, shared backend API
client, minimal backend routes/services/repositories for missing widget and
memory-inspection support, reusable clean-error components, and focused tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Phase Scope**: PASS. This plan implements only Phase 8 internal Streamlit
  UI behavior. It excludes public embedded widget delivery, backend auth/memory
  rewrites, new chatbot orchestration, new RAG/model behavior, and direct data
  access paths.
- **Layered Architecture**: PASS. Streamlit code is presentation and backend API
  client code only. New backend routes, if required, stay HTTP-only. Backend
  services keep ownership of widget config workflows, snippet generation,
  memory-inspection authorization, persistence, and redaction. Repositories own
  SQL only. Streamlit must not import repositories, ORM models, database
  sessions, Redis clients, Vault clients, or model clients.
- **FastAPI Resource Management**: PASS. Any backend additions use the existing
  app factory, lifespan-managed database/session resources, and dependency
  injection. Streamlit only calls managed backend resources through HTTP.
- **Async Safety**: PASS. Streamlit is a synchronous UI runtime, but all network
  calls use `httpx` with explicit timeouts. The plan avoids long-running work,
  model calls, ingestion, training, or direct persistence in the UI process.
- **Secrets And Redaction**: PASS. Backend base URL is non-secret configuration.
  Tokens stay in `st.session_state`, are sent only as authorization headers, and
  are cleared on logout or invalid authentication. Streamlit does not log raw
  chat, memory, tokens, snippets, or backend traces.
- **Observability And Errors**: PASS. UI errors are mapped from backend
  structured errors, timeout failures, and service-unavailable conditions into
  clean user-facing messages without stack traces or secret payloads.
- **AI Evidence And Eval Gates**: PASS. This is not an AI decision phase. The UI
  consumes Phase 6 and Phase 7 backend contracts and does not change classifier,
  RAG, model, embedding, memory-type, or eval decisions.
- **Critical Tests And CI**: PASS. Tests cover login, chat, admin gating, widget
  config backend/client calls, snippet display, memory inspector authorization,
  timeout handling, clean errors, session clearing, no direct DB/persistence
  imports from Streamlit, backend route/service ownership, and no hardcoded
  secrets.
- **Simplicity**: PASS. The plan adds one Streamlit app and one backend client.
  It does not add agents, extra data stores, new orchestration frameworks, or a
  second business-logic path.

## Project Structure

### Documentation (this feature)

```text
specs/008-streamlit-admin-app/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── internal-ui-backend.openapi.yaml
│   └── streamlit-ui.md
└── tasks.md
```

### Source Code (repository root)

```text
app/
├── api/
│   └── routes/
│       ├── widget_configs.py
│       └── memory_inspector.py
├── domain/
│   ├── widget_config.py
│   └── memory_inspector.py
├── repositories/
│   ├── widget_config_repository.py
│   └── memory_inspector_repository.py
└── services/
    ├── widget_config_service.py
    └── memory_inspector_service.py

streamlit_app/
├── app.py
├── config.py
├── models.py
├── clients/
│   └── backend_api.py
├── components/
│   ├── auth.py
│   ├── errors.py
│   └── snippets.py
└── pages/
    ├── chat.py
    ├── admin_widget_config.py
    └── memory_inspector.py

tests/
├── unit/
│   ├── test_widget_config_service.py
│   ├── test_memory_inspector_service.py
│   ├── test_streamlit_backend_client.py
│   ├── test_streamlit_session_auth.py
│   ├── test_streamlit_admin_guard.py
│   ├── test_streamlit_error_display.py
│   └── test_streamlit_no_direct_db_or_secrets.py
├── contract/
│   ├── test_internal_ui_backend_contract.py
│   └── test_streamlit_backend_contract.py
└── integration/
    └── test_streamlit_backend_flow.py
```

**Structure Decision**: Add `streamlit_app/` as a UI-only top-level package so
reviewers can quickly distinguish internal UI code from backend application
layers. Add minimal backend modules only where Phase 8 needs API support that
does not already exist: widget configuration CRUD/snippet generation and
authorized memory inspection. `streamlit_app/clients/backend_api.py` is the only
Streamlit data access path and must use backend HTTP endpoints with timeouts.
Streamlit pages and components consume typed UI/client models and never call
database, Redis, Vault, model, RAG, or repository modules directly.

## Complexity Tracking

No constitution violations are planned.

## Post-Design Constitution Check

- **Phase Scope**: PASS. The generated research, data model, UI contract, and
  quickstart describe only the Phase 8 internal Streamlit app.
- **Layered Architecture**: PASS. Contracts explicitly require backend-only data
  access from Streamlit, place widget and memory-inspection logic in backend
  services/repositories, and forbid direct persistence, infra, and model imports
  from Streamlit.
- **FastAPI Resource Management**: PASS. The UI does not create backend shared
  resources. Minimal backend additions use existing FastAPI dependency injection
  and managed database sessions.
- **Async Safety**: PASS. Backend calls are bounded by `httpx` timeouts and no
  long-running work is placed in UI request handling.
- **Secrets And Redaction**: PASS. Token/session handling and no-sensitive-log
  rules are documented in research, data model, contracts, and quickstart.
- **Observability And Errors**: PASS. Clean UI error mapping is a named contract
  and test target.
- **AI Evidence And Eval Gates**: PASS. No AI/model/eval decisions are changed.
- **Critical Tests And CI**: PASS. Critical UI, API-client, authorization,
  timeout, and static architecture checks are included.
- **Simplicity**: PASS. The selected structure uses one UI app and one backend
  API client without adding unneeded infrastructure.

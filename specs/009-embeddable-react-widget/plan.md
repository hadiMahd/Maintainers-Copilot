# Implementation Plan: Embeddable React Widget

**Branch**: `009-embeddable-react-widget` | **Date**: 2026-05-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/009-embeddable-react-widget/spec.md`

## Summary

Build Phase 9 as the production-shaped embedded chatbot surface: a Vite React
widget, a small `/widget.js` loader, iframe isolation, public widget config
reads, origin-gated streamed widget chat, admin widget configuration, and an
allowed plus blocked host demo. Reuse or extend the Phase 8 widget admin API
shape rather than creating a parallel admin surface. Widget configuration
create/update/delete flows go through backend services and write audit rows.
Serve the loader from the FastAPI backend, configure Vite to emit one standalone
initial widget JavaScript bundle, serve widget assets from an API static route
with cache headers for the first implementation, use vanilla CSS to keep the
bundle small, and restrict `postMessage` to controlled resize messages.

## Technical Context

**Language/Version**: Python 3.11 or newer for backend; TypeScript, React, and
Vite for the widget  
**Primary Dependencies**: FastAPI, pydantic-settings, SQLAlchemy async, asyncpg,
Alembic, pytest, httpx, Vite, React, React DOM, TypeScript, Vitest with a DOM
test environment for widget and loader tests; vanilla CSS for widget styling  
**Storage**: PostgreSQL widget configuration table with `widget_id`,
`allowed_origins`, theme, greeting, enabled tools, enabled flag, creator, and
timestamps; hashed widget bundle artifacts served by API static route with cache
headers; audit rows for widget config create/update/delete; no Streamlit
storage or widget-side persistence beyond transient browser state  
**Testing**: pytest and httpx for backend unit, contract, and integration tests;
Vitest for widget component, loader, message-channel, and config application
tests; optional manual browser smoke test through `demo/host` if no browser
automation is present; bundle validation that enforces one standalone initial
widget JavaScript bundle or documents an exception  
**Target Platform**: Local Linux/container development environment, modern
browsers on allowed host pages, and the existing FastAPI backend  
**Project Type**: Web-service extension plus embeddable frontend widget and host
demo  
**Performance Goals**: `/widget.js` remains below 5 KB gzip; the initial widget
bundle target is below 120 KB gzip; public config reads and widget chat setup are
bounded by explicit backend timeouts; widget asset responses use appropriate
cache headers  
**Constraints**: Phase 9 only; no new chatbot intelligence, model training, RAG
indexing, Streamlit UI work, or broad CI/security polish; dependencies stay
minimal; no large UI libraries; Tailwind is not added unless already configured
without material bundle growth; `postMessage` is only for controlled resize
messages; widget code must not reference Streamlit  
**Scale/Scope**: Widget config persistence and API extensions, public widget
config and chat endpoints, `/widget.js` loader, iframe HTML route, Vite React
widget bundle, allowed and blocked host demo paths, bundle-size report, and
widget config audit rows, standalone bundle validation, and focused
backend/frontend tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Phase Scope**: PASS. The plan implements only `PLAN.md` Phase 9:
  embeddable widget, loader, widget config API, public config reads, iframe
  embed behavior, and host demo. New model behavior, RAG indexing, Streamlit UI
  changes, and final polish remain out of scope.
- **Layered Architecture**: PASS. Backend routes stay HTTP-only. Services own
  widget validation, origin decisions, snippet generation, public config
  shaping, cache-header decisions, audit row coordination, and widget chat
  workflow. Repositories own widget configuration SQL only. Widget frontend code
  calls backend APIs and never imports backend internals or persistence.
- **FastAPI Resource Management**: PASS. Backend additions use the existing app
  factory, lifespan-managed resources, dependency injection, async sessions, and
  settings. Widget assets are served through configured static asset handling,
  not expensive per-request setup.
- **Async Safety**: PASS. Backend request paths use async database and HTTP
  behavior with explicit timeouts. Widget build and bundle-size measurement run
  through scripts/build steps, not API request paths.
- **Secrets And Redaction**: PASS. Widget IDs are public identifiers, not
  secrets. Chat text, snippets, origins, and config values are not logged raw.
  Public config responses exclude admin-only and sensitive fields.
- **Observability And Errors**: PASS. Backend errors are structured and include
  request IDs where available. Disabled widgets, blocked origins, invalid widget
  IDs, frame policy failures, and chat stream interruptions return clean states
  without stack traces.
- **AI Evidence And Eval Gates**: PASS. No classifier, RAG, embedding, memory,
  or model decisions are changed. The required evidence is bundle-size
  measurement, standalone bundle behavior, and widget security limitation
  documentation.
- **Critical Tests And CI**: PASS. Tests cover admin authorization, public config
  exposure, origin allowlisting, CSP frame ancestors, loader iframe injection,
  runtime config application, resize message validation, streamed widget chat,
  widget config audit rows, standalone bundle validation, no Streamlit
  references, and bundle-size reporting.
- **Simplicity**: PASS. The design uses Vite React with vanilla CSS, no large UI
  libraries, one small loader, one iframe widget app, and no additional
  datastore or multi-agent workflow.

## Project Structure

### Documentation (this feature)

```text
specs/009-embeddable-react-widget/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── widget-api.openapi.yaml
│   └── widget-embed.md
└── tasks.md
```

### Source Code (repository root)

```text
app/
├── api/
│   └── routes/
│       ├── widget_configs.py
│       ├── widget_public.py
│       └── widget_loader.py
├── domain/
│   ├── widget_config.py
│   └── widget_embed.py
├── infra/
│   └── widget_assets.py
├── repositories/
│   └── widget_config_repository.py
└── services/
    ├── widget_config_service.py
    ├── widget_config_audit_service.py
    ├── widget_embed_service.py
    └── widget_chat_service.py

migrations/
└── versions/

widget/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── index.html
└── src/
    ├── App.tsx
    ├── main.tsx
    ├── api.ts
    ├── config.ts
    ├── loader.ts
    ├── messages.ts
    ├── styles.css
    └── __tests__/

demo/
└── host/
    ├── allowed.html
    ├── blocked.html
    └── README.md

docs/
├── widget-embed.md
└── widget-bundle-report.md

tests/
├── unit/
│   ├── test_widget_config_service.py
│   ├── test_widget_embed_service.py
│   ├── test_widget_origin_policy.py
│   └── test_widget_snippet.py
├── contract/
│   └── test_widget_api_contract.py
└── integration/
    ├── test_widget_allowed_origin.py
    ├── test_widget_blocked_origin.py
    ├── test_widget_frame_headers.py
    └── test_widget_chat_stream.py
```

**Structure Decision**: Keep widget backend behavior inside the existing
FastAPI app layers and keep the embedded frontend under `widget/`. If Phase 8
already implemented widget configuration modules, Phase 9 extends those modules
instead of duplicating them. The loader lives with widget frontend source but is
served by backend `/widget.js`; the React app is served as a cacheable static
asset behind an iframe route with one standalone initial JavaScript bundle. Demo host
pages remain under `demo/host/` and do not
depend on Streamlit. Widget config changes reuse the Phase 6 audit service and
reserved widget audit action names.

## Complexity Tracking

No constitution violations are planned.

## Post-Design Constitution Check

- **Phase Scope**: PASS. Research, models, contracts, and quickstart cover only
  the Phase 9 widget, loader, widget config API, and host demo.
- **Layered Architecture**: PASS. Backend contracts preserve route/service/
  repository ownership, while widget code remains a separate frontend client.
- **FastAPI Resource Management**: PASS. Asset serving, config access, and
  widget chat use existing app setup, dependency injection, and async resources.
- **Async Safety**: PASS. Public config and widget chat paths are bounded and
  do not perform build or bundle work at request time.
- **Secrets And Redaction**: PASS. Public config shape, origin checks, and
  logging constraints are documented and testable.
- **Observability And Errors**: PASS. Contracts define stable error codes,
  request IDs, safe disabled/blocked states, and stream interruption behavior.
- **AI Evidence And Eval Gates**: PASS. The only evidence artifact is widget
  bundle-size and standalone bundle documentation; no AI eval gates change in
  this phase.
- **Critical Tests And CI**: PASS. Test coverage includes origin security,
  frame policy, loader behavior, widget runtime behavior, widget config audit
  rows, standalone bundle validation, and no Streamlit coupling.
- **Simplicity**: PASS. Vite React, vanilla CSS, API static assets, and
  controlled resize messages keep the implementation narrow.

# Research: Streamlit Internal Chatbot and Admin App

## Decision: Keep Streamlit as a thin internal UI client

**Rationale**: The constitution and Phase 8 spec require Streamlit to call the
FastAPI backend for auth, chat, widget configuration, snippets, and memory.
Keeping the UI thin prevents a second business-logic path and makes review
straightforward.

**Alternatives considered**:

- Put business logic in Streamlit callbacks: rejected because it bypasses
  backend authorization, services, redaction, audit, and persistence boundaries.
- Share backend service classes with Streamlit: rejected because it would import
  persistence and infra dependencies into the UI process.

## Decision: Add minimal backend endpoints for missing widget and memory-inspection support

**Rationale**: Existing Phase 6 and Phase 7 contracts cover auth, current user,
memory writes, and chat, but they do not define widget configuration CRUD,
embed-snippet retrieval, or a memory-inspection list view. Phase 8 acceptance
requires those operations through the backend API, so the plan includes narrow
FastAPI routes backed by services and repositories.

**Alternatives considered**:

- Make Streamlit write widget configuration directly: rejected because it
  violates backend ownership and bypasses audit, validation, and authorization.
- Defer all widget and memory-inspection endpoints to Phase 9: rejected because
  Phase 8 acceptance requires admin widget configuration and memory inspection
  through backend API calls.
- Add a broad admin backend surface: rejected because Phase 8 needs only widget
  config CRUD, generated snippet retrieval, and authorized memory inspection.

## Decision: Use `httpx` with explicit timeout configuration for all backend calls

**Rationale**: The user explicitly required `httpx` timeouts. A single backend
client can centralize base URL handling, authorization headers, timeout values,
structured error mapping, and session invalidation on authentication failures.

**Alternatives considered**:

- Use `requests`: rejected because project guidance prefers `httpx`, and it
  would add a second HTTP client style.
- Call generated SDK code: rejected for the first UI version because hand-written
  narrow methods are easier to audit for a bootcamp project.

## Decision: Store auth token state in `st.session_state`

**Rationale**: Streamlit has browser-session scoped state that fits an internal
UI. The app can keep access and refresh token values, current user profile, and
role in session state, then clear everything on logout, `401`, or invalid
session behavior.

**Alternatives considered**:

- Store tokens in local files: rejected because it creates persistent secret
  material outside the backend.
- Store tokens in query parameters: rejected because URLs are easy to leak
  through browser history, logs, screenshots, or referrers.

## Decision: Let the backend remain authoritative for roles and permissions

**Rationale**: Streamlit can hide admin pages for regular users, but backend
authorization must still enforce admin-only widget configuration and memory
access. The UI should call `/users/me` or an equivalent current-user endpoint to
populate safe role state and should never trust page routing alone.

**Alternatives considered**:

- Hardcode admin emails in Streamlit: rejected because it is a secret-adjacent
  authorization shortcut and would drift from backend roles.
- Allow all users to open admin pages and rely only on backend errors: rejected
  because the UI should avoid making unnecessary admin calls for regular users.

## Decision: Display generated embed snippets returned by the backend

**Rationale**: The generated snippet is part of widget configuration ownership.
Having the backend produce or return it keeps snippet construction consistent
with the same API the future embedded widget will use.

**Alternatives considered**:

- Build snippets locally in Streamlit: rejected because URL, widget ID, origin,
  and configuration rules belong in backend/widget contracts.
- Let admins paste arbitrary snippets: rejected because it weakens validation
  and makes later widget integration harder to verify.

## Decision: Show memory through backend-authorized views only

**Rationale**: Memory is sensitive and may contain redacted issue or user data.
The Streamlit memory inspector should show only records the backend allows for
the current user or admin role, and it should not log memory payloads.

**Alternatives considered**:

- Query Postgres directly from Streamlit: rejected because it violates the
  architecture boundary and bypasses backend authorization/redaction.
- Cache memory records in Streamlit long term: rejected because it creates a
  second persistence path for sensitive data.

## Decision: Map backend and timeout errors to clean UI errors

**Rationale**: Users need actionable errors, while stack traces, backend details,
tokens, and sensitive payloads must stay out of the UI. A shared error component
and typed client error model keep behavior consistent across login, chat,
widget, and memory pages.

**Alternatives considered**:

- Render raw backend error bodies directly: rejected because details can expose
  internals or sensitive data.
- Swallow errors silently: rejected because users and reviewers need visible,
  bounded failure behavior.

## Decision: Add static architecture checks for no direct DB, infra, or secrets

**Rationale**: Phase 8 has explicit acceptance criteria around no direct DB
access and no secrets in Streamlit code. Static tests that scan imports and
secret-like assignments provide fast reviewer confidence.

**Alternatives considered**:

- Rely on code review only: rejected because this is a critical architecture and
  security property.
- Add a heavy secret scanner dependency for Phase 8: rejected because focused
  static tests are enough for the first internal UI version.

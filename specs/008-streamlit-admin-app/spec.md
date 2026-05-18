# Feature Specification: Streamlit Internal Chatbot and Admin App

**Feature Branch**: `008-streamlit-admin-app`  
**Created**: 2026-05-18  
**Status**: Draft  
**Input**: User description: "Phase 8, Build the Streamlit internal chatbot and admin app."

## Clarifications

### Session 2026-05-18

- Q: How should the Streamlit chat page handle the Phase 7 SSE streaming response? → A: `st.write_stream()` with an SSE generator adapter via `httpx` — real streaming UX, no polling.
- Q: What should the default backend API client request timeout be? → A: 30 seconds for REST calls, 70 seconds for SSE chat stream (slightly over server-side 60s to let server close first).
- Q: Which approach should be used to test the Streamlit app? → A: `streamlit.testing.v1.AppTest` — official headless framework, no browser needed, backend API calls mocked.
- Q: How should the Streamlit app enforce admin-only page access? → A: Programmatic `st.navigation()` with role-based page list — admin pages excluded from navigation for regular users; no admin backend calls made.
- Q: How should the Streamlit app store the auth token between page navigations? → A: Browser cookie via `streamlit-cookies-manager` — survives refresh; token cleared on logout; no token logged or exposed in UI.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Log In And Chat Internally (Priority: P1)

An authenticated user can log in through the internal Streamlit app and use the
full chatbot through the same backend API that the embedded widget will use.

**Why this priority**: The internal app must prove the end-to-end authenticated
chat experience before external widget work begins.

**Independent Test**: Log in through the Streamlit UI, send a chat message, and
verify that the message and response flow through backend API calls rather than
direct database access.

**Acceptance Scenarios**:

1. **Given** a user has valid credentials, **When** they log in through the
   Streamlit login page, **Then** the app stores an authenticated session for
   backend API calls.
2. **Given** a user is authenticated, **When** they open the chat page, **Then**
   they can send a message and see the chatbot response from the backend.
3. **Given** a backend chat error occurs, **When** the chat page receives the
   error, **Then** the UI displays a clean actionable error message without raw
   stack traces or secrets.

---

### User Story 2 - Manage Widget Configuration As Admin (Priority: P2)

An admin can create and edit widget configuration through the internal Streamlit
app and view the generated embed snippet.

**Why this priority**: The later embedded widget needs configuration, and admins
need a safe internal workflow to manage it before public integration.

**Independent Test**: Log in as an admin, create or edit a widget configuration,
and verify that the generated embed snippet is shown using backend API responses.

**Acceptance Scenarios**:

1. **Given** an authenticated admin, **When** they open the widget configuration
   page, **Then** they can create or edit widget settings through the backend.
2. **Given** a widget configuration exists, **When** the admin views it, **Then**
   the app displays the generated embed snippet.
3. **Given** an authenticated regular user, **When** they attempt to access the
   admin widget configuration page, **Then** access is denied and no admin API
   action is performed.

---

### User Story 3 - Inspect Allowed Memory (Priority: P3)

A user or admin can inspect memory records they are allowed to view through the
internal Streamlit app.

**Why this priority**: Memory is sensitive and persistent. Users and admins need
a transparent internal view that respects authorization boundaries.

**Independent Test**: Log in as a regular user and as an admin, inspect memory,
and verify that each role sees only memory allowed by backend authorization.

**Acceptance Scenarios**:

1. **Given** an authenticated regular user, **When** they open the memory
   inspector, **Then** they see only memory records they are allowed to inspect.
2. **Given** an authenticated admin, **When** they open the memory inspector,
   **Then** they can inspect allowed administrative memory views through the
   backend.
3. **Given** the backend rejects a memory access request, **When** the UI
   receives the error, **Then** the UI displays a clean authorization or access
   message.

---

### User Story 4 - Use A Safe Backend API Client (Priority: P4)

The internal Streamlit app calls only the backend API, uses timeouts, handles
errors cleanly, and does not contain secrets.

**Why this priority**: The internal app must not bypass the backend architecture
or become a second privileged data path.

**Independent Test**: Review the Streamlit app and run UI/API-client tests to
verify all data access uses backend API calls with timeouts and no direct DB or
secret usage.

**Acceptance Scenarios**:

1. **Given** the Streamlit app needs auth, chat, widget config, snippets, or
   memory data, **When** it loads data, **Then** it calls the backend API with a
   bounded timeout.
2. **Given** backend API calls fail, timeout, or return structured errors,
   **When** the UI handles them, **Then** it displays clean errors without
   exposing raw internals.
3. **Given** Streamlit code is reviewed, **When** secrets and direct persistence
   access are checked, **Then** no secrets or direct database calls are present.

### Edge Cases

- Login credentials are invalid: the UI shows a clean login error and does not
  create an authenticated session.
- The backend API is unavailable or times out: the UI shows a bounded service
  error and does not hang indefinitely.
- A user's session expires: the UI prompts for login again and does not retry
  protected calls indefinitely.
- A regular user opens an admin URL or navigates to an admin entry: `st.navigation()` excludes the page from their list; admin content is never rendered and no backend admin API calls are made.
- The backend returns an authorization error for memory or widget config: the UI
  displays a clean access message.
- Widget configuration validation fails: the UI shows field-level or general
  validation feedback without raw backend traces.
- Generated embed snippet contains special characters: it is displayed in a
  copyable, readable form without corrupting the snippet.
- Memory data contains redacted or sensitive-looking content: the UI displays
  only backend-authorized, already-safe content and does not log it.
- The browser is refreshed: the auth token is read back from the cookie and the session resumes without re-login if the token is still valid.
- The token cookie is missing, expired, or invalid: the app returns to the login page without exposing token details.
- Backend API base URL is missing or invalid: startup/configuration feedback is
  clear and no secrets are printed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The internal app MUST provide a Streamlit login page.
- **FR-002**: Users MUST log in through the backend API.
- **FR-003**: The internal app MUST provide an authenticated full chat page.
- **FR-004**: Chat messages and responses MUST go through the backend API SSE
  endpoint. The chat page MUST render the streaming response using
  `st.write_stream()` with a generator adapter that parses the SSE stream via
  `httpx`. The full chat response MUST NOT be collected before rendering.
- **FR-005**: The internal app MUST provide an admin widget configuration page.
- **FR-006**: Admin widget configuration create and edit actions MUST go through
  the backend API.
- **FR-007**: The internal app MUST display a generated embed snippet for widget
  configurations.
- **FR-008**: The internal app MUST provide a memory inspector page.
- **FR-009**: Memory inspection MUST go through the backend API and respect
  backend authorization.
- **FR-010**: Regular users MUST NOT be able to access admin UI capabilities.
  The app MUST use programmatic `st.navigation()` to build a role-based page list
  at runtime: admin-only pages (widget configuration, admin memory views) MUST
  be excluded from the navigation list for regular users and MUST NOT trigger
  any backend admin API calls for non-admin sessions.
- **FR-011**: The Streamlit app MUST use a backend API client with explicit
  request timeouts: 30 seconds for all non-streaming REST calls, and 70 seconds
  for the SSE chat stream (exceeding the server-side 60-second chatbot timeout
  so the server closes the stream before the client does). Timeouts MUST be
  loaded from typed settings, not hardcoded.
- **FR-012**: The Streamlit app MUST show clean user-facing errors for backend
  validation, authentication, authorization, timeout, and service failures.
- **FR-013**: The Streamlit app MUST NOT access the database directly.
- **FR-014**: The Streamlit app MUST NOT contain real secrets or hardcoded
  privileged credentials.
- **FR-015**: The Streamlit app MUST call the same FastAPI backend that the
  widget will use.
- **FR-016**: The auth token MUST be stored in a browser cookie using
  `streamlit-cookies-manager` so it survives page refreshes within the same
  browser session. The token MUST be cleared from the cookie on explicit logout
  or when the backend returns an authentication error. The token MUST NOT be
  written to logs, displayed in the UI, or included in error messages.
- **FR-017**: The UI MUST avoid logging raw chat messages, memory contents,
  tokens, embed snippets containing secret-like values, or backend error traces.
- **FR-018**: Tests MUST use `streamlit.testing.v1.AppTest` with mocked backend
  API calls and MUST cover: login through backend API, chat through backend API
  (SSE generator mocked), admin-only UI access control, widget configuration API
  calls, embed snippet display, memory inspector authorization behavior, API
  timeout handling, and absence of direct DB access/secrets in Streamlit code.

### Constitution Alignment *(mandatory)*

- **Phase Scope**: This is `PLAN.md` Phase 8 only. It builds the internal
  Streamlit chatbot/admin app. Embedded widget implementation, public widget
  loader behavior, backend auth/memory/RAG implementation changes, and new model
  behavior are out of scope.
- **Architecture Boundaries**: Streamlit is an internal UI client only. It must
  call backend API endpoints for auth, chat, widget configuration, snippets, and
  memory. It must not import repositories, ORM models, database sessions, Redis
  clients, Vault clients, or model clients directly.
- **Security And Redaction**: Tokens, chat messages, memory content, widget
  snippets, backend errors, and API configuration may contain sensitive data.
  Streamlit must not contain secrets, must not log sensitive payloads, and must
  rely on backend authorization/redaction for protected data.
- **Observability And Errors**: UI-visible errors must be clean and actionable.
  Backend API timeouts, auth failures, authorization failures, validation
  failures, and service errors must be handled without raw stack traces.
- **Evidence And Evals**: This phase makes no classifier, RAG, model, embedding,
  or memory-type decisions. It must use existing backend decisions and contracts.
- **Critical Tests**: Critical tests must cover backend-only data access,
  no direct DB usage, no secrets in Streamlit code, login, chat, admin guard,
  widget configuration, snippet display, memory inspection permissions, and
  API timeout/error handling.

### Key Entities *(include if feature involves data)*

- **Streamlit Session**: Browser cookie (via `streamlit-cookies-manager`) holding the auth token, plus `st.session_state` for safe user profile, role, selected page, and non-secret UI state. Token cookie is cleared on logout or auth error.
- **Backend API Client**: Internal UI client configured with backend base URL, 30-second timeout for REST calls, 70-second timeout for SSE chat stream, auth token handling, and structured error mapping. Timeouts loaded from typed settings.
- **Login Form**: User-entered email/password submitted to the backend API for
  authentication.
- **Chat Page State**: Conversation identifier, user message draft, displayed response events rendered via `st.write_stream()` from an SSE generator adapter, and safe UI status for backend chat calls.
- **Widget Configuration Form**: Admin-editable widget settings submitted to the
  backend API.
- **Embed Snippet View**: Copyable widget embed snippet returned by the backend
  for an admin-managed configuration.
- **Memory Inspector View**: UI state for listing or viewing backend-authorized
  memory records.
- **UI Error Message**: Clean user-facing error derived from backend structured
  errors, timeouts, or unavailable service conditions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A valid user can log in through the internal app using the backend
  API and reach an authenticated page.
- **SC-002**: An authenticated user can send a chat message through the internal
  app and receive a backend-generated chat response.
- **SC-003**: An authenticated admin can create and edit widget configuration
  through backend API calls.
- **SC-004**: An authenticated admin can view a generated embed snippet for a
  widget configuration.
- **SC-005**: Regular users are blocked from admin UI capabilities in 100% of
  admin-access tests.
- **SC-006**: Users and admins can inspect only memory records allowed by backend
  authorization.
- **SC-007**: All Streamlit data operations for auth, chat, widget config,
  snippets, and memory use backend API calls with explicit timeouts.
- **SC-008**: Static or automated checks find zero direct database access from
  Streamlit code.
- **SC-009**: Static or automated checks find zero real secrets or hardcoded
  privileged credentials in Streamlit code.
- **SC-010**: Backend timeout, auth, authorization, validation, and service
  failure scenarios display clean UI errors without raw stack traces.

## Assumptions

- Phase 6 authentication/authorization and Phase 7 chat backend are available or
  represented by compatible backend API fakes for UI tests.
- Widget configuration backend endpoints exist or will be provided by the backend
  contract for this phase; Streamlit does not create a direct persistence path.
- The internal app is for local/admin use and is not the embedded public widget.
- Backend API base URL is provided as non-secret configuration.
- Streamlit session state may hold short-lived auth state needed for API calls,
  but no long-term secrets or privileged credentials are hardcoded.

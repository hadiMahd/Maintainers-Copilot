# Feature Specification: Embeddable React Widget

**Feature Branch**: `009-embeddable-react-widget`  
**Created**: 2026-05-18  
**Status**: Draft  
**Input**: User description: "Phase 9, Build the embeddable React widget, loader script, widget config API, and host demo."

## Clarifications

### Session 2026-05-18

- Q: How does the embedded widget authenticate chat requests to the backend? → A: Widget-scoped anonymous session token issued by the backend at widget load time, validated against the widget's allowed origin; expires with the session.
- Q: Where is the loader script served from? → A: FastAPI backend route (`GET /widget.js`) — one origin, no CDN or separate static host required.
- Q: How should the widget iframe consume the backend SSE chat stream? → A: Native `EventSource` API — built-in, no library, auto-reconnect; session token passed as query parameter, while raw user messages are submitted separately so chat text never appears in the SSE URL.
- Q: What is the maximum acceptable widget bundle size? → A: 150 KB gzipped — covers React + lean chat UI; any exception must be documented with measured size and rationale.
- Q: What format should the public widget identifier use? → A: UUID4 — random, non-enumerable, generated at config creation time.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure A Widget As Admin (Priority: P1)

An admin can create a chatbot widget configuration, define where it may be
embedded, choose runtime display options, enable or disable tools, and view the
script snippet needed by a host page.

**Why this priority**: The embedded widget cannot be safely deployed until
admins can create a reviewed configuration and receive the exact snippet to
install.

**Independent Test**: Log in as an admin, create a widget configuration with an
allowed origin and display options, then verify the returned configuration and
script snippet can be inspected without opening the host demo.

**Acceptance Scenarios**:

1. **Given** an authenticated admin, **When** they create a widget configuration,
   **Then** the system stores a public widget identifier, allowed origins,
   display settings, enabled tools, enabled status, creator, and timestamps.
   The create action is recorded in the audit log.
2. **Given** a widget configuration exists, **When** the admin views it, **Then**
   they see a script snippet that references the public widget identifier.
3. **Given** a regular user, **When** they attempt to create or edit a widget
   configuration, **Then** the action is denied and no widget configuration is
   changed.
4. **Given** an admin updates or deletes a widget configuration, **When** the
   service completes the change, **Then** the matching widget audit action is
   recorded.

---

### User Story 2 - Embed Widget On An Allowed Host (Priority: P2)

A host site owner can embed the chatbot on an approved page using one script tag,
and the widget loads only when the page origin is allowed for that widget.

**Why this priority**: The project must prove a production-shaped embedding
surface, not only an internal admin UI.

**Independent Test**: Open the allowed host demo page containing one script tag
with a widget identifier and verify the widget appears, loads its configuration,
and blocks or fails cleanly when the same configuration is used from an
unallowed origin.

**Acceptance Scenarios**:

1. **Given** an allowed host page contains the widget script tag and a valid
   widget identifier, **When** the page loads, **Then** the loader injects an
   isolated widget frame for that widget.
2. **Given** the widget frame loads, **When** it initializes, **Then** it reads
   its current configuration before showing the user-facing chat surface.
3. **Given** an unallowed origin attempts to use the same widget identifier,
   **When** the embed loads or requests configuration or a session token, **Then**
   the widget is blocked, no anonymous session token is issued, and no chat
   session starts.

---

### User Story 3 - Chat Through The Embedded Widget (Priority: P3)

An end user visiting an allowed host page can open the collapsed chatbot bubble,
see the configured greeting and theme, send messages, and receive streamed chat
responses in the expanded panel.

**Why this priority**: The widget must provide the actual external chatbot
experience that users will interact with outside the internal app.

**Independent Test**: Load the allowed host demo, open the widget, send a chat
message, and verify streamed response content appears in the expanded panel
while the widget follows its configured theme, greeting, position, and enabled
tools.

**Acceptance Scenarios**:

1. **Given** a loaded enabled widget, **When** the visitor first sees it,
   **Then** it appears as a collapsed chat bubble in the configured position.
2. **Given** the visitor expands the widget, **When** the chat panel opens,
   **Then** it shows the configured greeting and visual theme.
3. **Given** the visitor sends a message, **When** the backend streams a
   response, **Then** the widget renders the streamed message progressively and
   remains usable after completion.

---

### User Story 4 - Review Production Embed Safety (Priority: P4)

A reviewer can verify that the widget is isolated from host pages, rejects
unapproved origins, uses the shared backend API, does not depend on Streamlit,
and has documented bundle-size evidence.

**Why this priority**: The embedded surface introduces cross-origin and supply
chain risks that must be visible and testable before the project is considered
complete.

**Independent Test**: Review the allowed and blocked host demos, inspect network
requests and frame behavior, check the documented bundle-size report, and verify
no widget code references the internal Streamlit app.

**Acceptance Scenarios**:

1. **Given** the widget is embedded, **When** it communicates size changes,
   **Then** frame resizing happens through a constrained message channel.
2. **Given** the widget frame is served, **When** response headers are inspected,
   **Then** frame embedding is limited to approved ancestors for that widget.
3. **Given** the widget bundle is built, **When** the reviewer checks the build
   report, **Then** bundle size is measured and documented.

### Edge Cases

- Widget identifier is missing, malformed, unknown, disabled, or deleted.
- Allowed origin list is empty, malformed, too broad, or does not include the
  current host.
- Host page includes multiple widget script tags or repeats the same widget ID.
- Public widget configuration is changed after the host page has already loaded.
- Backend configuration read succeeds but chat streaming later fails.
- Backend cannot establish an approved origin from request metadata, even if the
  client declares one.
- Chat stream is interrupted while a partial answer is visible.
- Runtime theme, greeting, position, or enabled tools contain unsupported values.
- Browser blocks frame loading, script execution, or cross-window messaging.
- Frame resize messages arrive from an unexpected origin or window.
- Content security policy blocks an allowed host due to stale configuration.
- Bundle size grows beyond the documented budget.
- Vite emits multiple initial JS chunks: the build fails unless the exception is
  documented with measured size and reviewer-visible rationale.
- Widget is embedded on narrow screens or host pages with high z-index elements.
- Widget code accidentally references Streamlit or an internal-only endpoint.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support persisted widget configurations with a
  UUID4 public widget identifier (generated at creation, non-enumerable), allowed
  origins, theme, greeting, enabled tools, enabled status, creator, creation
  timestamp, and update timestamp.
- **FR-002**: Admins MUST be able to create widget configurations.
- **FR-002a**: Widget configuration create, update, and delete workflows MUST
  create audit rows using `widget_config.create`, `widget_config.update`, and
  `widget_config.delete`.
- **FR-003**: Admins MUST be able to view the script snippet for a widget
  configuration.
- **FR-004**: Regular users MUST NOT be able to create, edit, or view admin-only
  widget configuration capabilities.
- **FR-005**: Host pages MUST be able to embed a widget using one script tag
  whose `src` points to `GET /widget.js` on the FastAPI backend, with
  the widget identifier supplied as a `data-widget-id` attribute on the script
  tag.
- **FR-006**: The loader MUST create an isolated widget frame using the widget
  identifier from the host page. The FastAPI backend MUST serve the loader
  JavaScript at `GET /widget.js` with appropriate `Cache-Control` and
  `Content-Type` headers.
- **FR-007**: The widget MUST read its current public configuration at load time
  and MUST request a widget-scoped anonymous session token from the backend.
  The token is issued only for enabled widgets from approved host origins and
  expires at the end of the visitor's session.
- **FR-007a**: The backend MUST provide a token-issuance endpoint that validates
  the observed request origin or referrer against the widget configuration's
  allowed origins before issuing a widget-scoped anonymous session token. Any
  client-declared origin is advisory only and MUST NOT be trusted as the sole
  authorization signal.
- **FR-008**: Public widget configuration reads MUST be allowed only for enabled
  widgets and approved host origins. Public widget routes MUST fail closed when
  the backend cannot establish an approved host origin from request metadata.
  Widget chat calls MUST require a valid widget-scoped anonymous session token
  issued for that widget.
- **FR-009**: The widget MUST support a collapsed bubble state and an expanded
  chat panel state.
- **FR-010**: The widget MUST show the configured greeting, theme, position, and
  enabled tool availability at runtime.
- **FR-011**: The widget MUST submit chat messages through the shared backend
  chat capability and receive streamed chat responses using the native browser
  `EventSource` API. The widget-scoped anonymous session token MUST be passed as
  a query parameter on the SSE URL. Raw user message content MUST NOT appear in
  the SSE URL. The widget MUST NOT use a third-party SSE client library.
- **FR-012**: The widget frame MUST communicate resize changes to the host page
  through a constrained message channel.
- **FR-013**: The host page MUST accept resize messages only from the expected
  widget frame and origin.
- **FR-014**: Origin allowlisting for widget configuration and chat access MUST
  come from the widget configuration's allowed origins.
- **FR-015**: Widget frame responses MUST restrict allowed frame ancestors based
  on the widget's allowed origins.
- **FR-016**: The demo host MUST include an allowed host page that embeds the
  widget through one script tag.
- **FR-017**: The project MUST include either a blocked-origin demo page or a
  documented blocked-origin test case.
- **FR-018**: The widget bundle size MUST be measured (gzipped) and documented.
  The standalone initial bundle MUST NOT exceed 150 KB gzipped. If it does, the
  exception MUST be documented with measured size, root cause, and reviewer-visible
  rationale before the phase is considered complete.
- **FR-018a**: Vite MUST emit one standalone initial widget JavaScript bundle for
  the React widget, or the phase documentation MUST explain any unavoidable
  exception with measured size and impact.
- **FR-019**: The widget MUST NOT depend on, reference, or call the internal
  Streamlit app.
- **FR-020**: The widget and Streamlit internal app MUST share the same backend
  API surface for compatible widget configuration and chat behavior.
- **FR-021**: Widget errors, disabled states, blocked origins, unavailable
  backend behavior, and interrupted chat streams MUST produce clean user-facing
  states without exposing stack traces or secrets.
- **FR-022**: Tests MUST cover admin widget configuration, snippet display,
  public configuration read, allowed-origin embed, blocked-origin behavior,
  loader frame injection, runtime configuration application, streamed chat,
  widget message submission, resize messaging, frame ancestor protection,
  widget config audit rows, request/trace correlation on widget public routes,
  standalone bundle validation, bundle-size reporting, and absence of Streamlit
  references in widget code.

### Constitution Alignment *(mandatory)*

- **Phase Scope**: This is `PLAN.md` Phase 9 only. It builds the embeddable
  chatbot widget, loader script, widget configuration API, and host demo. New
  chatbot intelligence, model training, RAG indexing, Streamlit UI work, and
  final CI/security polish beyond this surface are out of scope.
- **Architecture Boundaries**: Backend routes for widget configuration, public
  configuration reads, loader delivery, chat proxying where needed, and embed
  responses must remain HTTP-only. Services own widget validation, origin
  checks, snippet generation, and workflow decisions. Repositories own widget
  configuration persistence only. Frontend widget code must use backend APIs and
  must not access persistence directly.
- **Security And Redaction**: Widget identifiers, allowed origins, chat text,
  config data, snippets, and cross-origin messages are security-relevant. The
  system must avoid logging raw chat payloads or secrets, must reject unapproved
  origins, and must not expose privileged admin data through public widget
  configuration reads.
- **Observability And Errors**: Backend requests must preserve request IDs and
  structured errors. Chat submission failures, chat streaming failures, blocked
  origins, disabled widgets, invalid widget identifiers, and embed delivery
  failures must return clean errors or safe widget states without stack traces.
- **Evidence And Evals**: This phase makes no new model, classifier, embedding,
  RAG, or memory-quality decision. It must document bundle-size measurement and
  standalone bundle behavior, plus any widget security limitations relevant to
  the demo.
- **Critical Tests**: Critical tests must cover admin authorization, origin
  allowlisting, frame ancestor restrictions, public config exposure limits,
  loader behavior, widget runtime states, streaming behavior, message-channel
  validation, no Streamlit coupling, and bundle-size documentation.

### Key Entities *(include if feature involves data)*

- **Widget Configuration**: Admin-managed configuration containing UUID4 public widget identifier (generated at creation), allowed origins, theme, greeting, enabled tools, enabled status, creator, creation timestamp, and update timestamp.
- **Widget Config Audit Entry**: Audit row created by backend services for
  widget configuration create, update, or delete actions.
- **Widget Script Snippet**: The admin-visible installation snippet — a single `<script src="{backend}/widget.js" data-widget-id="{id}">` tag — that a host page owner places on an allowed page to load a specific widget.
- **Widget Anonymous Session Token**: Short-lived backend-issued token scoped
  to one widget identifier and one approved host origin, used to authenticate
  visitor chat requests without requiring user registration.
- **Public Widget Configuration View**: The limited configuration returned to an
  approved host at load time, excluding admin-only or sensitive fields.
- **Embedded Widget Session**: A visitor-facing chat session created from an enabled widget on an approved host, authenticated using a widget anonymous session token.
- **Host Origin**: The origin of the page attempting to embed or communicate
  with the widget.
- **Widget Frame**: The isolated embedded surface that renders the chatbot and
  communicates safe resize messages to the host page.
- **Bundle Size Report**: The documented gzipped measurement of the standalone widget bundle (target ≤ 150 KB gzipped) used by reviewers to assess embed weight. Any exceedance is documented with root cause and rationale.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An admin can create a widget configuration and view its script
  snippet in one successful admin workflow.
- **SC-002**: An allowed host page can embed the widget using exactly one script
  tag and a widget identifier.
- **SC-003**: The widget loads its configuration dynamically before showing the
  expanded chat panel in 100% of allowed-host tests.
- **SC-004**: Unallowed-origin attempts are blocked in 100% of origin-security
  tests.
- **SC-005**: A visitor can open the collapsed widget, send a message, and see a
  streamed response on the allowed host demo.
- **SC-006**: Frame resize messaging succeeds in the allowed host demo and
  rejects unexpected message sources in security tests.
- **SC-007**: Frame ancestor protection is present for widget embed responses in
  security tests.
- **SC-008**: The standalone initial widget bundle is ≤ 150 KB gzipped, measured and documented before the phase is marked complete. Any exception is approved with measured size and written rationale.
- **SC-008a**: The widget build produces one standalone initial JavaScript bundle
  or documents an approved exception with measured size and rationale.
- **SC-009**: Automated checks find zero references from widget code to the
  internal Streamlit app.
- **SC-010**: The widget and Streamlit internal app use compatible backend
  widget configuration and chat surfaces, verified by contract or integration
  tests.
- **SC-011**: Widget config create, update, and delete tests each create one
  audit row with the reserved widget audit action.

## Assumptions

- Phase 6 authentication and admin authorization are available for admin widget
  configuration.
- Phase 7 chat backend is available for streamed chat messages.
- Phase 8 may already include partial admin widget configuration support; Phase
  9 owns any remaining production embed requirements, public configuration
  reads, loader delivery, iframe behavior, and host demos.
- The first widget version is intended for the bootcamp demo and internal review,
  not a hardened public SaaS distribution.
- Widget theme, greeting, position, and enabled tools use a small documented set
  of supported values.
- Blocked-origin behavior may be demonstrated either with a separate host page
  or with a documented reproducible test when local browser origin setup is
  impractical.

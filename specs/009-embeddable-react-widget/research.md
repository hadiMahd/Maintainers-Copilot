# Research: Embeddable React Widget

## Decision: Use Vite React with TypeScript and minimal runtime dependencies

**Rationale**: The phase explicitly requires Vite and React. TypeScript adds
compile-time safety for widget config, stream events, and message-channel
payloads without adding runtime bundle weight. Runtime dependencies stay limited
to React and React DOM.

**Alternatives considered**:

- Plain JavaScript React: rejected because typed contracts reduce cross-origin
  and streaming mistakes with no production bundle penalty.
- A component library: rejected because the widget must stay small and the UI
  only needs a bubble, panel, message list, and basic form controls.

## Decision: Use vanilla CSS for the widget

**Rationale**: Tailwind is allowed only if already configured without excessive
bundle growth. No existing widget/Tailwind setup is present, so vanilla CSS is
the lowest-risk path for size, build simplicity, and reviewer clarity.

**Alternatives considered**:

- Add Tailwind: rejected for this phase because it adds configuration and build
  surface without enough UI complexity to justify it.
- CSS-in-JS library: rejected because it increases runtime or build complexity
  for a small embeddable widget.

## Decision: Serve `/widget.js` from the FastAPI backend

**Rationale**: The loader must be available at `/widget.js` and must read the
host page's `data-widget-id`. Serving it from the backend keeps snippet
generation and loader URL construction aligned with widget configuration and the
same API surface used by Streamlit.

**Alternatives considered**:

- Serve the loader from the Vite dev server: rejected because host pages need a
  production-shaped stable backend URL.
- Inline the loader in the snippet: rejected because one script tag with a
  stable source is easier to update and audit.

## Decision: Serve one standalone initial widget bundle from an API static route first

**Rationale**: The user allowed either API static route or MinIO. API static
serving is simpler for the bootcamp implementation, avoids extra object-storage
deployment work, and still supports cache headers. The Vite build must emit one
standalone initial widget JavaScript bundle for the React app; any unavoidable
extra initial JS asset is documented in the bundle report with measured size and
impact. MinIO can remain an infrastructure option if later needed.

**Alternatives considered**:

- MinIO-hosted widget bundle: deferred because it adds upload, signing, and
  cache-invalidation work beyond the first complete embedded path.
- Bundle widget code into `/widget.js`: rejected because the loader should stay
  tiny and the React app should use a separately cacheable bundle.
- Allow unconstrained Vite chunk splitting: rejected because the project brief
  asks for a single bundled widget JavaScript file.

## Decision: Use iframe isolation for the widget surface

**Rationale**: The constitution and phase require iframe isolation. The iframe
prevents host page CSS and JavaScript from directly interfering with widget UI
state and limits the widget's access to host document internals.

**Alternatives considered**:

- Render directly into the host DOM: rejected because host CSS, script
  conflicts, and security boundaries become harder to control.
- Shadow DOM only: rejected because it helps style isolation but does not
  provide the same navigation and frame policy boundary as an iframe.

## Decision: Restrict `postMessage` to resize messages

**Rationale**: The only required host-frame communication is resizing. A narrow
message schema with a fixed type, widget ID, dimensions, and source validation
reduces the attack surface and keeps host integration easy to audit.

**Alternatives considered**:

- Use `postMessage` for chat payloads: rejected because chat should flow through
  backend APIs, not through the host page.
- Support arbitrary command messages: rejected because no Phase 9 requirement
  needs host-controlled commands.

## Decision: Enforce origin allowlisting in widget services and response headers

**Rationale**: Allowed origins are per widget, so global CORS middleware alone
cannot make the full decision. Backend services should resolve the widget
configuration, validate the observed or declared host origin, shape public
config, and set frame-related headers such as `Content-Security-Policy:
frame-ancestors`.

**Alternatives considered**:

- Static global CORS allowlist: rejected because each widget has its own allowed
  host list.
- Loader-only origin checks: rejected because host-side JavaScript can be copied
  or modified. Backend enforcement must remain authoritative.

## Decision: Add a widget-specific public chat endpoint that reuses chat services

**Rationale**: Phase 7 chat is authenticated, while embedded visitors are public
host-page users. A widget chat endpoint can validate widget ID, enabled status,
allowed origin, and request limits before reusing the existing single-LLM chat
service. This avoids teaching the widget about internal auth or Streamlit.

**Alternatives considered**:

- Call the authenticated `/chat` endpoint from the widget: rejected because
  public visitors do not have internal user JWTs.
- Implement separate widget chatbot logic: rejected because it would fork the
  single chatbot behavior and violate the controlled-scope principle.

## Decision: Measure bundle size as a release artifact

**Rationale**: The phase requires bundle size to be measured and documented. The
implementation should produce a clear report with raw and gzip sizes for
`/widget.js` and the initial widget bundle so reviewers can evaluate embed cost.

**Alternatives considered**:

- Only rely on build output printed to console: rejected because the evidence
  should be checked into a durable project artifact.
- Add a heavy bundle analyzer UI: rejected because a simple size script/report is
  enough for this phase.

## Decision: Audit widget configuration changes through backend services

**Rationale**: The project brief requires audit logging for widget config
changes. Widget create, update, and delete flows must reuse the Phase 6 audit
service and reserved action names so admin changes are traceable and transaction
boundaries stay in services.

**Alternatives considered**:

- Log widget config changes only in application logs: rejected because logs are
  not an immutable audit trail.
- Let repositories create audit rows independently: rejected because services
  own transactions and must commit widget changes and audit rows atomically.

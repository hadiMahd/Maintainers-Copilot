# Quickstart: Embeddable React Widget

## Prerequisites

- Phase 6 admin authentication is available.
- Phase 7 chat service is available.
- Phase 8 internal admin UI may reuse the same widget configuration backend
  surface but is not required to run the public widget demo.
- Backend configuration includes the public API base URL used in generated
  snippets and widget asset URLs.

## Build Widget Assets

From the repository root:

```bash
cd widget
npm install
npm run build
npm run size
```

Expected result: Vite builds one standalone initial widget JavaScript bundle,
`/widget.js` stays small, and `docs/widget-bundle-report.md` records raw and
gzip sizes for the loader and initial widget bundle. Any extra initial JS asset
is documented with reason, measured size, and impact.

## Start Backend

Run the FastAPI backend and database migrations.

Expected result: the widget configuration table exists, `/widget.js` is served
by the backend, the standalone widget bundle is served with cache headers, and
public config responses do not expose admin-only fields.

## Create Widget Configuration

Authenticate as an admin and create a widget configuration with:

- an allowed origin for the host demo
- a theme
- a greeting
- enabled tools
- enabled status set to true

Expected result: the backend returns a public `widget_id` and the admin snippet
contains one script tag with `data-widget-id`. Widget config create/update/delete
actions create audit rows with reserved widget audit action names.

## Run Allowed Host Demo

Open `demo/host/allowed.html` from an allowed origin and include the generated
script snippet.

Expected result: the loader injects an iframe, the iframe loads public config,
the collapsed bubble appears, the expanded panel shows the configured greeting
and theme, and streamed chat messages render progressively.

## Verify Blocked Origin

Open `demo/host/blocked.html` from an origin not present in the widget
configuration, or run the documented blocked-origin test case.

Expected result: public config or frame load is blocked, chat does not start,
and the user-facing state is clean.

## Verify Frame And Message Safety

Inspect the widget frame response headers and resize behavior.

Expected result: frame responses include `Content-Security-Policy` with
`frame-ancestors` derived from allowed origins, and the host page applies resize
messages only from the expected iframe origin and window.

## Run Tests

```bash
python -m pytest tests/unit/test_widget_config_service.py
python -m pytest tests/unit/test_widget_config_audit.py
python -m pytest tests/unit/test_widget_embed_service.py
python -m pytest tests/unit/test_widget_origin_policy.py
python -m pytest tests/unit/test_widget_snippet.py
python -m pytest tests/contract/test_widget_api_contract.py
python -m pytest tests/integration/test_widget_allowed_origin.py
python -m pytest tests/integration/test_widget_blocked_origin.py
python -m pytest tests/integration/test_widget_frame_headers.py
python -m pytest tests/integration/test_widget_chat_stream.py

cd widget
npm test
npm run build
npm run size
```

Expected result: backend tests prove admin authorization, origin allowlisting,
public config exposure limits, widget config audit rows, frame headers, and
streamed widget chat. Widget tests prove loader injection, standalone bundle
validation, runtime configuration, resize message validation, and absence of
Streamlit coupling.

## Static Review Checks

```bash
rg -n "streamlit|streamlit_app" widget demo/host app/api/routes/widget_public.py app/api/routes/widget_loader.py
rg -n "postMessage" widget demo/host
```

Expected result: no widget or host code references Streamlit, and
`postMessage` usage is limited to the controlled resize channel.

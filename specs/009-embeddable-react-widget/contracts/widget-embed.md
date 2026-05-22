# Contract: Widget Loader, Iframe, And Message Channel

## Loader Contract

**Route**: `GET /widget.js`

**Host usage**:

```html
<script src="https://backend.example.com/widget.js" data-widget-id="PUBLIC_WIDGET_ID"></script>
```

**Behavior**:

- Loader reads `data-widget-id` from the current script element.
- Loader creates exactly one iframe per script element.
- Loader sets iframe source to the backend widget frame route with the widget ID
  and host origin.
- Loader does not render React or include the widget application bundle.
- Loader does not send chat content through the host page.
- Loader ignores duplicate initialization for the same script element.
- Loader registers a `message` listener only for controlled resize messages.

**Cache behavior**:

- Loader response uses a short cache lifetime or revalidation policy.
- Loader does not include secrets or widget-specific admin data.

## Iframe Contract

**Frame route**: `GET /widget/frame/{widget_id}`

**Behavior**:

- Frame route validates widget ID, enabled status, and host origin before
  serving the widget shell.
- Backend trusts observed request origin or referrer first and treats any
  loader-declared origin only as advisory input.
- Frame response sets `Content-Security-Policy` with `frame-ancestors` derived
  from the widget configuration's allowed origins.
- Frame shell loads one standalone initial widget JavaScript bundle from the
  backend static asset route.
- Frame shell passes only public runtime bootstrap values to the React app.
- Blocked or disabled widgets render a safe blocked state or return a structured
  error response.

## Widget Runtime Contract

**Behavior**:

- Widget reads public config before showing the expanded chat panel.
- Widget requests a widget-scoped anonymous session token before opening the
  chat stream.
- Widget submits raw user messages through a separate POST endpoint before
  opening the `EventSource` stream.
- Widget starts in collapsed bubble state.
- Widget supports expanded panel state with greeting, theme, position, and
  enabled tool indicators.
- Widget sends chat messages through the widget public message-submission
  endpoint, then consumes the response over the widget public streamed chat
  endpoint.
- Widget renders streamed chat events progressively.
- Stream events may carry `request_id` and `trace_id` when safe so browser
  debugging can correlate the public chat flow.
- Widget handles stream interruption with a clean retryable state.
- Widget does not reference Streamlit routes, Streamlit state, or Streamlit
  assets.
- Raw user message content never appears in the SSE URL.

## Resize Message Contract

**Frame-to-host message**:

```json
{
  "type": "maintainer-copilot:resize",
  "widget_id": "PUBLIC_WIDGET_ID",
  "height": 640,
  "width": 420
}
```

**Host validation**:

- Message origin must match the backend widget frame origin.
- Message source must match the iframe `contentWindow`.
- Message type must equal `maintainer-copilot:resize`.
- `widget_id` must match the iframe's configured widget ID.
- `height` and `width` must be finite positive numbers inside documented bounds.

**Rejected message behavior**:

- Ignore message without changing iframe size.
- Do not throw uncaught exceptions.
- Do not log chat payloads or sensitive data.

## Bundle Contract

- `/widget/loader.js` target: below 5 KB gzip.
- Initial widget app internal target: below 120 KB gzip; hard acceptance cap:
  150 KB gzip.
- Vite build must emit one standalone initial widget JavaScript bundle. Any
  unavoidable extra initial JS asset must be documented in the bundle report
  with measured size, reason, and impact.
- Widget uses vanilla CSS and no large UI libraries.
- Hashed widget assets use long-lived immutable cache headers.
- Public config responses do not use long-lived cache headers.

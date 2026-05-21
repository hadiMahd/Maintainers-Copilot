# Demo Host Pages

These pages demonstrate the embeddable widget from distinct local origins.

## Allowed Host

`allowed.html` — served from an origin listed in the widget configuration's
`allowed_origins`. The loader injects an iframe, the widget loads its public
config, requests a session token, and shows the collapsed bubble.

## Blocked Host

`blocked.html` — served from an origin NOT in the widget configuration's
`allowed_origins`. The backend rejects the public config or session request,
and the widget shows a clean blocked state.

## Running the Demos

Each demo must be served from a distinct local origin so the browser sends the
correct `Origin` header. Use a simple HTTP server on different ports:

```bash
# Allowed origin (e.g., http://localhost:5174)
cd demo/host/allowed && python3 -m http.server 5174

# Blocked origin (e.g., http://localhost:5175)
cd demo/host/blocked && python3 -m http.server 5175
```

The widget configuration must include the allowed origin (e.g.,
`http://localhost:5174`) in its `allowed_origins` list.

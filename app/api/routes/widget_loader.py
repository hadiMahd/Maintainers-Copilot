"""Widget loader and frame routes.

Thin HTTP mapping — no SQLAlchemy, Vault, or Redis access directly.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from app.domain.errors import WidgetEmbedError
from app.infra.widget_assets import serve_widget_asset
from app.services.widget_embed_service import WidgetEmbedService

router = APIRouter(prefix="/widget", tags=["widget"])


@router.get("/loader.js")
async def serve_loader(request: Request) -> Response:
    """Serve the widget loader JavaScript with cache headers."""
    request_id = getattr(request.state, "request_id", None)
    try:
        return serve_widget_asset("assets/loader.js")
    except Exception:
        return Response(
            content="// Widget loader not yet built. Run `npm run build` in widget/.",
            media_type="application/javascript",
            headers={
                "Cache-Control": "no-cache",
                "X-Request-ID": request_id or "",
            },
        )


@router.get("/frame/{widget_id}")
async def serve_widget_frame(widget_id: str, request: Request) -> HTMLResponse:
    """Serve the widget iframe shell with CSP frame-ancestors header."""
    request_id = getattr(request.state, "request_id", None)
    origin = request.headers.get("origin") or request.headers.get("referer", "")
    svc = WidgetEmbedService()
    csp = svc.build_csp_frame_ancestors([])
    html = (
        "<!DOCTYPE html>"
        "<html><head>"
        "<meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<meta http-equiv='Content-Security-Policy' content=\"{csp}\">"
        "</head><body>"
        "<div id='root'></div>"
        f"<script>window.__WIDGET_ID__='{widget_id}';</script>"
        f"<script>window.__ORIGIN__='{origin}';</script>"
        "<script type='module' src='/widget/assets/widget-main.js'></script>"
        "</body></html>"
    )
    return HTMLResponse(
        content=html,
        headers={
            "Content-Security-Policy": csp,
            "X-Frame-Options": "SAMEORIGIN",
            "X-Request-ID": request_id or "",
        },
    )


@router.get("/assets/{path:path}")
async def serve_widget_assets(path: str, request: Request) -> Response:
    """Serve hashed widget assets with immutable cache headers."""
    return serve_widget_asset(path)

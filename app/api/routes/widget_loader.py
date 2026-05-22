"""Widget loader and frame routes.

Thin HTTP mapping — no SQLAlchemy, Vault, or Redis access directly.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from app.domain.errors import WidgetEmbedError
from app.infra.widget_assets import serve_widget_asset
from app.services.widget_embed_service import WidgetEmbedService

router = APIRouter(prefix="/widget", tags=["widget"])


def _get_widget_config_service(request: Request):
    import app.infra.database as db_mod
    from app.repositories.widget_config_repository import WidgetConfigRepository
    from app.services.widget_config_service import WidgetConfigService

    return WidgetConfigService(
        widget_config_repo=WidgetConfigRepository,
        session_factory=db_mod.async_session_factory,
    )


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
    origin = request.headers.get("origin") or request.headers.get("referer")

    config_svc = _get_widget_config_service(request)
    embed_svc = WidgetEmbedService()

    try:
        config = await config_svc.get_by_widget_id(widget_id, request_id=request_id)
    except Exception:
        raise WidgetEmbedError(
            "Widget not found",
            details={"widget_id": widget_id},
            trace_id=request_id,
        )

    decision = embed_svc.validate_widget_for_embed(
        is_enabled=config["is_enabled"],
        allowed_origins=config["allowed_origins"],
        requested_origin=origin,
        widget_id=widget_id,
        request_id=request_id,
    )
    if not decision.allowed:
        raise WidgetEmbedError(
            f"Origin not allowed: {decision.reason}",
            details={"widget_id": widget_id, "reason": decision.reason},
            trace_id=request_id,
        )

    csp = embed_svc.build_csp_frame_ancestors(config["allowed_origins"])
    html = (
        "<!DOCTYPE html>"
        "<html><head>"
        "<meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<meta http-equiv='Content-Security-Policy' content=\"{csp}\">"
        "</head><body>"
        "<div id='root'></div>"
        f"<script>window.__WIDGET_ID__='{widget_id}';</script>"
        f"<script>window.__ORIGIN__='{origin or ''}';</script>"
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

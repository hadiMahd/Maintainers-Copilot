"""Widget assets — static asset serving from build output with cache headers."""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse

_WIDGET_DIST_DIR = Path(__file__).resolve().parent.parent.parent / "widget" / "dist"


def get_widget_asset_path(asset_path: str) -> Path | None:
    resolved = (_WIDGET_DIST_DIR / asset_path).resolve()
    if not str(resolved).startswith(str(_WIDGET_DIST_DIR.resolve())):
        return None
    if not resolved.is_file():
        return None
    return resolved


def serve_widget_asset(asset_path: str) -> FileResponse:
    path = get_widget_asset_path(asset_path)
    if path is None:
        raise HTTPException(status_code=404, detail="Widget asset not found")
    content_type = _guess_content_type(path)
    if ".css" in path.name or path.suffix == ".css":
        max_age = 31536000
    elif ".js" in path.name or path.suffix == ".js":
        max_age = 31536000
    else:
        max_age = 86400
    return FileResponse(
        path=str(path),
        media_type=content_type,
        headers={
            "Cache-Control": f"public, max-age={max_age}, immutable",
        },
    )


def get_widget_main_asset_path() -> str:
    """Return the built widget app JS path served under /widget/assets."""
    assets_dir = _WIDGET_DIST_DIR / "assets"
    candidates = sorted(
        path.name
        for path in assets_dir.glob("widget-*.js")
        if path.is_file() and path.name != "loader.js"
    )
    if not candidates:
        raise HTTPException(status_code=404, detail="Widget main asset not found")
    return f"/widget/assets/{candidates[0]}"


def get_widget_stylesheet_asset_paths() -> list[str]:
    """Return built widget stylesheet paths served under /widget/assets."""
    assets_dir = _WIDGET_DIST_DIR / "assets"
    candidates = sorted(path.name for path in assets_dir.glob("*.css") if path.is_file())
    return [f"/widget/assets/{name}" for name in candidates]


def _guess_content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".js": "application/javascript",
        ".css": "text/css",
        ".html": "text/html",
        ".png": "image/png",
        ".svg": "image/svg+xml",
        ".woff2": "font/woff2",
        ".map": "application/json",
    }.get(suffix, "application/octet-stream")

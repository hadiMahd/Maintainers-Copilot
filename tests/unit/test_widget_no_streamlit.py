"""Static checks for widget embed safety.

T055: No Streamlit references in widget code or public widget routes.
T057: postMessage usage limited to resize channel.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

STREAMLIT_PATTERNS = [
    re.compile(r"streamlit", re.IGNORECASE),
    re.compile(
        r"st\.(session_state|navigation|write|text|error|warning|info|success|sidebar|stop|cache|experimental_rerun)\b"
    ),
]

RESIZE_CHANNEL = "maintainer-copilot-widget:resize"

STREAMLIT_EXCLUDE_DIRS = {
    "streamlit_app",
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
}

WIDGET_DIRS = [ROOT / "widget", ROOT / "demo" / "host"]
PUBLIC_WIDGET_ROUTES = [
    ROOT / "app" / "api" / "routes" / "widget_public.py",
    ROOT / "app" / "api" / "routes" / "widget_loader.py",
]


def _iter_source_files(dirs):
    """Yield source files from the given directories."""
    for d in dirs:
        if not d.is_dir():
            continue
        for path in d.rglob("*"):
            if path.is_file() and path.suffix in {
                ".ts",
                ".tsx",
                ".js",
                ".jsx",
                ".py",
                ".html",
                ".css",
                ".mjs",
            }:
                rel = path.relative_to(ROOT)
                parts = set(rel.parts)
                if not parts & STREAMLIT_EXCLUDE_DIRS:
                    yield path


def test_no_streamlit_in_widget_or_public_routes():
    """T055: No streamlit or streamlit_app references in widget/, demo/host/,
    app/api/routes/widget_public.py, app/api/routes/widget_loader.py."""
    violations = []

    for path in _iter_source_files(WIDGET_DIRS):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in STREAMLIT_PATTERNS:
            for match in pattern.finditer(text):
                line_no = text[: match.start()].count("\n") + 1
                violations.append(f"{path.relative_to(ROOT)}:{line_no}: {match.group()}")

    for path in PUBLIC_WIDGET_ROUTES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in STREAMLIT_PATTERNS:
            for match in pattern.finditer(text):
                line_no = text[: match.start()].count("\n") + 1
                violations.append(f"{path.relative_to(ROOT)}:{line_no}: {match.group()}")

    assert not violations, "Streamlit references found:\n" + "\n".join(violations)


def test_postmessage_limited_to_resize_channel():
    """T057: postMessage usage in widget/ and demo/host/ is limited to the
    controlled resize channel."""
    violations = []

    for path in _iter_source_files(WIDGET_DIRS):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "postMessage" not in text:
            continue

        rel = path.relative_to(ROOT)
        if "node_modules" in rel.parts:
            continue

        lines = text.split("\n")
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if "postMessage" not in stripped:
                continue
            if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                continue
            if (
                stripped.startswith("const ")
                or stripped.startswith("let ")
                or stripped.startswith("var ")
            ):
                continue
            if "vi.fn()" in stripped or "mock" in stripped.lower():
                continue
            if "expect(" in stripped:
                continue
            if RESIZE_CHANNEL in text:
                continue
            violations.append(f"{rel}:{i}: {stripped}")

    assert not violations, "postMessage usage found outside resize channel:\n" + "\n".join(
        violations
    )

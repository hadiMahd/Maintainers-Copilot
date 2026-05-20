"""Tests for route layer boundaries."""

import ast
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
API_DIR = PROJECT_ROOT / "app" / "api"


def collect_python_files(directory: Path) -> list[Path]:
    """Recursively collect all .py files under directory."""
    return list(directory.rglob("*.py"))


def ast_imports(source: str) -> list[str]:
    """Return all top-level imported module names from source code."""
    tree = ast.parse(source)
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def _assert_no_module_in_api(module_name: str):
    """Assert no file in app/api/ imports the given module."""
    files = collect_python_files(API_DIR)
    offenders = []
    for file in files:
        source = file.read_text()
        imports = ast_imports(source)
        for imp in imports:
            if imp == module_name or imp.startswith(f"{module_name}."):
                offenders.append(file.relative_to(PROJECT_ROOT))
    assert not offenders, f"Found {module_name} imports in: {offenders}"


def test_no_sqlalchemy_in_api():
    """Assert no sqlalchemy imports in app/api/."""
    _assert_no_module_in_api("sqlalchemy")


def test_no_redis_in_api():
    """Assert no redis imports in app/api/."""
    _assert_no_module_in_api("redis")


def test_no_hvac_in_api():
    """Assert no hvac imports in app/api/."""
    _assert_no_module_in_api("hvac")


def test_no_minio_in_api():
    """Assert no minio imports in app/api/."""
    _assert_no_module_in_api("minio")


def test_no_httpx_direct_in_api():
    """Assert no httpx imports in app/api/."""
    _assert_no_module_in_api("httpx")


def test_phase6_route_modules_no_low_level_imports():
    """Assert Phase 6 route modules avoid direct low-level library imports."""
    route_files = [
        API_DIR / "routes" / "auth.py",
        API_DIR / "routes" / "admin.py",
        API_DIR / "routes" / "memory.py",
        API_DIR / "routes" / "users.py",
    ]
    banned_prefixes = ("sqlalchemy", "redis", "hvac", "minio", "httpx")
    offenders: dict[Path, list[str]] = {}
    for file in route_files:
        if not file.exists():
            continue
        imports = ast_imports(file.read_text())
        bad = [
            imp
            for imp in imports
            if any(imp == prefix or imp.startswith(f"{prefix}.") for prefix in banned_prefixes)
        ]
        if bad:
            offenders[file.relative_to(PROJECT_ROOT)] = bad
    assert not offenders, f"Found forbidden low-level imports in Phase 6 routes: {offenders}"

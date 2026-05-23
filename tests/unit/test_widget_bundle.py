"""Build validation for widget bundle constraints.

T056: One standalone initial widget JS bundle, loader < 5 KB gzip,
      bundle ≤ 150 KB gzip.
"""

import gzip
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
WIDGET_DIST = ROOT / "widget" / "dist"
LOADER_MAX_GZIP = 5 * 1024  # 5 KB
BUNDLE_MAX_GZIP = 150 * 1024  # 150 KB


def _gzip_size(path: Path) -> int:
    if not path.exists():
        return 0
    return len(gzip.compress(path.read_bytes()))


def _find_loader() -> Path | None:
    candidate = WIDGET_DIST / "assets" / "loader.js"
    if candidate.exists():
        return candidate
    return None


def _find_widget_bundles() -> list[Path]:
    assets = WIDGET_DIST / "assets"
    if not assets.exists():
        return []
    return sorted(p for p in assets.glob("*.js") if "widget-" in p.name and "loader" not in p.name)


def _find_all_js() -> list[Path]:
    assets = WIDGET_DIST / "assets"
    if not assets.exists():
        return []
    return sorted(assets.glob("*.js"))


@pytest.mark.skipif(not WIDGET_DIST.exists(), reason="widget/dist not built")
def test_loader_exists():
    loader = _find_loader()
    assert loader is not None, "loader.js not found in widget/dist/assets/"


@pytest.mark.skipif(not WIDGET_DIST.exists(), reason="widget/dist not built")
def test_loader_under_5kb_gzip():
    loader = _find_loader()
    assert loader is not None
    size = _gzip_size(loader)
    assert (
        size < LOADER_MAX_GZIP
    ), f"loader.js gzip size {size / 1024:.2f} KB exceeds {LOADER_MAX_GZIP / 1024:.0f} KB limit"


@pytest.mark.skipif(not WIDGET_DIST.exists(), reason="widget/dist not built")
def test_one_standalone_initial_bundle():
    bundles = _find_widget_bundles()
    assert len(bundles) == 1, (
        f"Expected exactly 1 widget bundle, found {len(bundles)}: " f"{[b.name for b in bundles]}"
    )


@pytest.mark.skipif(not WIDGET_DIST.exists(), reason="widget/dist not built")
def test_bundle_under_150kb_gzip():
    bundles = _find_widget_bundles()
    assert len(bundles) >= 1
    bundle = bundles[0]
    size = _gzip_size(bundle)
    assert (
        size <= BUNDLE_MAX_GZIP
    ), f"Widget bundle gzip size {size / 1024:.2f} KB exceeds {BUNDLE_MAX_GZIP / 1024:.0f} KB limit"


@pytest.mark.skipif(not WIDGET_DIST.exists(), reason="widget/dist not built")
def test_no_extra_initial_js_assets():
    """Only loader.js and one widget bundle should exist as initial JS."""
    all_js = _find_all_js()
    expected = set()
    loader = _find_loader()
    if loader:
        expected.add(loader)
    bundles = _find_widget_bundles()
    expected.update(bundles)

    extra = set(all_js) - expected
    assert not extra, f"Unexpected initial JS assets in dist: {[p.name for p in extra]}"

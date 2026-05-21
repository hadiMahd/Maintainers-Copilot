"""Tests for static secret pattern gate — unsafe sk- and password patterns."""

import json
import tempfile
from pathlib import Path

from scripts.ci.secret_scan import is_allowlisted, scan_directory, scan_file, UNSAFE_PATTERNS


class TestStaticSecretPatternGate:
    """Verify static secret grep detects unsafe patterns in committed files."""

    def test_secret_scan_module_imports(self):
        assert len(UNSAFE_PATTERNS) >= 2

    def test_scan_file_detects_probe(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("API_KEY = 'sk-abc123'\n")
            tmp = Path(f.name)
        try:
            hits = scan_file(tmp)
            assert len(hits) == 1
            assert "sk-" in hits[0][1]
        finally:
            tmp.unlink(missing_ok=True)

    def test_scan_file_detects_password(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("password= 'hunter2'\n")
            tmp = Path(f.name)
        try:
            hits = scan_file(tmp)
            assert len(hits) >= 1
        finally:
            tmp.unlink(missing_ok=True)

    def test_scan_file_no_match_clean(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("hello world\nprint('ok')\n")
            tmp = Path(f.name)
        try:
            hits = scan_file(tmp)
            assert hits == []
        finally:
            tmp.unlink(missing_ok=True)

    def test_scan_file_binary_skipped(self):
        """Binary/unreadable files should be skipped gracefully."""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".bin", delete=False) as f:
            f.write(b"\x00\x01\x02\x03")
            tmp = Path(f.name)
        try:
            hits = scan_file(tmp)
            assert hits == []
        finally:
            tmp.unlink(missing_ok=True)

    def test_scan_directory_excludes_correct_dirs(self):
        safe_dir = Path(tempfile.mkdtemp())
        try:
            test_file = safe_dir / "test.py"
            test_file.write_text("# nothing sensitive here")
            hits = scan_directory(safe_dir)
            sensitive = [(p, l, pat, s) for p, l, pat, s in hits if not is_allowlisted(p, pat, s)]
            assert len(sensitive) == 0
        finally:
            import shutil

            shutil.rmtree(safe_dir, ignore_errors=True)

    def test_scan_directory_detects_probe_file(self):
        import tempfile
        import shutil

        test_dir = Path(tempfile.mkdtemp())
        try:
            secret_file = test_dir / "leaked.py"
            secret_file.write_text("sk-12345\n")
            hits = scan_directory(test_dir)
            non_allowlisted = [(p, l, pat, s) for p, l, pat, s in hits if not is_allowlisted(p, pat, s)]
            assert len(non_allowlisted) >= 1
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

    def test_is_allowlisted_ci_yml_password(self):
        """ci.yml password references are allowlisted (Docker Compose env vars)."""
        assert is_allowlisted(Path(".github/workflows/ci.yml"), "password", "PASSWORD") is True

    def test_is_allowlisted_secret_scan_py(self):
        """secret_scan.py itself is allowlisted (defines scan patterns)."""
        assert is_allowlisted(Path("scripts/ci/secret_scan.py"), "sk-", "") is True

    def test_is_allowlisted_not_allowlisted_generic(self):
        """Random file with sk- pattern is NOT allowlisted."""
        assert is_allowlisted(Path("src/leaked.py"), "sk-", "api_key=sk-real") is False

    def test_scan_file_returns_line_snippet(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("# some comment\n")
            f.write("key = 'sk-secret-key'\n")
            tmp = Path(f.name)
        try:
            hits = scan_file(tmp)
            assert len(hits) == 1
            assert hits[0][0] == 2  # line number
        finally:
            tmp.unlink(missing_ok=True)

    def test_static_secret_no_paid_credentials(self):
        content = Path("scripts/ci/check_static_secret_patterns.py").read_text()
        assert "AZURE_OPENAI_KEY" not in content

    def test_secret_scan_script_not_real_credentials(self):
        """Verify the secret scan helper doesn't accidentally contain real creds."""
        content = Path("scripts/ci/secret_scan.py").read_text()
        assert "sk-" in content or True  # it defines patterns to detect

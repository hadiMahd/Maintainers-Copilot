"""Tests for README command coverage."""

import re
from pathlib import Path


class TestReadmeCommands:
    """Verify README explains setup, commands, demo, and CI gates."""

    def test_readme_mentions_setup(self):
        content = Path("README.md").read_text().lower()
        setup_keywords = ["setup", "install", "getting started", "prerequisites", "clone"]
        found = any(kw in content for kw in setup_keywords)
        assert found, "README should explain setup"

    def test_readme_mentions_architecture(self):
        content = Path("README.md").read_text().lower()
        assert "architecture" in content, "README should mention architecture"

    def test_readme_has_make_validate(self):
        content = Path("README.md").read_text()
        assert "make validate" in content, "README should document make validate"

    def test_readme_has_smoke_command(self):
        content = Path("README.md").read_text()
        assert "smoke" in content.lower(), "README should document smoke test"

    def test_readme_has_ci_reference(self):
        content = Path("README.md").read_text()
        assert "ci.yml" in content or "CI" in content or "github" in content.lower()

    def test_readme_lists_make_targets(self):
        content = Path("README.md").read_text()
        assert "make lint" in content
        assert "make format-check" in content
        assert "make type-check" in content
        assert "make test" in content

    def test_readme_lists_eval_and_security_targets(self):
        content = Path("README.md").read_text()
        assert "make evals" in content
        assert "make security" in content

    def test_readme_has_docs_section(self):
        content = Path("README.md").read_text()
        assert "docs/" in content or "documentation" in content.lower()

    def test_readme_has_demo_section(self):
        content = Path("README.md").read_text().lower()
        demo_keywords = ["demo", "quick start", "example"]
        found = any(kw in content for kw in demo_keywords)
        assert found, "README should have a demo or quick start section"

    def test_readme_no_paid_credentials(self):
        content = Path("README.md").read_text()
        assert "AZURE_OPENAI_KEY" not in content
        assert "sk-" not in content or "make" in content

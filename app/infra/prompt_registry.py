"""Prompt registry for version-controlled chat prompts."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from pydantic import BaseModel

from app.core.config import AppSettings
from app.domain.errors import ConfigError


class PromptBundle(BaseModel):
    """Loaded prompt texts plus a stable version fingerprint."""

    system_prompt: str
    tool_policy_prompt: str
    untrusted_context_prompt: str
    version: str


class PromptRegistry:
    """Load and validate prompt files from disk."""

    def __init__(
        self, system_path: Path, tool_policy_path: Path, untrusted_context_path: Path
    ) -> None:
        self._system_path = system_path
        self._tool_policy_path = tool_policy_path
        self._untrusted_context_path = untrusted_context_path
        self._bundle: PromptBundle | None = None

    @classmethod
    def from_settings(cls, settings: AppSettings) -> "PromptRegistry":
        """Construct the registry from typed settings."""
        return cls(
            system_path=Path(settings.chat_prompt_system_path),
            tool_policy_path=Path(settings.chat_prompt_tool_policy_path),
            untrusted_context_path=Path(settings.chat_prompt_untrusted_context_path),
        )

    def load(self) -> PromptBundle:
        """Load all required prompt files and validate they are non-empty."""
        system_prompt = self._read_prompt(self._system_path)
        tool_policy_prompt = self._read_prompt(self._tool_policy_path)
        untrusted_context_prompt = self._read_prompt(self._untrusted_context_path)
        version = sha256(
            "\n".join([system_prompt, tool_policy_prompt, untrusted_context_prompt]).encode()
        ).hexdigest()[:12]
        self._bundle = PromptBundle(
            system_prompt=system_prompt,
            tool_policy_prompt=tool_policy_prompt,
            untrusted_context_prompt=untrusted_context_prompt,
            version=version,
        )
        return self._bundle

    def get_bundle(self) -> PromptBundle:
        """Return the prompt bundle, loading on first access."""
        if self._bundle is None:
            return self.load()
        return self._bundle

    @staticmethod
    def _read_prompt(path: Path) -> str:
        if not path.exists():
            raise ConfigError(f"Missing prompt file: {path}")
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            raise ConfigError(f"Prompt file is empty: {path}")
        return content

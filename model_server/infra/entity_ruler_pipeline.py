"""spaCy EntityRuler pipeline factory and pattern definitions."""

from __future__ import annotations

import logging

import spacy
from spacy.pipeline import EntityRuler

from model_server.domain.issue_analysis import SUPPORTED_ENTITY_TYPES, EntityType

logger = logging.getLogger(__name__)

_FILE_EXT_TOKEN_RE = (
    r"^[a-zA-Z0-9_\-\.]+\."
    r"(?:py|js|ts|jsx|tsx|java|rb|go|rs|c|h|cpp|hpp|sh|yaml|yml|json|toml|ini|cfg|md|txt)$"
)

_FUNC_NAME_TOKEN_RE = r"^[a-z_][a-zA-Z0-9_]*$"

_CLASS_NAME_TOKEN_RE = r"^[A-Z][a-zA-Z]+$"

_ENTITY_RULER_PATTERNS: list[dict] = [
    {
        "label": "stack_trace_marker",
        "pattern": [
            {"TEXT": "File"},
            {"TEXT": '"'},
        ],
    },
    {
        "label": "url",
        "pattern": [
            {"TEXT": {"REGEX": r"^https?://[^\s\)\]\"\<\>]+$"}},
        ],
    },
    {
        "label": "file_path",
        "pattern": [
            {"TEXT": {"REGEX": r"^[a-zA-Z0-9_\-\.]+$"}},
            {"TEXT": "/"},
            {"TEXT": {"REGEX": r"^[a-zA-Z0-9_\-\.]+$"}},
            {"TEXT": "/", "OP": "?"},
            {"TEXT": {"REGEX": r"^[a-zA-Z0-9_\-\.]+$"}, "OP": "?"},
        ],
    },
    {
        "label": "file_path",
        "pattern": [{"TEXT": {"REGEX": _FILE_EXT_TOKEN_RE}}],
    },
    {
        "label": "error_code",
        "pattern": [
            {"TEXT": {"REGEX": r"^(?:ERR|ERROR|E|WARN)_[A-Za-z0-9_\-]{1,30}$"}},
        ],
    },
    {
        "label": "version_number",
        "pattern": [{"TEXT": {"REGEX": r"^\d+\.\d+(?:\.\d+)?(?:[a-z]+\d*)?$"}}],
    },
    {
        "label": "function_name",
        "pattern": [
            {"TEXT": {"REGEX": _FUNC_NAME_TOKEN_RE}},
            {"TEXT": "("},
        ],
    },
    {
        "label": "function_name",
        "pattern": [
            {"TEXT": {"REGEX": r"^[a-z_][a-zA-Z0-9_]*\(.*$"}},
        ],
    },
    {
        "label": "class_name",
        "pattern": [{"TEXT": {"REGEX": _CLASS_NAME_TOKEN_RE}}],
    },
    {
        "label": "class_name",
        "pattern": [
            {"TEXT": {"REGEX": r"^[A-Z][a-z]+(?:[A-Z][a-z]+)+$"}},
        ],
    },
    {
        "label": "package_name",
        "pattern": [
            {"TEXT": {"REGEX": r"^[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*$"}},
        ],
    },
    {
        "label": "environment_name",
        "pattern": [
            {"LOWER": {"IN": ["dev", "staging", "production", "prod", "test", "ci", "local"]}},
        ],
    },
    {
        "label": "command_snippet",
        "pattern": [
            {
                "LOWER": {
                    "IN": [
                        "pip",
                        "pip3",
                        "npm",
                        "yarn",
                        "docker",
                        "git",
                        "curl",
                        "wget",
                        "node",
                        "java",
                        "go",
                        "cargo",
                        "pytest",
                        "make",
                        "gcc",
                        "g++",
                        "mvn",
                        "gradle",
                        "cmake",
                        "ssh",
                        "scp",
                        "rsync",
                    ]
                }
            },
            {"OP": "{0,4}"},
        ],
    },
]


class EntityExtractionResult:
    __slots__ = ("text", "type", "start", "end")

    def __init__(self, text: str, entity_type: EntityType, start: int, end: int) -> None:
        self.text = text
        self.type: EntityType = entity_type
        self.start = start
        self.end = end


class EntityRulerPipeline:
    """spaCy EntityRuler pipeline for deterministic code-shaped entity extraction.

    Uses spaCy's built-in EntityRuler component with custom token-level
    patterns added to a blank English pipeline. Entity spans and types are
    produced by running the pipeline via ``nlp(text)`` and reading from
    ``doc.ents``. Pattern priority follows EntityRuler pattern ordering:
    earlier patterns take precedence for overlapping spans, and longer
    entities win when multiple patterns match the same start position.
    """

    def __init__(self) -> None:
        self._nlp: spacy.Language | None = None
        self._configured: bool = False
        self._pipeline_name: str = "entity_ruler_ner"
        self._supported_entity_types: list[str] = list(SUPPORTED_ENTITY_TYPES)

    @property
    def configured(self) -> bool:
        return self._configured

    @property
    def pipeline_name(self) -> str:
        return self._pipeline_name

    @property
    def supported_entity_types(self) -> list[str]:
        return list(self._supported_entity_types)

    def initialize(self) -> None:
        self._nlp = spacy.blank("en")
        ruler = self._nlp.add_pipe("entity_ruler", name="entity_ruler", last=True)
        if isinstance(ruler, EntityRuler):
            ruler.add_patterns(_ENTITY_RULER_PATTERNS)
        self._configured = True
        logger.info(
            "EntityRuler pipeline initialized: patterns=%d types=%d",
            len(_ENTITY_RULER_PATTERNS),
            len(self._supported_entity_types),
        )

    def extract_entities(self, text: str) -> list[EntityExtractionResult]:
        if not self._configured or self._nlp is None:
            raise RuntimeError("EntityRuler pipeline is not initialized")
        doc = self._nlp(text)
        results: list[EntityExtractionResult] = []
        for ent in doc.ents:
            entity_text = ent.text
            entity_label = ent.label_
            if entity_label == "function_name":
                paren_idx = entity_text.find("(")
                if paren_idx != -1:
                    entity_text = entity_text[:paren_idx]
            results.append(
                EntityExtractionResult(
                    text=entity_text,
                    entity_type=entity_label,
                    start=ent.start_char,
                    end=ent.end_char,
                )
            )
        return results

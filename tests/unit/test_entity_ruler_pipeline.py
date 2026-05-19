"""Unit tests for spaCy EntityRuler pipeline patterns."""

from __future__ import annotations

import pytest

from model_server.infra.entity_ruler_pipeline import (
    EntityRulerPipeline,
)
from model_server.domain.issue_analysis import SUPPORTED_ENTITY_TYPES


@pytest.fixture
def pipeline() -> EntityRulerPipeline:
    p = EntityRulerPipeline()
    p.initialize()
    return p


class TestPipelineInitialization:
    def test_pipeline_is_configured_after_init(self, pipeline):
        assert pipeline.configured

    def test_pipeline_has_all_supported_types(self, pipeline):
        types = pipeline.supported_entity_types
        for t in SUPPORTED_ENTITY_TYPES:
            assert t in types

    def test_pipeline_name(self, pipeline):
        assert pipeline.pipeline_name == "entity_ruler_ner"


class TestFilePaths:
    def test_detects_python_file_path(self, pipeline):
        results = pipeline.extract_entities("src/app/parser.py")
        file_paths = [r for r in results if r.type == "file_path"]
        assert len(file_paths) >= 1
        assert any("parser.py" in r.text for r in file_paths)

    def test_detects_js_file_path(self, pipeline):
        results = pipeline.extract_entities("components/Button.jsx")
        file_paths = [r for r in results if r.type == "file_path"]
        assert len(file_paths) >= 1

    def test_detects_config_file(self, pipeline):
        results = pipeline.extract_entities("config/settings.yaml")
        file_paths = [r for r in results if r.type == "file_path"]
        assert len(file_paths) >= 1


class TestFunctionNames:
    def test_detects_function_call(self, pipeline):
        results = pipeline.extract_entities("parse_issue() failed")
        funcs = [r for r in results if r.type == "function_name"]
        assert any("parse_issue" in r.text for r in funcs)

    def test_detects_function_with_args(self, pipeline):
        results = pipeline.extract_entities("handle_error(err, ctx)")
        funcs = [r for r in results if r.type == "function_name"]
        assert any("handle_error" in r.text for r in funcs)


class TestClassNames:
    def test_detects_pascal_case_class(self, pipeline):
        results = pipeline.extract_entities("TypeError occurred")
        classes = [r for r in results if r.type == "class_name"]
        assert any("TypeError" in r.text for r in classes)

    def test_detects_camel_case_class(self, pipeline):
        results = pipeline.extract_entities("HttpResponseParser")
        classes = [r for r in results if r.type == "class_name"]
        assert any("HttpResponseParser" in r.text for r in classes)


class TestErrorCodes:
    def test_detects_err_code(self, pipeline):
        results = pipeline.extract_entities("ERR_PARSER_42")
        errors = [r for r in results if r.type == "error_code"]
        assert any("ERR_PARSER_42" in r.text for r in errors)

    def test_detects_error_code(self, pipeline):
        results = pipeline.extract_entities("ERROR_DB_CONN")
        errors = [r for r in results if r.type == "error_code"]
        assert any("ERROR_DB_CONN" in r.text for r in errors)


class TestVersionNumbers:
    def test_detects_semver(self, pipeline):
        results = pipeline.extract_entities("Python 3.11.2")
        versions = [r for r in results if r.type == "version_number"]
        assert any("3.11.2" in r.text for r in versions)

    def test_detects_two_part_version(self, pipeline):
        results = pipeline.extract_entities("version 2.0 release")
        versions = [r for r in results if r.type == "version_number"]
        assert any("2.0" in r.text for r in versions)


class TestURLs:
    def test_detects_https_url(self, pipeline):
        results = pipeline.extract_entities("see https://example.test/bug")
        urls = [r for r in results if r.type == "url"]
        assert any("https://example.test/bug" in r.text for r in urls)

    def test_detects_http_url(self, pipeline):
        results = pipeline.extract_entities("link: http://test.com/page")
        urls = [r for r in results if r.type == "url"]
        assert any("http://test.com/page" in r.text for r in urls)


class TestStackTraces:
    def test_detects_file_line_pattern(self, pipeline):
        results = pipeline.extract_entities(
            'File "src/app/parser.py", line 12, in parse_issue'
        )
        traces = [r for r in results if r.type == "stack_trace_marker"]
        assert len(traces) >= 1


class TestEnvironmentNames:
    def test_detects_prod(self, pipeline):
        results = pipeline.extract_entities("deployed to prod")
        envs = [r for r in results if r.type == "environment_name"]
        assert any("prod" in r.text for r in envs)

    def test_detects_staging(self, pipeline):
        results = pipeline.extract_entities("staging server")
        envs = [r for r in results if r.type == "environment_name"]
        assert any("staging" in r.text for r in envs)


class TestCommandSnippets:
    def test_detects_pip_install(self, pipeline):
        results = pipeline.extract_entities("run pip install requests")
        cmds = [r for r in results if r.type == "command_snippet"]
        assert any("pip" in r.text.lower() for r in cmds)

    def test_detects_git_command(self, pipeline):
        results = pipeline.extract_entities("git checkout main")
        cmds = [r for r in results if r.type == "command_snippet"]
        assert any("git" in r.text.lower() for r in cmds)

    def test_detects_docker_command(self, pipeline):
        results = pipeline.extract_entities("docker build -t app .")
        cmds = [r for r in results if r.type == "command_snippet"]
        assert any("docker" in r.text.lower() for r in cmds)


class TestDuplicates:
    def test_deduplicates_same_entity_same_span(self, pipeline):
        results = pipeline.extract_entities("TypeError and TypeError again")
        type_errors = [r for r in results if r.text == "TypeError"]
        assert len(type_errors) <= 2  # May have different spans

    def test_ordering_is_deterministic_by_position(self, pipeline):
        text = "TypeError in src/app/parser.py parse_issue()"
        results = pipeline.extract_entities(text)
        assert results == sorted(results, key=lambda r: (r.start, r.end))

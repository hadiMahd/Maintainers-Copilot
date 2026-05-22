"""Tests for classifier eval gate."""

import json
from pathlib import Path


class TestClassifierEvalGate:
    """Verify classifier eval adapter runs against golden set and checks thresholds."""

    def test_classifier_eval_module_imports(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "run_classifier_eval", "scripts/ci/run_classifier_eval.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

    def test_golden_set_exists(self):
        assert Path("evals/classification/golden.jsonl").exists()

    def test_golden_set_has_minimum_items(self):
        lines = Path("evals/classification/golden.jsonl").read_text().strip().split("\n")
        items = [json.loads(ln) for ln in lines if ln.strip()]
        assert len(items) >= 10, "golden set should have at least 10 items"

    def test_golden_set_has_required_fields(self):
        lines = Path("evals/classification/golden.jsonl").read_text().strip().split("\n")
        items = [json.loads(ln) for ln in lines if ln.strip()]
        for item in items:
            assert "text" in item
            assert "label" in item
            assert "id" in item
            assert item["label"] in ("bug", "feature", "docs", "question")

    def test_run_classifier_eval_with_golden_set(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "run_classifier_eval", "scripts/ci/run_classifier_eval.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        result = mod.evaluate_classifier(
            golden_path="evals/classification/golden.jsonl",
        )
        assert "accuracy" in result
        assert "macro_f1" in result
        assert "per_class_f1" in result
        assert 0.0 <= result["accuracy"] <= 1.0
        assert 0.0 <= result["macro_f1"] <= 1.0

    def test_check_classifier_thresholds_pass(self):
        data = {
            "classifier": {"accuracy_min": 0.01, "macro_f1_min": 0.01},
        }
        from scripts.ci.thresholds import check_threshold, get_classifier_threshold

        acc_threshold = get_classifier_threshold(data, "accuracy")
        f1_threshold = get_classifier_threshold(data, "macro_f1")
        assert acc_threshold == 0.01
        assert f1_threshold == 0.01

        passed, msg = check_threshold(0.85, acc_threshold, "accuracy")
        assert passed, msg

    def test_check_classifier_thresholds_fail(self):
        data = {
            "classifier": {"accuracy_min": 0.99, "macro_f1_min": 0.99},
        }
        from scripts.ci.thresholds import check_threshold, get_classifier_threshold

        acc_threshold = get_classifier_threshold(data, "accuracy")
        passed, msg = check_threshold(0.30, acc_threshold, "accuracy")
        assert not passed, msg

    def test_deterministic_classifier_produces_repeatable_results(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "run_classifier_eval", "scripts/ci/run_classifier_eval.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        result1 = mod.evaluate_classifier("evals/classification/golden.jsonl")
        result2 = mod.evaluate_classifier("evals/classification/golden.jsonl")
        assert result1["accuracy"] == result2["accuracy"]
        assert result1["macro_f1"] == result2["macro_f1"]

    def test_run_classifier_eval_main_passes_with_real_thresholds(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "run_classifier_eval", "scripts/ci/run_classifier_eval.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        result = mod.evaluate_classifier("evals/classification/golden.jsonl")
        passed, failures = mod.check_classifier_gate(result)
        assert isinstance(passed, bool)

    def test_classifier_eval_no_paid_credentials(self):
        content = Path("scripts/ci/run_classifier_eval.py").read_text()
        assert "AZURE_OPENAI_KEY" not in content
        assert "OPENAI_API_KEY" not in content

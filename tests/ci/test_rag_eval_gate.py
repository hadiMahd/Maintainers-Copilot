"""Tests for RAG eval gate."""

import json
from pathlib import Path


class TestRAGEvalGate:
    """Verify RAG eval adapter runs against golden set and checks thresholds."""

    def test_rag_eval_module_imports(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("run_rag_eval", "scripts/ci/run_rag_eval.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

    def test_rag_golden_set_exists(self):
        assert Path("evals/rag/golden.jsonl").exists()

    def test_rag_golden_set_has_minimum_items(self):
        lines = Path("evals/rag/golden.jsonl").read_text().strip().split("\n")
        items = [json.loads(ln) for ln in lines if ln.strip()]
        assert len(items) >= 5, "RAG golden set should have at least 5 items"

    def test_rag_golden_set_has_required_fields(self):
        lines = Path("evals/rag/golden.jsonl").read_text().strip().split("\n")
        items = [json.loads(ln) for ln in lines if ln.strip()]
        for item in items:
            assert "question" in item
            assert "answer" in item
            assert "expected_chunks" in item

    def test_run_rag_eval_with_golden_set(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("run_rag_eval", "scripts/ci/run_rag_eval.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        result = mod.evaluate_rag("evals/rag/golden.jsonl")
        assert "hit_at_5" in result
        assert "mrr_at_10" in result
        assert "faithfulness" in result
        assert "answer_relevancy" in result
        assert 0.0 <= result["hit_at_5"] <= 1.0
        assert 0.0 <= result["mrr_at_10"] <= 1.0
        assert "ragas" not in result

    def test_ragas_real_eval_flag_is_documented_in_runner(self):
        content = Path("scripts/ci/run_rag_eval.py").read_text()
        assert "USE_RAGAS_EVALS" in content
        assert "resolve_ragas_judge" in content

    def test_check_rag_thresholds_pass(self):
        data = {
            "rag": {
                "hit_at_5_min": 0.01,
                "mrr_at_10_min": 0.01,
                "faithfulness_min": 0.01,
                "answer_relevancy_min": 0.01,
            },
        }
        from scripts.ci.thresholds import check_threshold, get_rag_threshold

        h5 = get_rag_threshold(data, "hit_at_5")
        assert h5 == 0.01
        passed, msg = check_threshold(0.5, h5, "hit_at_5")
        assert passed, msg

    def test_check_rag_thresholds_fail(self):
        data = {
            "rag": {
                "hit_at_5_min": 0.99,
                "mrr_at_10_min": 0.99,
                "faithfulness_min": 0.01,
                "answer_relevancy_min": 0.01,
            },
        }
        from scripts.ci.thresholds import check_threshold, get_rag_threshold

        h5 = get_rag_threshold(data, "hit_at_5")
        passed, msg = check_threshold(0.01, h5, "hit_at_5")
        assert not passed, msg

    def test_rag_eval_uses_fake_providers(self):
        content = Path("scripts/ci/run_rag_eval.py").read_text()
        assert (
            "FakeGenerationClient" in content or "Fake" in content or "fixture" in content.lower()
        )

    def test_rag_eval_no_paid_credentials(self):
        content = Path("scripts/ci/run_rag_eval.py").read_text()
        assert "AZURE_OPENAI_KEY" not in content
        assert "OPENAI_API_KEY" not in content

    def test_run_rag_eval_main_passes(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("run_rag_eval", "scripts/ci/run_rag_eval.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        result = mod.evaluate_rag("evals/rag/golden.jsonl")
        passed, failures = mod.check_rag_gate(result)
        assert isinstance(passed, bool)

    def test_rag_gate_keeps_manual_metrics_as_gate_when_ragas_present(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("run_rag_eval", "scripts/ci/run_rag_eval.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        passed, failures = mod.check_rag_gate(
            {
                "hit_at_5": 1.0,
                "mrr_at_10": 1.0,
                "faithfulness": 1.0,
                "answer_relevancy": 1.0,
                "ragas": {
                    "enabled": True,
                    "context_precision": None,
                    "context_recall": None,
                    "context_entity_recall": None,
                    "noise_sensitivity": None,
                    "faithfulness": None,
                    "response_relevancy": None,
                    "failures": ["judge unavailable"],
                },
            }
        )
        assert passed, failures

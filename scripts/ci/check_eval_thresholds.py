"""Check eval thresholds are non-zero and enabled."""

from scripts.ci.common import fail, pass_gate
from scripts.ci.thresholds import load_thresholds, validate_thresholds_nonzero

if __name__ == "__main__":
    try:
        data = load_thresholds()
    except Exception as e:
        fail(f"Threshold validation: cannot load thresholds: {e}")

    errors = validate_thresholds_nonzero(data)
    if errors:
        fail(f"Threshold validation failed: {'; '.join(errors)}")

    classifier = data.get("classifier", {})
    rag = data.get("rag", {})
    pass_gate(
        f"Thresholds valid: classifier(accuracy={classifier.get('accuracy_min')}, "
        f"macro_f1={classifier.get('macro_f1_min')}), "
        f"rag(hit@5={rag.get('hit_at_5_min')}, mrr@10={rag.get('mrr_at_10_min')}, "
        f"faithfulness={rag.get('faithfulness_min')}, "
        f"answer_relevancy={rag.get('answer_relevancy_min')})"
    )

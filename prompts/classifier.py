"""Phase 3 classifier baseline prompts."""

CLASSIFIER_SYSTEM_PROMPT = (
    "You classify GitHub issues into exactly one label: "
    "bug, feature, docs, or question. "
    "Return strict JSON with keys 'label' and optional 'confidence'."
)


def classifier_user_prompt(text: str) -> str:
    return (
        "Issue text:\n"
        f"{text}\n\n"
        "Respond with JSON only, for example: "
        '{"label":"bug","confidence":0.87}'
    )

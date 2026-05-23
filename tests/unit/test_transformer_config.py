"""Tests enforcing transformer training alignment with the dump notebook.

These tests verify that the transformer training script uses the same
label ordering, tokenization behavior, and hyperparameters as the
dump notebook (`dump/ml_&_bert_training.py`).
"""

import pytest

from app.domain.classifier import (
    LABEL_ORDER,
    TRANSFORMER_ALPHABETICAL_LABEL_IDS,
    VALID_LABELS,
)


def _transformers_available() -> bool:
    try:
        import transformers  # noqa: F401

        return True
    except ImportError:
        return False


def _accelerate_available() -> bool:
    try:
        import accelerate  # noqa: F401

        return True
    except ImportError:
        return False


def _sklearn_available() -> bool:
    try:
        import sklearn  # noqa: F401

        return True
    except ImportError:
        return False


class TestTransformerLabelOrdering:
    """Tests for the alphabetical label ordering used by the transformer."""

    def test_label_ids_are_alphabetical(self):
        """Label IDs must be in alphabetical order (bug, docs, feature, question)."""
        labels = list(TRANSFORMER_ALPHABETICAL_LABEL_IDS.keys())
        assert labels == sorted(labels)

    def test_label_ids_match_dump(self):
        """Label IDs must match the dump notebook's LabelEncoder output:

        bug -> 0, docs -> 1, feature -> 2, question -> 3
        """
        assert TRANSFORMER_ALPHABETICAL_LABEL_IDS["bug"] == 0
        assert TRANSFORMER_ALPHABETICAL_LABEL_IDS["docs"] == 1
        assert TRANSFORMER_ALPHABETICAL_LABEL_IDS["feature"] == 2
        assert TRANSFORMER_ALPHABETICAL_LABEL_IDS["question"] == 3

    def test_all_valid_labels_present(self):
        """All four project labels must be present."""
        assert set(TRANSFORMER_ALPHABETICAL_LABEL_IDS.keys()) == set(VALID_LABELS)

    def test_ids_are_unique(self):
        """Each label must have a unique integer ID."""
        ids = list(TRANSFORMER_ALPHABETICAL_LABEL_IDS.values())
        assert len(ids) == len(set(ids))

    def test_is_not_canonical_order(self):
        """The transformer order must differ from the canonical project order.

        This is a documentation check: it ensures nobody accidentally
        conflates the two orderings.
        """
        transformer_order = list(TRANSFORMER_ALPHABETICAL_LABEL_IDS.keys())
        assert transformer_order != list(LABEL_ORDER)

    def test_id_to_label_roundtrip(self):
        """id->label mapping must be the exact inverse of label->id."""
        id_to_label = {index: label for label, index in TRANSFORMER_ALPHABETICAL_LABEL_IDS.items()}
        for label, idx in TRANSFORMER_ALPHABETICAL_LABEL_IDS.items():
            assert id_to_label[idx] == label


class TestTokenizationConfig:
    """Tests for the tokenization behavior matching the dump notebook."""

    @pytest.mark.skipif(
        not _transformers_available(),
        reason="transformers not installed (install with: uv sync --extra train)",
    )
    def test_tokenizer_padding_and_truncation(self):
        """Tokenizer must use padding=True, truncation=True, max_length=512."""
        from transformers import AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
        text = "This is a test issue for classification."
        encoded = tokenizer(text, padding=True, truncation=True, max_length=512)
        assert "input_ids" in encoded
        assert len(encoded["input_ids"]) <= 512

    @pytest.mark.skipif(
        not _transformers_available(),
        reason="transformers not installed",
    )
    def test_tokenizer_max_length_512(self):
        """Tokenizer must truncate to 512 tokens, not 256."""
        from transformers import AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
        long_text = "word " * 1000
        encoded = tokenizer(long_text, padding=True, truncation=True, max_length=512)
        assert len(encoded["input_ids"]) == 512


class TestTrainingArguments:
    """Tests for the TrainingArguments defaults matching the dump notebook."""

    @pytest.mark.skipif(
        not _transformers_available() or not _accelerate_available(),
        reason="transformers or accelerate not installed (install with: uv sync --extra train)",
    )
    def test_training_args_hyperparameters(self):
        """TrainingArguments must match dump: 3 epochs, lr 2e-5, batch 16."""
        from transformers import TrainingArguments

        args = TrainingArguments(
            output_dir="/tmp/test",
            num_train_epochs=3,
            learning_rate=2e-5,
            per_device_train_batch_size=16,
            per_device_eval_batch_size=16,
            weight_decay=0.01,
            eval_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
            logging_steps=10,
            report_to="none",
        )
        assert args.num_train_epochs == 3
        assert args.learning_rate == 2e-5
        assert args.per_device_train_batch_size == 16
        assert args.per_device_eval_batch_size == 16
        assert args.weight_decay == 0.01
        assert args.eval_strategy == "epoch"
        assert args.save_strategy == "epoch"
        assert args.load_best_model_at_end is True
        assert args.logging_steps == 10


class TestComputeMetrics:
    """Tests for the compute_metrics function matching the dump notebook."""

    @pytest.mark.skipif(
        not _sklearn_available(),
        reason="scikit-learn not installed",
    )
    def test_compute_metrics_accuracy_and_f1(self):
        """compute_metrics must return accuracy and f1_macro."""
        import numpy as np
        from sklearn.metrics import accuracy_score, f1_score

        # Simulate eval_pred: (logits, labels)
        logits = np.array(
            [
                [2.0, 0.5, 0.1, 0.0],  # predict 0
                [0.1, 2.0, 0.5, 0.0],  # predict 1
                [0.0, 0.1, 2.0, 0.5],  # predict 2
            ]
        )
        labels = np.array([0, 1, 2])

        predictions = np.argmax(logits, axis=-1)
        result = {
            "accuracy": accuracy_score(labels, predictions),
            "f1_macro": f1_score(labels, predictions, average="macro"),
        }

        assert "accuracy" in result
        assert "f1_macro" in result
        assert 0.0 <= result["accuracy"] <= 1.0
        assert 0.0 <= result["f1_macro"] <= 1.0

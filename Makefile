.PHONY: validate lint format-check import-check type-check test evals security smoke docs

validate: lint format-check import-check type-check test
	@echo "=== Full validation: lint, format, imports, type-check, tests ==="
	@echo "Gate: validate PASSED"

lint:
	scripts/ci/run_lint.sh

format-check:
	scripts/ci/run_format_check.sh

import-check:
	@uv run isort --check-only .

type-check:
	scripts/ci/run_type_check.sh

test:
	scripts/ci/run_tests.sh

evals:
	@echo "=== Eval gates: thresholds, classifier, RAG, report, storage, diff ==="
	@uv run python scripts/ci/check_eval_thresholds.py
	@scripts/ci/run_evals.sh
	@echo "Gate: evals PASSED"

security:
	@echo "=== Security gates: redaction, static grep, model artifacts, startup, tracing ==="
	@uv run python scripts/ci/check_redaction_leaks.py
	@uv run python scripts/ci/check_static_secret_patterns.py
	@uv run python scripts/ci/check_model_artifacts.py
	@uv run python scripts/ci/check_startup_failures.py
	@uv run python scripts/ci/validate_tracing.py
	@echo "Gate: security PASSED"

smoke:
	scripts/ci/smoke_stack.sh

docs:
	@echo "=== Documentation completeness ==="
	@uv run python scripts/ci/validate_docs.py
	@echo "Gate: docs PASSED"

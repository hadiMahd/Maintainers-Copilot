FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
ARG UV_SYNC_EXTRAS="--extra llm"
RUN pip install uv && uv sync --no-dev --frozen $UV_SYNC_EXTRAS

COPY model_server/ ./model_server/
COPY app/ ./app/
COPY config/ ./config/
COPY prompts/ ./prompts/

RUN mkdir -p artifacts/classifiers/classical/pandas_logreg && \
    uv run python -c "import json, joblib; from pathlib import Path; from sklearn.dummy import DummyClassifier; p=Path('artifacts/classifiers/classical/pandas_logreg'); model=DummyClassifier(strategy='constant', constant='question'); model.fit(['placeholder'], ['question']); joblib.dump({'model': model, 'labels': ['bug', 'feature', 'docs', 'question']}, p / 'model.joblib'); (p / 'config.json').write_text(json.dumps({'version': 'ci-smoke-classifier'}))"

ENV CLASSIFIER_ARTIFACT_DIR=artifacts/classifiers/classical

CMD ["uv", "run", "uvicorn", "model_server.main:app", "--host", "0.0.0.0", "--port", "8001"]

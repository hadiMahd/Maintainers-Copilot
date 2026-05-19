FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --no-dev --frozen

COPY model_server/ ./model_server/
COPY app/ ./app/
COPY config/ ./config/

ENV CLASSIFIER_ARTIFACT_DIR=artifacts/classifiers/classical

CMD ["uv", "run", "uvicorn", "model_server.main:app", "--host", "0.0.0.0", "--port", "8001"]
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
ARG UV_SYNC_EXTRAS="--extra llm"
RUN pip install uv && uv sync --no-dev --frozen $UV_SYNC_EXTRAS

COPY model_server/ ./model_server/
COPY app/ ./app/
COPY config/ ./config/
COPY artifacts/ ./artifacts/
COPY prompts/ ./prompts/

ENV CLASSIFIER_ARTIFACT_DIR=artifacts/classifiers/classical

CMD ["uv", "run", "uvicorn", "model_server.main:app", "--host", "0.0.0.0", "--port", "8001"]

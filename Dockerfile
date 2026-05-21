FROM python:3.11-slim

WORKDIR /app

RUN pip install uv

ENV PATH="/app/.venv/bin:$PATH"
ARG UV_SYNC_EXTRAS="--extra llm"

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev $UV_SYNC_EXTRAS --no-install-project

COPY . .
RUN uv sync --frozen --no-dev $UV_SYNC_EXTRAS

EXPOSE 8000

CMD ["uvicorn", "app.core.application:app", "--host", "0.0.0.0", "--port", "8000"]

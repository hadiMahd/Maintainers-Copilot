FROM node:20-alpine AS widget-build

WORKDIR /widget

COPY widget/package.json widget/package-lock.json ./
RUN npm ci

COPY widget/ ./
RUN npm run build

FROM python:3.11-slim

WORKDIR /app

RUN pip install uv

ENV PATH="/app/.venv/bin:$PATH"
ARG UV_SYNC_EXTRAS="--extra llm --extra rag"

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev $UV_SYNC_EXTRAS --no-install-project

COPY . .
COPY --from=widget-build /widget/dist ./widget/dist
RUN uv sync --frozen --no-dev $UV_SYNC_EXTRAS

EXPOSE 8000

CMD ["uvicorn", "app.core.application:app", "--host", "0.0.0.0", "--port", "8000"]

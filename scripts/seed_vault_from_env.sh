#!/bin/sh
# Seed Vault from .env using curl to avoid exposing secrets via CLI args.
# Secrets travel only in HTTP request bodies, never in process listings.
set -eu

ENV_FILE="${1:-.env}"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: env file not found: $ENV_FILE" >&2
  exit 1
fi

# Allow caller overrides for container environments (e.g. docker-compose)
VAULT_ADDR_OVERRIDE="${VAULT_ADDR:-}"
VAULT_TOKEN_OVERRIDE="${VAULT_TOKEN:-}"

set -a
. "$ENV_FILE"
set +a

if [ -n "$VAULT_ADDR_OVERRIDE" ]; then
  VAULT_ADDR="$VAULT_ADDR_OVERRIDE"
fi

if [ -n "$VAULT_TOKEN_OVERRIDE" ]; then
  VAULT_TOKEN="$VAULT_TOKEN_OVERRIDE"
fi

export VAULT_ADDR VAULT_TOKEN

required_vars="
  VAULT_ADDR
  VAULT_TOKEN
  APP_DATABASE_URL
  APP_REDIS_URL
  APP_MINIO_ENDPOINT
  APP_MINIO_ACCESS_KEY
  APP_MINIO_SECRET_KEY
  JWT_SIGNING_KEY
  AZURE_OPENAI_KEY
  AZURE_OPENAI_ENDPOINT
  AZURE_OPENAI_MODEL
  AZURE_EMBEDDING_MODEL
  LANGSMITH_TRACING
  LANGSMITH_ENDPOINT
  LANGSMITH_API_KEY
  LANGSMITH_PROJECT
"

for var_name in $required_vars; do
  eval "var_value=\${$var_name:-}"
  if [ -z "$var_value" ]; then
    echo "ERROR: required env var missing: $var_name" >&2
    exit 1
  fi
done

# Vault HTTP API helper — writes JSON via curl, never via CLI args
_vault_write() {
  _path="$1"
  _json="$2"
  curl -sf -X POST \
    -H "X-Vault-Token: $VAULT_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$_json" \
    "${VAULT_ADDR}/v1/secret/data/${_path}" >/dev/null
}

# Enable KV v2 engine
curl -sf -X POST \
  -H "X-Vault-Token: $VAULT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type":"kv-v2"}' \
  "${VAULT_ADDR}/v1/sys/mounts/secret" >/dev/null 2>&1 || true

# Build JSON payloads as shell variables (expanded safely inside _vault_write)
APP_JSON="{\"data\":{\"database_url\":\"$APP_DATABASE_URL\",\"redis_url\":\"$APP_REDIS_URL\",\"minio_endpoint\":\"$APP_MINIO_ENDPOINT\",\"minio_access_key\":\"$APP_MINIO_ACCESS_KEY\",\"minio_secret_key\":\"$APP_MINIO_SECRET_KEY\",\"jwt_signing_key\":\"$JWT_SIGNING_KEY\"}}"

AZURE_JSON="{\"data\":{\"endpoint\":\"$AZURE_OPENAI_ENDPOINT\",\"api_key\":\"$AZURE_OPENAI_KEY\",\"openai_model\":\"$AZURE_OPENAI_MODEL\",\"embedding_model\":\"$AZURE_EMBEDDING_MODEL\"}}"

LANGSMITH_PROJECT_CLEAN=$(echo "$LANGSMITH_PROJECT" | tr -d '"')
LANGSMITH_JSON="{\"data\":{\"tracing\":\"$LANGSMITH_TRACING\",\"endpoint\":\"$LANGSMITH_ENDPOINT\",\"api_key\":\"$LANGSMITH_API_KEY\",\"project\":\"$LANGSMITH_PROJECT_CLEAN\"}}"

_vault_write maintainer-copilot/app "$APP_JSON"
_vault_write maintainer-copilot/azure-openai "$AZURE_JSON"
_vault_write maintainer-copilot/langsmith "$LANGSMITH_JSON"

echo "Seeded Vault secrets from $ENV_FILE"

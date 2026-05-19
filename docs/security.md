# Security

## Secret Handling Policy

- No secrets committed to git.
- `.env.example` contains only fake values.
- All real secrets resolved from Vault AppRole at startup.

## Vault AppRole Policy

- Role must have read-only access to `secret/data/maintainer-copilot/app`.
- `role_id` and `secret_id` sourced from environment at container start, never hardcoded.

## Redaction Policy

Placeholder — will be activated in Phase 4+ when PII or sensitive data flows through the system. All AI inference logs must redact user content by default.

## `.gitignore` Rules

Secret-related entries:
- `.env`
- `.env.local`
- `data/raw/`
- `data/processed/`
- `artifacts/`

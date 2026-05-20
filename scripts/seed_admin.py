"""Bootstrap the first admin user.

Usage::

    uv run python scripts/seed_admin.py --email admin@example.com

The script creates one admin when no admin user exists.  It fails loudly
when the Vault signing key (RS256) is unavailable and is idempotent:
re-running reports that an admin already exists.  This path is isolated
from normal HTTP registration.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from app.core.config import AppSettings
from app.domain.errors import ConfigError
from app.infra.database import create_engine, create_session_factory
from app.infra.vault_client import init_vault_client, resolve_jwt_key


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap the first admin user")
    parser.add_argument(
        "--email",
        required=True,
        help="Admin email address",
    )
    parser.add_argument(
        "--password",
        help="Admin password (prompts if omitted)",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    settings = AppSettings()

    # Resolve signing key
    vault_client = init_vault_client(settings)
    try:
        resolve_jwt_key(vault_client, settings)
    except ConfigError:
        print("ERROR: Vault JWT signing key unavailable. Cannot bootstrap admin.", file=sys.stderr)
        sys.exit(1)

    if not settings.database_url:
        print("ERROR: database_url not configured.", file=sys.stderr)
        sys.exit(1)

    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    from app.repositories.user_repository import UserRepository

    async with session_factory() as session:
        repo = UserRepository(session)
        existing = await repo.get_by_role("admin", limit=1)
        if existing:
            print(f"Admin already exists: {existing[0].email}")
            return

        password = args.password
        if not password:
            import getpass
            password = getpass.getpass("Admin password: ")

        from app.infra.password_hasher import PasswordHasher

        hasher = PasswordHasher()
        hashed = hasher.hash(password)
        user = await repo.create(args.email, hashed, role="admin")
        await session.commit()
        print(f"Admin created: {user.email} (id={user.id})")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

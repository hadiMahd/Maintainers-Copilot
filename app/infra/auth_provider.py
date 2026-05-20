"""Authentication provider adapter.

Wires ``PasswordHasher``, ``TokenSigner``, and repositories for the
auth service.  This is a thin infra adapter — business workflows live in
``app/services/auth_service.py``.
"""


class AuthProvider:
    """Wiring adapter for auth dependencies.  No business logic."""

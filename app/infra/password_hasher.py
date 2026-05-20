"""Argon2id password hashing adapter.

Uses ``argon2-cffi`` for OWASP-recommended argon2id password hashing.
Plaintext passwords are never logged, stored, or returned.
"""

from argon2 import PasswordHasher as Argon2Hasher
from argon2.exceptions import VerificationError, VerifyMismatchError


class PasswordHasher:
    """Hash and verify passwords with argon2id."""

    def __init__(self) -> None:
        self._hasher = Argon2Hasher()

    def hash(self, password: str) -> str:
        """Hash a plaintext password.  Returns an argon2id hash string."""
        return self._hasher.hash(password)

    def verify(self, hash_str: str, password: str) -> bool:
        """Verify a plaintext password against an argon2id hash."""
        try:
            self._hasher.verify(hash_str, password)
            return True
        except VerifyMismatchError:
            return False
        except VerificationError:
            return False

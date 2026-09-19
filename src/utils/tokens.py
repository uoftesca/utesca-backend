"""Helpers for generating and hashing opaque bearer tokens."""

import hashlib
import secrets

TOKEN_BYTES = 32


def generate_token() -> str:
    """Return a URL-safe token with 256 bits of cryptographic randomness."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> str:
    """Return the SHA-256 hex digest stored in the database for a raw token."""
    if not token:
        raise ValueError("Token cannot be empty")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

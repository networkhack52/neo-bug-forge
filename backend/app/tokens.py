"""API token generation + hashing.

Tokens are 192 bits of randomness, so a fast SHA-256 (no salt) is the right
choice for at-rest hashing — unlike passwords, they don't need a slow KDF. We
store only the hash; the raw token is shown to the client once at issue/rotate
and never persisted, so a database leak can't be turned into account access.
"""
from __future__ import annotations

import hashlib
import secrets

PREFIX = "atl_"


def new_token() -> str:
    return PREFIX + secrets.token_urlsafe(24)


def hash_token(token: str) -> str:
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()

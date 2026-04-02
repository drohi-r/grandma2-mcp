"""Content hashing utilities."""

from __future__ import annotations

import hashlib


def sha256(text: str) -> str:
    """Return the hex SHA-256 digest of *text*."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

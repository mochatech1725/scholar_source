"""Stable hashing helpers for deduplication and run comparison."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def normalize_for_hash(value: str) -> str:
    """Collapse whitespace and case so equivalent text hashes identically."""
    return " ".join(value.split()).casefold()


def sha256_text(value: str) -> str:
    """Return the SHA-256 hex digest of normalized text."""
    return hashlib.sha256(normalize_for_hash(value).encode("utf-8")).hexdigest()


def sha256_json(value: dict[str, Any] | list[Any]) -> str:
    """Return a deterministic SHA-256 digest for JSON-compatible values."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def short_hash(value: str, *, length: int = 12) -> str:
    """Return a short stable hash for trace keys and log lines."""
    if length <= 0:
        raise ValueError("length must be greater than zero.")
    return sha256_text(value)[:length]

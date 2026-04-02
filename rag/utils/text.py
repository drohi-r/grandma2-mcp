"""Text processing utilities for the RAG pipeline."""

from __future__ import annotations

import re


def normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace into single spaces and strip."""
    return re.sub(r"\s+", " ", text).strip()

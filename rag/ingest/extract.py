"""Symbol extraction from source files."""

from __future__ import annotations

import ast
import logging
import re

logger = logging.getLogger(__name__)


def extract_symbols(language: str, text: str) -> list[str]:
    """Extract top-level symbol names from *text* based on its language.

    - Python: function and class names via AST
    - Markdown: heading text
    - Others: empty list
    """
    if language == "python":
        return _extract_python_symbols(text)
    if language == "markdown":
        return _extract_markdown_headings(text)
    return []


def _extract_python_symbols(text: str) -> list[str]:
    """Extract top-level function and class names using the AST."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        logger.debug("AST parse failed, returning empty symbols")
        return []

    symbols: list[str] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.append(node.name)
    return symbols


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)", re.MULTILINE)


def _extract_markdown_headings(text: str) -> list[str]:
    """Extract heading text from markdown."""
    return [m.group(2).strip() for m in _HEADING_RE.finditer(text)]

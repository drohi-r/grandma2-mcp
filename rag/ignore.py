"""Gitignore-aware file filtering for the RAG crawler."""

from __future__ import annotations

import fnmatch
from pathlib import Path

from rag.config import IGNORED_EXTENSIONS

# Directories that are always ignored (relative names)
_DEFAULT_DIR_IGNORES: frozenset[str] = frozenset({
    ".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "node_modules", ".venv", "venv", ".env", "dist", ".augment",
    ".vscode", ".idea",
})

# File patterns that are always ignored
_DEFAULT_FILE_PATTERNS: list[str] = [
    "*.pyc",
    "*.pyo",
    ".DS_Store",
    "Thumbs.db",
]


def load_gitignore_patterns(root: Path) -> list[str]:
    """Load patterns from the .gitignore file at *root*, if it exists."""
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        return []

    patterns: list[str] = []
    for line in gitignore.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        # Skip blanks and comments
        if not line or line.startswith("#"):
            continue
        patterns.append(line)
    return patterns


def _matches_any(name: str, patterns: list[str]) -> bool:
    """Check if *name* matches any fnmatch pattern."""
    return any(fnmatch.fnmatch(name, pat) for pat in patterns)


class IgnoreFilter:
    """Decides whether a path should be ignored during crawling."""

    def __init__(self, root: Path) -> None:
        self._gitignore_patterns = load_gitignore_patterns(root)

    def should_ignore(self, relative_path: str, *, is_dir: bool = False) -> bool:
        """Return True if *relative_path* should be skipped."""
        parts = Path(relative_path).parts
        name = parts[-1] if parts else ""

        # Directory-level checks
        for part in parts:
            if part in _DEFAULT_DIR_IGNORES:
                return True

        if is_dir:
            # Check gitignore patterns for directories
            return self._matches_gitignore(relative_path, is_dir=True)

        # Extension check
        suffix = Path(name).suffix.lower()
        if suffix in IGNORED_EXTENSIONS:
            return True

        # Default file patterns
        if _matches_any(name, _DEFAULT_FILE_PATTERNS):
            return True

        # Gitignore patterns
        return self._matches_gitignore(relative_path, is_dir=False)

    def _matches_gitignore(self, relative_path: str, *, is_dir: bool) -> bool:
        """Check against loaded .gitignore patterns."""
        name = Path(relative_path).name
        for pattern in self._gitignore_patterns:
            # Directory-only patterns (ending with /)
            if pattern.endswith("/"):
                dir_pat = pattern.rstrip("/")
                if is_dir and fnmatch.fnmatch(name, dir_pat):
                    return True
                # Also check if any path component matches
                for part in Path(relative_path).parts:
                    if fnmatch.fnmatch(part, dir_pat):
                        return True
                continue

            # General patterns — match against name and full relative path
            if fnmatch.fnmatch(name, pattern):
                return True
            if fnmatch.fnmatch(relative_path, pattern):
                return True

        return False

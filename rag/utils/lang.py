"""Language detection and file kind classification."""

from __future__ import annotations

from pathlib import PurePosixPath

from rag.types import RagKind

_EXTENSION_MAP: dict[str, str] = {
    ".py": "python",
    ".md": "markdown",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".toml": "toml",
    ".json": "json",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".html": "html",
    ".css": "css",
    ".sql": "sql",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".txt": "text",
    ".rst": "restructuredtext",
    ".ini": "ini",
    ".cfg": "ini",
    ".env": "dotenv",
}

_CONFIG_EXTENSIONS: frozenset[str] = frozenset({
    ".toml", ".yml", ".yaml", ".json", ".ini", ".cfg",
})

_CONFIG_FILENAMES: frozenset[str] = frozenset({
    ".gitignore", ".editorconfig", ".flake8", ".pylintrc",
    "Makefile", "Dockerfile", "docker-compose.yml",
})


def detect_language(path: str) -> str:
    """Map a file path to a language identifier based on its extension."""
    p = PurePosixPath(path)
    ext = p.suffix.lower()
    if ext in _EXTENSION_MAP:
        return _EXTENSION_MAP[ext]
    # dotenv variants (.env, .env.template, etc.)
    if p.name.startswith(".env"):
        return "dotenv"
    return "unknown"


def detect_kind(path: str, language: str) -> RagKind:
    """Classify a file as source, test, doc, or config."""
    p = PurePosixPath(path.replace("\\", "/"))
    parts = p.parts

    # Tests
    if "tests" in parts or "test" in parts or p.name.startswith("test_"):
        return "test"

    # Docs
    if language in ("markdown", "restructuredtext"):
        return "doc"
    if "doc" in parts or "docs" in parts:
        return "doc"

    # Config
    if language in ("toml", "yaml", "json", "ini", "dotenv"):
        return "config"
    if p.suffix.lower() in _CONFIG_EXTENSIONS:
        return "config"
    if p.name in _CONFIG_FILENAMES:
        return "config"

    return "source"

"""RAG pipeline configuration constants."""

from __future__ import annotations

from pathlib import Path

# Database
RAG_DB_PATH: Path = Path("rag/store/rag.db")

# Chunking
DEFAULT_CHUNK_MAX_TOKENS: int = 1200
DEFAULT_CHUNK_OVERLAP_LINES: int = 20
CHARS_PER_TOKEN: int = 4  # rough estimate

# Retrieval
DEFAULT_TOP_K: int = 12

# File size limit (skip files larger than this)
MAX_FILE_BYTES: int = 2 * 1024 * 1024  # 2 MB

# Binary / media extensions to always skip
IGNORED_EXTENSIONS: frozenset[str] = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg", ".webp",
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".flv",
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    ".exe", ".dll", ".so", ".dylib", ".bin",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".pyc", ".pyo", ".class", ".o",
    ".db", ".sqlite", ".sqlite3",
    ".lock",
})

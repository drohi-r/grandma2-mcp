"""Recursive file walker with gitignore-aware filtering."""

from __future__ import annotations

import logging
from pathlib import Path

from rag.config import MAX_FILE_BYTES
from rag.ignore import IgnoreFilter
from rag.types import RepoFile
from rag.utils.hash import sha256
from rag.utils.lang import detect_kind, detect_language

logger = logging.getLogger(__name__)


def crawl_repo(root_dir: str | Path) -> list[RepoFile]:
    """Walk *root_dir* recursively and return a list of indexable files.

    Skips files that are ignored by .gitignore rules, binary extensions,
    or exceed the max file size.
    """
    root = Path(root_dir).resolve()
    ignore = IgnoreFilter(root)
    files: list[RepoFile] = []

    for item in sorted(root.rglob("*")):
        relative = str(item.relative_to(root)).replace("\\", "/")

        if item.is_dir():
            continue

        if ignore.should_ignore(relative, is_dir=False):
            logger.debug("Ignored: %s", relative)
            continue

        # Check parent directories
        skip = False
        for parent in item.relative_to(root).parents:
            parent_str = str(parent)
            if parent_str != "." and ignore.should_ignore(parent_str, is_dir=True):
                skip = True
                break
        if skip:
            logger.debug("Ignored (parent): %s", relative)
            continue

        # Size check
        try:
            size = item.stat().st_size
        except OSError:
            continue
        if size > MAX_FILE_BYTES:
            logger.debug("Skipped (too large: %d bytes): %s", size, relative)
            continue

        # Read content
        try:
            text = item.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            logger.debug("Skipped (unreadable): %s", relative)
            continue

        language = detect_language(relative)
        kind = detect_kind(relative, language)
        content_hash = sha256(text)

        files.append(RepoFile(
            path=relative,
            kind=kind,
            language=language,
            text=text,
            hash=content_hash,
        ))

    logger.info("Crawled %d files from %s", len(files), root)
    return files

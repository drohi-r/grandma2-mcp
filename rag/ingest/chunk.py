"""AST-aware chunking for Python, heading-based for markdown, line-based fallback."""

from __future__ import annotations

import ast
import logging
import re

from rag.config import CHARS_PER_TOKEN, DEFAULT_CHUNK_MAX_TOKENS, DEFAULT_CHUNK_OVERLAP_LINES
from rag.ingest.extract import extract_symbols
from rag.types import Chunk, RepoFile
from rag.utils.hash import sha256

logger = logging.getLogger(__name__)


def chunk_file(
    file: RepoFile,
    doc_id: str,
    *,
    max_tokens: int = DEFAULT_CHUNK_MAX_TOKENS,
    overlap_lines: int = DEFAULT_CHUNK_OVERLAP_LINES,
) -> list[Chunk]:
    """Split a file into chunks using the best strategy for its language."""
    if file.language == "python":
        chunks = _chunk_python(file, doc_id, max_tokens=max_tokens, overlap_lines=overlap_lines)
    elif file.language == "markdown":
        chunks = _chunk_markdown(file, doc_id, max_tokens=max_tokens, overlap_lines=overlap_lines)
    else:
        chunks = _chunk_lines(file, doc_id, max_tokens=max_tokens, overlap_lines=overlap_lines)

    # Filter out empty chunks
    return [c for c in chunks if c.text.strip()]


# ---------------------------------------------------------------------------
# Python chunking (AST-based)
# ---------------------------------------------------------------------------


def _chunk_python(
    file: RepoFile,
    doc_id: str,
    *,
    max_tokens: int,
    overlap_lines: int,
) -> list[Chunk]:
    """Split Python source by top-level def/class boundaries via AST."""
    try:
        tree = ast.parse(file.text)
    except SyntaxError:
        logger.debug("AST parse failed for %s, falling back to line-based", file.path)
        return _chunk_lines(file, doc_id, max_tokens=max_tokens, overlap_lines=overlap_lines)

    lines = file.text.splitlines(keepends=True)
    if not lines:
        return []

    # Collect top-level node boundaries (1-indexed)
    boundaries: list[tuple[int, int, list[str]]] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            # Include decorators
            start = node.decorator_list[0].lineno if node.decorator_list else node.lineno
            end = node.end_lineno or node.lineno
            symbols = [node.name]
            boundaries.append((start, end, symbols))

    if not boundaries:
        # No functions/classes — treat the whole file as one chunk
        return _make_chunks_from_ranges(
            file, doc_id, [(1, len(lines), [])], lines, max_tokens=max_tokens, overlap_lines=overlap_lines
        )

    # Sort by start line
    boundaries.sort(key=lambda b: b[0])

    ranges: list[tuple[int, int, list[str]]] = []

    # Preamble: everything before the first node
    first_start = boundaries[0][0]
    if first_start > 1:
        preamble_symbols = extract_symbols("python", "".join(lines[: first_start - 1]))
        ranges.append((1, first_start - 1, preamble_symbols))

    # Each top-level node
    for start, end, syms in boundaries:
        ranges.append((start, end, syms))

    # Anything after the last node
    last_end = boundaries[-1][1]
    if last_end < len(lines):
        ranges.append((last_end + 1, len(lines), []))

    return _make_chunks_from_ranges(file, doc_id, ranges, lines, max_tokens=max_tokens, overlap_lines=overlap_lines)


# ---------------------------------------------------------------------------
# Markdown chunking (heading-based)
# ---------------------------------------------------------------------------

_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+", re.MULTILINE)


def _chunk_markdown(
    file: RepoFile,
    doc_id: str,
    *,
    max_tokens: int,
    overlap_lines: int,
) -> list[Chunk]:
    """Split markdown by headings."""
    lines = file.text.splitlines(keepends=True)
    if not lines:
        return []

    # Find heading line numbers (1-indexed)
    heading_lines: list[int] = []
    for i, line in enumerate(lines, start=1):
        if _HEADING_PATTERN.match(line):
            heading_lines.append(i)

    if not heading_lines:
        return _chunk_lines(file, doc_id, max_tokens=max_tokens, overlap_lines=overlap_lines)

    ranges: list[tuple[int, int, list[str]]] = []

    # Content before first heading
    if heading_lines[0] > 1:
        ranges.append((1, heading_lines[0] - 1, []))

    # Each heading section
    for idx, start in enumerate(heading_lines):
        end = heading_lines[idx + 1] - 1 if idx + 1 < len(heading_lines) else len(lines)
        heading_text = lines[start - 1].lstrip("#").strip()
        ranges.append((start, end, [heading_text]))

    return _make_chunks_from_ranges(file, doc_id, ranges, lines, max_tokens=max_tokens, overlap_lines=overlap_lines)


# ---------------------------------------------------------------------------
# Line-based fallback
# ---------------------------------------------------------------------------


def _chunk_lines(
    file: RepoFile,
    doc_id: str,
    *,
    max_tokens: int,
    overlap_lines: int,
) -> list[Chunk]:
    """Fixed-size line-based chunking with overlap."""
    lines = file.text.splitlines(keepends=True)
    if not lines:
        return []

    max_chars = max_tokens * CHARS_PER_TOKEN
    # Approximate lines per chunk
    avg_line_len = max(1, len(file.text) // max(1, len(lines)))
    lines_per_chunk = max(10, max_chars // avg_line_len)
    # Cap overlap so pos always advances by ≥ 1 (avoids infinite loop on long-line files)
    safe_overlap = min(overlap_lines, lines_per_chunk - 1)

    ranges: list[tuple[int, int, list[str]]] = []
    start = 0
    while start < len(lines):
        end = min(start + lines_per_chunk, len(lines))
        ranges.append((start + 1, end, []))  # 1-indexed
        start = end - safe_overlap if end < len(lines) else end

    symbols = extract_symbols(file.language, file.text)
    if symbols:
        for i in range(len(ranges)):
            ranges[i] = (ranges[i][0], ranges[i][1], symbols)

    return _make_chunks_from_ranges(file, doc_id, ranges, lines, max_tokens=max_tokens, overlap_lines=overlap_lines)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_chunks_from_ranges(
    file: RepoFile,
    doc_id: str,
    ranges: list[tuple[int, int, list[str]]],
    lines: list[str],
    *,
    max_tokens: int,
    overlap_lines: int,
) -> list[Chunk]:
    """Convert line ranges into Chunk objects, splitting oversized ranges."""
    max_chars = max_tokens * CHARS_PER_TOKEN
    chunks: list[Chunk] = []

    for start_line, end_line, symbols in ranges:
        text = "".join(lines[start_line - 1 : end_line])
        if not text.strip():
            continue

        if len(text) <= max_chars:
            chunk_id = sha256(f"{doc_id}:{start_line}:{end_line}")
            chunks.append(Chunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                path=file.path,
                kind=file.kind,
                language=file.language,
                text=text,
                start_line=start_line,
                end_line=end_line,
                symbols=symbols,
                chunk_hash=sha256(text),
            ))
        else:
            # Split oversized range into sub-chunks
            sub_ranges = _split_range(start_line, end_line, lines, max_chars, overlap_lines)
            for sub_start, sub_end in sub_ranges:
                sub_text = "".join(lines[sub_start - 1 : sub_end])
                if not sub_text.strip():
                    continue
                chunk_id = sha256(f"{doc_id}:{sub_start}:{sub_end}")
                chunks.append(Chunk(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    path=file.path,
                    kind=file.kind,
                    language=file.language,
                    text=sub_text,
                    start_line=sub_start,
                    end_line=sub_end,
                    symbols=symbols,
                    chunk_hash=sha256(sub_text),
                ))

    return chunks


def _split_range(
    start_line: int,
    end_line: int,
    lines: list[str],
    max_chars: int,
    overlap_lines: int,
) -> list[tuple[int, int]]:
    """Split an oversized range into smaller sub-ranges."""
    total_lines = end_line - start_line + 1
    avg_line_len = max(1, sum(len(lines[i]) for i in range(start_line - 1, end_line)) // total_lines)
    lines_per_sub = max(10, max_chars // avg_line_len)
    # Cap overlap so pos always advances by ≥ 1 (avoids infinite loop on long-line files)
    safe_overlap = min(overlap_lines, lines_per_sub - 1)

    sub_ranges: list[tuple[int, int]] = []
    pos = start_line
    while pos <= end_line:
        sub_end = min(pos + lines_per_sub - 1, end_line)
        sub_ranges.append((pos, sub_end))
        pos = sub_end + 1 - safe_overlap if sub_end < end_line else sub_end + 1

    return sub_ranges

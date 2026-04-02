"""Core dataclasses for the RAG pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

RagKind = Literal["source", "test", "doc", "config"]


@dataclass
class RepoFile:
    """A file discovered by the repo crawler."""

    path: str
    kind: RagKind
    language: str
    text: str
    hash: str  # sha256 of content


@dataclass
class Chunk:
    """A text chunk ready for embedding and storage."""

    chunk_id: str
    doc_id: str
    path: str
    kind: RagKind
    language: str
    text: str
    start_line: int
    end_line: int
    symbols: list[str] = field(default_factory=list)
    chunk_hash: str = ""


@dataclass
class RagHit:
    """A single retrieval result returned by the query pipeline."""

    chunk_id: str
    path: str
    kind: RagKind
    start_line: int
    end_line: int
    score: float
    text: str


@dataclass
class DocumentRecord:
    """Metadata for a file stored in the documents table."""

    doc_id: str
    repo_ref: str
    path: str
    language: str
    kind: RagKind
    file_hash: str


@dataclass
class IngestResult:
    """Statistics returned after an ingest run."""

    files_processed: int = 0
    files_skipped: int = 0
    chunks_created: int = 0

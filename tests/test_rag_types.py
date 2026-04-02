"""Tests for RAG core types and dataclasses."""

from rag.types import Chunk, DocumentRecord, IngestResult, RagHit, RepoFile


class TestRepoFile:
    def test_construction(self):
        f = RepoFile(path="src/server.py", kind="source", language="python", text="code", hash="abc123")
        assert f.path == "src/server.py"
        assert f.kind == "source"
        assert f.language == "python"
        assert f.text == "code"
        assert f.hash == "abc123"


class TestChunk:
    def test_defaults(self):
        c = Chunk(
            chunk_id="id1", doc_id="doc1", path="foo.py",
            kind="source", language="python", text="code",
            start_line=1, end_line=10,
        )
        assert c.symbols == []
        assert c.chunk_hash == ""

    def test_with_symbols(self):
        c = Chunk(
            chunk_id="id1", doc_id="doc1", path="foo.py",
            kind="source", language="python", text="code",
            start_line=1, end_line=10, symbols=["my_func"],
        )
        assert c.symbols == ["my_func"]


class TestRagHit:
    def test_construction(self):
        hit = RagHit(
            chunk_id="c1", path="store.py", kind="source",
            start_line=20, end_line=50, score=0.95, text="store cue 1",
        )
        assert hit.score == 0.95
        assert hit.kind == "source"


class TestDocumentRecord:
    def test_construction(self):
        doc = DocumentRecord(
            doc_id="d1", repo_ref="main", path="README.md",
            language="markdown", kind="doc", file_hash="xyz",
        )
        assert doc.repo_ref == "main"


class TestIngestResult:
    def test_defaults(self):
        result = IngestResult()
        assert result.files_processed == 0
        assert result.files_skipped == 0
        assert result.chunks_created == 0

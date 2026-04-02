"""Tests for the RAG repo crawler."""

from rag.ingest.crawl_repo import crawl_repo


class TestCrawlRepo:
    def test_crawls_python_files(self, tmp_path):
        (tmp_path / "main.py").write_text("print('hello')", encoding="utf-8")
        files = crawl_repo(tmp_path)
        assert len(files) == 1
        assert files[0].path == "main.py"
        assert files[0].language == "python"
        assert files[0].kind == "source"

    def test_crawls_markdown_files(self, tmp_path):
        (tmp_path / "README.md").write_text("# Hello", encoding="utf-8")
        files = crawl_repo(tmp_path)
        assert len(files) == 1
        assert files[0].language == "markdown"
        assert files[0].kind == "doc"

    def test_detects_test_files(self, tmp_path):
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_foo.py").write_text("def test_foo(): pass", encoding="utf-8")
        files = crawl_repo(tmp_path)
        assert len(files) == 1
        assert files[0].kind == "test"

    def test_detects_config_files(self, tmp_path):
        (tmp_path / "config.toml").write_text("[section]\nkey=1", encoding="utf-8")
        files = crawl_repo(tmp_path)
        assert len(files) == 1
        assert files[0].kind == "config"

    def test_skips_gitignored_directories(self, tmp_path):
        (tmp_path / ".gitignore").write_text("build/\n", encoding="utf-8")
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        (build_dir / "output.py").write_text("x = 1", encoding="utf-8")
        (tmp_path / "src.py").write_text("y = 2", encoding="utf-8")

        files = crawl_repo(tmp_path)
        paths = [f.path for f in files]
        assert "src.py" in paths
        assert "build/output.py" not in paths

    def test_skips_pycache(self, tmp_path):
        cache_dir = tmp_path / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "mod.cpython-312.pyc").write_bytes(b"\x00\x00")
        (tmp_path / "mod.py").write_text("x = 1", encoding="utf-8")

        files = crawl_repo(tmp_path)
        assert len(files) == 1
        assert files[0].path == "mod.py"

    def test_skips_binary_extensions(self, tmp_path):
        (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n")
        (tmp_path / "code.py").write_text("x = 1", encoding="utf-8")

        files = crawl_repo(tmp_path)
        assert len(files) == 1
        assert files[0].path == "code.py"

    def test_skips_large_files(self, tmp_path):
        large_file = tmp_path / "huge.py"
        large_file.write_text("x" * (3 * 1024 * 1024), encoding="utf-8")  # 3MB
        (tmp_path / "small.py").write_text("y = 1", encoding="utf-8")

        files = crawl_repo(tmp_path)
        assert len(files) == 1
        assert files[0].path == "small.py"

    def test_computes_hash(self, tmp_path):
        (tmp_path / "a.py").write_text("content_a", encoding="utf-8")
        (tmp_path / "b.py").write_text("content_b", encoding="utf-8")

        files = crawl_repo(tmp_path)
        hashes = [f.hash for f in files]
        # Different content should produce different hashes
        assert hashes[0] != hashes[1]

    def test_empty_directory(self, tmp_path):
        files = crawl_repo(tmp_path)
        assert files == []

    def test_skips_unreadable_binary(self, tmp_path):
        (tmp_path / "data.bin").write_bytes(bytes(range(256)))
        files = crawl_repo(tmp_path)
        # .bin is in IGNORED_EXTENSIONS, so it should be skipped
        assert len(files) == 0

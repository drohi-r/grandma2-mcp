"""Tests for the RAG ignore filter."""

from rag.ignore import IgnoreFilter, load_gitignore_patterns


class TestIgnoreFilter:
    def test_ignores_pycache(self, tmp_path):
        filt = IgnoreFilter(tmp_path)
        assert filt.should_ignore("__pycache__/module.pyc", is_dir=False)

    def test_ignores_git_dir(self, tmp_path):
        filt = IgnoreFilter(tmp_path)
        assert filt.should_ignore(".git/config", is_dir=False)

    def test_ignores_node_modules(self, tmp_path):
        filt = IgnoreFilter(tmp_path)
        assert filt.should_ignore("node_modules/package/index.js", is_dir=False)

    def test_ignores_pyc_extension(self, tmp_path):
        filt = IgnoreFilter(tmp_path)
        assert filt.should_ignore("module.pyc", is_dir=False)

    def test_ignores_binary_extensions(self, tmp_path):
        filt = IgnoreFilter(tmp_path)
        assert filt.should_ignore("image.png", is_dir=False)
        assert filt.should_ignore("archive.zip", is_dir=False)
        assert filt.should_ignore("data.db", is_dir=False)

    def test_allows_python_files(self, tmp_path):
        filt = IgnoreFilter(tmp_path)
        assert not filt.should_ignore("src/server.py", is_dir=False)

    def test_allows_markdown_files(self, tmp_path):
        filt = IgnoreFilter(tmp_path)
        assert not filt.should_ignore("README.md", is_dir=False)

    def test_dir_ignore(self, tmp_path):
        filt = IgnoreFilter(tmp_path)
        assert filt.should_ignore(".venv", is_dir=True)
        assert filt.should_ignore("__pycache__", is_dir=True)


class TestGitignorePatterns:
    def test_loads_gitignore(self, tmp_path):
        (tmp_path / ".gitignore").write_text("*.log\nbuild/\n", encoding="utf-8")
        patterns = load_gitignore_patterns(tmp_path)
        assert "*.log" in patterns
        assert "build/" in patterns

    def test_skips_comments_and_blanks(self, tmp_path):
        (tmp_path / ".gitignore").write_text("# comment\n\n*.log\n", encoding="utf-8")
        patterns = load_gitignore_patterns(tmp_path)
        assert patterns == ["*.log"]

    def test_no_gitignore(self, tmp_path):
        patterns = load_gitignore_patterns(tmp_path)
        assert patterns == []

    def test_gitignore_dir_pattern(self, tmp_path):
        (tmp_path / ".gitignore").write_text("dist/\n", encoding="utf-8")
        filt = IgnoreFilter(tmp_path)
        assert filt.should_ignore("dist", is_dir=True)

    def test_gitignore_file_pattern(self, tmp_path):
        (tmp_path / ".gitignore").write_text("*.log\n", encoding="utf-8")
        filt = IgnoreFilter(tmp_path)
        assert filt.should_ignore("app.log", is_dir=False)
        assert not filt.should_ignore("app.py", is_dir=False)

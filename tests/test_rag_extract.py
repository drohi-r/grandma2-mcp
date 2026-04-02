"""Tests for RAG symbol extraction."""

from rag.ingest.extract import extract_symbols


class TestPythonSymbols:
    def test_functions(self):
        code = "def foo():\n    pass\n\ndef bar():\n    pass\n"
        symbols = extract_symbols("python", code)
        assert symbols == ["foo", "bar"]

    def test_classes(self):
        code = "class MyClass:\n    pass\n"
        symbols = extract_symbols("python", code)
        assert symbols == ["MyClass"]

    def test_async_function(self):
        code = "async def async_handler():\n    pass\n"
        symbols = extract_symbols("python", code)
        assert symbols == ["async_handler"]

    def test_mixed(self):
        code = (
            "class Foo:\n    pass\n\n"
            "def bar():\n    pass\n\n"
            "async def baz():\n    pass\n"
        )
        symbols = extract_symbols("python", code)
        assert symbols == ["Foo", "bar", "baz"]

    def test_syntax_error(self):
        code = "def broken(\n"
        symbols = extract_symbols("python", code)
        assert symbols == []

    def test_empty(self):
        symbols = extract_symbols("python", "")
        assert symbols == []

    def test_no_top_level_defs(self):
        code = "import os\nX = 1\nprint('hello')\n"
        symbols = extract_symbols("python", code)
        assert symbols == []


class TestMarkdownSymbols:
    def test_headings(self):
        md = "# Title\n\nText.\n\n## Section A\n\n## Section B\n"
        symbols = extract_symbols("markdown", md)
        assert symbols == ["Title", "Section A", "Section B"]

    def test_no_headings(self):
        md = "Just text.\n"
        symbols = extract_symbols("markdown", md)
        assert symbols == []

    def test_nested_headings(self):
        md = "# Top\n## Sub\n### SubSub\n"
        symbols = extract_symbols("markdown", md)
        assert symbols == ["Top", "Sub", "SubSub"]


class TestOtherLanguages:
    def test_unknown_returns_empty(self):
        symbols = extract_symbols("yaml", "key: value\n")
        assert symbols == []

    def test_json_returns_empty(self):
        symbols = extract_symbols("json", '{"key": "value"}')
        assert symbols == []

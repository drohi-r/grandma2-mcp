"""Tests for rag.ingest.crawl_web — HTML crawling and text extraction."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from rag.ingest.crawl_web import (
    _convert_headings_to_markdown,
    _extract_links,
    _extract_text,
    _normalize_url,
    crawl_web,
)
from rag.types import RepoFile
from scripts.rag_ingest_web import _dedup_pages

# ---------------------------------------------------------------------------
# URL normalisation
# ---------------------------------------------------------------------------


class TestNormalizeUrl:
    def test_removes_fragment(self):
        assert _normalize_url("https://example.com/page#section") == "https://example.com/page"

    def test_strips_whitespace(self):
        assert _normalize_url("  https://example.com/page  ") == "https://example.com/page"

    def test_preserves_query(self):
        assert _normalize_url("https://example.com/page?q=1") == "https://example.com/page?q=1"


# ---------------------------------------------------------------------------
# Link extraction
# ---------------------------------------------------------------------------

_LINK_HTML = """
<html><body>
<a href="page1.html">Page 1</a>
<a href="page2.html">Page 2</a>
<a href="https://other.com/external">External</a>
<a href="#anchor">Anchor only</a>
<a href="../parent.html">Parent</a>
</body></html>
"""


class TestExtractLinks:
    def test_follows_links_within_prefix(self):
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(_LINK_HTML, "html.parser")
        links = _extract_links(soup, "https://example.com/docs/index.html", ["https://example.com/docs/"])
        assert "https://example.com/docs/page1.html" in links
        assert "https://example.com/docs/page2.html" in links

    def test_excludes_external_links(self):
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(_LINK_HTML, "html.parser")
        links = _extract_links(soup, "https://example.com/docs/index.html", ["https://example.com/docs/"])
        assert not any("other.com" in link for link in links)

    def test_resolves_relative_links(self):
        from bs4 import BeautifulSoup

        soup = BeautifulSoup('<a href="sub/page.html">Sub</a>', "html.parser")
        links = _extract_links(soup, "https://example.com/docs/", ["https://example.com/"])
        assert "https://example.com/docs/sub/page.html" in links

    def test_multiple_prefixes(self):
        from bs4 import BeautifulSoup

        html = """
        <html><body>
        <a href="https://help.example.com/docs/page1.html">Help</a>
        <a href="https://help2.example.com/docs/notes.html">Notes</a>
        <a href="https://other.com/external">External</a>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        prefixes = [
            "https://help.example.com/docs/",
            "https://help2.example.com/docs/",
        ]
        links = _extract_links(soup, "https://help.example.com/docs/", prefixes)
        assert "https://help.example.com/docs/page1.html" in links
        assert "https://help2.example.com/docs/notes.html" in links
        assert not any("other.com" in link for link in links)


# ---------------------------------------------------------------------------
# HTML → text extraction
# ---------------------------------------------------------------------------

_CONTENT_HTML = """
<html>
<head><title>Test</title></head>
<body>
<nav>Navigation menu</nav>
<script>var x = 1;</script>
<style>.foo { color: red; }</style>
<div class="topic-content">
    <h1>Main Title</h1>
    <p>This is the main content paragraph.</p>
    <h2>Subsection</h2>
    <p>More details here.</p>
</div>
<footer>Footer text</footer>
</body>
</html>
"""


class TestExtractText:
    def test_strips_nav_script_style_footer(self):
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(_CONTENT_HTML, "html.parser")
        text = _extract_text(soup)
        assert "Navigation menu" not in text
        assert "var x = 1" not in text
        assert ".foo" not in text
        assert "Footer text" not in text

    def test_preserves_content(self):
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(_CONTENT_HTML, "html.parser")
        text = _extract_text(soup)
        assert "main content paragraph" in text
        assert "More details here" in text

    def test_converts_headings_to_markdown(self):
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(_CONTENT_HTML, "html.parser")
        text = _extract_text(soup)
        assert "# Main Title" in text
        assert "## Subsection" in text

    def test_removes_sidebar_selectors(self):
        from bs4 import BeautifulSoup

        html = '<body><div id="offline-tree">sidebar</div><main><p>content</p></main></body>'
        soup = BeautifulSoup(html, "html.parser")
        text = _extract_text(soup)
        assert "sidebar" not in text
        assert "content" in text

    def test_falls_back_to_body(self):
        from bs4 import BeautifulSoup

        html = "<html><body><p>Just body content.</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        text = _extract_text(soup)
        assert "Just body content" in text


# ---------------------------------------------------------------------------
# Heading conversion
# ---------------------------------------------------------------------------


class TestConvertHeadings:
    def test_all_heading_levels(self):
        from bs4 import BeautifulSoup

        html = "<div><h1>One</h1><h2>Two</h2><h3>Three</h3><h4>Four</h4><h5>Five</h5><h6>Six</h6></div>"
        soup = BeautifulSoup(html, "html.parser")
        div = soup.find("div")
        _convert_headings_to_markdown(div)
        text = div.get_text(separator="\n")
        assert "# One" in text
        assert "## Two" in text
        assert "### Three" in text
        assert "#### Four" in text
        assert "##### Five" in text
        assert "###### Six" in text


# ---------------------------------------------------------------------------
# URL deduplication in crawl
# ---------------------------------------------------------------------------


class TestCrawlDeduplication:
    @patch("rag.ingest.crawl_web.httpx.Client")
    def test_does_not_revisit_urls(self, mock_client_cls):
        """The same URL (with and without fragment) should only be fetched once."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        # The page links back to itself with a fragment — content must be >50 chars
        html = '<html><body><div class="topic-content"><h1>Title</h1><p>Content here for testing dedup with enough text to pass the minimum length filter.</p><a href="#frag">self</a></div></body></html>'
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.headers = {"content-type": "text/html"}
        mock_resp.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_resp

        pages = crawl_web(["https://example.com/docs/"], max_pages=5, delay=0)
        # Should only fetch once despite the self-link
        assert mock_client.get.call_count == 1
        assert len(pages) == 1


# ---------------------------------------------------------------------------
# RepoFile correctness
# ---------------------------------------------------------------------------


class TestRepoFileFields:
    @patch("rag.ingest.crawl_web.httpx.Client")
    def test_repofile_has_correct_fields(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        html = '<html><body><div class="topic-content"><h1>Patching</h1><p>How to patch fixtures in grandMA2. This page explains the full patching workflow for DMX universes and fixture types.</p></div></body></html>'
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.headers = {"content-type": "text/html"}
        mock_resp.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_resp

        pages = crawl_web(["https://help.malighting.com/grandMA2/en/help/patch.html"], max_pages=1, delay=0)
        assert len(pages) == 1

        page = pages[0]
        assert page.kind == "doc"
        assert page.language == "markdown"
        assert "grandMA2/en/help/patch.html" in page.path
        assert "Patching" in page.text
        assert len(page.hash) == 64  # SHA-256 hex digest


# ---------------------------------------------------------------------------
# Multi-prefix crawl (auto-derived)
# ---------------------------------------------------------------------------


class TestMultiPrefixCrawl:
    @patch("rag.ingest.crawl_web.httpx.Client")
    def test_auto_derives_prefix_per_start_url(self, mock_client_cls):
        """Two start URLs on different domains should each get their own prefix."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        # Page on domain A links to a sub-page on domain B
        html_a = (
            '<html><body><div class="topic-content">'
            "<h1>Main</h1><p>Content on domain A with enough text to pass filter.</p>"
            '<a href="https://help2.example.com/docs/notes/v3.html">Release Notes</a>'
            "</div></body></html>"
        )
        html_b = (
            '<html><body><div class="topic-content">'
            "<h1>Notes</h1><p>Release notes on domain B with enough text to pass.</p>"
            "</div></body></html>"
        )

        def fake_get(url):
            resp = MagicMock()
            resp.headers = {"content-type": "text/html"}
            resp.raise_for_status = MagicMock()
            if "help2" in url:
                resp.text = html_b
            else:
                resp.text = html_a
            return resp

        mock_client.get.side_effect = fake_get

        pages = crawl_web(
            [
                "https://help.example.com/docs/",
                "https://help2.example.com/docs/notes/",
            ],
            max_pages=10,
            delay=0,
        )

        paths = [p.path for p in pages]
        # Both domains should be crawled
        assert any("docs/" in p for p in paths)
        # The link from domain A to domain B sub-page should be followed
        assert any("notes/v3.html" in p for p in paths)


# ---------------------------------------------------------------------------
# Page deduplication
# ---------------------------------------------------------------------------


class TestDedupPages:
    def test_removes_duplicate_paths(self):
        pages = [
            RepoFile(path="docs/index.html", kind="doc", language="markdown", text="short", hash="a"),
            RepoFile(path="docs/index.html", kind="doc", language="markdown", text="longer content here", hash="b"),
            RepoFile(path="docs/other.html", kind="doc", language="markdown", text="unique", hash="c"),
        ]
        result = _dedup_pages(pages)
        assert len(result) == 2
        paths = [p.path for p in result]
        assert "docs/index.html" in paths
        assert "docs/other.html" in paths

    def test_keeps_longer_content(self):
        pages = [
            RepoFile(path="same.html", kind="doc", language="markdown", text="short", hash="a"),
            RepoFile(path="same.html", kind="doc", language="markdown", text="much longer content wins", hash="b"),
        ]
        result = _dedup_pages(pages)
        assert len(result) == 1
        assert result[0].text == "much longer content wins"

    def test_no_duplicates_unchanged(self):
        pages = [
            RepoFile(path="a.html", kind="doc", language="markdown", text="aaa", hash="1"),
            RepoFile(path="b.html", kind="doc", language="markdown", text="bbb", hash="2"),
        ]
        result = _dedup_pages(pages)
        assert len(result) == 2

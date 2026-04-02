"""Web crawler for HTML documentation sites.

Crawls from start URLs using BFS, extracts clean text from HTML pages,
and returns RepoFile objects compatible with the RAG ingest pipeline.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from collections import deque
from urllib.parse import urljoin, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup, Tag

from rag.types import RepoFile

logger = logging.getLogger(__name__)

# Elements to strip from the page before text extraction
_STRIP_TAGS = {"script", "style", "nav", "header", "footer", "noscript"}

# CSS selectors for sidebar / navigation trees to remove
_STRIP_SELECTORS = ["#offline-tree", ".topic-tree-container", ".jstree"]

# Selectors to try for main content, in priority order
_CONTENT_SELECTORS = [".topic-content", "main", "article", "[role='main']"]

_HEADING_RE = re.compile(r"^(h[1-6])$", re.IGNORECASE)


def crawl_web(
    start_urls: list[str],
    *,
    url_prefix: str | list[str] | None = None,
    delay: float = 0.5,
    max_pages: int = 2000,
) -> list[RepoFile]:
    """Crawl HTML pages starting from *start_urls* and return RepoFile list.

    Parameters
    ----------
    start_urls:
        One or more seed URLs to begin crawling from.
    url_prefix:
        Only follow links whose URL starts with one of these prefixes.
        Accepts a single string or a list of strings.
        If ``None``, one prefix is derived per start URL so that
        multi-domain seed lists work correctly.
    delay:
        Seconds to wait between HTTP requests (politeness).
    max_pages:
        Maximum number of pages to crawl.

    Returns
    -------
    list[RepoFile]
        One RepoFile per successfully crawled page, with ``kind="doc"``,
        ``language="markdown"``, and cleaned text content.
    """
    if not start_urls:
        return []

    # Build the list of allowed URL prefixes
    if url_prefix is None:
        prefixes: list[str] = []
        for url in start_urls:
            parsed = urlparse(url)
            p = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if not p.endswith("/"):
                p = p.rsplit("/", 1)[0] + "/"
            if p not in prefixes:
                prefixes.append(p)
    elif isinstance(url_prefix, str):
        prefixes = [url_prefix]
    else:
        prefixes = list(url_prefix)

    visited: set[str] = set()
    queue: deque[str] = deque()
    files: list[RepoFile] = []

    # Seed the queue
    for url in start_urls:
        normalized = _normalize_url(url)
        if normalized not in visited:
            visited.add(normalized)
            queue.append(normalized)

    client = httpx.Client(
        timeout=30.0,
        follow_redirects=True,
        headers={"User-Agent": "ma2-agent-rag-crawler/1.0 (documentation indexer)"},
    )

    try:
        while queue and len(files) < max_pages:
            url = queue.popleft()

            try:
                resp = client.get(url)
                resp.raise_for_status()
            except httpx.TimeoutException:
                logger.warning("Timeout (transient) fetching %s — skipping", url)
                continue
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status in {403, 404, 410}:
                    logger.info("Permanent error %d for %s — skipping", status, url)
                else:
                    logger.warning("Transient error %d for %s — skipping", status, url)
                continue
            except httpx.HTTPError as exc:
                logger.warning("Network error fetching %s: %s", url, exc)
                continue

            content_type = resp.headers.get("content-type", "")
            if "text/html" not in content_type:
                logger.debug("Skipping non-HTML: %s (%s)", url, content_type)
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            # Discover links
            for link in _extract_links(soup, url, prefixes):
                if link not in visited:
                    visited.add(link)
                    queue.append(link)

            # Extract text
            text = _extract_text(soup)
            if not text or len(text.strip()) < 50:
                logger.debug("Skipping (too little content): %s", url)
                continue

            # Build relative path from URL
            parsed = urlparse(url)
            path = parsed.path.lstrip("/")
            if not path or path.endswith("/"):
                path += "index.html"

            content_hash = hashlib.sha256(text.encode()).hexdigest()

            files.append(RepoFile(
                path=path,
                kind="doc",
                language="markdown",
                text=text,
                hash=content_hash,
            ))

            logger.info("Crawled [%d/%d]: %s (%d chars)", len(files), max_pages, path, len(text))

            if delay > 0:
                time.sleep(delay)

    finally:
        client.close()

    logger.info("Crawl complete: %d pages from %d visited URLs", len(files), len(visited))
    return files


def _normalize_url(url: str) -> str:
    """Normalize a URL: lowercase scheme/host, strip fragment + tracking params."""
    parsed = urlparse(url.strip())
    # Lowercase scheme and netloc for consistent deduplication
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    # Strip tracking parameters
    _TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid", "ref"}
    if parsed.query:
        from urllib.parse import parse_qs, urlencode
        params = parse_qs(parsed.query, keep_blank_values=True)
        filtered = {k: v for k, v in params.items() if k.lower() not in _TRACKING_PARAMS}
        query = urlencode(filtered, doseq=True)
    else:
        query = ""
    # Remove fragment, normalize path trailing slash
    path = parsed.path.rstrip("/") if parsed.path != "/" else "/"
    return urlunparse((scheme, netloc, path, parsed.params, query, ""))


def _extract_links(soup: BeautifulSoup, base_url: str, prefixes: list[str]) -> list[str]:
    """Extract and filter links from a page."""
    links: list[str] = []
    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        if isinstance(href, list):
            href = href[0]
        absolute = urljoin(base_url, href)
        normalized = _normalize_url(absolute)

        # Only follow links within one of the allowed prefixes
        if any(normalized.startswith(p) for p in prefixes):
            links.append(normalized)

    return links


def _extract_text(soup: BeautifulSoup) -> str:
    """Extract clean text from an HTML page, converting headings to markdown."""
    # Remove unwanted elements
    for tag_name in _STRIP_TAGS:
        for el in soup.find_all(tag_name):
            el.decompose()

    for selector in _STRIP_SELECTORS:
        for el in soup.select(selector):
            el.decompose()

    # Find the main content container
    content: Tag | None = None
    for selector in _CONTENT_SELECTORS:
        found = soup.select_one(selector)
        if found and isinstance(found, Tag):
            content = found
            break

    if content is None:
        content = soup.body  # type: ignore[assignment]
    if content is None:
        return ""

    # Convert headings to markdown-style before extracting text
    _convert_headings_to_markdown(content)

    text = content.get_text(separator="\n")

    # Clean up excessive blank lines
    lines = text.splitlines()
    cleaned: list[str] = []
    blank_count = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            blank_count += 1
            if blank_count <= 2:
                cleaned.append("")
        else:
            blank_count = 0
            cleaned.append(stripped)

    return "\n".join(cleaned).strip()


def _convert_headings_to_markdown(element: Tag) -> None:
    """Replace <h1>–<h6> tags with markdown heading text in-place."""
    for tag in element.find_all(_HEADING_RE):
        level = int(tag.name[1])  # h1 → 1, h2 → 2, etc.
        prefix = "#" * level
        heading_text = tag.get_text(strip=True)
        tag.string = f"{prefix} {heading_text}"

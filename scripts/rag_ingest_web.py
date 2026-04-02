"""CLI script to crawl web documentation and ingest into the RAG index.

Usage:
    uv run python scripts/rag_ingest_web.py [OPTIONS]
    uv run python scripts/rag_ingest_web.py \
        --url "https://help.malighting.com/grandMA2/en/help/" \
        --url "https://help2.malighting.com/grandMA2/en/help/release_notes/" \
        --provider github -v

    # First run: crawl + cache + embed batch 1
    uv run python scripts/rag_ingest_web.py --provider github --cache-crawl --batch-size 50

    # Subsequent days: load from cache, embed next batch (no re-crawl)
    uv run python scripts/rag_ingest_web.py --provider github --cache-crawl --batch-size 50

    # Force a fresh crawl and overwrite the cache
    uv run python scripts/rag_ingest_web.py --provider github --cache-crawl --recrawl
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.config import RAG_DB_PATH
from rag.ingest.crawl_web import crawl_web
from rag.ingest.index import ingest
from rag.types import RepoFile

# Reuse the provider factory from the repo ingest script
from scripts.rag_ingest import make_provider

logger = logging.getLogger(__name__)

DEFAULT_URLS = [
    "https://help.malighting.com/grandMA2/en/help/",
    "https://help2.malighting.com/grandMA2/en/help/release_notes/",
]

DEFAULT_CACHE_PATH = Path("rag/store/web_crawl_cache.json")
_CACHE_SCHEMA_VERSION = 2  # bumped: v1 cache missing release notes due to prefix bug


def _dedup_pages(pages: list[RepoFile]) -> list[RepoFile]:
    """Deduplicate pages by path, keeping the version with the most content."""
    seen: dict[str, RepoFile] = {}
    for page in pages:
        if page.path not in seen or len(page.text) > len(seen[page.path].text):
            seen[page.path] = page
    return list(seen.values())


def _save_cache(path: Path, pages: list[RepoFile], start_urls: list[str]) -> None:
    """Serialise crawled pages to a JSON cache file (atomic write)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "schema_version": _CACHE_SCHEMA_VERSION,
        "crawled_at": datetime.now(timezone.utc).isoformat(),
        "start_urls": start_urls,
        "page_count": len(pages),
        "pages": [dataclasses.asdict(p) for p in pages],
    }
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp_path, path)
    logger.info("Cache saved: %d pages -> %s", len(pages), path)


def _load_cache(path: Path) -> list[RepoFile] | None:
    """Load crawled pages from a JSON cache file. Returns None on any error."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        version = data.get("schema_version")
        if version != _CACHE_SCHEMA_VERSION:
            logger.warning("Cache schema version %s is unsupported, re-crawling", version)
            return None
        pages = [RepoFile(**p) for p in data["pages"]]
        logger.info(
            "Loaded %d pages from cache (crawled %s)",
            len(pages),
            data.get("crawled_at", "unknown"),
        )
        return pages
    except (json.JSONDecodeError, KeyError, TypeError, OSError) as exc:
        logger.warning("Could not load cache from %s: %s", path, exc)
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl web docs and ingest into the RAG index")
    parser.add_argument(
        "--url", action="append", dest="urls", default=None,
        help="Start URL(s) to crawl (can repeat; defaults to grandMA2 help sites)",
    )
    parser.add_argument("--ref", default="ma2-help-docs", help="Repo reference label (default: ma2-help-docs)")
    parser.add_argument("--db", default=str(RAG_DB_PATH), help=f"SQLite database path (default: {RAG_DB_PATH})")
    parser.add_argument(
        "--provider", choices=["github", "zero"], default=None,
        help="Embedding provider (default: auto-detect from env vars)",
    )
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between requests in seconds (default: 0.5)")
    parser.add_argument("--max-pages", type=int, default=2000, help="Maximum pages to crawl (default: 2000)")
    parser.add_argument(
        "--batch-size", type=int, default=0,
        help="Max new pages to embed per run (0 = unlimited). Hash-dedup skips already-indexed pages.",
    )
    parser.add_argument(
        "--embed-delay",
        type=float,
        default=4.0,
        metavar="SECS",
        help="Seconds between embedding API calls (default: 4.0). Prevents per-minute rate limits.",
    )
    parser.add_argument(
        "--embed-batch-size",
        type=int,
        default=32,
        metavar="N",
        help="Texts per embedding API request (default: 32).",
    )
    parser.add_argument(
        "--cache-crawl",
        nargs="?",
        const=str(DEFAULT_CACHE_PATH),
        default=None,
        metavar="PATH",
        help=(
            f"Path to crawl cache JSON (default: {DEFAULT_CACHE_PATH}). "
            "Loads from cache if it exists, otherwise crawls and saves. "
            "Eliminates the ~5 min re-crawl on every daily batch run."
        ),
    )
    parser.add_argument(
        "--recrawl",
        action="store_true",
        help="Force a fresh crawl even if --cache-crawl file exists. Overwrites the cache.",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    if args.recrawl and not args.cache_crawl:
        logger.warning("--recrawl has no effect without --cache-crawl")

    urls = args.urls or DEFAULT_URLS

    # Ensure the database directory exists
    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    provider = make_provider(
        args.provider,
        inter_request_delay=args.embed_delay,
        batch_size=args.embed_batch_size,
    )
    logger.info("Using embedding provider: %s", provider.model_name)

    # --- Crawl or load from cache ---
    cache_path = Path(args.cache_crawl) if args.cache_crawl else None
    pages: list[RepoFile] = []
    crawled_fresh = False

    if cache_path and not args.recrawl:
        pages = _load_cache(cache_path) or []
        if pages:
            print(f"Using cached crawl ({len(pages)} pages) from {cache_path}")
        else:
            msg = "Cache could not be loaded" if cache_path.exists() else "No cache found"
            print(f"{msg} at {cache_path}. Crawling fresh...")

    if not pages:
        print(f"Crawling {len(urls)} start URL(s) (max {args.max_pages} pages, {args.delay}s delay)...")
        for u in urls:
            print(f"  - {u}")
        pages = crawl_web(urls, delay=args.delay, max_pages=args.max_pages)
        print(f"\nCrawled {len(pages)} pages")
        crawled_fresh = True

    # Deduplicate pages that share the same path (e.g. from different domains)
    before = len(pages)
    pages = _dedup_pages(pages)
    if len(pages) < before:
        print(f"Deduplicated: {before} -> {len(pages)} unique pages")

    if crawled_fresh and cache_path and pages:
        _save_cache(cache_path, pages, urls)
        print(f"Crawl cached to {cache_path}")

    if not pages:
        print("No pages to ingest.")
        return

    result = ingest(
        files=pages,
        repo_ref=args.ref,
        embedding_provider=provider,
        db_path=db_path,
        max_new=args.batch_size,
    )

    print("\nIngest complete:")
    print(f"  Provider:        {provider.model_name}")
    print(f"  Pages available: {len(pages)}")
    print(f"  Files processed: {result.files_processed}")
    print(f"  Files skipped:   {result.files_skipped}")
    print(f"  Chunks created:  {result.chunks_created}")


if __name__ == "__main__":
    main()

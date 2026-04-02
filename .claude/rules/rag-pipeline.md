---
title: RAG Pipeline Developer Conventions
description: How the crawl-chunk-embed-store-retrieve pipeline works and how to maintain it
version: 1.0.0
created: 2026-03-29T21:44:45Z
last_updated: 2026-03-29T21:44:45Z
---

# RAG Pipeline Developer Conventions

> Loaded when working on rag/, scripts/rag_ingest*.py, or the search_codebase tool.

---

## How it works

```
crawl → chunk → embed → store (SQLite) → query → rerank
```

- Python files: AST-aware chunking. Markdown: heading-based. Everything else: line-based.
- Embeddings: `GitHubModelsProvider` (requires `GITHUB_MODELS_TOKEN`) or `ZeroVectorProvider` (CI/testing stub, 1536-dim zero vectors).
- The `search_codebase` MCP tool queries the store; auto-detects token and falls back to text search when absent.
- Embedding API is rate-limited — 4s inter-request delay, batch_size=32 to stay within GitHub Models free tier.
- Dimension mismatch between old zero-vector chunks and new real embeddings is handled gracefully.

---

## Three indexed knowledge sources

| `repo_ref` | Script | Content |
|------------|--------|---------|
| `worktree` | `rag_ingest.py` | This server's Python source, tests, docs, configs |
| `ma2-help-docs` | `rag_ingest_web.py` | ~1,043 grandMA2 help pages from help.malighting.com |
| `mcp-sdk` | `rag_ingest_mcp_sdk.py` | Installed MCP SDK source (~110 files) |

---

## Pre-commit hook

`make install-hooks` installs `.githooks/pre-commit`, which runs zero-vector ingest on every commit (fast, no API calls). Real-vector rebuild must be run manually.

---

## Web doc batching

~1,043 grandMA2 help pages, embedded in nightly runs. The `--cache-crawl` flag saves the crawl to `rag/store/web_crawl_cache.json` — subsequent runs skip re-crawling.

**Web cache note:** cache schema version must match `_CACHE_SCHEMA_VERSION` in `scripts/rag_ingest_web.py` (currently v2). If the cache file has an older version (v1), it is invalidated automatically. Re-run with `--recrawl` to force a fresh crawl.

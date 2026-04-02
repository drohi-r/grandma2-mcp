---
title: Contributing to ma2-onPC-MCP
description: Development setup, branch model, code conventions, test requirements, and skill contribution guide
version: 1.0.0
created: 2026-04-01T00:00:00Z
last_updated: 2026-04-01T00:00:00Z
---

# Contributing to ma2-onPC-MCP

Thank you for your interest in contributing. This project controls physical lighting hardware on live production stages — please read this guide carefully before submitting changes.

---

## Reporting Bugs

Open an issue on GitHub. Include:

- A concise description of the problem
- The MA2 software version (e.g. `3.9.60.65` — readable via `list_system_variables`)
- The MCP tool name and parameters that triggered the issue
- The full error message or unexpected console response
- Whether the issue occurs on onPC, a physical console, or both

For **security vulnerabilities** (e.g. command injection, auth bypass), do **not** open a public issue. Email the maintainer directly and allow 14 days for a patch before disclosure.

---

## Development Setup

```bash
# 1. Clone and enter the repo
git clone https://github.com/thisis-romar/ma2-onPC-mcp
cd ma2-onPC-mcp

# 2. Install dependencies (requires uv)
uv sync

# 3. Copy environment template and fill in your values
cp .env.template .env
# Edit .env — set GMA_HOST, GMA_PORT, credentials

# 4. Install git hooks (runs zero-vector RAG ingest on every commit)
make install-hooks

# 5. Run the test suite
uv run python -m pytest -v

# 6. Start the MCP server
uv run python -m src.server
```

Python 3.12 is required (enforced by `.python-version`).

---

## Branch Model

```
main ← feature/your-feature-name
     ← fix/issue-description
     ← docs/what-you-documented
```

- Branch from `main`, open a PR back to `main`.
- Keep PRs focused — one logical change per PR.
- Do not push directly to `main`.

---

## Code Conventions

See `CLAUDE.md` for the full rules. Key points:

- **Command builders** in `src/commands/` must be pure functions — no network I/O, no imports from `src.server` or `src.navigation`.
- **New MCP tools** follow the decorator order: `@mcp.tool()` → `@require_scope(OAuthScope.X)` → `@_handle_errors`.
- **DESTRUCTIVE tools** must accept `confirm_destructive: bool = False` and gate on it. Never pass `confirm_destructive=True` internally.
- **All `.md` files** require YAML front matter (`title`, `description`, `version`, `created`, `last_updated`). See `.claude/rules/markdown-frontmatter.md`.
- **Test IDs** — use object ID 99 and executor 201 in tests to avoid collisions with real show data.

---

## Test Requirements

All PRs must pass the full test suite before review:

```bash
uv run python -m pytest -v
```

Current baseline: **2355 tests** (unit + live integration). Live integration tests are skipped by default (`tests/test_live_integration.py` requires `RUN_LIVE_TESTS=1`).

- Add tests for every new command builder in `tests/test_<feature>.py`.
- Add tests for every new MCP tool in `tests/test_tools.py` or a feature-specific file.
- Async tools use `@pytest.mark.asyncio`.
- Mock the Telnet client with `@patch("src.server.get_client")` + `AsyncMock`.
- Auth tests that test scope *blocking* must call `monkeypatch.delenv("GMA_AUTH_BYPASS", raising=False)` — `conftest.py` sets bypass=1 by default for all other tests.

---

## Skill Contribution Guide

Skills are instruction playbooks stored in `.claude/skills/<name>/SKILL.md`. They are injected as user messages by the orchestrator and host application — they are NOT executed code.

### Skill file format

```markdown
---
title: Skill Name
description: One-line description of what this skill teaches
version: 1.0.0
safety_scope: SAFE_READ   # SAFE_READ | SAFE_WRITE | DESTRUCTIVE
created: YYYY-MM-DDTHH:MM:SSZ
last_updated: YYYY-MM-DDTHH:MM:SSZ
---

# Skill Name

## Purpose
[What task or workflow this skill covers]

## Allowed Tools
[List of MCP tool names this skill authorises the agent to call]

## Steps
[Step-by-step instructions]
```

### Rules for skills

1. **`safety_scope` must be declared** — `SAFE_READ`, `SAFE_WRITE`, or `DESTRUCTIVE`.
2. **DESTRUCTIVE skills** must include an explicit "Human Approval Required" section explaining what irreversible actions the skill may trigger.
3. **Allowed tools list** must be exhaustive — only tools listed may be called during skill execution.
4. **No hardcoded show names, fixture IDs, or IP addresses** — skills must be show-agnostic.
5. **NEVER include `new_show` without `preserve_connectivity=True`** — see `.claude/rules/ma2-conventions.md`.

### Submitting a new skill

1. Create `.claude/skills/<slug>/SKILL.md` following the format above.
2. Update `tests/test_skill.py` count assertions to reflect the new total.
3. Open a PR with the skill file and the test update.

---

## No CLA Required

Contributions are accepted under the terms of the Apache License 2.0. By submitting a pull request, you confirm that you have the right to license your contribution under the Apache License 2.0 and that you do so. No separate Contributor License Agreement is required.

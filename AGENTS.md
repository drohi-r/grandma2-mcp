# AGENTS.md

## Purpose

Agent-facing working guide for this repo. This file is intentionally short.

For deeper repo rules, architecture details, and MA2-specific conventions, read [CLAUDE.md](./CLAUDE.md). Treat `CLAUDE.md` as the detailed rulebook and this file as the portable entry point.

## Project

- Product: `grandma2-mcp` / `ma2-agent`
- Domain: grandMA2 lighting console control via Telnet
- Main entrypoints:
- `uv run python -m src.server`
- `uv run python -m src.ui`

## Core Rules

- Keep network I/O out of command builders in `src/commands/`.
- Treat `src/commands/` as pure string builders with no side effects.
- Route Telnet and console interaction through the existing client/session layers.
- Keep destructive operations explicitly gated. Never auto-enable destructive confirmations.
- Prefer surgical fixes over broad refactors.

## Key Commands

```bash
uv sync
uv run python -m pytest -v
uv run python -m src.server
uv run python -m src.ui
```

## Key Paths

- `src/server.py`: MCP server surface
- `src/ui.py`: local browser UI
- `src/server_orchestration_tools.py`: agent/orchestration layer
- `src/telnet_client.py`: Telnet transport
- `src/commands/`: pure command builders
- `tests/`: verification

## When Editing

- Add or update tests with behavior changes.
- Preserve safety semantics and rights checks.
- Do not duplicate architecture guidance here; update `CLAUDE.md` if repo-wide deep guidance changes.

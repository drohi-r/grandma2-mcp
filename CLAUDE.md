---
title: Project Rules
description: Thin root conventions for MA2 Agent — architectural invariants, safety rules, and build commands
version: 1.0.0
created: 2026-03-01T23:37:51Z
last_updated: 2026-04-02T04:31:14Z
---

# Project Rules

## Project Identity

MCP server exposing **210 tools**, **13 resources**, **10 prompts**, and **44 skills** so AI assistants can control a grandMA2 lighting console via Telnet. Includes an **agent harness** (`src/agent/`) for autonomous multi-step execution with planning, policy enforcement, verification, and audit traces.

Central rule: **planner decides → skills carry instructions → subagents execute in isolation → tools take narrow actions → memory stores distilled checkpoints**.

All network I/O is isolated in `src/telnet_client.py`. Command builders in `src/commands/` are pure functions returning strings — no side effects.

---

## Architecture Quick Reference

| Module | Role |
|--------|------|
| `src/server.py` | FastMCP server — 176 tools + 13 MCP resources + 10 MCP prompts, safety gate |
| `src/server_orchestration_tools.py` | Registers 34 agentic tools (IDs 110-144, excluding 130) onto FastMCP |
| `src/telnet_client.py` | Async Telnet (telnetlib3), auth, send/receive, injection prevention |
| `src/session_manager.py` | Per-operator Telnet session pool (LRU, keepalive, auto-reconnect) |
| `src/credentials.py` | OAuth tier → console user credential resolver |
| `src/auth.py` | OAuth 2.1 scope enforcement (`@require_scope`, `@require_ma2_right`) |
| `src/navigation.py` | cd + list + prompt parsing orchestration |
| `src/prompt_parser.py` | Parse console prompts and `list` tabular output |
| `src/commands/` | 198 pure command-builder functions (206 exports incl. 8 constants), grouped by keyword type |
| `src/commands/helpers.py` | `quote_name()` wildcard spec, `_build_store_options()` flag assembly |
| `src/vocab.py` | 157 keyword vocab entries (90 function + 56 object + 5 helping + 6 special), `KeywordCategory`, `RiskTier`, `classify_token()` |
| `src/orchestrator.py` | Multi-agent task runner: hydration, risk-tier isolation, LTM; `_showfile_guard()` + `check_showfile()` |
| `src/task_decomposer.py` | Natural-language goal → ordered SubTask plan (rule-based) |
| `src/agent_memory.py` | WorkingMemory (ephemeral) + LongTermMemory (SQLite session log) + DecisionCheckpoint cache; showfile baseline tracking (`baseline_showfile`, `showfile_changed()`) |
| `src/console_state.py` | ConsoleStateSnapshot: hydrates all 19 show-memory gaps; `parse_showfile_from_listvar()` |
| `src/pool_name_index.py` | In-memory pool name/ID registry, zero-cost object resolution |
| `src/rights.py` | MA2 native rights enforcement, FeedbackClass, parse_telnet_feedback |
| `src/telemetry.py` | Per-tool invocation recorder: `tool_invocations` table, latency, risk tier |
| `src/skill.py` | `Skill` dataclass + `SkillRegistry`: versioned playbooks with lineage + filesystem skill fallback (`_load_filesystem_skill`, `_list_filesystem_skills`) |
| `src/skill_improver.py` | `SkillImprover`: repair suggestions + promotion candidates (read-only) |
| `src/tools.py` | Global GMA2 telnet client accessor — `get_client()` used by all tools |
| `src/categorization/` | ML-based tool categorization: K-Means clustering + auto-labeling |
| `rag/` | crawl → chunk → embed → store → retrieve pipeline |
| `.claude/rules/` | Scoped rule files (loaded on demand, not at startup) |
| `.claude/skills/` | Instruction modules (playbooks injected as user messages) |
| `src/agent/runtime.py` | Agent harness: goal → plan → execute → verify → trace |
| `src/agent/planner.py` | Rule-based domain planner, goal classification |
| `src/agent/executor.py` | Step executor with retries, confirmation flow |
| `src/agent/policy.py` | Plan-level governance (extends `src/vocab.py` safety) |
| `src/agent/verification.py` | Post-mutation state verification |
| `src/agent/memory.py` | SQLite workflow memory (conventions, recipes, run history) |
| `src/agent/trace.py` | Structured JSON execution traces |
| `src/agent/state.py` | Data models: RunContext, PlanStep, Checkpoint |
| `src/agent/workflows/` | Workflow templates: patch, preset, playback, common |

**Responsibility map:** see `doc/responsibility-map.md`.
**Tool tier classification:** see `doc/tool-surface-tiers.md`.
**MCP primitive audit:** see `doc/transcript-architecture-audit.md`.

---

## MCP Servers (project-level)

`.mcp.json` at the repo root registers the following servers for Claude Code CLI agents:

| Server | Command | Purpose |
|--------|---------|---------|
| `time` | `npx -y @modelcontextprotocol/server-time` | Accurate timestamps for `.md` front matter |

When writing or editing any `.md` file, call `get_current_time` first and use the returned `datetime` value for `created` / `last_updated` front matter fields.

---

## Development Commands

```bash
# Run all tests
uv run python -m pytest -v

# Run a subset
uv run python -m pytest tests/test_vocab.py

# Start MCP server
uv run python -m src.server

# Ingest repo into RAG (zero-vector, no API key — runs on every commit)
uv run python scripts/rag_ingest.py --root . --provider zero

# Install git hooks
make install-hooks
```

---

## Code Conventions

### Adding a new MCP tool
1. Add command builder in `src/commands/` — pure, returns `str`, no I/O.
2. Export from `src/commands/__init__.py`.
3. Register in `src/server.py` with `@mcp.tool()` and `@_handle_errors`.
4. Apply `@require_ma2_right(MA2Right.X)` — see `doc/ma2-rights-matrix.json`.
5. If DESTRUCTIVE, accept `confirm_destructive: bool = False` and gate on it.
6. Add tests in `tests/test_<feature>.py`.

### Adding a new MCP resource
- Use `@mcp.resource("ma2://category/name")` for static docs or URI-addressable state.
- Use `@mcp.resource("ma2://category/{param}")` for templated dynamic resources.
- Resources must be read-only — no console side-effects.

### Adding a new MCP prompt
- Use `@mcp.prompt()` for user-initiated workflow templates.
- Prompts accept arguments and may reference resources.
- Prompts must not themselves execute destructive operations — they orchestrate tools.

### Command builders
- Pure functions only — no imports from `src.telnet_client`, `src.navigation`, or `src.server`.
- Return raw grandMA2 command strings, e.g. `"Store Cue 1 Sequence 99 /merge"`.
- See `.claude/rules/ma2-conventions.md` for quoting, path, and timing rules.

### Tests
- Unit tests import command builders or vocab directly and assert on returned strings.
- No live console required; live tests are in `tests/test_live_integration.py` (skipped by default).
- Use `@pytest.mark.asyncio` for async tests.
- Current counts (2026-04-02): **2773 tests** (2631 passing, 142 skipped, 0 failed).

---

## Safety Rules

Three tiers enforced before any command reaches the console:

| Tier | Examples | Policy |
|------|----------|--------|
| `SAFE_READ` | `list`, `info`, `cd` | Always allowed |
| `SAFE_WRITE` | `go`, `at`, `clear`, `park` | Allowed in `standard` and `admin` modes |
| `DESTRUCTIVE` | `delete`, `store`, `copy`, `move`, `assign` | Blocked unless `confirm_destructive=True` |

- Any tool calling a `DESTRUCTIVE` command must accept `confirm_destructive: bool = False` and gate on it.
- Never pass `confirm_destructive=True` automatically.
- Line breaks (`\r`, `\n`) in command strings are rejected by the safety gate.
- **`new_show` without `/globalsettings` disables Telnet** — always keep `preserve_connectivity=True`.

---

## Agent Harness (`src/agent/`)

The agent harness enables autonomous multi-step execution on top of the existing MCP tools — no changes to command builders, telnet client, or navigation.

```
AgentRuntime (runtime.py)
  → DomainPlanner (planner.py) — rule-based goal → plan
  → PolicyEngine (policy.py) — plan-level governance
  → StepExecutor (executor.py) — tool dispatch + retries
  → Verifier (verification.py) — post-mutation checks
  → WorkflowMemory (memory.py) — SQLite operational memory
  → ExecutionTrace (trace.py) — JSON audit artifacts
```

MCP tools added: `run_agent_goal(goal, auto_confirm, dry_run)`, `plan_agent_goal(goal)`.

**Note:** `DomainPlanner` uses its own `PlanStep` model. Use `src/agent_bridge.py` (see below) to convert between `PlanStep` and main's `SubTask` for cross-system interop.

---

## Scoped Rules (loaded on demand)

These files are NOT loaded at startup. Reference them explicitly when working on the relevant area:

| File | When to load |
|------|-------------|
| `.claude/rules/ma2-conventions.md` | MA2 commands, quoting, navigation, macros, system vars |
| `.claude/rules/functional-domains.md` | Vocab domains, hardkey chains, executor priorities |
| `.claude/rules/openspace-layer.md` | Telemetry, skills, SkillImprover, LTM compression |
| `.claude/rules/rag-pipeline.md` | RAG ingest scripts, embedding providers, web docs |
| `.claude/rules/markdown-frontmatter.md` | Front matter requirements for new/edited .md files |

---

## What NOT To Do

- Do not add network I/O to command builders in `src/commands/` — they must stay pure.
- Do not import from `src.server` or `src.navigation` inside `src/commands/`.
- Do not hardcode `GMA_HOST`, `GMA_PORT`, or credentials — always read from env vars.
- Do not set `confirm_destructive=True` inside server tool implementations.
- Do not commit `rag/store/rag.db` or `rag/store/web_crawl_cache.json` — local artifacts.
- Do not edit `src/grandMA2_v3_9_telnet_keyword_vocabulary.json` manually.
- Do not call `new_show` with `preserve_connectivity=False` unless the user explicitly accepts Telnet will be disabled.
- Do not pass pre-quoted strings to `quote_name()` — pass raw names only.
- Do not call `ToolTelemetry.record_sync()` manually — `@_handle_errors` records automatically.
- Do not call `SkillRegistry.approve()` from tool implementations — only Tool 143 may.
- Do not auto-promote Skills from `SkillImprover` output — promotion is operator-initiated via Tool 141.
- Do not make MCP resources perform console side-effects — resources are read-only context.
- Do not put MA2 operating knowledge into tool docstrings — put it in `.claude/skills/` instead.

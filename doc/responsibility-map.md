---
title: Responsibility Map
description: File-by-file module role matrix with smell detection for the ma2-onPC-MCP architecture
version: 1.2.0
created: 2026-03-29T21:44:45Z
last_updated: 2026-03-31T23:56:48Z
---

# Responsibility Map

Every module in ma2-onPC-MCP has exactly one primary role. This map is the first
artifact in the Phase 1 architecture refactor based on the transcript's central rule:

> planner decides → skills carry instructions → subagents execute in isolation → tools take narrow actions → memory stores distilled checkpoints

---

## Role Taxonomy

| Role | Definition |
|------|-----------|
| **Planner** | Decides what to do, selects workers, merges results, blocks unsafe actions |
| **Skill / Instruction module** | Reusable know-how injected as user messages; no execution |
| **Subagent worker** | Isolated execution context; consumes high-token task, returns compressed summary |
| **Tool / Action** | Narrow callable that performs one side-effecting or read operation |
| **Memory / State** | Stores distilled checkpoints, session decisions, or object registry |
| **Transport / I/O** | Manages Telnet wire protocol, session lifecycle, auth |
| **Policy / Authorization** | Enforces rights, OAuth scopes, safety tiers |
| **MCP Surface** | Exposes primitives (tools, resources, prompts) to the MCP host |

---

## Module Role Matrix

| Module | Primary Role | Smells / Notes |
|--------|-------------|----------------|
| `src/server.py` | MCP Surface | ⚠ Also contains `_handle_errors` decorator (policy) and `_load_taxonomy_cached` (state) — acceptable boundary violations for FastMCP pattern |
| `src/server_orchestration_tools.py` | MCP Surface | Registers agentic tools 110-143; creates singletons for telemetry/skill/memory — thin wrapper, acceptable |
| `src/orchestrator.py` | Planner | ✅ Correct role — hydrates state, decomposes, executes, persists to LTM. ⚠ `_default_sub_agent` is in-process, not a true isolated context |
| `src/task_decomposer.py` | Planner support | ✅ Pure rule-based NL → SubTask. ⚠ Only 3 hardcoded rules + fallback — narrow planning capability |
| `src/commands/*.py` | Tool | ✅ Pure functions, no I/O. No smells. |
| `src/commands/helpers.py` | Tool | ✅ Pure helpers (`quote_name`, `_build_options`). No smells. |
| `src/commands/constants.py` | Tool | ✅ Pure constants (`PRESET_TYPES`, `HARDKEY_CHAINS`, etc.). No smells. |
| `src/telnet_client.py` | Transport / I/O | ✅ Correct role — async Telnet, auth, injection prevention. No smells. |
| `src/session_manager.py` | Transport / I/O | ✅ LRU session pool, keepalive, auto-reconnect. No smells. |
| `src/navigation.py` | Transport / I/O | ✅ cd + list orchestration. No smells. |
| `src/prompt_parser.py` | Transport / I/O | ✅ Parses console output. No smells. |
| `src/auth.py` | Policy / Authorization | ✅ OAuth 2.1 scope enforcement. No smells. |
| `src/rights.py` | Policy / Authorization | ✅ MA2 native rights, FeedbackClass, parse_telnet_feedback. No smells. |
| `src/credentials.py` | Policy / Authorization | ✅ OAuth tier → credential resolver. No smells. |
| `src/vocab.py` | Policy / Authorization | ✅ Keyword safety classification (`classify_token`, `RiskTier`). No smells. |
| `src/agent_memory.py` | Memory / State | ✅ WorkingMemory + LongTermMemory. ⚠ Session snapshots now v2 compressed (fixed in audit); `wm.to_dict()` still available for legacy compat |
| `src/console_state.py` | Memory / State | ✅ ConsoleStateSnapshot hydrates 19 show-memory gaps. ⚠ Expensive — some hydrations could be lazy-computed on demand |
| `src/pool_name_index.py` | Memory / State | ✅ In-memory name/ID registry. No smells. |
| `src/telemetry.py` | Memory / State | ✅ Invocation recorder. No smells. |
| `src/skill.py` | Skill / Instruction module | ✅ Correct role — Skill dataclass + SkillRegistry. `as_user_message()` provides injection payload. ⚠ No file-reference / progressive disclosure yet |
| `src/skill_improver.py` | Skill / Instruction module | ✅ Read-only analysis. No smells. |
| `src/categorization/` | Tool | ✅ K-Means clustering + taxonomy. Used by `suggest_tool_for_task`. No smells. |
| `rag/ingest/` | Transport / I/O | ✅ Crawl, chunk, embed pipeline. No smells. |
| `rag/retrieve/` | Tool | ✅ Cosine similarity + rerank. No smells. |
| `rag/store/sqlite.py` | Memory / State | ✅ SQLite vector store. No smells. |
| `CLAUDE.md` | Skill / Instruction module | ✅ Now thin root (~160 lines). Detail moved to `.claude/rules/`. |
| `.claude/rules/*.md` | Skill / Instruction module | ✅ Scoped rules, loaded on demand. |
| `.claude/skills/*/SKILL.md` | Skill / Instruction module | ✅ Reusable playbooks for injection as user messages. |

---

## Detected Smells

### S1 — Subagent is in-process (Critical)
**Location:** `src/orchestrator.py:144` — `_default_sub_agent()`
**Problem:** Executes tool calls in the same Python process. No fresh LLM context window.
**Fix:** Wire a real subagent spawner via `sub_agent_fn` parameter. Requires Claude API / Agent SDK — out of MCP server scope. Document pattern for integrators.

### S2 — Planner sees all 176 tools (Medium)
**Location:** `src/server.py` — all tools always registered at startup
**Problem:** All 176 tools consume instruction budget in every session.
**Fix:** Use `suggest_tool_for_task` for pre-session retrieval. Long-term: FastMCP dynamic tool registration. See `doc/tool-surface-tiers.md`.

### S3 — TaskDecomposer has 3 hardcoded rules (Low)
**Location:** `src/task_decomposer.py:94–229`
**Problem:** Only wash_look, blackout_sequence, group_preset_library + generic fallback.
**Fix:** Add more rules as additional MA2 workflows are validated. Each rule should map to one of the three standard workflows: Inspect / Plan / Execute.

### S4 — No progressive disclosure in skills (Low)
**Location:** `src/skill.py` — `body` stored inline
**Problem:** No file-reference mechanism; large playbooks are loaded fully even when partial.
**Fix:** Add `references: list[str]` field to Skill dataclass. Load referenced files lazily.

### S5 — server.py instructions= block is stale (Medium)
**Location:** `src/server.py:371` — FastMCP `instructions=` argument
**Problem:** Lists ~28 tools from an older version; does not reflect 176 current tools.
**Fix:** Replace with a compact summary pointing to `suggest_tool_for_task` for discovery. See Phase 3 in the refactor plan.

---

## Standard Workflows (Planner Level)

Every orchestrated request should map to exactly one of these three workflows:

| Workflow | Operations | Output |
|----------|-----------|--------|
| **Inspect** | SAFE_READ tools only; query + summarize; no mutation | State summary + findings |
| **Plan** | Inspect + preflight rights check + proposed changes; no mutation | Change plan + safety assessment |
| **Execute** | Run approved commands; verify post-state; emit audit summary | Execution result + verification |

`TaskDecomposer` rules should be extended to classify each subtask into one of these workflows.

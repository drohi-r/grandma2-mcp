---
title: OpenSpace Framework Comparison Audit
description: Feature-by-feature comparison of MA2 Agent against the OpenSpace self-evolving skill framework, with gap analysis and prioritised roadmap
version: 1.5.0
created: 2026-03-29T16:59:35Z
last_updated: 2026-04-02T04:16:48Z
---

# OpenSpace Framework Comparison Audit

## Context

This audit compares **MA2 Agent** against the **OpenSpace** self-evolving skill framework.
The goal is to produce an honest, evidence-based gap analysis — not a marketing comparison — so that
any decision to close the gap is grounded in what the code actually does today.

All findings were verified directly against the repository source as of 2026-03-29
(HEAD commit `fdfea00`, branch `main`).

---

## 1. What Each System Is

### MA2 Agent

An MCP server that exposes **210 tools** so AI assistants can control a grandMA2 lighting console
via Telnet. Its own README describes it as:

> "an agent-ready, syntax-aware Telnet control server for MA Lighting grandMA2 consoles"
> that "bridges grandMA2's command line engine with modern AI agents through the Model Context
> Protocol (MCP), enabling deterministic console programming, structured command generation,
> and safe remote execution."

That single sentence is the key to the audit. *Deterministic control server* vs.
*autonomous self-evolving skill framework* — these are categorically different things.

### OpenSpace

A framework for autonomous, self-improving AI agents that:
- monitors its own task executions,
- captures successful run patterns as reusable versioned "Skills",
- auto-repairs broken Skills (AutoFix),
- mines cross-task patterns to improve future planning (AutoLearn),
- exposes a community registry for sharing Skills across teams.

The core claim is that agents improve themselves without human intervention.

---

## 2. Feature-by-Feature Comparison Table

| OpenSpace Capability | Present in MA2 Agent? | Evidence / Location |
|---|---|---|
| Self-evolution engine | ❌ Absent | No execution-monitoring hooks; no mutation logic anywhere in `src/` |
| AutoFix (broken skills) | ❌ Absent | Safety tiers prevent harm but don't auto-repair |
| AutoImprove (capture success) | ❌ Absent | No run-to-skill promotion pipeline |
| AutoLearn (cross-task patterns) | ❌ Absent | No cross-run mining or synthesis |
| Skill artifact model (versioned) | ❌ Absent | No `Skill` object; no version/lineage metadata. Closest analog: `SubTask` in `src/task_decomposer.py` |
| Skill evolution dashboard | ❌ Absent | No React dashboard |
| CloudSkill community / registry | ❌ Absent | RAG store is local SQLite only (`rag/store/rag.db`) |
| Token efficiency tracking | ⚠️ Partial | Session-level `token_spend` / `charge_tokens()` / `token_report()` in `WorkingMemory` (`src/agent_memory.py:96,210–220`). Per-MCP-tool invocation instrumentation is absent. |
| MCP integration | ✅ Excellent | 210 tools (176 in `server.py` + 34 in `src/server_orchestration_tools.py`), stdio transport, Claude Desktop + VS Code configs |
| Python 3.12 | ✅ Yes | `.python-version` file |
| MIT license | ⚠️ No — Apache 2.0 | `LICENSE` file |
| Benchmark / metrics pipeline | ❌ Absent | 2773 tests exist but no performance-benchmark loop |

---

## 3. Where MA2 Agent Is Genuinely Strong

These are areas the OpenSpace framework design does not address, where this repo outperforms
OpenSpace's stated architecture.

### 3.1 Safety architecture — the strongest differentiator

Three-tier risk model enforced before any command reaches the console:

| Tier | Examples | Policy |
|---|---|---|
| `SAFE_READ` | `list`, `info`, `cd` | Always allowed |
| `SAFE_WRITE` | `go`, `at`, `clear`, `park` | Allowed in `standard` and `admin` modes |
| `DESTRUCTIVE` | `delete`, `store`, `copy`, `assign` | Blocked unless `confirm_destructive=True` |

Command injection prevention, `@_handle_errors` wrapper (`src/server.py:477–494`), and a
157-keyword vocabulary classifier (`src/vocab.py`) back this up. OpenSpace mentions none of
this. For a system controlling live physical hardware, this safety model is more mature.

### 3.2 MCP tool quality

210 tools across 15 server categories plus a 34-tool orchestration layer, pure-function command builders in `src/commands/`,
structured schemas, VS Code extension, Claude Desktop config. This is production-grade MCP work.

### 3.3 RAG pipeline

AST-aware chunking, cosine-similarity retrieval, re-ranking, and a `search_codebase` tool
exposed through MCP. Three indexed knowledge sources:

| `repo_ref` | Content |
|---|---|
| `worktree` | This server's Python source, tests, docs, configs |
| `ma2-help-docs` | ~1,043 grandMA2 help pages |
| `mcp-sdk` | Installed MCP SDK source |

OpenSpace has no equivalent documentation retrieval layer.

### 3.4 ML tool discovery

K-Means clustering of tool embeddings with `suggest_tool_for_task`
(`src/categorization/clustering.py`) partially mirrors AutoLearn's intent, applied to tool
selection rather than skill creation.

### 3.5 Orchestration layer with rights enforcement

`src/orchestrator.py` provides a multi-agent task runner with full console-state hydration,
MA2 native rights validation, `FeedbackClass` classification (`PASS_ALLOWED`, `PASS_DENIED`,
`FAILED_OPEN`, `FAILED_CLOSED`), and a `_preflight_guard` (`lines 69–138`) that enforces five
checks before any DESTRUCTIVE step. OpenSpace has no equivalent hardware-safety layer.

### 3.6 Test coverage

2355 unit tests + live integration tests. OpenSpace's repository shows no equivalent
test infrastructure.

---

## 4. Where the Repo Diverges Most Severely from OpenSpace

### 4.1 No self-evolution engine

OpenSpace's core claim is that agents monitor their own execution and improve autonomously.
The architecture here — MCP Server → Navigation → Command Builders → Telnet Client — is a
static pipeline. Nothing writes back to improve tools at runtime.

### 4.2 No first-class Skill entity

OpenSpace defines skills as versioned, lineage-tracked artifacts with quality metrics.
This repo has tools (static functions) and command builders (pure string generators).
`SubTask` in `src/task_decomposer.py` is the closest analog but lacks versioning, lineage,
quality scoring, or any runtime mutability.

### 4.3 No per-tool execution telemetry store

OpenSpace requires a persistent log of every run: inputs, outputs, latency, token cost,
success/failure classification. `WorkingMemory` tracks `token_spend` per orchestration
session (`src/agent_memory.py:96`), and `LongTermMemory` persists sessions to SQLite
(`rag/store/agent_memory.db`). However, individual MCP tool invocations are not instrumented.
The `@_handle_errors` decorator (`src/server.py:477`) is the natural hook point — it wraps
every tool call — but currently only catches exceptions rather than recording metrics.

### 4.4 No shared community layer

The RAG pipeline uses a local SQLite file. There is no publish / download / access-control
skill registry and no integration with any external skill community.

---

## 5. Prioritised Roadmap to Close the Gap

The gap is real but bridgeable in layers. Priority is ordered by prerequisite dependency,
not business value.

### Layer 1 — Telemetry foundation (prerequisite for all subsequent layers)

Wrap every tool call in `src/server.py` via an extension to `@_handle_errors` (or a new
`@_instrument` decorator applied after it) that persists to a `tool_invocations` table in
`rag/store/agent_memory.db`:

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `ts` | REAL | `time.time()` |
| `tool_name` | TEXT | |
| `inputs_json` | TEXT | Serialised kwargs |
| `output_preview` | TEXT | First 500 chars of return value |
| `error_class` | TEXT | NULL on success |
| `latency_ms` | REAL | |
| `risk_tier` | TEXT | `SAFE_READ` / `SAFE_WRITE` / `DESTRUCTIVE` |
| `operator` | TEXT | From session context |
| `session_id` | TEXT | FK → `sessions` table |

Without this table, AutoFix / AutoImprove / AutoLearn have nothing to learn from.

### Layer 2 — Skill artifact model

Introduce a `Skill` dataclass distinct from raw MCP tools. Suggested fields:

```python
@dataclass
class Skill:
    id: str                     # UUID
    version: int                # monotonic
    parent_version: int | None  # lineage
    name: str
    description: str
    body: str                   # Markdown playbook
    quality_score: float        # 0.0–1.0, from telemetry
    safety_scope: RiskTier      # max tier this skill may invoke
    applicable_context: str     # free-text hint for retrieval
    created_at: float
    updated_at: float
```

Store in a new `skills` table in `agent_memory.db`. The RAG chunker already handles markdown
artifacts — pivot it to serve Skills alongside source code chunks.

### Layer 3 — Controlled improvement loop (with physical-control gates)

After successful runs (telemetry `error_class IS NULL`, `quality_score > 0.8`):
- Propose reusable playbooks derived from completed `TaskPlan` instances.

After repeated failures of the same `SubTask` type:
- Generate candidate repairs and surface them to the operator for review.

**Critical domain constraint**: any Skill touching `DESTRUCTIVE` tier commands must require
explicit human approval before promotion. Never auto-promote Skills that can issue `delete`,
`store`, or `assign` commands. This constraint does not exist in vanilla OpenSpace — it must
be designed in from the start for a live-hardware control system.

### Layer 4 — Metrics, lineage graph, optional sharing

- Benchmark dashboard (latency, error rates, quality score trends per skill)
- Skill ancestry visualisation (parent → child lineage graph)
- Optional: signed skill registry for cross-show or cross-operator sharing

This is the lowest priority relative to Layers 1–3.

---

## 6. Domain-Specific Safety Constraint OpenSpace Never Raises

In OpenSpace, a broken skill failing to fix itself wastes tokens.
In MA2 Agent, a broken skill or an autonomous repair gone wrong can:
- corrupt a live show mid-performance,
- issue `delete` or `store` commands that overwrite programming,
- sever the Telnet connection by inadvertently calling `new_show` without `/globalsettings`.

Any learning loop must be strictly sandboxed from live execution until human-approved.
This constraint should shape every architectural decision in Layers 1–3 above.

---

## 7. Current Implementation Status (2026-03-31)

A codebase audit against the four-layer roadmap revealed the repo is at **Layer 1.5–2.0**,
not Layer 0 as originally stated. Three structural bugs were found and fixed.

### Layer Status

| Layer | Status | Notes |
|---|---|---|
| **Layer 1 — Telemetry** | ✅ Fixed | `tool_invocations` table exists; `session_id` ContextVar linkage added (`src/context.py`); singleton isolation fixed |
| **Layer 2 — Skill artifact** | ✅ Complete | `Skill` dataclass, `SkillRegistry`, versioning, lineage, approval workflow all implemented. Filesystem skill fallback (`_load_filesystem_skill`, `_list_filesystem_skills`) wires `.claude/skills/` into the registry. |
| **Layer 3 — Improvement loop** | ⚠️ Partial | `SkillImprover` surfaces suggestions; Tool 141 handles promotion (manual, not autonomous). No auto-repair loop. Showfile change detection implemented: Tool 144 (`assert_showfile_unchanged`), `WorkingMemory.showfile_changed()`, and `parse_showfile_from_listvar()` guard against mid-session show switches. |
| **Layer 4 — Metrics/UI** | ❌ Absent | No dashboard, no community registry, no lineage visualisation |

### Known Bugs Fixed (2026-03-31)

**Bug 1 — No `session_id` in telemetry decorator** (`src/server.py`)

Every tool call recorded `session_id=""` (empty default), breaking the
tool-invocation → session linkage that `SkillImprover` depends on.

**Fix:** Added `src/context.py` with `_current_session_id: ContextVar[str]`.
`Orchestrator._run_sequential` and `_run_parallel` now set it before each SubTask;
`@_handle_errors` reads it when writing to `tool_invocations`. The ContextVar is
async-safe (isolated per asyncio Task).

**Bug 2 — Singleton isolation** (`src/server_orchestration_tools.py`)

Tools 138–143 created `ToolTelemetry()` at registration time — a separate SQLite
connection from the one `@_handle_errors` writes to. `get_tool_metrics` returned
0 rows even when invocations existed.

**Fix:** Tools 138–143 now import the singleton via `_get_telemetry()` from `src/server.py`,
guaranteeing both the reader (Tool 138) and the writer (`@_handle_errors`) share one DB.

**Bug 3 — Duplicate checkpoint methods** (`src/agent_memory.py`)

`WorkingMemory.add_checkpoint()` and `fresh_checkpoint()` were each defined twice.
Python MRO silently used the second definition; the first was unreachable dead code.

**Fix:** Removed the first (dead) pair. The surviving implementation uses keyword
args and returns a `DecisionCheckpoint` object — the correct API used everywhere.

---

## 8. Summary Verdict

| Dimension | Assessment |
|---|---|
| Architectural match to OpenSpace | ~30–35% overlap (Layer 1+2 complete, Layer 3 partial) |
| Production readiness as MCP control server | High — suitable for live use |
| Safety model vs. OpenSpace | Superior (hardware-aware, three-tier, rights-native) |
| Telemetry feedback loop | ✅ Fixed — session_id flows from orchestrator → tool call → DB row |
| Improvement loop | ⚠️ Partial — suggestions generated; promotion is manual (by design) |
| Next milestone | Layer 3 auto-repair: apply `RepairSuggestion` hints after operator review |

MA2 Agent is an **execution/control plane with an emerging learning layer**.
OpenSpace is a **learning/evolution plane**. The repo has closed the telemetry and
skill-artifact gaps. The remaining distance is the autonomous improvement loop —
intentionally gated behind human approval for a live-hardware control system.

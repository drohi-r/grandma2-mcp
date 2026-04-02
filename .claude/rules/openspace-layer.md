---
title: OpenSpace Layer Developer Conventions
description: Telemetry, skill lifecycle, DESTRUCTIVE approval, SkillImprover, and context management rules
version: 1.2.2
created: 2026-03-29T21:44:45Z
last_updated: 2026-03-31T21:54:06Z
---

# OpenSpace Layer Developer Conventions

> Loaded when working on src/telemetry.py, src/skill.py, src/skill_improver.py, src/agent_memory.py, or src/orchestrator.py.

---

## Context Management

**Subagent isolation** — `Orchestrator._default_sub_agent()` (`src/orchestrator.py:144`)
executes tool calls in-process. It is NOT a fresh LLM context window. True context
isolation requires an LLM client (Claude API / Agent SDK). The `sub_agent_fn` parameter
in `Orchestrator.__init__` is the correct injection point for integrators who want to
wire in a real subagent spawner.

**LTM session compression** — `LongTermMemory.save_session()` stores a compressed
decision summary (`_v: 2` format). Fixture detail is already in `fixture_history` table;
the snapshot retains only: `completed_steps`, `failed_steps`, `token_spend`,
`park_ledger`, `console_state_summary`, `fixture_summary` (names + values only).
`recall_session()` handles both v1 (legacy full blob) and v2 transparently.

**Skill injection** — `Skill.as_user_message()` returns the skill body formatted as a
user message (`[Skill: {name} v{version}]\n{body}`). Use `SkillRegistry.get_usable(id)`
as a safe combined fetch + usability guard — returns `None` for missing or un-approved
DESTRUCTIVE skills. The MCP server cannot insert messages into the host's conversation;
the formatted payload must be injected by the orchestrator or the host application.

**Tool retrieval** — `suggest_tool_for_task` defaults to `prefer_semantic=True`: when
`GITHUB_MODELS_TOKEN` is set it automatically uses embedding cosine similarity; without
a token it uses keyword overlap and adds a `warning` field to the response.

---

## Telemetry (`src/telemetry.py`)

Every MCP tool call is recorded automatically via the `@_handle_errors` decorator in
`src/server.py`. No per-tool changes are needed.

| Env var | Default | Effect |
|---|---|---|
| `GMA_TELEMETRY=1` | enabled | Records every invocation to `tool_invocations` table |
| `GMA_TELEMETRY=0` | — | Disables recording; use in unit tests that do not need a DB write |

**Risk-tier inference** (`infer_risk_tier(func)`) runs once at decoration time:

1. `confirm_destructive` in signature → `DESTRUCTIVE`
2. Name starts with `list_`, `get_`, `discover_`, `search_`, `info_`, `suggest_`, `assert_`, `recall_` → `SAFE_READ`
3. Anything else → `SAFE_WRITE`

Do not call `ToolTelemetry.record_sync()` directly. Do not add telemetry to `src/commands/`.

---

## Skill lifecycle (`src/skill.py`)

**Naming** — always use `SkillRegistry.promote_from_session()`, which calls `_slugify()` internally. Pass the raw human name; do not pre-slugify.

**Versioning** — use `SkillRegistry.bump_version(skill_id, body=...)` to create a new version. Never edit a skill's `body` in-place.

**Lineage** — `SkillRegistry.get_lineage(skill_id)` returns the full ancestor chain oldest-first.

**Quality score** — 0.0–1.0 from `steps_done / (steps_done + steps_failed)`. Update via `SkillRegistry.update_quality(skill_id, score)`.

---

## DESTRUCTIVE skill approval workflow

| Step | Who | How |
|---|---|---|
| Skill promoted with `safety_scope="DESTRUCTIVE"` | Agent or operator | `approved` auto-set to `False` |
| Skill surfaces in suggestions / registry | Agent | `is_usable()` returns `False` |
| Human inspects body and lineage | Operator | `get_skill(skill_id)` via Tool 140 |
| Human approves | Operator | `approve_skill(skill_id)` — Tool 143, `OAuthScope.SYSTEM_ADMIN` |

**Rules:**
- `promote_from_session(safety_scope="DESTRUCTIVE")` always produces `approved=False`.
- `bump_version()` on a DESTRUCTIVE skill sets `approved=False` on the new version.
- Never call `SkillRegistry.approve()` from tool implementations — only Tool 143 may.

---

## SkillImprover (`src/skill_improver.py`)

`SkillImprover` is **read-only**. It never writes to the skill registry.

| Method | Returns | Purpose |
|---|---|---|
| `identify_failure_patterns(days, min_failures)` | `list[RepairSuggestion]` | Tools failing ≥ N times |
| `identify_promotion_candidates(min_quality)` | `list[PromotionCandidate]` | Sessions ready to promote |
| `quality_score_for_session(session_id)` | `float` | Compute quality before promoting |

Exposed as MCP Tool 142. Do not add autonomous promotion logic to `SkillImprover`.
Promotion is always operator-initiated via Tool 141.

---

## DecisionCheckpoint (`src/agent_memory.py`)

`DecisionCheckpoint` is a lightweight cache record for replaying known-good decisions without re-querying the console.

```python
@dataclass
class DecisionCheckpoint:
    fault: str              # fault label (e.g. "rights_denied_store", "cue_audit_seq_1")
    query: str              # MA2 command / tool call that produced the finding
    observed_at: float      # Unix timestamp (time.time())
    fresh_for_seconds: int  # seconds before the checkpoint should be replayed (no default)
    replay: str             # command / tool call to re-run to refresh the finding
    confidence: str = "medium"  # "high" | "medium" | "low"
```

**Key method:** `is_fresh()` — returns `True` if `time.time() - observed_at < fresh_for_seconds`.

**`WorkingMemory` integration:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `add_checkpoint` | `(fault, query, fresh_for_seconds=30, replay="", confidence="medium")` | Record a new checkpoint; appends to `checkpoints` list |
| `fresh_checkpoint` | `(fault) -> DecisionCheckpoint \| None` | Return the most recent fresh checkpoint for a fault, or `None` |

**Usage pattern:**
- Call `working_memory.add_checkpoint(fault, query, fresh_for_seconds=60)` after a successful console read.
- Before re-querying, call `working_memory.fresh_checkpoint(fault)` — returns the `DecisionCheckpoint` or `None` if stale/absent.
- Never cache DESTRUCTIVE decisions — checkpoints are for read/resolve results only.

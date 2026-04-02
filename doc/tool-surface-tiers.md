---
title: Tool Surface Tiers
description: Classification of the 210-tool MCP surface into planner-visible tiers A/B/C to manage context budget
version: 1.2.0
created: 2026-03-29T21:44:45Z
last_updated: 2026-04-02T04:16:48Z
---

# Tool Surface Tiers

The transcript's core observation: **210 tools always visible to the parent planner is a context budget risk**. This document classifies the current tool surface into three tiers to guide future dynamic tool loading.

---

## Tier Definitions

| Tier | Visibility | Selection Criterion |
|------|-----------|---------------------|
| **A — Always exposed** | Planner sees at startup | Inspect entrypoints, safety reads, orchestration primitives |
| **B — Retrievable / worker-only** | Retrieved via `suggest_tool_for_task` | Specialized programming, batch helpers, niche transforms |
| **C — Internal only** | Not exposed to parent planner | Builder helpers, low-level primitives, state hydration internals |

Target: Tier A ≤ 20 tools visible to the planner by default.

---

## Tier A — Always Exposed (Planner Core)

These tools give the planner situational awareness and safe entrypoints. They cover the **Inspect** workflow.

| Tool | Category | Justification |
|------|---------|--------------|
| `navigate_console` | Navigation | Core tree navigation |
| `get_console_location` | Navigation | Orientation without mutation |
| `list_console_destination` | Navigation | List objects at path |
| `get_object_info` | Queries | Inspect any object |
| `query_object_list` | Queries | List cues, groups, presets |
| `list_system_variables` | Queries | Read all 26 system vars |
| `get_variable` | Queries | Read one system var |
| `discover_object_names` | Queries | Pool name discovery for wildcards |
| `search_codebase` | Search | Semantic search over docs + source |
| `suggest_tool_for_task` | Meta | Dynamic tool retrieval |
| `list_skills` | OpenSpace | Skill registry |
| `get_skill` | OpenSpace | Inspect skill body + lineage |
| `get_tool_metrics` | OpenSpace | Tool failure/latency telemetry |
| `get_improvement_suggestions` | OpenSpace | SkillImprover read-only |
| `run_agent_goal` | Orchestration | Top-level planner entrypoint for the agent harness |
| `hydrate_console_state` | Orchestration | Snapshot all 19 memory gaps |
| `send_raw_command` | Escape hatch | Direct MA2 command (safety-gated) |
| `playback_action` | Playback | go/pause/goto on executors |
| `set_intensity` | Lighting | Dimmer control |
| `clear_programmer` | Programmer | Reset programmer state |
| `get_executor_state` | Executor Inspection | Read all 32 fields of one executor via List Executor page.id |
| `scan_page_executor_layout` | Executor Inspection | Map occupied slots on a page — required before width expansion |
| `discover_fixture_type_attributes` | Executor Inspection | Attribute names for a fixture type via EditSetup tree navigation |

---

## Tier B — Retrievable / Worker-Only

Retrieved via `suggest_tool_for_task` or explicitly requested. These tools are used inside specific subtask workers.

### Programming / Store
- `store_current_cue`, `store_new_preset`, `store_object`
- `copy_or_move_object`, `delete_object`, `remove_content`
- `create_fixture_group`, `store_matricks_preset`

### Attribute Control
- `set_attribute`, `apply_preset`, `apply_appearance`
- `set_color_rgb`, `set_color_hsb`, `set_color_hex`
- `manage_matricks`, `manage_effects`

### Assignment & Layout
- `assign_object`, `assign_delay`, `assign_fade`, `assign_function`
- `label_or_appearance`, `edit_object`, `assign_to_layout`

### Sequence & Cue Management
- `execute_sequence`, `create_sequence`, `create_cue`
- `goto_cue`, `go_back`, `release_executor`
- `create_executor_page`, `assign_temp_fader`

### Fixture & Patch
- `patch_fixture`, `select_fixture_type`
- `park_fixture`, `unpark_fixture`
- `select_fixtures`, `add_to_selection`

### Variables & Scripting
- `manage_variable`, `run_macro`, `set_user_variable`
- `create_macro`, `edit_macro_line`

### Show Management
- `save_show`, `load_show`, `new_show`
- `export_object`, `import_object`

### Library Generation
- `create_filter_library`, `create_matricks_library`
- `browse_effect_library`, `browse_macro_library`

### User Management (Tier 5 / Admin)
- `list_console_users`, `create_user`, `delete_user`
- `set_user_password`, `set_user_rights`

### OpenSpace Mutating
- `promote_session_to_skill`, `approve_skill`
- `recall_session_memory`, `list_session_memory`

---

## Tier C — Internal Only

Not exposed to the parent planner. Used internally by workers or tool implementations.

- `scan_console_indexes` — batch scan helper used by `hydrate_console_state`
- `_load_taxonomy_cached` — internal taxonomy cache
- All command builder functions in `src/commands/` — pure function primitives
- `_build_options`, `quote_name` — helper utilities
- Session pool internals (`src/session_manager.py`)
- RAG pipeline internals (`rag/ingest/`, `rag/retrieve/`)

---

## Proposed Worker Catalog

Six narrow workers, each with explicit tool access:

| Worker | Allowed Tools (Tier A + selected B) | Output Schema |
|--------|-------------------------------------|---------------|
| `show-file-analyzer` | `list_console_destination`, `get_object_info`, `query_object_list`, `scan_console_indexes` | `{summary, findings[], confidence}` |
| `cue-list-auditor` | `query_object_list`, `get_object_info`, `list_system_variables` | `{cue_count, gaps[], warnings[]}` |
| `telnet-feedback-investigator` | `send_raw_command`, `get_variable`, `list_system_variables` | `{fault_class, finding, recommended_actions[]}` |
| `console-state-hydrator` | `hydrate_console_state`, `list_system_variables` | ConsoleStateSnapshot |
| `object-resolution-worker` | `discover_object_names`, `query_object_list`, `get_object_info` | `{resolved_id, resolved_name, pool}` |
| `safety-preflight-checker` | `list_system_variables`, `get_variable`, SAFE_READ tools only | `{rights_level, blind_mode, park_count, verdict}` |

All workers return a **fixed envelope**:
```json
{
  "summary": "One-sentence conclusion",
  "findings": [{"kind": "...", "detail": "..."}],
  "recommended_actions": ["..."],
  "state_changes": [],
  "confidence": "high | medium | low"
}
```

---

## MCP Primitive Classification

For the 210-tool surface, the question "is this really a tool?" has three answers:

| If it… | Should be |
|--------|-----------|
| Returns stable reference data (docs, rights matrix, vocab) | **Resource** |
| Defines a user-initiated workflow template | **Prompt** |
| Performs an action or live read against the console | **Tool** |

See `doc/transcript-architecture-audit.md` §3 for the full resource/prompt gap analysis.

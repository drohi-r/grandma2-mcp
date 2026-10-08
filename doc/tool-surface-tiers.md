---
title: Tool Surface Tiers
description: Tool profiles (GMA_TOOL_PROFILE) that control how many of the MCP tools a client sees
version: 2.0.0
created: 2026-03-29T21:44:45Z
last_updated: 2026-10-07T22:25:16Z
---

# Tool Surface Tiers

Clients that load every tool schema up front pay roughly 40k tokens for the full
237-tool surface. `GMA_TOOL_PROFILE` picks a curated subset:

| Profile | Tools | What it covers |
|---------|-------|----------------|
| `core` | 28 | Inspect (navigate/list/info/variables), the agent harness (`plan_agent_goal`, `run_agent_goal`), escape hatches (`send_raw_command`, `run_command_batch`, `answer_console_popup`, `disconnect_console`), basic playback, `save_show`, `undo_last_action`, `diagnose_no_output` |
| `standard` | 104 | `core` + day-to-day programming: store/update/delete/label, selection and values, executors and playback, pools/effects/MAtricks, patch and fixture types, timecode, macros/Lua, show files, analysis and divergence checks |
| `full` (default) | 237 | Everything, including overlapping and niche tools |

The source of truth is [`src/tool_profiles.py`](../src/tool_profiles.py); the
`ma2://docs/tool-surface-tiers` resource renders the exact per-profile tool
lists from it, so this page only describes the intent.

## Rules

- Smaller profiles include **one tool per overlap cluster** — e.g.
  `get_executor_state` (not `get_executor_status` / `get_executor_detail`),
  `check_pool_slot_availability` (not `check_pool_availability`), `diff_cues`
  (not `compare_cue_values`), `master_control` (not `control_special_master`).
  `full` keeps every name, so nothing that references a tool breaks.
- A profile only hides tools from MCP clients. `run_agent_goal` still calls any
  registered tool, and `suggest_tool_for_task` only suggests visible ones.
- New tools land in `full`; add them to `CORE_TOOLS` / `STANDARD_TOOLS` only when
  they are the canonical choice for their job. `tests/test_tool_profiles.py`
  fails on misspelled members and on two tools from one cluster in `standard`.

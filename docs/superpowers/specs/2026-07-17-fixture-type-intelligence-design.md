---
title: Fixture-Type Intelligence & Preset Automation
description: Design spec for a fixture-type model, ID-block hygiene, type-ordered selection, plugin orchestration, native preset creation, and planner integration
version: 1.0.0
created: 2026-07-17T10:58:36Z
last_updated: 2026-07-17T10:58:36Z
---

# Fixture-Type Intelligence & Preset Automation

## Problem

On real shows, the operator asked the MCP to "create presets from the fixtures I have" and it could not: the server has no model of fixture types or their attribute capabilities. The operator's preset-generation and color-picker plugins additionally require (a) fixtures numbered in the standard 100-block scheme per type category, and (b) type-ordered selection at plugin runtime. Nothing in the server verifies, repairs, or prepares either precondition.

This is sub-project 1 of the broader "make the server smarter" roadmap (planner overhaul, console-state divergence detection, and the learning loop are later sub-projects). It was chosen first because the fixture-type model is the foundation the others build on.

## Goals

1. Build a hydrated **FixtureTypeModel** of the patch: types, member fixtures, attribute capabilities, category classification.
2. Verify and (destructively, gated) repair fixture-ID block compliance against the 100-block scheme.
3. Build type-ordered selections independent of ID numbering.
4. Orchestrate the operator's preset/color-picker plugins end-to-end: precondition checks → selection → run → output verification.
5. Create presets natively, capability-aware, when plugins don't fit.
6. Route natural-language goals to all of the above through the agent planner.

## Non-Goals

- General planner overhaul beyond the three new intents (later sub-project).
- Console-state divergence detection / auto-rehydration beyond the patch re-read before renumbering (later sub-project).
- Telemetry/skill-improver loop changes (later sub-project).

## Architecture

New module `src/fixture_types.py` plus tools/workflows layered on top. Follows existing invariants: pure command builders in `src/commands/`, console I/O only via the telnet client, `@_handle_errors` + rights decorators + safety tiers on every tool, resources read-only.

### 1. FixtureTypeModel (`src/fixture_types.py`)

- **Hydration**: read the patched fixture list and each FixtureType's attribute set from the console (fixture-type tree via `cd`/`list`, reusing `src/navigation.py` and `src/prompt_parser.py` patterns as in `src/console_state.py`).
- **Record shape** per type: `type_id`, `name`, `member_fixture_ids`, capability flags (`dimmer`, `color_mix`, `position`, `gobo`, `beam`, `focus`, `control`), `category`.
- **Curated fallback table**: for common types (LED wash, spot/profile movers, LED bars, strobes, blinders, conventionals) when console readback yields incomplete attribute data. Fallback entries are marked `source="fallback"` so consumers can distinguish read vs. inferred capabilities.
- **Category classification**: wash / mover / bar / strobe / blinder / conventional / other, mapped to the operator's 100-block scheme: 1-99 wash, 100-199 movers, 200-299 bars, 300-399 strobes, 400-499 blinders. Classification uses type name heuristics + capability flags; the block map is configurable data, not hardcoded logic.
- Parsing/classification is pure and offline-testable; only hydration touches the console.

### 2. ID-block verification & repair

- Tool `verify_id_blocks` (SAFE_READ): per-category report — fixtures outside their block, gaps, collisions — plus a proposed renumbering plan (old ID → new ID list).
- Tool `renumber_fixtures` (DESTRUCTIVE, `confirm_destructive` gated): executes a renumbering plan. Before executing: re-hydrates the patch (stale-model guard), and warns about objects that reference fixture IDs (groups, presets) so the operator can decide. Dry-run mode returns the exact command list without executing.

### 3. Type-ordered selection builder

- Tool `build_type_ordered_selection`: emits the selection command sequence category-by-category in canonical order (wash → mover → bar → strobe → blinder → conventional → other) or a caller-supplied custom order.
- Two modes: return the command list without executing (for embedding in workflows/macros), or execute as SAFE_WRITE.
- Works from the FixtureTypeModel's member lists, so it is correct even when ID blocks are dirty.

### 4. Plugin orchestration

- Workflow `run_preset_plugin`: (1) `check_plugin_available`; (2) verify preconditions from a per-plugin **manifest** — required free pool ranges, required groups, required images (requirements currently documented in the auto-layout-color-picker skill become manifest data); (3) build type-ordered selection; (4) run the plugin; (5) verify outputs landed (presets/layouts stored in expected slots) and report a diff.
- Manifests are data files (one per plugin) so new plugins require a manifest, not code. Manifest fields: plugin name/ID, required pool ranges, required objects, selection-order requirements, expected outputs.

### 5. Native capability-aware preset creation

- Workflow `create_presets_for_patch`: for each preset type (dimmer/position/color/gobo/beam/focus), select only fixtures whose type has that capability, apply values, store presets following preset-library-architect slot conventions (universal vs. selective strategy per that skill). All stores DESTRUCTIVE-gated; dry-run preview returns the full command plan first.

### 6. Planner integration (`src/agent/planner.py`)

- Three new intents with plan builders:
  - `PRESET_FROM_PATCH` — "create presets from my fixtures/patch" → hydrate model → verify → `create_presets_for_patch`.
  - `PLUGIN_SETUP` — "set up the color picker / run my preset plugin" → `run_preset_plugin` workflow.
  - `ID_HYGIENE` — "check/fix my fixture numbering" → `verify_id_blocks` (+ gated `renumber_fixtures`).
- Each plan includes verification steps and routes DESTRUCTIVE steps through the existing confirmation flow.
- Bug fix in passing: `_build_group_workflow` ignores `fixture_start`/`fixture_end` (planner.py:282) — populate them from the parsed goal.

## Error handling

- All tools use `@_handle_errors` (telemetry automatic) and `@require_ma2_right`.
- Renumbering and preset stores are DESTRUCTIVE-tier: blocked without `confirm_destructive=True`; never auto-confirmed.
- Hydration failures (timeout, unparseable list output) return structured errors with partial-model flags rather than raising mid-workflow; workflows abort before any DESTRUCTIVE step if the model is partial or stale.
- Plugin runs verify output; a plugin that ran but produced nothing is reported as a failure with the precondition report attached.

## Testing

- Unit tests for parsing, classification, block verification, renumbering-plan generation, and selection ordering using recorded console `list` output fixtures.
- Workflow tests assert emitted command strings (no console).
- Live-integration tests (skipped by default, `tests/test_live_integration.py` style): model hydration against the real console; one end-to-end plugin-prep run.

## Success criteria

- "Create presets from my fixtures" works end-to-end via `run_agent_goal`, storing only capability-appropriate presets.
- Color-picker plugin setup succeeds from a single goal, including precondition verification and output diff.
- `verify_id_blocks` correctly flags a deliberately mis-numbered fixture and proposes a valid repair plan.

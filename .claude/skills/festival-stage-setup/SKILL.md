---
title: Festival Stage Setup
description: End-to-end workflow for setting up a one-off festival stage — patch to busking-ready in one session
version: 1.0.0
safety_scope: DESTRUCTIVE
created: 2026-04-02T00:00:00Z
last_updated: 2026-04-02T00:00:00Z
---

# Festival Stage Setup

## Charter

DESTRUCTIVE skill — creates fixture groups, stores presets, assigns executors, and labels objects. Requires operator confirmation before each destructive phase.

## Invocation

Use when an operator needs to go from a fresh patch to a busking-ready show on a festival stage in a single session. Assumes fixtures are already patched.

## Target Users

Lighting programmers setting up a stage at a festival, corporate event, or one-off show where time is critical.

## What It Builds

A complete busking-ready show layout:
- Fixture groups organized by type and position
- Basic color, position, and gobo preset library
- Executor page with faders for effects, bumps, and masters
- Labels and color-coded pool objects

---

## Phase 1: Discovery (SAFE_READ)

**Goal:** Understand what's on the rig.

1. Call `list_fixtures` to get all patched fixtures
2. Call `list_fixture_types` to identify fixture categories
3. Group fixtures mentally by type (wash, spot, beam, dimmer, LED)
4. Present findings to operator: "I see 12x Mac Viper, 8x Sharpy, 24x Generic Dimmer..."
5. Ask operator to confirm grouping before proceeding

**Allowed tools:** `list_fixtures`, `list_fixture_types`, `get_object_info`

---

## Phase 2: Groups (DESTRUCTIVE)

**Goal:** Create fixture groups by type and position.

**OPERATOR CONFIRMATION REQUIRED** before this phase.

1. For each fixture type, call `create_fixture_group` with a descriptive name
2. Create position-based groups if fixtures have positional names (e.g., "FOH", "Truss 1")
3. Create an "All" group containing every fixture
4. Call `batch_label` to name all groups in one pass

**Allowed tools:** `create_fixture_group`, `batch_label`

---

## Phase 3: Presets (DESTRUCTIVE)

**Goal:** Build a basic preset library.

**OPERATOR CONFIRMATION REQUIRED** before this phase.

1. For each group, store color presets: Red, Blue, Green, Amber, White, Deep Blue, Magenta, UV
2. For moving lights, store position presets: Center Stage, Upstage, Downstage, Audience
3. For spots, store gobo presets if fixture type supports gobos
4. Label and color-code all presets using `batch_label` and `label_or_appearance`

**Allowed tools:** `set_attribute`, `store_new_preset`, `batch_label`, `label_or_appearance`, `select_fixtures_by_group`, `clear_programmer`

---

## Phase 4: Executor Page (DESTRUCTIVE)

**Goal:** Create a busking-ready executor page.

**OPERATOR CONFIRMATION REQUIRED** before this phase.

Layout template (adapt based on available executors):
- Fader 1: Grand Master (already assigned by default)
- Faders 2-5: Intensity groups (FOH, Truss, Back, All)
- Faders 6-8: Color effects (rainbow chase, color bump, strobe)
- Buttons 101-108: Color preset recalls
- Buttons 109-112: Position preset recalls

1. Create sequences for each effect
2. Use `bulk_executor_assign` to assign and configure each executor
3. Set appropriate priorities (effects = Normal, master = High)

**Allowed tools:** `store_current_cue`, `bulk_executor_assign`, `set_executor_priority`, `execute_sequence`

---

## Phase 5: Verification (SAFE_READ)

**Goal:** Confirm the show is busking-ready.

1. Call `scan_page_executor_layout` to verify executor assignments
2. Call `list_preset_pool` to confirm presets are stored
3. Present a summary to the operator

**Allowed tools:** `scan_page_executor_layout`, `list_preset_pool`, `get_executor_status`

---
title: Preset Impact Manager
description: Safely assess and plan preset updates or deletions by analyzing all downstream references
version: 1.0.0
safety_scope: SAFE_READ
created: 2026-04-02T00:00:00Z
last_updated: 2026-04-02T00:00:00Z
---

# Preset Impact Manager

## Charter

SAFE_READ skill — analyzes preset usage across the show without modifying anything. Recommends safe update strategies.

## Invocation

Use before updating, replacing, or deleting any preset. Especially critical for presets used in live show sequences or busking pages.

## Workflow

### Step 1: Impact Assessment
Call `preview_preset_update_impact(preset_type="color", preset_id=1)` to get a risk classification:
- **safe**: 0 references — update freely
- **risky**: 1-5 references — proceed with caution
- **catastrophic**: 6+ references — back up first

### Step 2: Detailed Reference Map
For risky/catastrophic presets, call `find_preset_usages(preset_type="color", preset_id=1)` to see every sequence, cue, and executor that references it.

### Step 3: Plan the Update
Based on impact level:

**Safe (0 refs):** Update directly with `store_new_preset`.

**Risky (1-5 refs):**
1. Enter Blind mode: `toggle_console_mode(mode="blind")`
2. Make the preset change
3. Walk through affected cues with `diff_cues` to verify the look
4. Exit Blind and store

**Catastrophic (6+ refs):**
1. Save the show: `save_show`
2. Consider creating a NEW preset in an unused slot instead of editing
3. If editing is required, use Blind mode and verify every affected sequence
4. After storing, run `validate_preset_references` on affected sequences

## Allowed Tools

`preview_preset_update_impact`, `find_preset_usages`, `diff_cues`, `store_new_preset`, `save_show`, `toggle_console_mode`, `validate_preset_references`

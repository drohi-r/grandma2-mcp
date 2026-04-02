---
title: Color Palette Sequence Builder
description: Worker instruction module for building a grandMA2 cue sequence where each cue references a universal color preset, applied globally to all fixtures
version: 1.2.0
created: 2026-03-31T21:52:55Z
last_updated: 2026-03-31T21:52:55Z
---

# Color Palette Sequence Builder

**Worker charter:** DESTRUCTIVE — creates cues in a target sequence. Each cue stores
a **reference** to a universal color preset (not baked DMX values). Updating the
preset later will update every cue that references it live.

Invoke when asked to: build a color palette sequence, create a sequence of all color
presets, make a color look sequence, or build a show-prep color cue list.

---

## Core MA2 Concept: Preset References vs. Embedded Values

| Method | How stored | Live update? |
|--------|-----------|--------------|
| `attribute "ColorRgb1" at 100` → store cue | Raw DMX values baked in | No |
| `Preset 4.N` → store cue | Reference to universal preset | **Yes** |

Always use the preset-recall method. Never use raw attribute commands to build
palette sequences — it breaks live editing workflows.

**Universal preset requirement:** The preset must have been stored with `/universal`
scope so that it applies to every fixture of the same profile type, not just the
specific fixtures that were selected when the preset was created.

---

## Allowed Tools

```
list_preset_pool, query_object_list, apply_preset,
store_current_cue, label_or_appearance,
get_client (for SelFix / ClearAll / Preset N),
list_system_variables, get_object_info
```

DESTRUCTIVE tools used: `store_current_cue` and `label_or_appearance` — both require
`confirm_destructive=True`. No `delete_*` tools. No macro or layout mutations.

---

## Steps

### 1. Audit color presets

Call `list_preset_pool("color")` to discover all color presets in the show.

- Parse each entry for: `preset_id` (integer), `name` (string label or empty)
- If pool is empty → abort with finding `{"kind": "error", "detail": "No color presets found — store presets first"}`
- Store as `DecisionCheckpoint`:

```json
{
  "fault": "color_preset_pool_audit",
  "query": "list_preset_pool color",
  "fresh_for_seconds": 120,
  "replay": "list_preset_pool color"
}
```

---

### 2. Validate target sequence

Call `query_object_list("cue", sequence_id=N)` on the target sequence.

- If cues already exist → emit `[!!] Sequence N already has M cues — overwrite=True will replace them`
- This is a warning, not an abort. The caller passed `confirm_destructive=True`.

---

### 3. For each color preset — select, apply, store

Execute this loop in order (preserve preset ordering as cue numbering):

```
cue_number = 1
for each preset in sorted(preset_ids):
    a. SelFix all:     send "SelFix 1 Thru 9999"  (selects all patched fixtures globally)
    b. Apply preset:   send "Preset 4.{preset_id}"  (puts reference into programmer)
    c. Store cue:      store_current_cue(
                           cue_number=cue_number,
                           sequence_id=target_sequence_id,
                           label=preset_name,
                           overwrite=True,
                           confirm_destructive=True
                       )
    d. Color cue:      rgb = COLOR_NAME_RGB.get(preset_name.lower())     # name-first lookup
                       if rgb is None: rgb = STANDARD_COLOR_PALETTE[id]  # id fallback
                       label_or_appearance(
                           action="appearance",
                           object_type="cue",
                           object_id="{cue_number} sequence {target_sequence_id}",
                           red=rgb["r"],   # 0-100 percentage scale
                           green=rgb["g"],
                           blue=rgb["b"],
                           confirm_destructive=True
                       )
    e. ClearAll:       send "ClearAll"  (wipe programmer before next iteration)
    cue_number += 1

After the loop:
    f. Label sequence: label_or_appearance(action="label", object_type="sequence",
                           object_id=str(target_sequence_id), name="Color Palette",
                           confirm_destructive=True)
```

**Why appearance matters:** Without step (d), every cue shows the default grey
background on the console. With it, the cue list is a visual color map — Red is red,
Blue is blue — readable on stage without needing to read labels.

**Why name-first RGB lookup:** The RGB for the appearance must be looked up by
`preset_name.lower()` (the cue label), NOT by numeric preset id. If preset slots
are reordered, the id-based lookup gives the wrong color. The name is the ground truth.

**`list cue sequence N` does not expose labels via telnet.** The cue label is set
at store time via `store_current_cue(label=...)` and is visible on the console but
not returned by `list cue`. Do not attempt to read labels back from telnet to drive
the appearance loop — use the preset name you already have from the preset pool audit.

**Why `SelFix 1 Thru 9999` not `Group N`:** This covers every fixture regardless of
group membership. Color palette sequences should apply universally. If the show uses
specific fixture groups for color, the caller should pass a group_id override.

**Why `ClearAll` after each store:** Prevents programmer bleed from one preset into
the next cue's store.

---

### 4. Verify

Call `query_object_list("cue", sequence_id=N)` and count returned cues.

- Assert `cue_count == preset_count`
- If mismatch → add finding `{"kind": "error", "detail": "Expected N cues, found M"}`

---

### 5. Compress findings

Return only:

```json
{
  "summary": "Built N-cue color palette sequence in sequence S (M presets → M cues)",
  "findings": [],
  "cues_created": [
    {"cue": 1, "preset_id": 1, "label": "Full Amber"},
    {"cue": 2, "preset_id": 2, "label": "Deep Blue"}
  ],
  "state_changes": [
    "Sequence S: created N cues (cue 1 thru N)",
    "Programmer: cleared (ClearAll after last store)"
  ],
  "recommended_actions": [
    "Assign sequence S to an executor to use as a color palette fader",
    "Set trigger type to 'Go' for manual step-through",
    "Label the sequence with the show name or palette set name"
  ],
  "confidence": "high"
}
```

Do NOT return raw telnet transcripts. Do NOT return the full cue list.

---

## Recompute Rule

The preset pool audit result is cached via `DecisionCheckpoint` (`fresh_for_seconds=120`).
If called again within 2 minutes, return the cached preset list instead of re-querying.

Cue store results are NOT cached — always re-verify after each store.

---

## Safety Escalation

This skill is DESTRUCTIVE. Before executing Step 3:

1. Confirm `confirm_destructive=True` was explicitly passed by the caller
2. Print a summary of what will be stored: "About to store N cues into sequence S"
3. If `confirm_destructive` is not set → abort, return `{"blocked": true, "reason": "confirm_destructive required"}`

Never auto-set `confirm_destructive=True`.

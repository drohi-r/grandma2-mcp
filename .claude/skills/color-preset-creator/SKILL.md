---
title: Color Preset Creator
description: Worker instruction module for storing universal color presets in grandMA2 from RGB values — creates the preset pool that color-palette-sequence-builder reads from
version: 1.0.0
created: 2026-03-31T21:52:55Z
last_updated: 2026-03-31T21:52:55Z
---

# Color Preset Creator

**Worker charter:** DESTRUCTIVE — creates or overwrites color presets in the show's
preset pool. All presets are stored as **universal** scope so they apply to any
fixture of the same profile type.

Invoke when asked to: create color presets, build a color palette, store color
libraries, or populate the preset pool before building a palette sequence.

---

## Core MA2 Concept: Universal vs. Selective Presets

| Scope | Command flag | Who it applies to | Cue reference? |
|-------|-------------|-------------------|----------------|
| Selective | (none / default) | Only the specific fixtures selected at store time | No — embeds values |
| Universal | `/universal` | Any fixture of the same profile type | **Yes — live reference** |

Always store color palette presets as `/universal`. This is what makes cues that
reference these presets update live when the preset is edited.

---

## RGB Scale

MA2 color attributes use a **0–100 percentage scale**, not 0–255.

| Attribute name | Channel | Range |
|---------------|---------|-------|
| `ColorRgb1`   | Red     | 0–100 |
| `ColorRgb2`   | Green   | 0–100 |
| `ColorRgb3`   | Blue    | 0–100 |

For CMY fixtures: use `ColorCmy1` (Cyan), `ColorCmy2` (Magenta), `ColorCmy3` (Yellow)
with the same 0–100 scale. Do not mix RGB and CMY attribute names on the same store call.

---

## Allowed Tools

```
get_client (for SelFix, attribute, ClearAll — via send_command_with_response),
store_new_preset, list_preset_pool, list_system_variables
```

DESTRUCTIVE tools used: `store_new_preset` with `confirm_destructive=True`.
No cue mutations, no sequence edits, no macro changes.

---

## Steps

### 1. Confirm fixture attribute type

Call `list_system_variables(filter_prefix="VERSION")` to get console version,
then check the patched fixture profiles to confirm the correct attribute names.

For the standard `claude_ma2_ctrl` show (Mac 700 Profile Extended):
- Use `ColorRgb1`, `ColorRgb2`, `ColorRgb3`

If other fixture types are patched: discover attribute names via `browse_preset_type(4)`.

---

### 2. For each color in the palette — select, set, store

Execute this loop in order:

```
for each color (id, name, r, g, b):
    a. SelFix all:    send "SelFix 1 Thru 9999"
    b. Red channel:   send 'attribute "ColorRgb1" at {r}'
    c. Green channel: send 'attribute "ColorRgb2" at {g}'
    d. Blue channel:  send 'attribute "ColorRgb3" at {b}'
    e. Store:         store_new_preset(
                          preset_type="color",
                          preset_id=id,
                          universal=True,
                          overwrite=True,
                          confirm_destructive=True,
                      )
    f. Clear:         send "ClearAll"
```

**Why `SelFix 1 Thru 9999` before each color:** MA2 requires fixtures to be
selected in the programmer for `attribute` commands to apply. `SelFix` selects
by fixture number range — covering all patched fixtures regardless of type.

**Why `ClearAll` after each store:** Wipes the programmer so the next color's
attribute commands start from a clean state. Without this, residual values from
the previous color can bleed into the next preset.

---

### 3. Verify

Call `list_preset_pool("color")` and count entries.

- Assert `entry_count == expected_preset_count`
- If mismatch → emit finding `{"kind": "error", "detail": "Expected N presets, found M"}`

---

### 4. Compress findings

Return only:

```json
{
  "summary": "Created N universal color presets (Preset 4.1 thru 4.N)",
  "findings": [],
  "presets_created": [
    {"preset_id": 1, "name": "Red",  "r": 100, "g": 0,   "b": 0},
    {"preset_id": 2, "name": "Blue", "r": 0,   "g": 0,   "b": 100}
  ],
  "state_changes": [
    "Preset pool: 8 universal color presets written (4.1–4.8)",
    "Programmer: cleared (ClearAll after last store)"
  ],
  "recommended_actions": [
    "Run color-palette-sequence-builder to build a cue sequence from these presets",
    "Verify presets on console: list_preset_pool('color')"
  ],
  "confidence": "high"
}
```

---

## Standard 8-Color LED Palette

Reference palette for RGB/LED rigs (Mac 700, generic LED, etc.):

| ID | Name    | R   | G   | B   |
|----|---------|-----|-----|-----|
| 1  | Red     | 100 | 0   | 0   |
| 2  | Blue    | 0   | 0   | 100 |
| 3  | Green   | 0   | 100 | 0   |
| 4  | Amber   | 100 | 55  | 0   |
| 5  | White   | 100 | 100 | 100 |
| 6  | Magenta | 100 | 0   | 100 |
| 7  | Cyan    | 0   | 100 | 100 |
| 8  | UV      | 20  | 0   | 100 |

---

## Safety Escalation

Before executing Step 2, confirm `confirm_destructive=True` was explicitly passed.
Print: `"About to store/overwrite N color presets (Preset 4.1–4.N)"`.
If not set → abort with `{"blocked": true, "reason": "confirm_destructive required"}`.

Never auto-set `confirm_destructive=True`.

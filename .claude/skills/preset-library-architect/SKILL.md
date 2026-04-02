---
title: Preset Library Architect
description: Instruction module for designing and building a complete grandMA2 preset library — slot allocation, universal vs. selective strategy, fixture selection, and store discipline
version: 1.0.0
created: 2026-03-31T18:00:00Z
last_updated: 2026-03-31T18:00:00Z
---

# Preset Library Architect

**Charter:** Planner-level skill for designing a complete preset library across all
preset types (Dimmer, Position, Gobo, Color, Beam). Covers slot strategy, store order,
fixture selection discipline, and `/overwrite` safety.

Invoke when asked to: design a preset library, plan preset slot layout, create all
preset types for a rig, or establish a preset numbering convention for a show.

---

## MA2 Preset Type Map

| Pool ID | Type     | cd path  | $PRESET |
|---------|----------|---------|---------|
| 1       | Dimmer   | 10.2.1  | DIMMER  |
| 2       | Position | 10.2.2  | POSITION|
| 3       | Gobo     | 10.2.3  | GOBO    |
| 4       | Color    | 10.2.4  | COLOR   |
| 5       | Beam     | 10.2.5  | BEAM    |
| 6       | Focus    | 10.2.6  | FOCUS   |
| 7       | Control  | 10.2.7  | CONTROL |

Slot reference: `Preset {type}.{slot}` — e.g., `Preset 4.3` = Color preset 3.

---

## Universal vs. Selective Presets

| Scope | MA2 flag | Live cue reference? | When to use |
|-------|----------|---------------------|-------------|
| Universal | `/universal` | **Yes** — cue updates when preset edited | Color, Gobo, Beam palettes (shared across rig) |
| Selective | (none) | No — values embedded in cue at store time | Position snapshots specific to fixture IDs |

**Rule:** Store Color, Gobo, and Beam presets as `/universal`.
Store Position presets without `/universal` (they are fixture-geometry specific).
Store Dimmer presets as universal (percentage levels are generic).

---

## Standard Slot Layout

Use this numbering convention for all shows. Reserve these ranges:

| Type | Slots | Labels |
|------|-------|--------|
| Dimmer (1.x) | 1.1–1.5 | Full, 75pct, Half, 25pct, Off |
| Position (2.x) | 2.1–2.8 | Home, FOH-Center, Stage-Left, Stage-Right, TopLight, Balcony, Side-Left, Side-Right |
| Gobo (3.x) | 3.1–3.8 | Open, Gobo1, Gobo2, Gobo3, Gobo4, Gobo5, Gobo6, Gobo7 |
| Color (4.x) | 4.1–4.8 | White, Red, Green, Blue, Amber, Cyan, Magenta, Yellow |
| Color hue (4.101–4.196) | 4.101–4.196 | 96 HSB hue presets (hue-palette-creator) |
| Beam (5.x) | 5.1–5.5 | Open, Narrow, Medium, Wide, Max |

Check existing slot availability before storing:
```
list_preset_pool("dimmer")   # check 1.x occupancy
list_preset_pool("position") # check 2.x
list_preset_pool("color")    # check 4.x
```

---

## Fixture Selection Strategy

### Dimmer presets (type 1)
No fixture selection needed — dimmer is universal by nature.
```
at {level}                    # No SelFix needed; applies to programmer
Store Preset 1.{N} /overwrite
```

### Position presets (type 2)
Select **all moving heads** (profiles + washes). Group by physical type:
```
SelFix Fixture 111 Thru 125 + Fixture 201 Thru 220
attribute "Pan" at {pan}
attribute "Tilt" at {tilt}
Store Preset 2.{N} /overwrite
```

### Gobo presets (type 3)
Select **profile spots only** — washes have no gobo wheel:
```
SelFix Fixture 111 Thru 125
attribute "Gobo1" at {value}
Store Preset 3.{N} /overwrite
```

### Color presets (type 4)
Select **all fixtures** — universal scope covers all patched profiles:
```
SelFix 1 Thru 9999
attribute "ColorRgb1" at {r}
attribute "ColorRgb2" at {g}
attribute "ColorRgb3" at {b}
Store Preset 4.{N} /overwrite /universal
```

For CMY fixtures: use `ColorCmy1` (Cyan), `ColorCmy2` (Magenta), `ColorCmy3` (Yellow).
Check attribute names via `browse_preset_type(4)` or `Info FixtureType N` before storing.

---

## Store Discipline — ClearAll Between Stores

Always `ClearAll` after each `Store Preset`. Without this, residual programmer
values from the previous preset bleed into the next store call.

```
# Correct pattern for each slot:
SelFix ...
attribute "X" at {value}
Store Preset {type}.{N} /overwrite
Label Preset {type}.{N} "{name}"
ClearAll         ← REQUIRED between each preset
```

**Exception:** Consecutive `attribute` commands for the same fixture selection can
be batched before a single store. Do NOT ClearAll between the Pan and Tilt commands
for the same position preset.

---

## /overwrite vs. slot availability check

Use `/overwrite` for all stores unless the show has existing presets that must be
preserved. Before a full library build:

1. Call `list_preset_pool()` for each type to audit existing content.
2. If slots 1–8 are empty → proceed with `/overwrite` (idempotent).
3. If slots are occupied with different content → confirm with operator before overwriting.

Never use `/merge` for palette presets — merge can silently combine stale values
from previous fixtures with new ones.

---

## Color Reference Palette (standard 8-slot)

| Slot | Name    | R   | G   | B   |
|------|---------|-----|-----|-----|
| 4.1  | White   | 100 | 100 | 100 |
| 4.2  | Red     | 100 | 0   | 0   |
| 4.3  | Green   | 0   | 100 | 0   |
| 4.4  | Blue    | 0   | 0   | 100 |
| 4.5  | Amber   | 100 | 55  | 0   |
| 4.6  | Cyan    | 0   | 100 | 100 |
| 4.7  | Magenta | 100 | 0   | 100 |
| 4.8  | Yellow  | 100 | 100 | 0   |

Scale: 0–100 (NOT 0–255). MA2 uses percentage scale throughout.

---

## Position Reference (standard 5-slot)

| Slot | Name       | Pan | Tilt |
|------|------------|-----|------|
| 2.1  | Home       | 50  | 50   |
| 2.2  | FOH-Center | 50  | 35   |
| 2.3  | Stage-Left | 25  | 35   |
| 2.4  | Stage-Right| 75  | 35   |
| 2.5  | TopLight   | 50  | 0    |

Adjust pan/tilt values for each venue. These are starting defaults (0–100 % of DMX range).

---

## Labeling

Always label immediately after storing. Use `label_preset` tool or direct command:
```
Label Preset {type}.{N} "{name}"
```

For color presets, also set appearance color for visual identification in the pool:
```
Appearance Preset 4.{N} /r={r} /g={g} /b={b}
```
Appearance uses the same 0–100 scale.

---

## Build Order

1. **Dimmer** (1.x) — fastest, no fixture selection needed
2. **Color** (4.x) — 8 slots, universal, all fixtures
3. **Position** (2.x) — 5+ slots, per moving head group
4. **Gobo** (3.x) — 5+ slots, profile spots only
5. **Beam** (5.x) — optional; only if beam presets are needed

Build dimmer and color first so they are available as building blocks for sequences.

---

## Verification

After all stores, verify counts:
```
list_preset_pool("dimmer")    → assert ≥ 5 entries
list_preset_pool("position")  → assert ≥ 5 entries
list_preset_pool("gobo")      → assert ≥ 5 entries
list_preset_pool("color")     → assert ≥ 8 entries
```

---

## Safety

- All `store_new_preset` calls require `confirm_destructive=True`.
- Print intent before each store: `"Storing {type} preset {N} — {name}"`.
- Never auto-set `confirm_destructive=True` from within the skill.
- Abort and emit `{"blocked": true, "reason": "confirm_destructive required"}` if not set.

---
title: Busking Template Generator
description: Worker instruction module for generating a complete grandMA2 busking template from patch — fixture groups by type, color/position/beam presets, speed masters, and executor page layout
version: 1.0.0
created: 2026-04-01T00:00:00Z
last_updated: 2026-04-01T00:00:00Z
---

# Busking Template Generator

**Worker charter:** DESTRUCTIVE — creates groups, presets, sequences, and executor assignments. Always save show before starting. Confirm each phase with operator before executing.

Invoke when asked to: build a busking template, generate a busk rig from patch, auto-generate groups and presets, or set up a festival busking page.

Target users: Busking operators at festivals/clubs, emerging EDM artists, venue operators setting up for unknown visiting acts.

---

## What This Builds

From a patched rig with fixture types already imported, this skill generates:

1. **Fixture groups** by type (all wash movers, all spots, all beams, all LED bars, all strobes)
2. **Color presets** — 8 universal colors per fixture group: red, orange, yellow, green, cyan, blue, magenta, white
3. **Position presets** — 4 universal positions per mover group: home, down-center, stage-left-top, stage-right-top
4. **Effects** — 3 universal effects per group: slow color chase, medium position wave, fast strobe
5. **Speed masters** — assign speed master 1 to all chase effects
6. **Executor layout** — single page: groups on right wing, effects across main faders

---

## Phase 0 — Survey (SAFE_READ, always first)

```python
hydrate_console_state()
list_fixtures()           # total fixture count
list_fixture_types()      # what types are in the rig
list_universes()          # which universes are used
list_preset_pool(preset_type="color")     # check if presets already exist
list_preset_pool(preset_type="position")
```

Present summary to operator: "Found [N] fixtures across [M] types. Color pool has [K] existing presets. Proceed?"

---

## Phase 1 — Group Creation (DESTRUCTIVE)

For each unique fixture type found:
```python
create_fixture_group(
    group_id=<next_available>,  # start from 1 or first empty slot
    fixture_selection="FixtureType [TypeName] 1 Thru",
    confirm_destructive=True
)
label_or_appearance(object_type="group", object_id=N, label="[TypeName] ALL")
```

Use HSB color coding per group type (0-100 percentage scale):
- Wash → blue (hue 240, sat 100, brightness 80)
- Spot → white (hue 0, sat 0, brightness 100)
- Beam → yellow (hue 60, sat 100, brightness 80)
- Strobe → red (hue 0, sat 100, brightness 80)

---

## Phase 2 — Color Presets (DESTRUCTIVE)

For each group, create 8 universal color presets. RGB values use the 0-100 percentage scale (NOT 0-255):

| Label | R | G | B |
|-------|---|---|---|
| Red | 100 | 0 | 0 |
| Orange | 100 | 40 | 0 |
| Yellow | 100 | 100 | 0 |
| Green | 0 | 100 | 0 |
| Cyan | 0 | 100 | 100 |
| Blue | 0 | 0 | 100 |
| Magenta | 100 | 0 | 100 |
| White | 100 | 100 | 100 |

```python
# Select fixture group first
select_fixtures_by_group(group_id=N)
# Set color attribute (0-100 scale)
set_attribute(attribute="ColorRgb1", value=100)
# Store as universal preset
store_new_preset(preset_type="color", preset_id=<slot>, scope="universal", confirm_destructive=True)
label_or_appearance(object_type="preset", object_id=<slot>, preset_type="color", label="Red")
```

---

## Phase 3 — Position Presets (DESTRUCTIVE, mover groups only)

Only for fixture groups whose types have Pan and Tilt attributes.

| Label | Pan | Tilt |
|-------|-----|------|
| Home | 50 | 50 |
| DownCenter | 50 | 80 |
| SL Top | 25 | 30 |
| SR Top | 75 | 30 |

```python
select_fixtures_by_group(group_id=N)
set_attribute(attribute="Pan", value=50)
set_attribute(attribute="Tilt", value=50)
store_new_preset(preset_type="position", preset_id=<slot>, scope="universal", confirm_destructive=True)
label_or_appearance(object_type="preset", preset_type="position", object_id=<slot>, label="Home")
```

---

## Phase 4 — Executor Layout (DESTRUCTIVE)

Assign sequences to executors on a dedicated busking page:

| Exec | Content | Label |
|------|---------|-------|
| 1 | Song loader macro | LOAD |
| 2-5 | Effect sequences per fixture type | FX [Type] |
| 6-8 | Group masters (intensity only) | GRP [N] |
| 9 | Speed master 1 | SPD |
| 10 | Emergency blackout macro | BO |

```python
assign_sequence_to_executor(sequence_id=N, executor_id="[page].[exec]", confirm_destructive=True)
control_special_master(master_type="speed", master_id=1, value=120)  # default 120 BPM
```

---

## Phase 5 — Verify and Save

```python
get_console_state()           # confirm groups, presets registered
save_show(confirm_destructive=True)   # always save after template build
```

---

## Operator Confirmation Gates

Pause and confirm with operator before each DESTRUCTIVE phase:

- **Phase 1:** "I will create [N] groups. This will overwrite slots [X-Y]. Proceed?"
- **Phase 2:** "I will create [M] color presets in slots [A-B]. Proceed?"
- **Phase 4:** "I will assign sequences to page [P] executors 1-10. This will overwrite existing assignments. Proceed?"

Never proceed past a confirmation gate without explicit operator approval.

---

## Allowed Tools

```
SAFE_READ: hydrate_console_state, list_fixtures, list_fixture_types, list_universes, list_preset_pool
DESTRUCTIVE: create_fixture_group, label_or_appearance, set_attribute, store_new_preset,
             store_current_cue, assign_sequence_to_executor, control_special_master, save_show
```

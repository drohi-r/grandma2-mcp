---
title: Effect Programmer
description: Worker instruction module for creating, storing, and assigning grandMA2 effects — from scratch in the programmer, from predefined library, and storing effects in cues
version: 1.0.0
created: 2026-03-31T20:00:00Z
last_updated: 2026-03-31T20:00:00Z
---

# Effect Programmer

**Charter:** DESTRUCTIVE — creates and stores effects in the grandMA2 Effects pool,
assigns them to executors, and stores effect states in cues.

Invoke when asked to: create a color/dimmer/position effect, add a chase effect,
build an effect from scratch, assign an effect to an executor, or store an effect in a cue.

---

## Core Concept: Template vs. Selective Effects

| Type | What it affects | When to use |
|------|----------------|-------------|
| **Template effect** | Runs from a pool slot; any fixture that plays it uses the effect | Reusable library effects (color circle, dimmer chase) |
| **Selective effect** | Saved with specific fixture values baked in | One-off effects tied to a specific look |

Always build as template for reusable busking tools.
Use selective for cue-embedded one-time effects.

---

## Effect Parameters

| Parameter | MA2 attribute name | Range | Description |
|-----------|-------------------|-------|-------------|
| Speed | BPM or Hz | 0–65535 BPM | Steps per minute |
| Width | Width | 0–100% | Pulse duty cycle |
| Phase | Phase | 0–359° | Stagger between fixtures |
| High | High | 0–100% | Upper limit of waveform |
| Low | Low | 0–100% | Lower limit of waveform |
| Attack | Attack | 0–100% | Rise time |
| Decay | Decay | 0–100% | Fall time |

Effect forms (waveforms): `sine`, `square`, `ramp_up`, `ramp_down`, `random`, `triangle`.
Discover available forms: `list_forms()`.

---

## Attribute Names for Effects

Use these exact MA2 attribute names in `set_effect_param` and programmer commands:

| Effect on | Attribute name |
|-----------|---------------|
| Intensity / Dimmer | `Dimmer` |
| Red channel | `ColorRgb1` |
| Green channel | `ColorRgb2` |
| Blue channel | `ColorRgb3` |
| Pan | `Pan` |
| Tilt | `Tilt` |
| Gobo wheel | `Gobo1` |

For CMY fixtures: `ColorCmy1` (Cyan), `ColorCmy2` (Magenta), `ColorCmy3` (Yellow).

---

## Workflow A — Build an Effect from Scratch (Programmer)

### Step 1: Select fixtures

```
SelFix Fixture 111 Thru 125       # or use a group
```

### Step 2: Enter effect mode and set parameters

Use the MCP tool `set_effect_param` for each parameter:
```python
set_effect_param("bpm", 60)       # speed: 60 BPM
set_effect_param("high", 100)     # full intensity at peak
set_effect_param("low", 0)        # off at trough
set_effect_param("phase", 30)     # 30° phase spread across fixtures
set_effect_param("width", 50)     # 50% duty cycle
```

Or via raw command:
```
EffectBPM 60
EffectHigh 100
EffectLow 0
EffectPhase 30
EffectWidth 50
```

### Step 3: Set the attribute for the effect

```
Feature Dimmer                    # select Dimmer attribute layer
```
or for color:
```
Feature Color                     # select Color attribute layer
attribute "ColorRgb1" at 100
attribute "ColorRgb2" at 0
attribute "ColorRgb3" at 0
```

### Step 4: Store the effect

```python
store_object(
    object_type="effect",
    object_id=1,
    name="Dimmer Chase",
    confirm_destructive=True,
)
```

This emits: `store effect 1` then `label effect 1 "Dimmer Chase"`.

### Step 5: Assign appearance color

```python
label_or_appearance("effect", 1, appearance_hsb=(30, 80, 100))
```

### Step 6: Verify

```python
list_effects_pool()
```

---

## Workflow B — Import from Predefined Library

Browse the built-in effect library first:
```python
browse_effect_library()        # lists all predefined effects
```

Import a predefined effect into the pool:
```python
import_objects(
    object_type="effect",
    source="predefined",
    target_id=5,
    confirm_destructive=True,
)
```

Or via raw command: `Import "filename" At Effect N`

---

## Workflow C — Assign Effect to Executor (Busking)

```python
assign_effect_to_executor(
    effect_id=1,
    executor_id=201,
    page=1,
    confirm_destructive=True,
)
```

This emits: `assign effect 1 at executor 1.201`

Then configure rate fader:
```python
set_effect_rate(executor_id=201, page=1)      # assigns rate control to fader
```

Verify: `get_executor_state(executor_id=201)`

---

## Workflow D — Store Effect in a Cue

This embeds an effect reference inside a cue (not on a standalone executor).

```
# 1. Select fixtures
SelFix Fixture 201 Thru 220

# 2. Apply the effect from pool (Preset-style recall)
Effect 1                        # applies effect 1 to programmer selection

# 3. Store into cue
store_current_cue(
    sequence_id=99,
    cue_id=5,
    label="Color Circle",
    confirm_destructive=True,
)

# 4. Clear
ClearAll
```

---

## Live Effect Control

Adjust a running effect via executor:
```python
# Rate (0-200, 100 = normal)
set_effect_rate(value=50, executor_id=201)    # half speed

# Speed (BPM)
set_effect_speed(value=120, executor_id=201)  # 120 BPM

# Remove effect from executor
remove_effect(executor_id=201, confirm_destructive=True)
```

---

## Allowed Tools

```
list_effects_pool         — SAFE_READ: browse existing effects
list_forms                — SAFE_READ: list available waveform shapes
browse_effect_library     — SAFE_READ: browse predefined effect library
set_effect_param          — SAFE_WRITE: set BPM/high/low/phase/width/attack/decay
store_object              — DESTRUCTIVE: create effect pool slot
label_or_appearance       — DESTRUCTIVE: label and color-code effect
assign_effect_to_executor — DESTRUCTIVE: assign effect to executor for busking
set_effect_rate           — SAFE_WRITE: adjust running effect rate
set_effect_speed          — SAFE_WRITE: adjust running effect BPM
remove_effect             — DESTRUCTIVE: remove effect from executor
store_current_cue         — DESTRUCTIVE: embed effect in cue
import_objects            — DESTRUCTIVE: import predefined effect
```

---

## Safety

- `store_object("effect", N)` requires `confirm_destructive=True`.
- Never set `High` and `Low` to the same value — creates a flat non-animating effect.
- Phase spread = 360 / fixture_count for even distribution (e.g., 10 fixtures → 36° per fixture).
- Test with `SelFix 1 Thru 9` before scaling to full rig.
- `ClearAll` after storing any effect cue — residual effect values can bleed into next store.

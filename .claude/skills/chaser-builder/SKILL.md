---
title: Chaser Builder
description: Instruction module for creating grandMA2 chasers — step-based sequences with speed, crossfade, direction, and MAtricks control for busking and automated chase effects
version: 1.1.0
created: 2026-03-31T21:00:00Z
last_updated: 2026-03-31T22:00:00Z
---

# Chaser Builder

**Charter:** DESTRUCTIVE — creates and configures chaser sequences in grandMA2,
including step storage, speed/crossfade assignment, and executor assignment.

Invoke when asked to: build a chase, create a strobe sequence, make a step-based effect,
set up a running light effect, configure a speed chaser, or create a color chase.

**Prerequisite:** Dimmer presets (type 1, slots 1.1=Full … 1.5=Off) and Color presets
(type 4, slots 4.1=White … 4.8=Yellow) must exist before building any chase sequence.
See `preset-library-architect` skill if the preset pool is empty.

---

## Core Concept: Chaser vs. Cue List

| Type | Behavior | Use for |
|------|----------|---------|
| **Cue List** | Sequential, manual or time-triggered | Show programming, pre-built looks |
| **Chaser** | Loops continuously at set speed | Busking effects, running lights, strobes |

A chaser is a regular sequence with the `chaser` flag set on its executor.
This flag makes it loop automatically and respond to rate/speed masters.

---

## Chaser Parameters

| Parameter | Range | Default | Controls |
|-----------|-------|---------|---------|
| Speed | 0-600 BPM | 60 | Steps per minute |
| Rate | 0-200% | 100% | Speed multiplier (relative) |
| Crossfade | 0-100% | 0% | Blend time between steps (0=snap) |
| Direction | Forward/Backward/Bounce/Random | Forward | Step order |
| MIB | on/off | off | Move In Black (pre-position while dark) |

---

## Workflow A — Build a Simple Color Chase

### Step 1: Discover free sequence slot

```python
list_sequences()      # find next free slot number
```

Pick the first unoccupied slot (e.g., 101).

### Step 2: Build steps in programmer

For each step (color):

```
# Step 1 — Red
SelFix Fixture 201 Thru 220
Preset 4.2                    # Red — color preset pool (stores a preset reference, not raw values)
store_current_cue(sequence_id=101, cue_id=1, label="Red", confirm_destructive=True)
ClearAll

# Step 2 — Green
SelFix Fixture 201 Thru 220
Preset 4.3                    # Green — color preset pool
store_current_cue(sequence_id=101, cue_id=2, label="Green", confirm_destructive=True)
ClearAll

# Step 3 — Blue
SelFix Fixture 201 Thru 220
Preset 4.4                    # Blue — color preset pool
store_current_cue(sequence_id=101, cue_id=3, label="Blue", confirm_destructive=True)
ClearAll
```

### Step 3: Label the sequence

```python
label_object(object_type="sequence", object_id=101, name="Color Chase — Washes")
```

### Step 4: Assign to executor with chaser flag

```python
assign_sequence_to_executor(
    sequence_id=101,
    executor_id=201,
    page=1,
    options=["chaser"],          # critical: enables loop mode
    confirm_destructive=True,
)
```

This emits: `assign sequence 101 at executor 1.201 /chaser`

### Step 5: Set speed and crossfade

```python
control_chaser(
    executor_id=201,
    page=1,
    rate=80,          # 80% of base speed
)

set_executor_crossfade(
    executor_id=201,
    page=1,
    crossfade=20,     # 20% = soft snap
)
```

---

## Workflow B — Running Light Chase (MAtricks)

A running light uses MAtricks to offset phase across fixtures without individual step storage.

### Step 1: Set MAtricks interleave

```python
manage_matricks(
    mode="interleave",
    value=1,           # 1 fixture per group = pure running light
)
```

### Step 2: Store a single-step chaser

```
SelFix Group 14       # all wash fixtures
Preset 1.1            # Full — dimmer preset pool (stores a preset reference, not raw value)
store_current_cue(sequence_id=102, cue_id=1, label="Run", confirm_destructive=True)
ClearAll
```

### Step 3: Assign with chaser + offset

```python
assign_sequence_to_executor(
    sequence_id=102,
    executor_id=202,
    page=1,
    options=["chaser"],
    confirm_destructive=True,
)
```

The MAtricks interleave setting is now baked into the stored values (offsets applied at store time).

---

## Workflow C — Strobe Chase

Strobe = 2-step chaser: Full → Off at high speed.

```
SelFix Fixture 111 Thru 125
Preset 1.1            # Full — dimmer preset pool
store_current_cue(sequence_id=103, cue_id=1, label="Full", confirm_destructive=True)
ClearAll

SelFix Fixture 111 Thru 125
Preset 1.5            # Off — dimmer preset pool
store_current_cue(sequence_id=103, cue_id=2, label="Off", confirm_destructive=True)
ClearAll
```

Assign with chaser flag, set speed high (180-600 BPM):

```python
control_chaser(executor_id=203, page=1, rate=150)  # 150% of base = fast strobe
```

---

## Chaser Direction Control

```python
# Via raw command
send_raw_command("Assign Executor 1.201 /direction=forward", confirm_destructive=True)
send_raw_command("Assign Executor 1.201 /direction=backward", confirm_destructive=True)
send_raw_command("Assign Executor 1.201 /direction=bounce", confirm_destructive=True)
send_raw_command("Assign Executor 1.201 /direction=random", confirm_destructive=True)
```

---

## Speed and Rate Masters

Assign a speed master to a chaser executor for fader control:

```python
send_raw_command(
    "Assign Executor 1.201 /speedmaster=speed1",
    confirm_destructive=True,
)
```

Speed masters 1-16 are global — multiple chasers can share one master.
Rate masters (ratemaster=rate1..rate16) multiply on top of speed.

---

## Step Skip

Jump to the next or previous step while running:

```python
control_chaser(executor_id=201, page=1, skip="plus")   # next step
control_chaser(executor_id=201, page=1, skip="minus")  # previous step
```

---

## Crossfade A/B Mode

Soft chaser where two steps blend simultaneously:

```python
control_chaser(executor_id=201, page=1, xfade_mode="ab")  # blend both
control_chaser(executor_id=201, page=1, xfade_mode="a")   # incoming only
control_chaser(executor_id=201, page=1, xfade_mode="b")   # outgoing only
```

---

## Appearance

Color-code chasers for easy identification on the wing:

```python
label_or_appearance("sequence", 101, appearance_hsb=(120, 80, 100))  # green
label_or_appearance("executor", 201, appearance_hsb=(120, 80, 100))  # match
```

---

## Allowed Tools

```
list_sequences             — SAFE_READ: find free sequence slots
store_current_cue          — DESTRUCTIVE: store programmer as chase step
label_object               — DESTRUCTIVE: name sequence
assign_sequence_to_executor — DESTRUCTIVE: assign with /chaser flag
control_chaser             — SAFE_WRITE: set rate/skip/xfade on running chaser
set_executor_crossfade     — SAFE_WRITE: set blend between steps
manage_matricks            — SAFE_WRITE: interleave/offset for running lights
label_or_appearance        — DESTRUCTIVE: color-code executor and sequence
send_raw_command           — DESTRUCTIVE: direction and master assignment
```

---

## Safety

- Always use `ClearAll` between steps — residual values bleed into subsequent stores.
- Chaser flag cannot be set without `confirm_destructive=True` on the assign call.
- Speed above 300 BPM can cause flicker on power-limited rigs — warn the operator.
- MAtricks interleave state affects ALL subsequent stores until reset — call `MAtricksReset` when done.
- A 2-step strobe at 600 BPM = 5 Hz — check rig safety spec for strobe frequency limits.

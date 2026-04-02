---
title: Cue Tracking and Timing
description: Instruction module for grandMA2 cue tracking modes, Block/Unblock, MIB (Move In Black), cue timing layers, and tracking vs. non-tracking sequence configuration
version: 1.1.0
created: 2026-03-31T21:00:00Z
last_updated: 2026-03-31T22:00:00Z
---

# Cue Tracking and Timing

**Charter:** DESTRUCTIVE — configures cue tracking behavior, blocking, MIB, and timing
for grandMA2 sequences. These settings affect how values flow between cues.

Invoke when asked to: fix tracking bleed, block a cue, set cue timing, configure MIB,
switch between tracking and non-tracking, edit fade/delay times, or debug a cue that
shows "wrong" values.

---

## Core Concept: Tracking vs. Non-Tracking

| Mode | Behavior | Use for |
|------|----------|---------|
| **Tracking** (default) | Only changed values are stored per cue; unchanged values track from previous cues | Show programming — efficient, consistent |
| **Non-tracking** | All values stored in every cue | One-shot looks, simple busking sequences |

In tracking mode: if Fixture 1 is Red in Cue 1 and not touched in Cue 2, it stays Red
in Cue 2. This is intentional and correct tracking behavior.

---

## Part 1 — Tracking and Blocking

### Understanding "T" values in cue sheets

A value shown as **T** (Tracked) in a cue sheet means the value is inherited from a
previous cue. It is not stored in that cue — it flows forward from where it was set.

### Blocking a cue

A **block** stores all current tracked values into a specific cue, making it a "hard"
cue that does not depend on any previous cue.

```python
block_cue(
    sequence_id=99,
    cue_id=5,
    confirm_destructive=True,
)
```

This emits: `Assign Cue 5 Sequence 99 /block`

Use blocking when:
- A cue must look the same regardless of what ran before it
- You are creating a "reset" point in the show
- A sequence will be called via macro (no guarantee of playback order)

### Unblocking a cue

Removes the block flag so values flow freely from the previous cue again:

```python
unblock_cue(sequence_id=99, cue_id=5, confirm_destructive=True)
```

This emits: `Assign Cue 5 Sequence 99 /unblock`

### Setting sequence to non-tracking

```python
send_raw_command(
    "Assign Sequence 99 /tracking=off",
    confirm_destructive=True,
)
```

Non-tracking stores all values in every cue — useful for simple color sequences where
tracking behavior is unwanted.

---

## Part 2 — Timing Layers

Each cue has five timing slots:

| Layer | Controls | Attribute |
|-------|----------|-----------|
| **Fade** | Default fade time for all attributes | `FadeTime` |
| **Delay** | Time before fade starts | `DelayTime` |
| **In Fade** | Intensity fade-in time | `InFade` |
| **Out Fade** | Intensity fade-out (if different) | `OutFade` |
| **Snap** | Attributes that snap (no fade) | Snap flag per attribute |

### Setting cue timing via raw command

```
# Set cue 5 fade time to 2.5 seconds
Assign Cue 5 Sequence 99 /time=2.5

# Set delay + fade
Assign Cue 5 Sequence 99 /delay=1 /time=2.5

# Set separate in/out fade
Assign Cue 5 Sequence 99 /infade=3 /outfade=1
```

### Setting cue timing via store options

When storing a cue, include timing:
```
Store Cue 5 Sequence 99 /time 2.5
```

### Attribute-level timing

Some attributes (Pan/Tilt) need different fade times than color:

```python
# In programmer: set per-attribute timing
send_raw_command("Attribute \"Pan\" /time=3")
send_raw_command("Attribute \"Tilt\" /time=3")
# Then store — timing is saved with the cue
store_current_cue(sequence_id=99, cue_id=5, confirm_destructive=True)
```

---

## Part 3 — MIB (Move In Black)

MIB pre-positions moving heads while they are dark (dimmer at 0) so they arrive in the
correct position when the next cue fires.

### When to use MIB

- Any sequence where fixtures need to change position between cues
- Cues where large pan/tilt moves would be visible if done at full intensity

### Enable MIB on a sequence

```python
send_raw_command(
    "Assign Sequence 99 /mib=on",
    confirm_destructive=True,
)
```

Or per-cue:
```
Assign Cue 5 Sequence 99 /mib=on
```

### MIB options

| Option | Behavior |
|--------|---------|
| `mibalways` | Always pre-position, even when not dark |
| `mibnever` | Never pre-position (disable MIB) |
| `prepos` | Pre-position uses values from the cue after next |

```python
send_raw_command(
    "Assign Executor 1.201 /mibalways",
    confirm_destructive=True,
)
```

---

## Part 4 — Cue Modes and Triggers

### Trigger types

| Trigger | Behavior |
|---------|---------|
| `go` (default) | Advances on GO press |
| `time` | Auto-fires after cue's wait time |
| `follow` | Fires immediately after previous cue finishes |
| `sound` | Fires on audio beat (requires audio input) |
| `timecode` | Fires on SMPTE position (see timecode-show-programmer skill) |

```python
# Set cue 6 to auto-follow cue 5 with 0.5s wait
send_raw_command("Assign Cue 6 Sequence 99 /trigger=follow /wait=0.5")
```

### Loop a range of cues

```python
send_raw_command(
    "Assign Cue 3 Sequence 99 /loop=2",  # loop back to cue 2 after cue 3
    confirm_destructive=True,
)
```

---

## Part 5 — Update vs. Store

### Update: Change stored values without re-storing the whole cue

```
# Recall preset into programmer (stores a preset reference, not a raw value)
Preset 4.6                    # Cyan — color preset pool
# Update cue 5 with the preset reference
Update Cue 5 Sequence 99
```

`Update` merges only programmer changes into the existing cue — no `confirm_destructive`
needed for `Update` (SAFE_WRITE tier).

**Important:** Always recall a `Preset N.M` before `Update`. Using raw `attribute … at N`
stores a raw value in the cue and breaks the preset-update chain — future edits to the
preset will not propagate to that cue.

### Store /merge vs. /overwrite vs. /remove

| Flag | Effect |
|------|--------|
| `/merge` (default) | Adds/updates values; preserves unmentioned attributes |
| `/overwrite` | Replaces the entire cue with current programmer content |
| `/remove` | Removes the stored attribute from the cue (value becomes tracked) |

```python
store_current_cue(
    sequence_id=99,
    cue_id=5,
    options=["merge"],       # or "overwrite"
    confirm_destructive=True,
)
```

---

## Allowed Tools

```
list_cues                  — SAFE_READ: inspect cue list and tracking status
get_cue_info               — SAFE_READ: read timing and flags for a specific cue
block_cue                  — DESTRUCTIVE: hard-block a cue's tracked values
unblock_cue                — DESTRUCTIVE: remove block flag
store_current_cue          — DESTRUCTIVE: store/merge/overwrite cue
send_raw_command           — DESTRUCTIVE: timing/trigger/MIB attribute assignment
```

---

## Diagnosing Tracking Issues

### Symptom: fixture shows wrong color in cue N

1. Run `list_cues(sequence_id=99)` — look for "T" on the attribute in question
2. Trace back to the cue where the value was last set (most recent non-T entry)
3. If a mid-show "reset" cue is needed, block it: `block_cue(99, N)`
4. If the value should NOT track from a prior cue, add it explicitly in cue N

### Symptom: moving head arrives late at position

MIB is off. Enable with `Assign Sequence 99 /mib=on`. Ensure dimmer goes to 0 at end
of previous cue so MIB can move.

---

## Safety

- `block_cue` is DESTRUCTIVE — it stores many values into the cue; only block when intentional.
- `unblock_cue` can expose previously-hidden tracking dependencies — test in blind mode first.
- MIB requires `mibalways` flag if fixtures never go fully dark between cues.
- Non-tracking mode doubles cue storage requirements — avoid for large rigs.
- `Update` writes to the currently running cue — use in blind mode to preview safely.

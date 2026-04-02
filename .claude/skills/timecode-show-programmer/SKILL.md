---
title: Timecode Show Programmer
description: Instruction module for building a grandMA2 SMPTE timecode show — creating the pool object, mapping cue triggers to SMPTE positions, and managing playback
version: 1.0.0
created: 2026-03-31T18:00:00Z
last_updated: 2026-03-31T18:00:00Z
---

# Timecode Show Programmer

**Charter:** DESTRUCTIVE — creates timecode pool objects and maps cue triggers to
SMPTE time positions. Used when building a fully timecoded automated show.

Invoke when asked to: build a timecode show, map cues to SMPTE times, create a
timecode track, trigger cues from a SMPTE signal, or automate a cue list to audio.

---

## Core Concept: Timecode Pool Object vs. Timecode Events

These are two distinct things — confusing them is the most common mistake:

| What | MA2 command | MCP tool | Purpose |
|------|------------|----------|---------|
| **Timecode pool object** | `store timecode N` | `store_object(object_type="timecode")` | Creates the named timecode track slot |
| **Timecode event (trigger)** | `assign timecode N cue C sequence S "HH:MM:SS:FF"` | `store_timecode_event` | Adds a cue trigger at a SMPTE position |

Always create the pool object first, then add events to it.

---

## SMPTE Position Format

All positions use the format `HH:MM:SS:FF` — four colon-separated fields, zero-padded:

| Field | Meaning | Range |
|-------|---------|-------|
| HH | Hours | 00–23 |
| MM | Minutes | 00–59 |
| SS | Seconds | 00–59 |
| FF | Frames | 00–24 (25fps) or 00–29 (30fps) |

Examples:
- `"00:01:30:12"` = 1 minute, 30 seconds, 12 frames
- `"00:00:00:00"` = time zero (beginning of show)
- `"01:15:00:00"` = 1 hour, 15 minutes

**Standard frame rates:** 25fps (Europe/PAL), 30fps (US/NTSC), 24fps (film).
Confirm the frame rate with the sound engineer before mapping events.

---

## Workflow

### Step 1 — Discover free timecode slots

```
list_timecode_events()
```

Inspect the raw_response to find which slot IDs are already occupied.
Pick the first free slot (typically 1 if the pool is empty).

---

### Step 2 — Create the timecode pool object

```python
store_object(
    object_type="timecode",
    object_id=1,           # slot number
    name="Show Master",    # optional label
    confirm_destructive=True,
)
```

This emits `store timecode 1` followed by `label timecode 1 "Show Master"`.

Alternatively, use `send_raw_command` with `confirm_destructive=True`:
```
store timecode 1
label timecode 1 "Show Master"
```

---

### Step 3 — Add cue trigger events

For each cue in the cue list that must fire at a SMPTE position:

```python
store_timecode_event(
    timecode_id=1,
    cue_id=1,
    sequence_id=99,
    timecode_position="00:00:10:00",   # fires cue 1 at 10 seconds
    confirm_destructive=True,
)
```

This emits: `assign timecode 1 cue 1 sequence 99 "00:00:10:00"`

Repeat for every cue trigger in the show:

| SMPTE position | Cue | Action |
|---------------|-----|--------|
| 00:00:10:00 | 1 | Opening wash |
| 00:00:45:00 | 2 | First color change |
| 00:01:20:12 | 3 | Spot pick |
| 00:02:00:00 | 4 | Blackout |

---

### Step 4 — Verify event list

```
list_timecode_events()
```

Confirm the slot appears with the correct event count. For detailed event
inspection, use `navigate_console` to cd into the timecode pool:
```
cd /
cd Timecode
list
```

---

### Step 5 — Start timecode playback

```python
control_timecode(
    action="start",
    timecode_id=1,
)
```

This emits `go timecode 1`. The console begins reading SMPTE from the
configured input and firing cues as position triggers are reached.

**SMPTE input must be connected** — if no external SMPTE source is present,
the console will not advance the timecode position.

---

### Step 6 — Jump to a specific position (for testing)

```python
control_timecode(
    action="goto",
    timecode_id=1,
    timecode_position="00:01:00:00",
)
```

This emits `goto timecode 1 "00:01:00:00"`. Use this to test trigger points
without playing the full show from the beginning.

---

### Step 7 — Stop timecode playback

```python
control_timecode(
    action="stop",
    timecode_id=1,
)
```

This emits `off timecode 1`.

---

## Timecode ID vs. Timecode Slot ID

The grandMA2 pool has two numbering concepts:

- **Pool slot** (`timecode_id`): The user-visible slot number (1, 2, 3…). This is
  what you pass to `store_timecode_event` and `control_timecode`.
- **Internal ID**: The console-internal UUID. Ignore this — only use slot numbers.

`list_timecode_events()` returns the slot numbers in its raw_response.

---

## Allowed Tools

```
list_timecode_events      — SAFE_READ: discover free slots
store_object              — DESTRUCTIVE: create timecode pool slot + label
store_timecode_event      — DESTRUCTIVE: add cue trigger at SMPTE position
control_timecode          — SAFE_WRITE: start / stop / goto timecode playback
send_raw_command          — DESTRUCTIVE: fallback for direct MA2 commands
```

Do NOT use `store_cue` for timecode events — those store cue data, not time triggers.
Do NOT use `go_sequence` for timecode playback — use `control_timecode(action="start")`.

---

## Safety

- `store_object` and `store_timecode_event` are DESTRUCTIVE — always require
  `confirm_destructive=True`.
- Print intent before each store: `"Adding trigger: cue {C} sequence {S} at {pos}"`
- Never auto-set `confirm_destructive=True`.
- Save show after completing the timecode map: `save_show(confirm_destructive=True)`.
- If position format is wrong (not `HH:MM:SS:FF`), the MA2 console will reject
  the assign command with an ILLEGAL ARGUMENT error. Validate format before sending.

---

## Complete Example: 4-cue timecode show

```python
# 1. Create pool slot
store_object("timecode", 1, name="Song A", confirm_destructive=True)

# 2. Map triggers
events = [
    (1, "00:00:05:00"),   # cue 1 at 5 seconds
    (2, "00:00:30:00"),   # cue 2 at 30 seconds
    (3, "00:01:00:00"),   # cue 3 at 1 minute
    (4, "00:01:45:00"),   # cue 4 (blackout) at 1:45
]
for cue_id, pos in events:
    store_timecode_event(1, cue_id, sequence_id=99,
                         timecode_position=pos, confirm_destructive=True)

# 3. Test jump to cue 3
control_timecode("goto", timecode_id=1, timecode_position="00:01:00:00")

# 4. Start
control_timecode("start", timecode_id=1)
```

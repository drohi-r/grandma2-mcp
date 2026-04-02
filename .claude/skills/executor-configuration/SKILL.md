---
title: Executor Configuration
description: Instruction module for configuring grandMA2 executors — trigger types, priority levels, start/stop modes, special masters, fader function, and wing layout
version: 1.0.0
created: 2026-03-31T21:00:00Z
last_updated: 2026-03-31T21:00:00Z
---

# Executor Configuration

**Charter:** DESTRUCTIVE — assigns options, priority, trigger types, and fader functions
to grandMA2 executors. Changes to executor configuration affect live playback behavior.

Invoke when asked to: set executor priority, configure a flash button, change trigger type,
assign a speed master to a fader, set autostart, configure kill protect, or assign GO+ mode.

---

## Core Concept: Executor vs. Sequence

The **sequence** stores the cue data. The **executor** is the hardware button/fader
slot that plays it back. Configuration lives on the executor (not the sequence):

| Stored on | Examples |
|-----------|---------|
| **Sequence** | cue data, cue labels, tracking mode, MIB |
| **Executor** | priority, trigger, start/stop options, fader function, appearance |

An executor is addressed as `[page].[exec_number]` (e.g., `1.201`).

---

## Part 1 — Priority

Controls how the executor competes with other playbacks for LTP (Latest Takes Precedence).

| Priority | cmd_value | Behavior |
|----------|-----------|---------|
| Super | `super` | Overrides everything including programmer |
| Swap | `swap` | LTP + negative override |
| HTP | `htp` | Highest intensity wins |
| High | `high` | Overrides Normal and Low |
| Normal | `normal` | Default LTP |
| Low | `low` | Overridden by everything else |

```python
send_raw_command(
    "Assign Executor 1.201 /priority=high",
    confirm_destructive=True,
)
```

**Warning:** HTP changes intensity priority for ALL attributes on that executor.
Use HTP only for pure intensity submasters, not for multi-attribute playbacks.

**Super priority** should be reserved for blackout and emergency executors only.

---

## Part 2 — Start and Stop Options

### Start options

| Option | Behavior |
|--------|---------|
| `autostart` | Sequence starts when fader is raised above 0 |
| `autostop` | Sequence stops when fader returns to 0 |
| `autostomp` | Overrides all lower-priority executors on start |
| `autofix` | Pre-positions fixtures in blind when executor is active |
| `restart` | Go back to cue 1 when executor restarts |

```python
send_raw_command(
    "Assign Executor 1.201 /autostart /autostop",
    confirm_destructive=True,
)
```

### Combining options

Options stack — apply multiple in one command:

```
Assign Executor 1.201 /autostart /autostop /restart /priority=normal
```

---

## Part 3 — Trigger Types

| Trigger | Value | Behavior |
|---------|-------|---------|
| Go | `go` | Fader = intensity; GO button advances cues |
| Temp | `temp` | Fader controls intensity only while held; releases on let-go |
| Flash | `flash` | Button flashes to full on press, returns on release |
| Top | `top` | Goes to last cue immediately |
| Kill | `kill` | Kills (releases) all other executors on the same page |

```python
send_raw_command(
    "Assign Executor 1.205 /trigger=flash",
    confirm_destructive=True,
)
```

---

## Part 4 — Fader Function

Controls what the physical fader does (beyond just intensity):

| Function | Behavior |
|----------|---------|
| `master` (default) | Fader = intensity/output level |
| `speed` | Fader controls speed of an effect/chaser |
| `rate` | Fader controls rate multiplier (0-200%) |
| `crossfade` | Fader controls crossfade between steps |
| `zoom` | Fader controls Zoom attribute |

```python
send_raw_command(
    "Assign Executor 1.201 /fader=rate",
    confirm_destructive=True,
)
```

**Speed master workflow:** Assign fader=speed on executor 210 (empty executor),
then assign target chasers to reference `speedmaster=speed1`:

```python
send_raw_command("Assign Executor 1.210 /fader=speed", confirm_destructive=True)
send_raw_command("Assign Executor 1.201 /speedmaster=speed1", confirm_destructive=True)
```

Now executor 210's fader globally controls the speed of executor 201.

---

## Part 5 — Protect Options

Prevent accidental kills and overwrites:

| Option | Behavior |
|--------|---------|
| `killprotect` | This executor cannot be killed by a Kill executor |
| `swopprotect` | This executor cannot be stomped by a Swap/Stomp executor |
| `ooo` | Out-Of-Order: marks executor as reserved (dimmed in pool) |

```python
send_raw_command(
    "Assign Executor 1.201 /killprotect",
    confirm_destructive=True,
)
```

---

## Part 6 — Special Masters

Special masters are system-wide control executors that affect everything:

| Master | Affects |
|--------|---------|
| `grandmaster` | All intensity output globally |
| `playbackmaster` | All playback executor outputs |
| `speed1`–`speed16` | Speed of any executor assigned to that speed group |
| `rate1`–`rate16` | Rate multiplier for any executor assigned to that rate group |

```python
set_special_master(master="grandmaster", value=80)   # 80% grand master
set_special_master(master="speed1", value=120)       # 120 BPM for speed group 1
```

---

## Part 7 — GO+ (Autoforward) Configuration

```python
send_raw_command(
    "Assign Executor 1.201 /autogo=1",  # auto-advance 1 step per trigger
    confirm_destructive=True,
)
```

For timecode-driven sequences, set trigger to timecode:
```
Assign Executor 1.201 /trigger=timecode
```

---

## Part 8 — Executor Layout and Appearance

```python
label_or_appearance(
    "executor",
    201,
    name="Wash Color",
    appearance_hsb=(200, 80, 100),  # blue
)
```

Wing layout conventions:
- Executors 1-100: main left wing (main sequences and masters)
- Executors 101-200: effect wing (busking effects)
- Executors 201-300: color wing (color sequences and presets)

---

## Discovery Workflow

Before configuring executors, audit what is already assigned:

```python
get_executor_state(executor_id=201)     # see current config + assigned sequence
list_executor_pages()                   # see all pages and fader assignments
```

---

## Allowed Tools

```
get_executor_state         — SAFE_READ: read current executor config and state
list_executor_pages        — SAFE_READ: audit wing layout
assign_sequence_to_executor — DESTRUCTIVE: assign sequence with options
set_special_master         — SAFE_WRITE: adjust grand/playback/speed masters
label_or_appearance        — DESTRUCTIVE: name and color-code executor
send_raw_command           — DESTRUCTIVE: set priority/trigger/fader/protect options
```

---

## Safety

- `priority=super` can override the programmer — operators lose control. Reserve for blackout only.
- `autostomp` will kill lower-priority executors silently — warn operator before enabling.
- `trigger=kill` will release ALL other executors on the same page when fired. Double-check page.
- Speed masters affect all assigned chasers globally — a value of 0 stops all assigned chasers.
- Fader function changes take effect immediately on a live system — use blind mode if possible.
- Protect flags survive show saves — always document which executors are kill-protected.

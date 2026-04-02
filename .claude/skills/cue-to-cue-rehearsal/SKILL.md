---
title: Cue-to-Cue Rehearsal
description: Guided cue-by-cue sequence walkthrough with state summaries and cue diffs for rehearsal
version: 1.0.0
safety_scope: SAFE_WRITE
created: 2026-04-02T00:00:00Z
last_updated: 2026-04-02T00:00:00Z
---

# Cue-to-Cue Rehearsal

## Charter

SAFE_WRITE skill — uses playback control (Go, GoBack, Goto) to walk through a sequence. Does not store, delete, or modify any cues.

## Invocation

Use when an operator or director wants to walk through a cue sequence step by step during technical rehearsal. Each cue is presented with a summary of what changes.

## Target Users

Lighting designers, stage managers, and technical directors running cue-to-cue rehearsals.

---

## Setup Phase (SAFE_READ)

1. Ask the operator for the **sequence ID** or **executor ID** to rehearse
2. Call `list_sequence_cues(sequence_id=N)` to get all cues
3. Present the cue list overview: total cues, numbering range, any labels
4. Confirm with operator before starting playback

---

## Rehearsal Loop (SAFE_WRITE)

### Go to First Cue

1. Call `load_cue` or `playback_action(action="goto", cue_id=FIRST, sequence_id=N)` to load cue 1
2. Present: "Now at Cue [N] — [label if any]"

### On "next" / "go"

1. Call `playback_action(action="go")` or `execute_sequence(sequence_id=N)` to advance
2. Call `compare_cue_values(sequence_id=N, cue_a=PREVIOUS, cue_b=CURRENT)` to show the diff
3. Present:
   - Current cue number and label
   - What changed from the previous cue (diff output)
   - Cue timing if available (fade, delay)

### On "back"

1. Call `playback_action(action="goback")` to go back one cue
2. Show the same diff but in reverse

### On "goto [number]"

1. Call `playback_action(action="goto", cue_id=NUMBER, sequence_id=N)` to jump
2. Show the cue state

### On "status" / "where am I"

1. Call `get_executor_status` to show current cue, next cue, and executor state
2. Call `list_sequence_cues` with `cue_id=CURRENT` to confirm existence

---

## End of Rehearsal

When the operator says "done" or reaches the last cue:

1. Present a summary: cues reviewed, total cues in sequence
2. Ask if they want to reset to cue 1 or leave the executor at current state

---

## Allowed Tools

**SAFE_READ:** `list_sequence_cues`, `compare_cue_values`, `get_executor_status`

**SAFE_WRITE:** `playback_action`, `execute_sequence`, `load_cue`

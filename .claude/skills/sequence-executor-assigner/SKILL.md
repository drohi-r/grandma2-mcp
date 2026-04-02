---
title: Sequence Executor Assigner
description: Worker instruction module for assigning a grandMA2 sequence to a free executor so it appears as a playback fader on the console
version: 1.0.0
created: 2026-03-31T21:52:55Z
last_updated: 2026-03-31T21:52:55Z
---

# Sequence Executor Assigner

**Worker charter:** DESTRUCTIVE — assigns a sequence to an executor slot, making it
appear as a playback fader on the console. The sequence must already exist in the show.

Invoke when asked to: assign a sequence to an executor, place a sequence on a fader,
mount a sequence onto a playback slot, or make a sequence accessible on stage.

---

## Core MA2 Concept: Executors and Assignment

A sequence exists in the pool but is **invisible on the console** until it is assigned
to an executor. Executors are numbered slots (1–240 per page) that correspond to
physical faders and buttons on the desk or the touch screen.

```
Sequence N (pool, invisible)
     |
     | Assign Sequence N At Executor E
     v
Executor E on current page (fader + buttons visible)
```

Once assigned:
- Fader controls intensity / master level
- Go button steps through cues
- Release removes the sequence from the programmer

---

## Executor ID Convention

- Test/demo objects in this repo use executor **201** to avoid colliding with real show data
- Default to 201 unless the operator passes an explicit executor ID or 201 is already occupied

---

## Allowed Tools

```
get_executor_status      (SAFE_READ  — list all executors or a specific one)
assign_object            (DESTRUCTIVE — assign sequence to executor)
```

DESTRUCTIVE tools used: `assign_object` with `confirm_destructive=True`.
No preset mutations, no cue edits, no macro changes.

---

## Steps

### 1. Detect a free executor

Call `get_executor_status()` (no args) to list all executors.

Parse the response to find executors with **no sequence assigned**:
- A line is "occupied" if it contains `Sequence=` or `Seq N` in the name/value columns
- Default target: executor 201 (unless explicitly provided or occupied)

If the desired executor is occupied → report it and fall back to the lowest free ID.

---

### 2. Assign the sequence

Call:

```python
assign_object(
    mode="assign",
    source_type="sequence",
    source_id=<sequence_id>,
    target_type="executor",
    target_id=<executor_id>,
    confirm_destructive=True,
)
```

This sends: `Assign Sequence <sequence_id> At Executor <executor_id>`

---

### 3. Verify the assignment

Call `get_executor_status(executor_id=<executor_id>)` and check that the response
contains a reference to the sequence number (e.g. `Seq 99` or `Sequence=99`).

- If confirmed → emit `{"kind": "ok", "detail": "Executor E assigned Sequence N"}`
- If not found → emit `{"kind": "error", "detail": "Assignment not confirmed"}`

---

### 4. Compress findings

Return only:

```json
{
  "summary": "Assigned Sequence N to Executor E",
  "findings": [],
  "assignment": {
    "sequence_id": 99,
    "executor_id": 201,
    "confirmed": true
  },
  "state_changes": [
    "Executor 201: Sequence 99 assigned (color palette fader)"
  ],
  "recommended_actions": [
    "Press Go on Executor 201 to step through the 8 color cues",
    "Edit Preset 4.1 to change the Red hue live (reference update)"
  ],
  "confidence": "high"
}
```

---

## Safety Escalation

Before executing Step 2, confirm `confirm_destructive=True` was explicitly passed.
Print: `"About to assign Sequence N to Executor E"`.
If not set → abort with `{"blocked": true, "reason": "confirm_destructive required"}`.

Never auto-set `confirm_destructive=True`.

---
title: Tracking Debugger
description: Diagnose and repair tracking leaks, unexpected blocks, and cue inheritance issues in grandMA2 sequences
version: 1.0.0
safety_scope: SAFE_READ
created: 2026-04-02T00:00:00Z
last_updated: 2026-04-02T00:00:00Z
---

# Tracking Debugger

## Charter

SAFE_READ skill — analyzes cue data without modifying the show. Recommends Block/Unblock actions but does not execute them.

## Invocation

Use when a lighting designer reports "cue X looks wrong" or "values are bleeding into later cues" or "my blackout cue isn't fully dark."

## Diagnostic Workflow

### Step 1: Scan for Leaks
Call `detect_tracking_leaks(sequence_id=N)` to find attributes that persist across adjacent cues without explicit sets.

### Step 2: Diff Suspicious Cues
For each leak reported, call `diff_cues(sequence_id=N, cue_a=LEAK_FROM, cue_b=LEAK_TO)` to see exactly what values are shared.

### Step 3: Identify Root Cause
- **Tracking forward**: A value set in cue 5 appears in cue 6+ because no later cue sets it differently. This is normal MA2 tracking — it's only a "leak" if unintended.
- **Missing block**: Cue should isolate values but doesn't have a Block marker.
- **Stale MIB**: Move In Black prepositioned a fixture but the cue that should use it was deleted.

### Step 4: Recommend Fixes
- **Block the cue**: `block_unblock_cue(action="block", cue_id=N, sequence_id=S)` — stops tracking at that cue
- **Unblock and re-track**: If block was applied too aggressively, unblock to let tracking resume
- **Insert a reset cue**: For blackout/reset looks, explicitly set all attributes to zero

## Allowed Tools

`detect_tracking_leaks`, `diff_cues`, `list_sequence_cues`, `compare_cue_values`, `block_unblock_cue`

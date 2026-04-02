---
title: Show Health Check
description: Worker instruction module for pre-show show file auditing — cue gaps, preset references, executor assignments, showfile integrity, and park ledger review. Returns GREEN/AMBER/RED per category.
version: 1.0.0
created: 2026-04-01T00:00:00Z
last_updated: 2026-04-01T00:00:00Z
---

# Show Health Check

**Worker charter:** SAFE_READ only. No mutations. Universal pre-show diagnostic for any operator, rental house, or production manager.

Invoke when asked to: run a pre-show check, audit show health, verify showfile integrity, or produce a readiness report.

---

## What This Audits (6 categories)

1. **Showfile** — correct show loaded, unchanged since last programmer session
2. **Preset Pool** — required preset types have content; no empty mandatory slots
3. **Executor Assignments** — all expected sequences are assigned; no unassigned slots
4. **Cue Integrity** — cue gaps, unlabeled cues, cues with zero fade on timed triggers
5. **Park Ledger** — any unexpectedly parked fixtures
6. **DMX** — patch summary (fixture count, universe utilization)

---

## Health Score Scale

| Score | Meaning |
|-------|---------|
| GREEN | No findings in this category |
| AMBER | Non-blocking findings — show will run but may have issues |
| RED | Blocking findings — show should not go live without addressing |

---

## Step-by-Step Workflow

**Step 1 — Showfile check (GREEN/RED)**
```python
get_showfile_info()            # record show name + version
assert_showfile_unchanged()    # RED if showfile changed since hydration baseline
```

**Step 2 — Hydrate**
```python
hydrate_console_state()
state = get_console_state()
```

**Step 3 — Preset pool check (GREEN/AMBER)**

For each preset type (Dimmer, Position, Gobo, Color, Beam):
```python
list_preset_pool(preset_type="color")
```
Flag AMBER if any expected preset type pool is empty.
Flag AMBER if any preset slot referenced in a cue returns "not found" from `assert_preset_exists`.

**Step 4 — Executor check (GREEN/AMBER/RED)**
```python
get_executor_detail(executor_id="1.1")  # repeat for key executors
```
Flag AMBER if executor has no assigned sequence.
Flag RED if executor marked as main sequence has no cues.

**Step 5 — Cue audit (GREEN/AMBER)**

For each main sequence:
```python
query_object_list(object_type="sequence", object_id=N)
```
Apply cue-list-auditor logic: gaps > 10 = AMBER, unlabeled cues = AMBER, zero fade on timed sequence = AMBER.

**Step 6 — Park ledger (GREEN/AMBER)**
```python
get_park_ledger()
```
Flag AMBER if any fixtures are parked (may be intentional — report, don't assume error).

**Step 7 — DMX summary (GREEN/AMBER)**
```python
list_universes()
list_fixtures()
```
Flag AMBER if any fixture has no DMX address (unpatched fixture in show).

---

## Output Format

```json
{
  "show_name": "MyShow_v3",
  "audit_timestamp": "2026-04-01T19:00:00Z",
  "overall": "AMBER",
  "categories": {
    "showfile": {"score": "GREEN", "findings": []},
    "preset_pool": {"score": "AMBER", "findings": ["Color preset pool has only 2 of expected 8 entries"]},
    "executor_assignments": {"score": "GREEN", "findings": []},
    "cue_integrity": {"score": "AMBER", "findings": ["Sequence 1: gap between cues 5 and 10"]},
    "park_ledger": {"score": "GREEN", "findings": []},
    "dmx": {"score": "GREEN", "findings": []}
  },
  "recommended_actions": ["Populate color preset slots 3-8 before show", "Investigate cue gap in sequence 1"]
}
```

Overall score = worst score across all categories.

---

## Allowed Tools

```
get_showfile_info, assert_showfile_unchanged, hydrate_console_state, get_console_state,
list_preset_pool, assert_preset_exists, get_executor_detail, query_object_list,
get_park_ledger, list_universes, list_fixtures, list_system_variables
```

No DESTRUCTIVE tools. Report findings only — never auto-fix.

---

## Recompute Rule

Store a `DecisionCheckpoint` after each category completes:

```json
{
  "fault": "show_health_check_<category>",
  "query": "list_preset_pool / query_object_list / etc.",
  "observed_at": "<timestamp>",
  "fresh_for_seconds": 120,
  "replay": "<same tool call>"
}
```

If re-invoked within `fresh_for_seconds`, return the cached finding instead of re-querying.

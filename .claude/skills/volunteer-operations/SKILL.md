---
title: Volunteer Operations
description: Instruction module for volunteer operators — SAFE_READ guided console orientation, Sunday morning preflight, and tiered access model for non-programmers
version: 1.0.0
created: 2026-04-01T00:00:00Z
last_updated: 2026-04-01T00:00:00Z
---

# Volunteer Operations

**Worker charter:** Primarily SAFE_READ. Volunteers operating under this skill may use SAFE_WRITE for guided single-cue updates. All DESTRUCTIVE operations are reserved for the Technical Director.

Invoke when asked to: run a preflight check, orient a new volunteer operator, verify the show before service, or guide a trained volunteer through a supervised playback operation.

Target users: Church technical directors training volunteers, venue staff onboarding new operators, IATSE training programs, any production environment with tiered staff skill levels.

---

## Allowed Tools

```
SAFE_READ (any volunteer):
  get_showfile_info, assert_showfile_unchanged, hydrate_console_state,
  get_console_state, list_preset_pool, assert_preset_exists, get_executor_detail,
  query_object_list, list_system_variables, get_console_location

SAFE_WRITE (trained volunteer, under supervision):
  playback_action, set_intensity, goto_cue, select_executor

DESTRUCTIVE (TD only — never delegate):
  store_current_cue, delete_object, partial_show_read, save_show,
  assign_sequence_to_executor, patch_fixture, store_new_preset
```

---

## The Three-Tier Access Model for Volunteers

| Tier | Who | What They Can Do |
|------|-----|-----------------|
| **SAFE_READ** | Any new volunteer | See console state, verify show is correct, confirm preset pool and executor assignments — zero risk |
| **SAFE_WRITE** | Trained volunteer | Apply presets, trigger go/pause, adjust fader levels — with guidance |
| **DESTRUCTIVE** | Technical Director only | Store cues, modify show file, change patch — never delegated without explicit TD authorization |

The GrandPA2-Buddy safety gate enforces these tiers automatically. A volunteer without DESTRUCTIVE scope cannot accidentally overwrite a cue, delete a fixture, or store a new preset — the system physically prevents it.

---

## Steps: Sunday Morning Preflight (SAFE_READ — any volunteer)

Run this sequence every Sunday before doors open.

**Step 1 — Verify the show**

```
get_showfile_info()          — confirm show name matches expected
assert_showfile_unchanged()  — confirm show hasn't been modified since TD last worked
```

Expected: show name matches the current series title. If wrong: STOP, call TD.

**Step 2 — Hydrate state**

```
hydrate_console_state()   — snapshot all show-memory gaps
get_console_state()       — review: park ledger, filter state, world state
```

Check: no unexpected parked fixtures, no active filter, correct world assigned. Any unexpected parked fixture or active filter is AMBER — report to TD before service.

**Step 3 — Verify preset pool**

```
list_preset_pool(preset_type="color")     — confirm color presets 1-N exist
list_preset_pool(preset_type="position")  — confirm position presets exist
assert_preset_exists(preset_type="color", preset_id=1)   — spot check
```

**Step 4 — Verify executor assignments**

```
get_executor_detail(executor_id="1.1")   — first executor on page 1
get_executor_detail(executor_id="1.2")   — spot check others
```

Confirm: sequences are assigned, priority is Normal or High (not Super unless intended). Super priority overrides all other playbacks — flag as AMBER if unexpected.

**Step 5 — Cue check**

```
query_object_list(object_type="sequence", object_id=1)   — list cues in main sequence
```

Confirm: correct number of cues, first cue is labeled correctly.

**Step 6 — Generate preflight report**

Summarize all checks as GREEN / AMBER / RED:

```json
{
  "show_name": "<name>",
  "show_unchanged": true,
  "park_ledger_clean": true,
  "filter_state": "none",
  "preset_pool_ok": true,
  "executor_assignments_ok": true,
  "cue_count": 0,
  "findings": [],
  "overall": "GREEN"
}
```

Present AMBER or RED findings to TD before opening doors. Do not proceed with AMBER or RED without TD sign-off.

---

## Steps: Guided Playback (SAFE_WRITE — trained volunteer)

Only run these steps if the Technical Director has explicitly authorized SAFE_WRITE access for this session.

- Use `playback_action(executor_id, action="go")` to advance cues
- Use `playback_action(executor_id, action="pause")` to pause
- Use `set_intensity(fixture_selection, value)` for manual dimmer adjustments ONLY when explicitly directed by TD
- Never use `store_current_cue`, `delete_object`, or `partial_show_read` — these require TD authorization

---

## What to Do When Things Go Wrong

1. **Wrong look on stage**: Do NOT try to fix it. Note the cue number and call TD.
2. **Console unresponsive**: Check Telnet connection with `get_console_location()`. If error, notify TD.
3. **Executor shows wrong color**: Run `get_executor_detail(executor_id)` and report findings to TD.
4. **Show file looks different**: Run `assert_showfile_unchanged()`. If it fails, STOP all changes, call TD immediately.
5. **Error message from any tool**: Screenshot it, stop operating, call TD.

When in doubt, do nothing and call the TD. A paused show is better than a corrupted show.

---

## Multi-Campus Notes

Each campus runs its own console. The show file should be named identically across campuses (e.g., `EasterSeries_2026_v3`). Before service, verify `get_showfile_info()` shows the same show name and version across all consoles. Discrepancies must be resolved by the TD before service, not during.

---

## Recompute Rule

Store a `DecisionCheckpoint` after the preflight hydration:

```json
{
  "fault": "volunteer_preflight",
  "query": "hydrate_console_state",
  "observed_at": "<timestamp>",
  "fresh_for_seconds": 120,
  "replay": "hydrate_console_state"
}
```

If a second volunteer runs preflight within 2 minutes, return the cached result rather than re-querying. Console state during preflight is stable — a 2-minute cache avoids redundant Telnet load.

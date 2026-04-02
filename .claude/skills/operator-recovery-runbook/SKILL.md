---
title: Operator Recovery Runbook
description: Incident response procedures for stuck playback, contaminated programmer, wrong world/filter, and other on-site emergencies
version: 1.0.0
safety_scope: SAFE_READ
created: 2026-04-02T00:00:00Z
last_updated: 2026-04-02T00:00:00Z
---

# Operator Recovery Runbook

## Charter

SAFE_READ skill — diagnoses the problem without making changes. Recovery actions are recommended with exact commands but require operator confirmation.

## Invocation

Use when something goes wrong during a show: fixtures not responding, wrong look on stage, stuck executor, or operator reports "it's broken."

## Emergency Triage

### Step 1: Capture Incident State
Call `incident_snapshot()` to freeze the current console state. This records showfile, page, modes, selection, parks, and recent errors — critical for post-incident review.

### Step 2: Check Programmer Contamination
Call `detect_programmer_contamination()` to identify leftover state:
- Selected fixtures bleeding into cues
- Highlight/Freeze/Solo modes still on
- Wrong World or Filter active
- MAtricks affecting selection

### Step 3: Route to Recovery Procedure

---

## Recovery: Contaminated Programmer
**Symptoms:** Cues look wrong, unexpected values on stage.

1. `ClearAll` — clears programmer, selection, and MAtricks
2. `Blind Off` — ensures we're in Live mode
3. `Highlight Off` — turns off highlight
4. `Freeze Off` — turns off freeze
5. Verify with `detect_programmer_contamination()` — should now be clean

---

## Recovery: Stuck Executor
**Symptoms:** Executor won't Go, release, or respond to fader.

1. Call `get_executor_status(executor_id=X)` to read state
2. Try `Release Executor {page}.{id}` — force release
3. If still stuck, try `Off Executor {page}.{id}` — force off
4. If still stuck, try `Kill Executor {page}.{id}` — force kill (breaks fade)
5. Last resort: `ClearAll` then re-trigger the sequence

---

## Recovery: Parked Fixtures
**Symptoms:** Some fixtures not responding, others work fine.

1. Call `get_park_ledger` to see which fixtures are parked
2. For each parked fixture: `unpark_fixture(fixture_id=N)`
3. Verify with `diagnose_no_output(fixture_id=N)`

---

## Recovery: Wrong World/Filter Active
**Symptoms:** Some fixtures invisible, unexpected attribute filtering.

1. Call `detect_programmer_contamination()` — check active_world and active_filter
2. To reset: `World 0` (default world, all fixtures visible)
3. To clear filter: `MAtricksFilter Off` or select World 0

---

## Recovery: Blackout Won't Release
**Symptoms:** Stage is dark, nothing responds.

1. Check Grand Master: `control_special_master(master="grandmaster", value=100)`
2. Check Blackout: `blackout_toggle()` to toggle B.O. off
3. Check if all executors are at zero: `scan_page_executor_layout(page=1)`

---

## Post-Incident

After recovery, always:
1. Call `incident_snapshot()` again to document the resolved state
2. Save the show: `save_show`
3. Brief the next operator on what happened

## Allowed Tools

`incident_snapshot`, `detect_programmer_contamination`, `get_executor_status`, `diagnose_no_output`, `get_park_ledger`, `scan_page_executor_layout`, `control_special_master`, `blackout_toggle`

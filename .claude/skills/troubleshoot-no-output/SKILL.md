---
title: Troubleshoot No Output
description: Diagnostic tree for fixtures not producing light — systematic checks from Grand Master to DMX cable
version: 1.0.0
safety_scope: SAFE_READ
created: 2026-04-02T00:00:00Z
last_updated: 2026-04-02T00:00:00Z
---

# Troubleshoot No Output

## Charter

SAFE_READ skill — performs only non-destructive inspection. No console state is modified.

## Invocation

Use when an operator reports "fixtures aren't responding" or "no light output." This skill systematically checks every possible cause from software to hardware.

## Target Users

Any operator — from volunteer to technical director. The diagnostic steps are safe for all access levels.

---

## Diagnostic Steps

Work through these checks in order. Stop as soon as you find the cause.

### Step 1: Grand Master and Blackout

Call `diagnose_no_output` to run the automated check. Also:

- Check if Grand Master is at 0 or very low — the most common cause
- Check if the B.O. (Blackout) button is active
- Call `get_variable(action="echo", var_name="FADERPAGE")` to confirm the active page

**If Grand Master is down:** Tell the operator to raise Grand Master. Done.
**If Blackout is active:** Tell the operator to release B.O. Done.

### Step 2: Park Ledger

Call `get_park_ledger` (from console state hydration) to check if fixtures are parked.

**If fixtures are parked:** Tell the operator to call `unpark_fixture` for the affected fixtures.

### Step 3: Fixture Selection and Programmer

Call `get_programmer_selection` to check if fixtures are selected in the programmer.

- If nothing is selected, the programmer is empty — intensity won't output from the programmer
- The operator may need to select fixtures first, or ensure a running cue/executor is providing values

### Step 4: Executor State

Call `get_executor_status` for the relevant executors:

- Is the executor active (running)?
- Is the fader level above 0?
- Is a sequence assigned?
- Is the executor on the correct page?

**If fader is at 0:** Raise the fader.
**If no sequence assigned:** Assign one with `bulk_executor_assign`.

### Step 5: Patch Verification

Call `list_fixtures` and `info fixture [ID]` to check:

- Is the fixture patched?
- What DMX address is it assigned to?
- What universe is it on?
- Does the fixture type match the physical fixture?

**If not patched:** The fixture needs to be patched in Setup.

### Step 6: DMX Universe Output

Call `list_universes` to check universe configuration:

- Is the universe enabled?
- Is it assigned to an output (Art-Net, sACN, DMX512)?
- Is the correct network/node configured?

### Step 7: Physical Layer (manual checks)

If all software checks pass, guide the operator through physical checks:

1. Is the DMX cable connected to the correct output?
2. Is the fixture powered on?
3. Is the fixture in DMX mode (not standalone/sound-active)?
4. Is the fixture address matching the patched address?
5. Is there a DMX terminator at the end of the chain?

---

## Allowed Tools

`diagnose_no_output`, `get_park_ledger`, `get_programmer_selection`, `get_executor_status`, `list_fixtures`, `get_object_info`, `list_universes`, `get_variable`, `list_system_variables`

---

## Output Format

Present findings as a clear checklist:

```
Diagnostic Results for [fixture/situation]:
[OK]      Grand Master at 100%
[OK]      Blackout is OFF
[FAIL]    Fixture 5 is PARKED → unpark_fixture(fixture_id=5)
[OK]      Executor 1.1 running, fader at 100%
[OK]      Fixture patched at Universe 1, Address 001
```

---
title: RDM Workflow
description: Instruction module for Remote Device Management (RDM) on grandMA2 — RDM discovery, device info, and autopatch workflow via telnet
version: 1.0.0
created: 2026-04-01T00:00:00Z
last_updated: 2026-04-01T00:00:00Z
---

# RDM Workflow

**Charter:** SAFE_READ + DESTRUCTIVE — discovers RDM-capable devices on a universe, reads
device identity and DMX footprint, then patches addresses. The patch step is destructive
and overwrites existing DMX assignments. Use when patching unknown fixtures, verifying
live DMX addresses, or pulling manufacturer data from intelligent fixtures without a
fixture sheet.

Invoke when asked to: auto-discover fixtures on a universe, read a fixture's DMX address
via RDM, patch a device to a specific address using RDM UID, or verify RDM support.

---

## What is RDM

RDM (Remote Device Management, ANSI E1.20) is a bidirectional extension of the DMX512
protocol. Fixtures that support RDM respond to discovery packets with a unique 48-bit
UID (manufacturer ID + device ID). Once discovered, the controller can query device
label, manufacturer name, DMX footprint (channel count), current DMX start address, and
set a new start address — all over the same DMX cable without breaking DMX output.

**Not all fixtures support RDM.** Moving lights, LED bars, and fog machines from most
major manufacturers do. Conventional dimmers and older fixtures generally do not.
Use `list_fixture_types()` to check if the fixture type profile has RDM support flagged
before starting a discovery session.

---

## RDM vs Manual Patching — Decision Tree

```
Does the rig have a fixture sheet with confirmed addresses?
  YES → Use manual patch (assign_dmx_address). RDM not needed.
  NO  → Are the fixtures RDM-capable? (check list_fixture_types())
          YES → Use this skill.
          NO  → Use a DMX tester tool or physical fixture menu to read addresses,
                then patch manually.

Are addresses already patched in MA2 but you suspect drift?
  → Run rdm_get_info(uid) on each device to verify live address matches patch.
```

---

## Allowed Tools

```
rdm_discover            — SAFE_READ: scan a universe for RDM-capable devices, returns UID list
rdm_get_info            — SAFE_READ: read device label, manufacturer, footprint, current DMX address
rdm_patch               — DESTRUCTIVE: set a device's DMX start address over RDM
list_fixture_types      — SAFE_READ: confirm RDM support flag on fixture type profiles
list_universes          — SAFE_READ: verify universe IDs and patch state after patching
list_fixtures           — SAFE_READ: confirm MA2 patch reflects new addresses
detect_dmx_address_conflicts  — SAFE_READ: check for overlapping address ranges (if available)
```

---

## Workflow

**Step 1 — Check fixture type RDM support**

```python
list_fixture_types()
# Confirm the fixture type profile you are patching has RDM enabled.
# If not listed as RDM-capable, stop and patch manually.
```

**Step 2 — Discover devices on a universe**

```python
rdm_discover(universe_id=1)
# Returns a list of RDM UIDs found on the universe.
# Each UID is a hex string, e.g. "0050A1001234".
# If the list is empty: check cable termination, verify RDM is not blocked by
# a non-RDM splitter/buffer, confirm the universe is active in MA2.
```

**Step 3 — Read device info for each UID**

```python
rdm_get_info(uid="0050A1001234")
# Returns: device_label, manufacturer, dmx_footprint, current_address
# Repeat for each UID from step 2.
# Note the current_address — compare against expected patch in the plan.
```

**Step 4 — Decide target address**

For each device:
- If MA2's auto-address suggestion fits the rig plan → accept it.
- If you need a specific address → specify `target_address` in step 5.
- If addresses conflict with other fixtures → run `detect_dmx_address_conflicts()`
  before patching.

**Step 5 — Patch the device**

```python
rdm_patch(
    uid="0050A1001234",
    target_address=201,    # 1-based DMX start address
    confirm_destructive=True,
)
# Sends the new start address to the device over RDM.
# The device responds immediately; no power cycle required.
```

Repeat steps 3–5 for each discovered UID.

**Step 6 — Verify**

```python
list_universes()    # confirm universe patch map updated
list_fixtures()     # confirm MA2 fixture patch shows correct addresses
```

Spot-check one fixture with `rdm_get_info()` after patching to confirm the device
accepted the new address.

---

## Common Issues

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `rdm_discover` returns empty list | Non-RDM splitter in signal path, or no RDM-capable devices | Bypass splitter; verify fixture supports RDM |
| Device found but `rdm_get_info` times out | Cable polarity reversed on data pair | Swap pins 2 and 3 on one end of the cable |
| Device reports wrong footprint | Fixture type profile mismatch | Update fixture type or select correct mode |
| Address conflict after patch | Two UIDs patched to overlapping ranges | Run `detect_dmx_address_conflicts()` and re-sequence |
| Device accepts patch but reverts | Fixture has address lock enabled in its local menu | Disable address lock on fixture panel |

---

## Safety Rules

- `rdm_patch` overwrites the device's DMX start address immediately. Always record the
  current address from `rdm_get_info` before patching — there is no undo over RDM.
- Never patch without confirming the target address range is free of other fixtures.
  A footprint overlap silently merges channels.
- RDM discovery can disrupt DMX output briefly (typically < 1 frame). Do not run
  `rdm_discover` during a live cue unless certain the disruption is acceptable.
- MA2 patch and the physical device address are independent until `rdm_patch` is called.
  `list_fixtures()` shows the MA2-side patch; `rdm_get_info` shows the device-side truth.

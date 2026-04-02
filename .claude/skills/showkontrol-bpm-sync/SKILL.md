---
title: ShowKontrol BPM Sync
description: Guide for syncing CDJ BPM data from ShowKontrol to grandMA2 speed masters for tempo-locked lighting effects
version: 1.0.0
safety_scope: SAFE_WRITE
created: 2026-04-02T00:00:00Z
last_updated: 2026-04-02T00:00:00Z
---

# ShowKontrol BPM Sync

## Charter

SAFE_WRITE skill — sets speed master BPM values via Telnet. Does not modify show data, cues, or presets.

## Invocation

Use when an operator wants CDJ tempo data to drive lighting effect speed in real time. ShowKontrol reads BPM from Pioneer CDJs via ProLink and this skill configures the MA2 side to receive it.

## Target Users

Lighting designers/operators working with DJs at clubs, festivals, and live events where lighting effects need to follow the music tempo.

---

## How It Works

```
Pioneer CDJs ──ProLink──→ ShowKontrol ──Telnet──→ grandMA2 Speed Master
                              │                         │
                         reads BPM from            effects follow
                         CDJ-3000/2000NXS2         DJ tempo live
```

ShowKontrol (or a bridge like Beat Link Trigger) sends `SpecialMaster 3.N At {BPM}` to grandMA2 via Telnet port 30000. Any executor assigned to that speed master automatically follows the tempo.

---

## Phase 1: MA2 Console Setup (SAFE_READ)

**Goal:** Verify Telnet is enabled and identify which speed master to use.

1. Call `list_system_variables` to verify the console is reachable
2. Call `control_special_master(master="speed1", value=120)` to test that speed master 1 responds
3. Note the console IP address (needed for ShowKontrol config)

**Allowed tools:** `list_system_variables`, `control_special_master`

---

## Phase 2: Assign Effects to Speed Master (SAFE_WRITE)

**Goal:** Connect executor effects to the speed master that will receive BPM.

For each effect executor that should follow the DJ's tempo:

1. Call `assign_executor_property` or use raw command: `Assign Executor {page}.{id} /speedmaster=speed1`
2. Verify with `get_executor_status(executor_id=X)` — check that speed master is assigned

**Allowed tools:** `playback_action`, `get_executor_status`, `send_raw_command`

---

## Phase 3: Configure ShowKontrol

**Goal:** Set up ShowKontrol to send BPM to the MA2 console.

### Option A: ShowKontrol via Telnet (recommended)

ShowKontrol can send Telnet commands directly to grandMA2:

1. Open ShowKontrol preferences
2. Go to **Outputs** → **Telnet** (or **Network**)
3. Configure:
   - **Host:** the grandMA2 console IP (e.g., `192.168.1.100`)
   - **Port:** `30000`
   - **Username:** your MA2 Telnet user
   - **Password:** your MA2 Telnet password
4. Set the BPM output command to: `SpecialMaster 3.1 At $BPM`
   - Replace `$BPM` with ShowKontrol's BPM variable token
   - Replace `3.1` with your speed master number if not using speed master 1

### Option B: ShowKontrol via MIDI → MA2 onPC

If using MA2 onPC on the same machine as ShowKontrol:

1. In ShowKontrol, configure MIDI output to a virtual MIDI bus (e.g., IAC Driver on Mac)
2. Map BPM to a MIDI CC (e.g., CC 1 on channel 1)
3. In MA2 onPC, go to Setup → MIDI → MIDI In
4. Create a MIDI remote: map the CC to `SpecialMaster 3.1`
5. Scale the CC range (0-127) to your BPM range

### Option C: Beat Link Trigger (alternative to ShowKontrol)

If using Beat Link Trigger instead of ShowKontrol:

1. Install Beat Link Trigger (Java app, reads ProLink directly)
2. Configure a trigger with the Tracked Update Expression:
   ```clojure
   (when trigger-active? (set-gm-tempo effective-tempo))
   ```
3. Set the grandMA2 connection in Global Setup:
   - IP: console address
   - Port: 30000
   - User/password: Telnet credentials
   - Speed master: `3.1`

---

## Phase 4: Test and Verify

**Goal:** Confirm BPM sync is working end-to-end.

1. Play a track on a CDJ (or use ShowKontrol's test BPM feature)
2. Call `set_bpm(bpm=128)` manually to verify the speed master responds
3. Watch the MA2 console — the speed master display should update
4. Start an effect on an executor assigned to the speed master
5. Change the track on the CDJ — the effect speed should follow

### Troubleshooting

| Problem | Check |
|---------|-------|
| No BPM update on MA2 | Is Telnet enabled? (Setup → Console → Global Settings) |
| Connection refused | Firewall blocking port 30000? |
| BPM arrives but effect doesn't change | Is the executor assigned to the correct speed master? |
| BPM value seems wrong | Check ShowKontrol's BPM range — MA2 accepts 1-300 |
| Jittery tempo | ShowKontrol may send too frequently — add a smoothing filter or rate-limit to ~4 updates/sec |

---

## Phase 5: Advanced — Multiple Speed Masters

For complex shows with multiple tempo zones:

- **Speed Master 1:** Main DJ deck (CDJ-1)
- **Speed Master 2:** Second DJ deck (CDJ-2) for B2B sets
- **Speed Master 3:** Manual override (for breakdown sections)

Configure ShowKontrol to send each deck's BPM to a different speed master:
- Deck 1: `SpecialMaster 3.1 At $BPM1`
- Deck 2: `SpecialMaster 3.2 At $BPM2`

Assign effect executors to the appropriate speed master based on which deck is live.

---

## Lua Plugin Alternative

For setups where Telnet isn't available, the grandMA2 BPM Controller Lua plugin (github.com/aGuyNamedJonas/grandma2-bpm-controller) provides an in-console solution:

1. Install the plugin on the MA2 console
2. Set BPM via MA2 user variables: `SetVar $bpm=128 ; SetVar $cmd=setBpm ; Go Plugin "bpmController"`
3. The plugin converts BPM to executor fader position (BPM/225 * 100%)

This approach is useful when the BPM source can only trigger MA2 macros (e.g., via MIDI Note triggers).

---

## Allowed Tools

`set_bpm`, `control_special_master`, `list_system_variables`, `get_executor_status`, `send_raw_command`, `playback_action`

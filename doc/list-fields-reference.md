---
title: grandMA2 List Command Field Reference
description: All column fields returned by List <ObjectType> for every major MA2 object type — live-verified from console (show claude_ma2_ctrl, 2026-03-31)
version: 1.0.0
created: 2026-03-31T21:52:55Z
last_updated: 2026-03-31T21:52:55Z
---

# grandMA2 List Command Field Reference

## Output Format — Two Modes

MA2 `List` produces **two distinct output formats** depending on the object type:

| Format | Used by | Layout |
|--------|---------|--------|
| **Tabular (column)** | All types except Executor | Header row of column names, then one data row per object |
| **KEY=VALUE inline** | `List Executor <page.id>` only | `Field=Value Field=Value ...` all on one line |

**Parser implication:** Column header names can be extracted by reading the first non-`Executing` line of the response. Values are positionally aligned under those headers (space-padded, not delimited). `Info` column typically contains `(N)` = child object count.

---

## Executor — KEY=VALUE Format (unique)

Only object type that returns `KEY=VALUE` for a single object.
**Must use page-qualified address**: `List Executor 1.203` — bare `List Executor 203` returns different/wrong data.

```
Exec 1.203  No.=1.203 Name=Washes Color Sequence=Seq 202(9)
Width=1 SwopProtect=off KillProtect=off AutoStart=on AutoStop=on
AutoFix=off OoO=on SoftLTP=on MasterGo=Off Restart=First Wrap=on
Crossfade=off AutoStomp=off Chaser=off Priority=Normal Prepos=off
EffectSpeed=on MIBNever=off MIBAlways=off TriggerIsGo=off
CmdDisable=off IgnoreExecTime=off Speed=Normal
SpeedMaster=Speed_Individual RateMaster=Rate_Individual
Filter=None OffTime=Default BreakingGo=off PlaybackMaster=Pb None
```

**All fields:** `No`, `Name`, `Sequence`, `Width`, `SwopProtect`, `KillProtect`, `AutoStart`, `AutoStop`, `AutoFix`, `OoO`, `SoftLTP`, `MasterGo`, `Restart`, `Wrap`, `Crossfade`, `AutoStomp`, `Chaser`, `Priority`, `Prepos`, `EffectSpeed`, `MIBNever`, `MIBAlways`, `TriggerIsGo`, `CmdDisable`, `IgnoreExecTime`, `Speed`, `SpeedMaster`, `RateMaster`, `Filter`, `OffTime`, `BreakingGo`, `PlaybackMaster`

See `memory/reference_executor_parameters.md` for Assign syntax and valid values per field.

---

## Sequence

Command: `List Sequence <id>`

| Column | Example Value | Notes |
|--------|--------------|-------|
| `No.` | `201` | Sequence number |
| `Name` | `Profiles Color` | Label |
| `Track` | `On` | Tracking mode on/off |
| `ReleaseFirststep` | `On` | Release on first step |
| `CueZero` | `Off` | Cue zero enabled |
| `CueZeroExtract` | `Off` | Extract on cue zero |
| `InputFilter` | `None` | Filter assigned to input |
| `TimecodeSlot` | `Link Selected` | Timecode input slot |
| `Info` | `(8)` | Cue count |
| `ForcedPos.mode` | `Pan/Tilt` | Position tracking mode |

```
         No.  Name            Track  ReleaseFirststep  CueZero  CueZeroExtract  InputFilter  TimecodeSlot   Info  ForcedPos.mode
Sequ 201 201  Profiles Color  On     On                Off      Off             None         Link Selected        Pan/Tilt         (8)
```

---

## Cue

Command: `List Cue <num> Sequence <id>` or `List Cue Sequence <id>` (all cues)

| Column | Example Value | Notes |
|--------|--------------|-------|
| `Number` | `1` | Cue number |
| `MIB` | *(empty)* | Move In Black flag |
| `Trig` | `Go` | Trigger type (Go / Time / Follow / Sound / BPM) |
| `TrigTime` | *(empty)* | Trigger time (for Time trigger) |
| `Mode` | `Normal` | Cue mode |
| `Loop` | `None` | Loop setting |
| `Lcount` | `Infinite` | Loop count |
| `Ltime` | `Infinite` | Loop time |
| `Info` | `(1)` | Part count |

```
      Number  MIB  Trig  TrigTime  Mode    Loop  Lcount    Ltime
Cue 1 1            Go              Normal  None  Infinite  Infinite   (1)
```

**Note:** Cue Name and fade/delay timing are NOT shown in `List Cue` tabular output. Use `Info Cue <num> Sequence <id>` for extended timing data.

---

## Group

Command: `List Group <id>`

| Column | Example Value | Notes |
|--------|--------------|-------|
| `No.` | `1` | Group number |
| `Name` | `FOH Warm` | Label |
| `Info` | *(empty)* | — |

```
        No.  Name      Info
Group 1 1    FOH Warm
```

---

## Preset

Command: `List Preset <type>.<slot>` or `List Preset <type>` (all slots of that type)

Preset type numbers: `1`=Dimmer `2`=Position `3`=Gobo `4`=Color `5`=Beam `6`=Focus `7`=Control

| Column | Example Value | Notes |
|--------|--------------|-------|
| `No.` | `4.1` | PresetType.Slot |
| `Name` | `White` | Label |
| `Special` | `Normal` | Normal / Universal / Global |
| `Info` | *(empty)* | Fixture count if selective |

```
          No.  Name   Special  Info
Color 4.1 4.1  White  Normal
```

---

## Fixture

Command: `List Fixture <id>` — **NEVER** use bare `List Fixture` (freezes onPC)

| Column | Example Value | Notes |
|--------|--------------|-------|
| `Name` | `Mac700 1` | Fixture label |
| `FixId` | `111` | Fixture ID |
| `ChaId` | `111` | Channel ID (usually = FixId) |
| `FixtureType` | `3 Mac 700 Profile Extended` | Type number + name |
| `Patch` | `2.001` | Universe.DMX (1-based DMX within universe) |
| `NoParameters` | `No` | No-parameters flag |
| `PosX` | `0.00` | 3D position X |
| `PosY` | `0.00` | 3D position Y |
| `PosZ` | `0.00` | 3D position Z |
| `RotX` | `0.00` | 3D rotation X |
| `RotY` | `0.00` | 3D rotation Y |
| `RotZ` | `0.00` | 3D rotation Z |
| `Info` | *(empty)* | Notes |
| `RDMID` | *(empty)* | RDM device identifier |

```
            Name      FixId  ChaId  FixtureType                 Patch   NoParameters  PosX  PosY  PosZ  RotX  RotY  RotZ  Info  RDMID
Fixture 111 Mac700 1  111    111    3 Mac 700 Profile Extended   2.001  No            0.00  0.00  0.00  0.00  0.00  0.00
```

---

## Channel

Command: `List Channel <id>` — **NEVER** use bare `List Channel` (same freeze risk)

Returns **identical columns to Fixture** — Channel and Fixture share the same display format.

---

## Macro

Command: `List Macro` or `List Macro <id>`

| Column | Example Value | Notes |
|--------|--------------|-------|
| `No.` | `1` | Macro number |
| `Name` | `MAtricks Filter Off` | Label |
| `CLI` | `On` | CLI-accessible |
| `Timing` | `On` | Timing enabled |
| `Info` | `(1)` | Line count |

Active macros: 1 (MAtricks Filter Off), 2 (MAtricks Reset), 4 (MAtricks Reset#2)

---

## Filter

Command: `List Filter <id>`

| Column | Example Value | Notes |
|--------|--------------|-------|
| `No.` | `1` | Filter number |
| `Name` | `All` | Label |
| `Info` | *(empty)* | — |

Only Filter 1 "All" (default) is present in this show.

---

## View

Command: `List View` or `List View <id>`

| Column | Example Value | Notes |
|--------|--------------|-------|
| `No.` | `1` | View number |
| `Name` | `View 1` | Label |
| `Screen` | `2` | Display screen number |
| `Info` | `(11)` | Window count |

Views on this show: 1 (View 1, screen 2), 2 (MATricks), 3, 4, 5 (Seq Content), 6 (Seq Exec), 7.

---

## Timer

Command: `List Timer` or `List Timer <id>`

| Column | Example Value | Notes |
|--------|--------------|-------|
| `No.` | `1` | Timer number |
| `Name` | `Stopwatch` | Label |
| `TimerMode` | `Stopwatch` | Stopwatch / Countdown |
| `WhenRestarting` | `Continue` | Continue / Reset |
| `TimeUnit` | `1/100 Seconds` | Time resolution |
| `ExecTrigger` | `Not Linked` | Executor trigger |
| `AlertType` | `Popup & Beep` | Alert style |
| `AlertRange` | `Local` | Alert scope |
| `CountdownTime` | `10` | Countdown duration |
| `AlertDuration` | `Infinite` | Alert duration |
| `AlertCommand` | *(empty)* | Command on alert |
| `AlertText` | *(empty)* | Alert message |
| `Info` | *(empty)* | — |

---

## World

Command: `List World <id>`

| Column | Example Value | Notes |
|--------|--------------|-------|
| `No.` | `1` | World number |
| `Name` | `Full` | Label |
| `Info` | *(empty)* | — |

---

## MAtricks

Command: `List MAtricks <id>`

| Column | Example Value | Notes |
|--------|--------------|-------|
| `No.` | `1` | MAtricks slot |
| `Name` | `W0-G0-B0-I0` | Settings encoded in name |
| `Info` | *(empty)* | — |

MAtricks settings (interleave/block/group/wing) are encoded in the Name field; full detail is only visible in GUI.

---

## Page

Command: `List Page <id>`

| Column | Example Value | Notes |
|--------|--------------|-------|
| `No.` | `1` | Page number |
| `Name` | `Sat Bands` | Label |
| `Info` | `(8)` | Executor count on page |

Pages on this show: 1 (13 exec), 2 Sat Bands (8), 3 Hue Faders (13), 4 (2), 5 (6).

---

## Plugin

Command: `List Plugin`

| Column | Example Value | Notes |
|--------|--------------|-------|
| `No.` | `1` | Plugin number |
| `Name` | `LUA` | Plugin type |
| `ExecuteOnLoad` | `No` | Auto-execute on show load |
| `Info` | *(empty)* | — |

---

## Effect

Command: `List Effect <id>`

| Column | Example Value | Notes |
|--------|--------------|-------|
| `No.` | `1` | Effect number |
| `Name` | `Effect` | Label |
| `Info` | `(1)` | Child object count |

```
           No.  Name    Info
Effect   1 1    Effect         (1)
```

---

## Layout

Command: `List Layout <id>`

| Column | Example Value | Notes |
|--------|--------------|-------|
| `No.` | `999` | Layout number |
| `Name` | `TestLayout` | Label |
| `Info` | `(1)` | Child object count |

```
           No.  Name        Info
Layout 999 999  TestLayout         (1)
```

---

## Timecode

Command: `List Timecode <id>` — richest tabular format after Executor

| Column | Example Value | Notes |
|--------|--------------|-------|
| `Name` | `TestTimecode` | Label |
| `Slot` | `Intern` | Input slot (Intern / SMPTE / MTC / etc.) |
| `Length` | `0:00` | Timecode length |
| `Offset` | `0:00` | Start offset |
| `Runs` | `Endless Repeat` | Playback mode |
| `SwitchOff` | `Playbacks Off` | Behavior on switch off |
| `StatusCall` | `On` | Status call enabled |
| `TimeUnit` | `1/100 Seconds` | Time resolution |
| `WhenEnding` | `Stop` | Behavior at end |
| `WhenStopping` | `Do Nothing` | Behavior when stopped |
| `AutoStart` | `Off` | Auto-start on show load |
| `RecordMode` | `Goto (Status)` | Recording mode |
| `UserBits` | `00000000` | SMPTE user bits |
| `Info` | *(empty)* | — |

```
             Name          Slot    Length  Offset  Runs            SwitchOff      StatusCall  TimeUnit       WhenEnding  WhenStopping  AutoStart  RecordMode     UserBits  Info
Timecode 999 TestTimecode  Intern  0:00    0:00    Endless Repeat  Playbacks Off  On          1/100 Seconds  Stop        Do Nothing    Off        Goto (Status)  00000000
```

---

## Quick Reference: Column Count by Type

| Type | Columns | Format |
|------|---------|--------|
| Executor | 32 | KEY=VALUE (unique) — page-qualified address required |
| Timecode | 14 | Tabular |
| Fixture / Channel | 14 | Tabular — identical output |
| Timer | 13 | Tabular |
| Sequence | 10 | Tabular |
| Cue | 8 | Tabular — name/timing not shown; use Info command |
| Macro | 5 | Tabular |
| View / Plugin | 4 | Tabular |
| Preset | 4 | Tabular |
| Effect / Layout / Filter / Group / World / MAtricks / Page | 3 | Tabular — minimal: No, Name, Info |

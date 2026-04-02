---
title: "grandMA2 CD Tree — Full Validated Print"
description: "Complete recursive cd tree of grandMA2 onPC v3.9.60.65, live-scanned via telnet"
version: 1.0.0
created: 2026-03-12T00:22:07Z
last_updated: 2026-03-12T00:22:07Z
---

# grandMA2 CD Tree — Full Validated Print

**Source:** `scan_output.json` (live telnet scan of grandMA2 onPC v3.9.60.65)
**Scan stats:** 8,293 nodes visited | 965 duplicates | 142 skipped | 138 min elapsed
**Max depth scanned:** 20 | **Max index probed:** 60 | **Gap probe:** 5

---

## Root Level Summary (`cd /`)

| cd | Location | Entries | Total Nodes | Max Depth | Notes |
|----|----------|---------|-------------|-----------|-------|
|  1 | Showfile 1 | 37 | 11 | 2 |  |
|  2 | TimeConfig 2 | 0 | 1 | 1 | [LEAF] |
|  3 | Settings 3 | 6 | 18 | 4 |  |
|  4 | DMX_Protocols | 6 | 10 | 3 |  |
|  5 | NetConfig | 5 | 10 | 4 |  |
|  6 | CITPNetConfig 6 | 0 | 1 | 1 | [LEAF] |
|  7 | TrackingSystems 7 | 0 | 1 | 1 | [LEAF] |
|  8 | UserImagePool | 13 | 11 | 2 |  |
|  9 | RDM_Data 9 | 2 | 13 | 3 |  |
| 10 | LiveSetup | 6 | 602 | 8 |  |
| 13 | Macros | 0 | 1 | 1 | [LEAF] |
| 14 | FlightRecordings | 0 | 1 | 1 | [LEAF] |
| 15 | Plugins | 1 | 2 | 2 |  |
| 16 | Gels | 13 | 144 | 3 |  |
| 17 | Presets | 0 | 1 | 1 | [LEAF] |
| 18 | Worlds | 1 | 2 | 2 |  |
| 19 | Filters | 1 | 2 | 2 |  |
| 20 | FadePaths 20 | 0 | 1 | 1 | [LEAF] |
| 21 | Programmer | 0 | 1 | 1 | [LEAF] |
| 22 | Groups | 0 | 1 | 1 | [LEAF] |
| 23 | Forms | 23 | 52 | 4 |  |
| 24 | Effects | 0 | 1 | 1 | [LEAF] |
| 25 | Sequences | 0 | 1 | 1 | [LEAF] |
| 26 | Timers | 1 | 2 | 2 |  |
| 27 | MasterSections | 0 | 1 | 1 | [LEAF] |
| 30 | ExecutorPages | 2 | 16 | 4 |  |
| 31 | ChannelPages | 9 | 10 | 2 |  |
| 33 | Songs | 0 | 1 | 1 | [LEAF] |
| 34 | Agendas | 0 | 1 | 1 | [LEAF] |
| 35 | Timecodes | 0 | 1 | 1 | [LEAF] |
| 36 | RemoteTypes | 3 | 4 | 2 |  |
| 37 | DMXSnapshotPool | 0 | 1 | 1 | [LEAF] |
| 38 | Layouts | 1 | 13 | 5 |  |
| 39 | UserProfiles | 254 | 7,345 | 5 |  |
| 40 | Users | 3 | 3 | 2 |  |
| 41 | PixelMapperContainer 41 | 3 | 6 | 2 |  |
| 42 | NDP_Root 42 | 0 | 1 | 1 | [LEAF] |

**Invalid indexes** (Error #72 COMMAND NOT EXECUTED): 12, 28, 29, 32, 44, 45, 47, 48, 49, 50

**Note:** Indexes 12, 28-29, 32, 44-45, 47-50 return errors. Index 11 (EditSetup) and
index 46 (Temp) exist but were not captured in this particular scan run.

---

## Known Caveats

### PresetType Tree (cd 10.2) — Scanner Bug


> **Scanner caveat:** `scan_output.json` falsely marks `cd 10.2` (PresetTypes) as
> `is_leaf: true` because the parser misses rows with the PresetType/Feature/Attribute
> format. The tree IS navigable 6 levels deep (live-verified 2026-03-10):
>
> ```
> cd 10.2        → 9 PresetTypes (Dimmer, Position, Gobo, Color, Beam, Focus, Control, Shapers, Video)
> cd 10.2.5      → Beam features: SHUTTER(20), BEAM1(21), EFFECT(22)
> cd 10.2.5.1    → Attributes under SHUTTER: SHUTTER(22), STROBE_RATIO(0)
> cd 10.2.5.1.1  → SubAttributes of SHUTTER (Shutter, Strobe, Pulse, ...)
> cd 10.2.5.1.1.N → Leaf (NO OBJECTS FOUND)
> ```
>
> | PresetType | ID | cd path   | $PRESET  | $FEATURE (1st) | $ATTRIBUTE (1st) |
> |------------|----|-----------|----------|----------------|------------------|
> | Dimmer     | 1  | cd 10.2.1 | DIMMER   | DIMMER         | DIM              |
> | Position   | 2  | cd 10.2.2 | POSITION | POSITION       | PAN              |
> | Gobo       | 3  | cd 10.2.3 | GOBO     | GOBO1          | GOBO1            |
> | Color      | 4  | cd 10.2.4 | COLOR    | COLORRGB       | COLORRGB1        |
> | Beam       | 5  | cd 10.2.5 | BEAM     | SHUTTER        | SHUTTER          |
> | Focus      | 6  | cd 10.2.6 | FOCUS    | FOCUS          | FOCUS            |
> | Control    | 7  | cd 10.2.7 | CONTROL  | MSPEED         | INTENSITYMSPEED  |
> | Shapers    | 8  | cd 10.2.8 | —        | fixture-dep    | —                |
> | Video      | 9  | cd 10.2.9 | —        | fixture-dep    | —                |


### UserProfiles (cd 39) — 89% of All Nodes

`cd 39` contains 7,345 of 8,293 total nodes (88%).
Each of the 254 profiles shares a nearly identical sub-structure (UserSettings,
Displays, Views, StoreDefaults, MatrixPool, ViewButtons, Arrangements, StoreSettings,
Cameras, RemoteDisplays, MaskPool). The full tree below shows the first profile
(Default) in detail and summarizes the rest.

---

## Full Tree

```
cd 1 → [Showfile 1] (37 entries, 11 nodes, depth 2) + 10 leaves
  cd 1.1 → [Showfile 1/History 1] [LEAF]
  cd 1.2 → [Showfile 1/History 2] [LEAF]
    ... (7 more leaves) ...
  cd 1.10 → [Showfile 1/History 10] [LEAF]
cd 2 → [TimeConfig 2] [LEAF]
cd 3 → [Settings 3] (6 entries, 18 nodes, depth 4) + 4 leaves
  cd 3.1 → [Settings 3/Global 1] [LEAF]
  cd 3.2 → [Settings 3/Local 2] (2 entries, 4 nodes, depth 3) + 1 leaves
    cd 3.2.1 → [Settings 3/Local 2/SurfaceCollect] (1 entries, 2 nodes, depth 2) + 1 leaves
      cd 3.2.1.1 → [Settings 3/Local 2/SurfaceCollect/Default 1] [LEAF]
    cd 3.2.2 → [Settings 3/Local 2/ShortcutDefinition 2] [LEAF]
  cd 3.3 → [Settings 3/Show 3] [LEAF]
  cd 3.4 → [Settings 3/Sound 4] [LEAF]
  cd 3.5 → [Settings 3/MidiConfig 5] [LEAF]
  cd 3.6 → [Settings 3/TimecodeStatus] (8 entries, 9 nodes, depth 2) + 8 leaves
    cd 3.6.1 → [Settings 3/TimecodeStatus /TC Slot 1] [LEAF]
    cd 3.6.2 → [Settings 3/TimecodeStatus /TC Slot 2] [LEAF]
      ... (5 more leaves) ...
    cd 3.6.8 → [Settings 3/TimecodeStatus /TC Slot 8] [LEAF]
cd 4 → [DMX_Protocols] (6 entries, 10 nodes, depth 3) + 3 leaves
  cd 4.1 → [DMX_Protocols/Art-Net 1] (1 entries, 2 nodes, depth 2) + 1 leaves
    cd 4.1.1 → [DMX_Protocols/Art-Net 1/ArtnetData 1] [LEAF]
  cd 4.2 → [DMX_Protocols/ETC Net2 2] [LEAF]
  cd 4.3 → [DMX_Protocols/Pathport 3] [LEAF]
  cd 4.4 → [DMX_Protocols/sACN 4] (1 entries, 2 nodes, depth 2) + 1 leaves
    cd 4.4.1 → [DMX_Protocols/sACN 4/ACNData 1] [LEAF]
  cd 4.5 → [DMX_Protocols/Shownet 5] [LEAF]
  cd 4.6 → [DMX_Protocols/Kinet1 6] (1 entries, 2 nodes, depth 2) + 1 leaves
    cd 4.6.1 → [DMX_Protocols/Kinet1 6/KinetData 1] [LEAF]
cd 5 → [NetConfig] (5 entries, 10 nodes, depth 4) + 4 leaves
  cd 5.1 → [NetConfig/Console 1] [LEAF]
  cd 5.2 → [NetConfig/onPC 2] (2 entries, 5 nodes, depth 3)
    cd 5.2.1 → [NetConfig/onPC 2/WINDELL-6OKD21F 1] (3 entries, 3 nodes, depth 2) + 2 leaves
      cd 5.2.1.1 → [NetConfig/onPC 2/WINDELL-6OKD21F 1/Command 1] [LEAF]
      cd 5.2.1.2 → [NetConfig/onPC 2/WINDELL-6OKD21F 1/Fader 1 2] [LEAF]
    cd 5.2.2 → [NetConfig/onPC 2/WINDELL-6OKD21F 2] (3 entries, 1 nodes, depth 1) [DUP of cd 5.2.1]
  cd 5.3 → [NetConfig/NPU 3] [LEAF]
  cd 5.4 → [NetConfig/3D 4] [LEAF]
  cd 5.5 → [NetConfig/VPU 5] [LEAF]
cd 6 → [CITPNetConfig 6] [LEAF]
cd 7 → [TrackingSystems 7] [LEAF]
cd 8 → [UserImagePool] (13 entries, 11 nodes, depth 2) + 10 leaves
  cd 8.1 → [UserImagePool /PAR 1] [LEAF]
  cd 8.2 → [UserImagePool /Fresnel 2] [LEAF]
    ... (7 more leaves) ...
  cd 8.10 → [UserImagePool /Moving 4 10] [LEAF]
cd 9 → [RDM_Data 9] (2 entries, 13 nodes, depth 3) + 1 leaves
  cd 9.1 → [RDM_Data 9/RDM_Fixture_Types 1] [LEAF]
  cd 9.2 → [RDM_Data 9/RDM_Universes] (256 entries, 11 nodes, depth 2) + 10 leaves
    cd 9.2.1 → [RDM_Data 9/RDM_Universes/RDM_Universe 1] [LEAF]
    cd 9.2.2 → [RDM_Data 9/RDM_Universes/RDM_Universe 2] [LEAF]
      ... (7 more leaves) ...
    cd 9.2.10 → [RDM_Data 9/RDM_Universes/RDM_Universe 10] [LEAF]
cd 10 → [LiveSetup] (6 entries, 602 nodes, depth 8) + 3 leaves
  cd 10.1 → [LiveSetup/DMX_Profiles 1] [LEAF]
  cd 10.2 → [LiveSetup/PresetTypes] [LEAF]
  cd 10.3 → [LiveSetup/FixtureTypes 3] (14 entries, 563 nodes, depth 7)
    cd 10.3.1 → [LiveSetup/FixtureTypes 3/1 Universal Attributes] (6 entries, 27 nodes, depth 5) + 4 leaves
      cd 10.3.1.1 → [LiveSetup/FixtureTypes 3/1 Universal Attributes/Modules 1] (1 entries, 18 nodes, depth 4)
        cd 10.3.1.1.1 → [LiveSetup/FixtureTypes 3/1 Universal Attributes/Modules 1/1 Universal Attributes] (8 entries, 17 nodes, depth 3)
          cd 10.3.1.1.1.1 → [LiveSetup/FixtureTypes 3/1 Universal Attributes/Modules 1/1 Universal Attributes/DIM 1] (1 entries, 2 nodes, depth 2) + 1 leaves
            cd 10.3.1.1.1.1.1 → [LiveSetup/FixtureTypes 3/1 Universal Attributes/Modules 1/1 Universal Attributes/DIM 1/Dim 1] [LEAF]
          cd 10.3.1.1.1.2 → [LiveSetup/FixtureTypes 3/1 Universal Attributes/Modules 1/1 Universal Attributes/TILT 2] (1 entries, 2 nodes, depth 2) + 1 leaves
            cd 10.3.1.1.1.2.1 → [LiveSetup/FixtureTypes 3/1 Universal Attributes/Modules 1/1 Universal Attributes/TILT 2/Tilt 1] [LEAF]
          cd 10.3.1.1.1.3 → [LiveSetup/FixtureTypes 3/1 Universal Attributes/Modules 1/1 Universal Attributes/PAN 3] (1 entries, 2 nodes, depth 2) + 1 leaves
            cd 10.3.1.1.1.3.1 → [LiveSetup/FixtureTypes 3/1 Universal Attributes/Modules 1/1 Universal Attributes/PAN 3/Pan 1] [LEAF]
          cd 10.3.1.1.1.4 → [LiveSetup/FixtureTypes 3/1 Universal Attributes/Modules 1/1 Universal Attributes/COLORRGB1 4] (1 entries, 2 nodes, depth 2) + 1 leaves
            cd 10.3.1.1.1.4.1 → [LiveSetup/FixtureTypes 3/1 Universal Attributes/Modules 1/1 Universal Attributes/COLORRGB1 4/R 1] [LEAF]
          cd 10.3.1.1.1.5 → [LiveSetup/FixtureTypes 3/1 Universal Attributes/Modules 1/1 Universal Attributes/COLORRGB2 5] (1 entries, 2 nodes, depth 2) + 1 leaves
            cd 10.3.1.1.1.5.1 → [LiveSetup/FixtureTypes 3/1 Universal Attributes/Modules 1/1 Universal Attributes/COLORRGB2 5/G 1] [LEAF]
          cd 10.3.1.1.1.6 → [LiveSetup/FixtureTypes 3/1 Universal Attributes/Modules 1/1 Universal Attributes/COLORRGB3 6] (1 entries, 2 nodes, depth 2) + 1 leaves
            cd 10.3.1.1.1.6.1 → [LiveSetup/FixtureTypes 3/1 Universal Attributes/Modules 1/1 Universal Attributes/COLORRGB3 6/B 1] [LEAF]
          cd 10.3.1.1.1.7 → [LiveSetup/FixtureTypes 3/1 Universal Attributes/Modules 1/1 Universal Attributes/COLORRGB4 7] (1 entries, 2 nodes, depth 2) + 1 leaves
            cd 10.3.1.1.1.7.1 → [LiveSetup/FixtureTypes 3/1 Universal Attributes/Modules 1/1 Universal Attributes/COLORRGB4 7/Amber 1] [LEAF]
          cd 10.3.1.1.1.8 → [LiveSetup/FixtureTypes 3/1 Universal Attributes/Modules 1/1 Universal Attributes/COLORRGB5 8] (1 entries, 2 nodes, depth 2) + 1 leaves
            cd 10.3.1.1.1.8.1 → [LiveSetup/FixtureTypes 3/1 Universal Attributes/Modules 1/1 Universal Attributes/COLORRGB5 8/White 1] [LEAF]
      cd 10.3.1.2 → [LiveSetup/FixtureTypes 3/1 Universal Attributes/Instances 2] (1 entries, 2 nodes, depth 2) + 1 leaves
        cd 10.3.1.2.1 → [LiveSetup/FixtureTypes 3/1 Universal Attributes/Instances 2/Instance 1] [LEAF]
      cd 10.3.1.3 → [LiveSetup/FixtureTypes 3/1 Universal Attributes/Wheels 3] [LEAF]
      cd 10.3.1.4 → [LiveSetup/FixtureTypes 3/1 Universal Attributes/VirtualFunctionBlocks 4] [LEAF]
      cd 10.3.1.5 → [LiveSetup/FixtureTypes 3/1 Universal Attributes/PresetReferences] [LEAF]
      cd 10.3.1.6 → [LiveSetup/FixtureTypes 3/1 Universal Attributes/FixtureMacroCollect 6] [LEAF]
      cd 10.3.1.7 → [LiveSetup/FixtureTypes 3/1 Universal Attributes/RdmNotifications 7] (1 entries, 2 nodes, depth 2) + 1 leaves
        cd 10.3.1.7.1 → [LiveSetup/FixtureTypes 3/1 Universal Attributes/RdmNotifications 7/RdmNotification 1] [LEAF]
    cd 10.3.2 → [LiveSetup/FixtureTypes 3/2 Dimmer 00] (6 entries, 1 nodes, depth 1) [DUP of cd 10.3.1]
    cd 10.3.3 → [LiveSetup/FixtureTypes 3/3 rgbw-13ch 13CH] (6 entries, 1 nodes, depth 1) [DUP of cd 10.3.1]
    cd 10.3.4 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH] (6 entries, 37 nodes, depth 6) + 4 leaves
      cd 10.3.4.1 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/Modules 1] (2 entries, 23 nodes, depth 5)
        cd 10.3.4.1.1 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/Modules 1/MAIN 1] (7 entries, 18 nodes, depth 4)
          cd 10.3.4.1.1.1 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/Modules 1/MAIN 1/TILT 1] (1 entries, 2 nodes, depth 2) + 1 leaves
            cd 10.3.4.1.1.1.1 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/Modules 1/MAIN 1/TILT 1/Tilt 1] [LEAF]
          cd 10.3.4.1.1.2 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/Modules 1/MAIN 1/DIM 2] (1 entries, 2 nodes, depth 2) + 1 leaves
            cd 10.3.4.1.1.2.1 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/Modules 1/MAIN 1/DIM 2/Dim 1] [LEAF]
          cd 10.3.4.1.1.3 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/Modules 1/MAIN 1/SHUTTER 3] (1 entries, 2 nodes, depth 2) + 1 leaves
            cd 10.3.4.1.1.3.1 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/Modules 1/MAIN 1/SHUTTER 3/Shutter 1] [LEAF]
          cd 10.3.4.1.1.4 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/Modules 1/MAIN 1/GOBO1 4] (1 entries, 2 nodes, depth 2) + 1 leaves
            cd 10.3.4.1.1.4.1 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/Modules 1/MAIN 1/GOBO1 4/Select 1] [LEAF]
          cd 10.3.4.1.1.5 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/Modules 1/MAIN 1/GOBO1_POS 5] (1 entries, 2 nodes, depth 2) + 1 leaves
            cd 10.3.4.1.1.5.1 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/Modules 1/MAIN 1/GOBO1_POS 5/Index 1] [LEAF]
          cd 10.3.4.1.1.6 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/Modules 1/MAIN 1/V_VSPEED 6] (1 entries, 2 nodes, depth 2) + 1 leaves
            cd 10.3.4.1.1.6.1 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/Modules 1/MAIN 1/V_VSPEED 6/Speed 1] [LEAF]
          cd 10.3.4.1.1.7 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/Modules 1/MAIN 1/DUMMY 7] (2 entries, 5 nodes, depth 3)
            cd 10.3.4.1.1.7.1 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/Modules 1/MAIN 1/DUMMY 7/Reserved 1] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.4.1.1.7.1.1 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/Modules 1/MAIN 1/DUMMY 7/Reserved 1/WU 1] [LEAF]
            cd 10.3.4.1.1.7.2 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/Modules 1/MAIN 1/DUMMY 7/No Feature 2] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.4.1.1.7.2.1 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/Modules 1/MAIN 1/DUMMY 7/No Feature 2/FUWEI 1] [LEAF]
        cd 10.3.4.1.2 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/Modules 1/DIODE 2] (2 entries, 4 nodes, depth 3)
          cd 10.3.4.1.2.1 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/Modules 1/DIODE 2/PAN 1] (1 entries, 2 nodes, depth 2) + 1 leaves
            cd 10.3.4.1.2.1.1 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/Modules 1/DIODE 2/PAN 1/Pan 1] [LEAF]
          cd 10.3.4.1.2.2 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/Modules 1/DIODE 2/DIM 2] (1 entries, 1 nodes, depth 1) [DUP of cd 10.3.4.1.1.2]
      cd 10.3.4.2 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/Instances 2] (7 entries, 8 nodes, depth 2) + 7 leaves
        cd 10.3.4.2.1 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/Instances 2/Instance 1] [LEAF]
        cd 10.3.4.2.2 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/Instances 2/Instance 2] [LEAF]
          ... (4 more leaves) ...
        cd 10.3.4.2.7 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/Instances 2/Instance 7] [LEAF]
      cd 10.3.4.3 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/Wheels 3] [LEAF]
      cd 10.3.4.4 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/VirtualFunctionBlocks 4] [LEAF]
      cd 10.3.4.5 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/PresetReferences] [LEAF]
      cd 10.3.4.6 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/FixtureMacroCollect 6] [LEAF]
      cd 10.3.4.7 → [LiveSetup/FixtureTypes 3/4 LASER BARS 26CH/RdmNotifications 7] (1 entries, 1 nodes, depth 1) [DUP of cd 10.3.1.7]
    cd 10.3.5 → [LiveSetup/FixtureTypes 3/5 RGBBLINDER BAR] (6 entries, 1 nodes, depth 1) [DUP of cd 10.3.1]
    cd 10.3.6 → [LiveSetup/FixtureTypes 3/6 LED Tri Bar F002] (6 entries, 1 nodes, depth 1) [DUP of cd 10.3.1]
    cd 10.3.7 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH] (6 entries, 32 nodes, depth 6) + 4 leaves
      cd 10.3.7.1 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH/Modules 1] (2 entries, 21 nodes, depth 5)
        cd 10.3.7.1.1 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH/Modules 1/Main Module 1] (2 entries, 9 nodes, depth 4)
          cd 10.3.7.1.1.1 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH/Modules 1/Main Module 1/INTENSITYMACROS 1] (1 entries, 4 nodes, depth 3)
            cd 10.3.7.1.1.1.1 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH/Modules 1/Main Module 1/INTENSITYMACROS 1/Audio 1] (2 entries, 3 nodes, depth 2) + 2 leaves
              cd 10.3.7.1.1.1.1.1 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH/Modules 1/Main Module 1/INTENSITYMACROS 1/Audio 1/min 1] [LEAF]
              cd 10.3.7.1.1.1.1.2 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH/Modules 1/Main Module 1/INTENSITYMACROS 1/Audio 1/max 2] [LEAF]
          cd 10.3.7.1.1.2 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH/Modules 1/Main Module 1/DIM 2] (1 entries, 4 nodes, depth 3)
            cd 10.3.7.1.1.2.1 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH/Modules 1/Main Module 1/DIM 2/Dim 1] (2 entries, 3 nodes, depth 2) + 2 leaves
              cd 10.3.7.1.1.2.1.1 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH/Modules 1/Main Module 1/DIM 2/Dim 1/closed 1] [LEAF]
              cd 10.3.7.1.1.2.1.2 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH/Modules 1/Main Module 1/DIM 2/Dim 1/open 2] [LEAF]
        cd 10.3.7.1.2 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH/Modules 1/RGB Cluster 2] (4 entries, 11 nodes, depth 4)
          cd 10.3.7.1.2.1 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH/Modules 1/RGB Cluster 2/COLORRGB1 1] (1 entries, 2 nodes, depth 2)
            cd 10.3.7.1.2.1.1 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH/Modules 1/RGB Cluster 2/COLORRGB1 1/R 1] (2 entries, 1 nodes, depth 1) [DUP of cd 10.3.7.1.1.1.1]
          cd 10.3.7.1.2.2 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH/Modules 1/RGB Cluster 2/COLORRGB2 2] (1 entries, 2 nodes, depth 2)
            cd 10.3.7.1.2.2.1 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH/Modules 1/RGB Cluster 2/COLORRGB2 2/G 1] (2 entries, 1 nodes, depth 1) [DUP of cd 10.3.7.1.1.1.1]
          cd 10.3.7.1.2.3 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH/Modules 1/RGB Cluster 2/COLORRGB3 3] (1 entries, 2 nodes, depth 2)
            cd 10.3.7.1.2.3.1 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH/Modules 1/RGB Cluster 2/COLORRGB3 3/B 1] (2 entries, 1 nodes, depth 1) [DUP of cd 10.3.7.1.1.1.1]
          cd 10.3.7.1.2.4 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH/Modules 1/RGB Cluster 2/DIM 4] (1 entries, 4 nodes, depth 3)
            cd 10.3.7.1.2.4.1 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH/Modules 1/RGB Cluster 2/DIM 4/Dim 1] (2 entries, 3 nodes, depth 2) + 2 leaves
              cd 10.3.7.1.2.4.1.1 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH/Modules 1/RGB Cluster 2/DIM 4/Dim 1/closed 1] [LEAF]
              cd 10.3.7.1.2.4.1.2 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH/Modules 1/RGB Cluster 2/DIM 4/Dim 1/open 2] [LEAF]
      cd 10.3.7.2 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH/Instances 2] (4 entries, 5 nodes, depth 2) + 4 leaves
        cd 10.3.7.2.1 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH/Instances 2/Instance 1] [LEAF]
        cd 10.3.7.2.2 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH/Instances 2/Instance 2] [LEAF]
        cd 10.3.7.2.3 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH/Instances 2/Instance 3] [LEAF]
        cd 10.3.7.2.4 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH/Instances 2/Instance 4] [LEAF]
      cd 10.3.7.3 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH/Wheels 3] [LEAF]
      cd 10.3.7.4 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH/VirtualFunctionBlocks 4] [LEAF]
      cd 10.3.7.5 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH/PresetReferences] [LEAF]
      cd 10.3.7.6 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH/FixtureMacroCollect 6] [LEAF]
      cd 10.3.7.7 → [LiveSetup/FixtureTypes 3/7 LED Bar 2 11CH/RdmNotifications 7] (1 entries, 1 nodes, depth 1) [DUP of cd 10.3.1.7]
    cd 10.3.8 → [LiveSetup/FixtureTypes 3/8 movingwash zone] (6 entries, 1 nodes, depth 1) [DUP of cd 10.3.1]
    cd 10.3.9 → [LiveSetup/FixtureTypes 3/9 movingwash zone] (6 entries, 1 nodes, depth 1) [DUP of cd 10.3.1]
    cd 10.3.10 → [LiveSetup/FixtureTypes 3/10 NEW WASH] (6 entries, 1 nodes, depth 1) [DUP of cd 10.3.1]
    cd 10.3.11 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2] (6 entries, 303 nodes, depth 6) + 3 leaves
      cd 10.3.11.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1] (1 entries, 258 nodes, depth 5)
        cd 10.3.11.1.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1] (16 entries, 257 nodes, depth 4)
          cd 10.3.11.1.1.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/PAN 1] (1 entries, 5 nodes, depth 3)
            cd 10.3.11.1.1.1.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/PAN 1/Pan 1] (3 entries, 4 nodes, depth 2) + 3 leaves
              cd 10.3.11.1.1.1.1.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/PAN 1/Pan 1/min 1] [LEAF]
              cd 10.3.11.1.1.1.1.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/PAN 1/Pan 1/center 2] [LEAF]
              cd 10.3.11.1.1.1.1.3 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/PAN 1/Pan 1/max 3] [LEAF]
          cd 10.3.11.1.1.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/TILT 2] (1 entries, 5 nodes, depth 3)
            cd 10.3.11.1.1.2.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/TILT 2/Tilt 1] (3 entries, 4 nodes, depth 2) + 3 leaves
              cd 10.3.11.1.1.2.1.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/TILT 2/Tilt 1/min 1] [LEAF]
              cd 10.3.11.1.1.2.1.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/TILT 2/Tilt 1/center 2] [LEAF]
              cd 10.3.11.1.1.2.1.3 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/TILT 2/Tilt 1/max 3] [LEAF]
          cd 10.3.11.1.1.3 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/POSITIONMSPEED 3] (1 entries, 4 nodes, depth 3)
            cd 10.3.11.1.1.3.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/POSITIONMSPEED 3/Track 1] (2 entries, 3 nodes, depth 2) + 2 leaves
              cd 10.3.11.1.1.3.1.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/POSITIONMSPEED 3/Track 1/max Track 1] [LEAF]
              cd 10.3.11.1.1.3.1.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/POSITIONMSPEED 3/Track 1/min Track 2] [LEAF]
          cd 10.3.11.1.1.4 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4] (21 entries, 42 nodes, depth 3) + 5 leaves
            cd 10.3.11.1.1.4.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/Reserved 1] [LEAF]
            cd 10.3.11.1.1.4.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/WiredDMX 2] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.11.1.1.4.2.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/WiredDMX 2/WiredDMX 1] [LEAF]
            cd 10.3.11.1.1.4.3 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/WirelessDMX 3] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.11.1.1.4.3.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/WirelessDMX 3/WirelessDMX 1] [LEAF]
            cd 10.3.11.1.1.4.4 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/Power 4] (2 entries, 3 nodes, depth 2) + 2 leaves
              cd 10.3.11.1.1.4.4.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/Power 4/Power 50% 1] [LEAF]
              cd 10.3.11.1.1.4.4.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/Power 4/Power 100% 2] [LEAF]
            cd 10.3.11.1.1.4.5 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/Reserved 5] [LEAF]
            cd 10.3.11.1.1.4.6 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/Track 6] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.11.1.1.4.6.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/Track 6/Track 1] [LEAF]
            cd 10.3.11.1.1.4.7 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/Time 7] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.11.1.1.4.7.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/Time 7/Time 1] [LEAF]
            cd 10.3.11.1.1.4.8 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/Blink 8] (2 entries, 3 nodes, depth 2) + 2 leaves
              cd 10.3.11.1.1.4.8.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/Blink 8/on 1] [LEAF]
              cd 10.3.11.1.1.4.8.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/Blink 8/off 2] [LEAF]
            cd 10.3.11.1.1.4.9 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/Select Blink 9] (2 entries, 3 nodes, depth 2) + 2 leaves
              cd 10.3.11.1.1.4.9.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/Select Blink 9/on (2) 1] [LEAF]
              cd 10.3.11.1.1.4.9.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/Select Blink 9/off (2) 2] [LEAF]
            cd 10.3.11.1.1.4.10 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/Blink 10] (2 entries, 3 nodes, depth 2) + 2 leaves
              cd 10.3.11.1.1.4.10.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/Blink 10/on (3) 1] [LEAF]
              cd 10.3.11.1.1.4.10.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/Blink 10/off (3) 2] [LEAF]
            cd 10.3.11.1.1.4.11 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/Lamp On 11] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.11.1.1.4.11.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/Lamp On 11/Lamp On 1] [LEAF]
            cd 10.3.11.1.1.4.12 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/PosReset 12] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.11.1.1.4.12.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/PosReset 12/PosReset 1] [LEAF]
            cd 10.3.11.1.1.4.13 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/ColWReset 13] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.11.1.1.4.13.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/ColWReset 13/ColWReset 1] [LEAF]
            cd 10.3.11.1.1.4.14 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/GW1Reset 14] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.11.1.1.4.14.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/GW1Reset 14/GW1Reset 1] [LEAF]
            cd 10.3.11.1.1.4.15 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/ShutReset 15] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.11.1.1.4.15.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/ShutReset 15/ShutReset 1] [LEAF]
            cd 10.3.11.1.1.4.16 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/ZoomReset 16] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.11.1.1.4.16.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/ZoomReset 16/ZoomReset 1] [LEAF]
            cd 10.3.11.1.1.4.17 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/Reserved 17] [LEAF]
            cd 10.3.11.1.1.4.18 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/Reset 18] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.11.1.1.4.18.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/Reset 18/Reset 1] [LEAF]
            cd 10.3.11.1.1.4.19 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/Reserved 19] [LEAF]
            cd 10.3.11.1.1.4.20 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/Lamp Off 20] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.11.1.1.4.20.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/Lamp Off 20/Lamp Off 1] [LEAF]
            cd 10.3.11.1.1.4.21 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/LAMPCONTROL 4/Reserved 21] [LEAF]
          cd 10.3.11.1.1.5 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/COLOR1 5] (4 entries, 23 nodes, depth 3)
            cd 10.3.11.1.1.5.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/COLOR1 5/Select 1] (29 entries, 11 nodes, depth 2) + 10 leaves
              cd 10.3.11.1.1.5.1.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/COLOR1 5/Select 1/open 1] [LEAF]
              cd 10.3.11.1.1.5.1.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/COLOR1 5/Select 1/deep red 2] [LEAF]
                ... (7 more leaves) ...
              cd 10.3.11.1.1.5.1.10 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/COLOR1 5/Select 1/amber 10] [LEAF]
            cd 10.3.11.1.1.5.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/COLOR1 5/Spin 2] (5 entries, 6 nodes, depth 2) + 5 leaves
              cd 10.3.11.1.1.5.2.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/COLOR1 5/Spin 2/>>> 1] [LEAF]
              cd 10.3.11.1.1.5.2.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/COLOR1 5/Spin 2/Spin 100..1% 2] [LEAF]
              cd 10.3.11.1.1.5.2.3 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/COLOR1 5/Spin 2/stop 3] [LEAF]
              cd 10.3.11.1.1.5.2.4 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/COLOR1 5/Spin 2/Spin -1..-100% 4] [LEAF]
              cd 10.3.11.1.1.5.2.5 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/COLOR1 5/Spin 2/<<< 5] [LEAF]
            cd 10.3.11.1.1.5.3 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/COLOR1 5/Select Audio 3] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.11.1.1.5.3.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/COLOR1 5/Select Audio 3/Select Audio 100% 1] [LEAF]
            cd 10.3.11.1.1.5.4 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/COLOR1 5/Rnd 100..1% 4] (2 entries, 3 nodes, depth 2) + 2 leaves
              cd 10.3.11.1.1.5.4.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/COLOR1 5/Rnd 100..1% 4/max Rnd 1] [LEAF]
              cd 10.3.11.1.1.5.4.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/COLOR1 5/Rnd 100..1% 4/min Rnd 2] [LEAF]
          cd 10.3.11.1.1.6 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2WHEELSELECTMSPEED 6] (1 entries, 4 nodes, depth 3)
            cd 10.3.11.1.1.6.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2WHEELSELECTMSPEED 6/Track2 1] (2 entries, 3 nodes, depth 2) + 2 leaves
              cd 10.3.11.1.1.6.1.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2WHEELSELECTMSPEED 6/Track2 1/max Track2 1] [LEAF]
              cd 10.3.11.1.1.6.1.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2WHEELSELECTMSPEED 6/Track2 1/min Track2 2] [LEAF]
          cd 10.3.11.1.1.7 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO1 7] (5 entries, 22 nodes, depth 3)
            cd 10.3.11.1.1.7.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO1 7/Select 1] (29 entries, 11 nodes, depth 2) + 10 leaves
              cd 10.3.11.1.1.7.1.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO1 7/Select 1/open 1] [LEAF]
              cd 10.3.11.1.1.7.1.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO1 7/Select 1/gobo 1.1 2] [LEAF]
                ... (7 more leaves) ...
              cd 10.3.11.1.1.7.1.10 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO1 7/Select 1/fan 3 10] [LEAF]
            cd 10.3.11.1.1.7.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO1 7/Shake 2] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.11.1.1.7.2.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO1 7/Shake 2/max Shake 1] [LEAF]
            cd 10.3.11.1.1.7.3 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO1 7/Spin 3] (5 entries, 6 nodes, depth 2) + 5 leaves
              cd 10.3.11.1.1.7.3.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO1 7/Spin 3/>>> 1] [LEAF]
              cd 10.3.11.1.1.7.3.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO1 7/Spin 3/Spin 100..1% 2] [LEAF]
              cd 10.3.11.1.1.7.3.3 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO1 7/Spin 3/stop 3] [LEAF]
              cd 10.3.11.1.1.7.3.4 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO1 7/Spin 3/Spin -1..-100% 4] [LEAF]
              cd 10.3.11.1.1.7.3.5 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO1 7/Spin 3/<<< 5] [LEAF]
            cd 10.3.11.1.1.7.4 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO1 7/Select Audio 4] (1 entries, 1 nodes, depth 1) [DUP of cd 10.3.11.1.1.5.3]
            cd 10.3.11.1.1.7.5 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO1 7/Rnd 100..1% 5] (2 entries, 1 nodes, depth 1) [DUP of cd 10.3.11.1.1.5.4]
          cd 10.3.11.1.1.8 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2 8] (8 entries, 55 nodes, depth 3) + 1 leaves
            cd 10.3.11.1.1.8.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2 8/Index2 1] (11 entries, 11 nodes, depth 2) + 10 leaves
              cd 10.3.11.1.1.8.1.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2 8/Index2 1/open 1] [LEAF]
              cd 10.3.11.1.1.8.1.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2 8/Index2 1/beam flattener 2] [LEAF]
                ... (7 more leaves) ...
              cd 10.3.11.1.1.8.1.10 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2 8/Index2 1/gobo 2.9 10] [LEAF]
            cd 10.3.11.1.1.8.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2 8/Rotate2<> 2] (9 entries, 10 nodes, depth 2) + 9 leaves
              cd 10.3.11.1.1.8.2.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2 8/Rotate2<> 2/gobo 2.2<> 1] [LEAF]
              cd 10.3.11.1.1.8.2.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2 8/Rotate2<> 2/gobo 2.3<> 2] [LEAF]
                ... (6 more leaves) ...
              cd 10.3.11.1.1.8.2.9 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2 8/Rotate2<> 2/gobo 2.10<> 9] [LEAF]
            cd 10.3.11.1.1.8.3 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2 8/Index2* 3] (9 entries, 10 nodes, depth 2) + 9 leaves
              cd 10.3.11.1.1.8.3.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2 8/Index2* 3/gobo 2.2* 1] [LEAF]
              cd 10.3.11.1.1.8.3.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2 8/Index2* 3/gobo 2.3* 2] [LEAF]
                ... (6 more leaves) ...
              cd 10.3.11.1.1.8.3.9 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2 8/Index2* 3/gobo 2.10* 9] [LEAF]
            cd 10.3.11.1.1.8.4 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2 8/Rotate2 4] (10 entries, 11 nodes, depth 2) + 10 leaves
              cd 10.3.11.1.1.8.4.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2 8/Rotate2 4/gobo 2.2<>* 1] [LEAF]
              cd 10.3.11.1.1.8.4.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2 8/Rotate2 4/gobo 2.3<>* 2] [LEAF]
                ... (7 more leaves) ...
              cd 10.3.11.1.1.8.4.10 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2 8/Rotate2 4/open<> 10] [LEAF]
            cd 10.3.11.1.1.8.5 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2 8/Spin2 5] (5 entries, 6 nodes, depth 2) + 5 leaves
              cd 10.3.11.1.1.8.5.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2 8/Spin2 5/>>> 1] [LEAF]
              cd 10.3.11.1.1.8.5.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2 8/Spin2 5/Spin2 100..1% 2] [LEAF]
              cd 10.3.11.1.1.8.5.3 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2 8/Spin2 5/stop 3] [LEAF]
              cd 10.3.11.1.1.8.5.4 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2 8/Spin2 5/Spin2 -1..-100% 4] [LEAF]
              cd 10.3.11.1.1.8.5.5 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2 8/Spin2 5/<<< 5] [LEAF]
            cd 10.3.11.1.1.8.6 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2 8/Select Audio2 6] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.11.1.1.8.6.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2 8/Select Audio2 6/Select Audio2 100% 1] [LEAF]
            cd 10.3.11.1.1.8.7 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2 8/Rnd2 100..1% 7] (2 entries, 3 nodes, depth 2) + 2 leaves
              cd 10.3.11.1.1.8.7.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2 8/Rnd2 100..1% 7/max Rnd2 1] [LEAF]
              cd 10.3.11.1.1.8.7.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2 8/Rnd2 100..1% 7/min Rnd2 2] [LEAF]
            cd 10.3.11.1.1.8.8 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2 8/No Feature 8] [LEAF]
          cd 10.3.11.1.1.9 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2_POS 9] (4 entries, 13 nodes, depth 3)
            cd 10.3.11.1.1.9.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2_POS 9/Index2 1] (2 entries, 3 nodes, depth 2) + 2 leaves
              cd 10.3.11.1.1.9.1.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2_POS 9/Index2 1/zero 1] [LEAF]
              cd 10.3.11.1.1.9.1.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2_POS 9/Index2 1/max CW 2] [LEAF]
            cd 10.3.11.1.1.9.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2_POS 9/Index2 2] (2 entries, 1 nodes, depth 1) [DUP of cd 10.3.11.1.1.9.1]
            cd 10.3.11.1.1.9.3 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2_POS 9/Rotate2 3] (6 entries, 7 nodes, depth 2) + 6 leaves
              cd 10.3.11.1.1.9.3.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2_POS 9/Rotate2 3/stop (2) 1] [LEAF]
              cd 10.3.11.1.1.9.3.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2_POS 9/Rotate2 3/>>> 2] [LEAF]
                ... (3 more leaves) ...
              cd 10.3.11.1.1.9.3.6 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2_POS 9/Rotate2 3/<<< 6] [LEAF]
            cd 10.3.11.1.1.9.4 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/GOBO2_POS 9/Rotate2 4] (6 entries, 1 nodes, depth 1) [DUP of cd 10.3.11.1.1.9.3]
          cd 10.3.11.1.1.10 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/EFFECTWHEEL 10] (6 entries, 22 nodes, depth 3)
            cd 10.3.11.1.1.10.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/EFFECTWHEEL 10/Select 1] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.11.1.1.10.1.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/EFFECTWHEEL 10/Select 1/open 1] [LEAF]
            cd 10.3.11.1.1.10.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/EFFECTWHEEL 10/Pos 2] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.11.1.1.10.2.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/EFFECTWHEEL 10/Pos 2/6 facet prism 1] [LEAF]
            cd 10.3.11.1.1.10.3 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/EFFECTWHEEL 10/Rot<> 3] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.11.1.1.10.3.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/EFFECTWHEEL 10/Rot<> 3/6 facet prism<> 1] [LEAF]
            cd 10.3.11.1.1.10.4 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/EFFECTWHEEL 10/Pos 4] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.11.1.1.10.4.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/EFFECTWHEEL 10/Pos 4/8 facet prism 1] [LEAF]
            cd 10.3.11.1.1.10.5 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/EFFECTWHEEL 10/Rot<> 5] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.11.1.1.10.5.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/EFFECTWHEEL 10/Rot<> 5/8 facet prism<> 1] [LEAF]
            cd 10.3.11.1.1.10.6 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/EFFECTWHEEL 10/Select 6] (16 entries, 11 nodes, depth 2) + 10 leaves
              cd 10.3.11.1.1.10.6.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/EFFECTWHEEL 10/Select 6/entry 1 1] [LEAF]
              cd 10.3.11.1.1.10.6.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/EFFECTWHEEL 10/Select 6/entry 2 2] [LEAF]
                ... (7 more leaves) ...
              cd 10.3.11.1.1.10.6.10 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/EFFECTWHEEL 10/Select 6/entry 10 10] [LEAF]
          cd 10.3.11.1.1.11 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/EFFECTINDEXROTATE 11] (6 entries, 15 nodes, depth 3) + 1 leaves
            cd 10.3.11.1.1.11.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/EFFECTINDEXROTATE 11/Index 1] (2 entries, 3 nodes, depth 2) + 2 leaves
              cd 10.3.11.1.1.11.1.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/EFFECTINDEXROTATE 11/Index 1/max CW 1] [LEAF]
              cd 10.3.11.1.1.11.1.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/EFFECTINDEXROTATE 11/Index 1/zero 2] [LEAF]
            cd 10.3.11.1.1.11.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/EFFECTINDEXROTATE 11/Pos 2] (2 entries, 1 nodes, depth 1) [DUP of cd 10.3.11.1.1.11.1]
            cd 10.3.11.1.1.11.3 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/EFFECTINDEXROTATE 11/Rot 3] (6 entries, 7 nodes, depth 2) + 6 leaves
              cd 10.3.11.1.1.11.3.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/EFFECTINDEXROTATE 11/Rot 3/stop (2) 1] [LEAF]
              cd 10.3.11.1.1.11.3.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/EFFECTINDEXROTATE 11/Rot 3/>>> 2] [LEAF]
                ... (3 more leaves) ...
              cd 10.3.11.1.1.11.3.6 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/EFFECTINDEXROTATE 11/Rot 3/<<< 6] [LEAF]
            cd 10.3.11.1.1.11.4 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/EFFECTINDEXROTATE 11/Pos 4] (2 entries, 1 nodes, depth 1) [DUP of cd 10.3.11.1.1.11.1]
            cd 10.3.11.1.1.11.5 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/EFFECTINDEXROTATE 11/Rot 5] (6 entries, 1 nodes, depth 1) [DUP of cd 10.3.11.1.1.11.3]
            cd 10.3.11.1.1.11.6 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/EFFECTINDEXROTATE 11/No Feature 6] [LEAF]
          cd 10.3.11.1.1.12 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/FROST 12] (4 entries, 14 nodes, depth 3)
            cd 10.3.11.1.1.12.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/FROST 12/Frost 1] (3 entries, 4 nodes, depth 2) + 3 leaves
              cd 10.3.11.1.1.12.1.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/FROST 12/Frost 1/min Frost 1] [LEAF]
              cd 10.3.11.1.1.12.1.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/FROST 12/Frost 1/Frost 0..100% 2] [LEAF]
              cd 10.3.11.1.1.12.1.3 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/FROST 12/Frost 1/Frost 100% 3] [LEAF]
            cd 10.3.11.1.1.12.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/FROST 12/Strobe Pulse Increase 1..100% 2] (2 entries, 3 nodes, depth 2) + 2 leaves
              cd 10.3.11.1.1.12.2.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/FROST 12/Strobe Pulse Increase 1..100% 2/min Strobe Pulse Increase 1] [LEAF]
              cd 10.3.11.1.1.12.2.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/FROST 12/Strobe Pulse Increase 1..100% 2/max Strobe Pulse Increase 2] [LEAF]
            cd 10.3.11.1.1.12.3 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/FROST 12/Strobe Pulse Decrease 100..1% 3] (2 entries, 3 nodes, depth 2) + 2 leaves
              cd 10.3.11.1.1.12.3.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/FROST 12/Strobe Pulse Decrease 100..1% 3/max Strobe Pulse Decrease 1] [LEAF]
              cd 10.3.11.1.1.12.3.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/FROST 12/Strobe Pulse Decrease 100..1% 3/min Strobe Pulse Decrease 2] [LEAF]
            cd 10.3.11.1.1.12.4 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/FROST 12/Strobe Pulse 100..1% 4] (2 entries, 3 nodes, depth 2) + 2 leaves
              cd 10.3.11.1.1.12.4.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/FROST 12/Strobe Pulse 100..1% 4/max Strobe Pulse 1] [LEAF]
              cd 10.3.11.1.1.12.4.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/FROST 12/Strobe Pulse 100..1% 4/min Strobe Pulse 2] [LEAF]
          cd 10.3.11.1.1.13 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/ZOOM 13] (1 entries, 5 nodes, depth 3)
            cd 10.3.11.1.1.13.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/ZOOM 13/Zoom 1] (3 entries, 4 nodes, depth 2) + 3 leaves
              cd 10.3.11.1.1.13.1.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/ZOOM 13/Zoom 1/wide 1] [LEAF]
              cd 10.3.11.1.1.13.1.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/ZOOM 13/Zoom 1/normal 2] [LEAF]
              cd 10.3.11.1.1.13.1.3 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/ZOOM 13/Zoom 1/narrow 3] [LEAF]
          cd 10.3.11.1.1.14 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/FOCUS 14] (1 entries, 4 nodes, depth 3)
            cd 10.3.11.1.1.14.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/FOCUS 14/Focus 1] (2 entries, 3 nodes, depth 2) + 2 leaves
              cd 10.3.11.1.1.14.1.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/FOCUS 14/Focus 1/max Focus 1] [LEAF]
              cd 10.3.11.1.1.14.1.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/FOCUS 14/Focus 1/min Focus 2] [LEAF]
          cd 10.3.11.1.1.15 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/SHUTTER 15] (8 entries, 22 nodes, depth 3)
            cd 10.3.11.1.1.15.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/SHUTTER 15/Shutter 1] (2 entries, 3 nodes, depth 2) + 2 leaves
              cd 10.3.11.1.1.15.1.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/SHUTTER 15/Shutter 1/closed 1] [LEAF]
              cd 10.3.11.1.1.15.1.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/SHUTTER 15/Shutter 1/open 2] [LEAF]
            cd 10.3.11.1.1.15.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/SHUTTER 15/Strobe 1..100% 2] (2 entries, 3 nodes, depth 2) + 2 leaves
              cd 10.3.11.1.1.15.2.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/SHUTTER 15/Strobe 1..100% 2/min Strobe 1] [LEAF]
              cd 10.3.11.1.1.15.2.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/SHUTTER 15/Strobe 1..100% 2/max Strobe 2] [LEAF]
            cd 10.3.11.1.1.15.3 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/SHUTTER 15/Shutter 3] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.11.1.1.15.3.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/SHUTTER 15/Shutter 3/open (2) 1] [LEAF]
            cd 10.3.11.1.1.15.4 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/SHUTTER 15/Pulse Open 1..100% 4] (2 entries, 3 nodes, depth 2) + 2 leaves
              cd 10.3.11.1.1.15.4.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/SHUTTER 15/Pulse Open 1..100% 4/min Pulse Open 1] [LEAF]
              cd 10.3.11.1.1.15.4.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/SHUTTER 15/Pulse Open 1..100% 4/max Pulse Open 2] [LEAF]
            cd 10.3.11.1.1.15.5 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/SHUTTER 15/Pulse Close 100..1% 5] (2 entries, 3 nodes, depth 2) + 2 leaves
              cd 10.3.11.1.1.15.5.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/SHUTTER 15/Pulse Close 100..1% 5/max Pulse Close 1] [LEAF]
              cd 10.3.11.1.1.15.5.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/SHUTTER 15/Pulse Close 100..1% 5/min Pulse Close 2] [LEAF]
            cd 10.3.11.1.1.15.6 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/SHUTTER 15/Shutter 6] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.11.1.1.15.6.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/SHUTTER 15/Shutter 6/open (3) 1] [LEAF]
            cd 10.3.11.1.1.15.7 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/SHUTTER 15/Rnd 1..100% 7] (2 entries, 3 nodes, depth 2) + 2 leaves
              cd 10.3.11.1.1.15.7.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/SHUTTER 15/Rnd 1..100% 7/min Rnd 1] [LEAF]
              cd 10.3.11.1.1.15.7.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/SHUTTER 15/Rnd 1..100% 7/max Rnd 2] [LEAF]
            cd 10.3.11.1.1.15.8 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/SHUTTER 15/Power 8] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.11.1.1.15.8.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/SHUTTER 15/Power 8/Power 100% 1] [LEAF]
          cd 10.3.11.1.1.16 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Modules 1/Main Module 1/DIM 16] (1 entries, 1 nodes, depth 1) [DUP of cd 10.3.7.1.1.2]
      cd 10.3.11.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Instances 2] (1 entries, 2 nodes, depth 2) + 1 leaves
        cd 10.3.11.2.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Instances 2/Instance 1] [LEAF]
      cd 10.3.11.3 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Wheels 3] (4 entries, 38 nodes, depth 3)
        cd 10.3.11.3.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Wheels 3/C1 - Select 1] (14 entries, 11 nodes, depth 2) + 10 leaves
          cd 10.3.11.3.1.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Wheels 3/C1 - Select 1/Slot 1] [LEAF]
          cd 10.3.11.3.1.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Wheels 3/C1 - Select 1/Slot 2] [LEAF]
            ... (7 more leaves) ...
          cd 10.3.11.3.1.10 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Wheels 3/C1 - Select 1/Slot 10] [LEAF]
        cd 10.3.11.3.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Wheels 3/G1 - Select 2] (15 entries, 11 nodes, depth 2) + 10 leaves
          cd 10.3.11.3.2.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Wheels 3/G1 - Select 2/Slot 1] [LEAF]
          cd 10.3.11.3.2.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Wheels 3/G1 - Select 2/Slot 2] [LEAF]
            ... (7 more leaves) ...
          cd 10.3.11.3.2.10 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Wheels 3/G1 - Select 2/Slot 10] [LEAF]
        cd 10.3.11.3.3 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Wheels 3/G2 - Select2 3] (11 entries, 11 nodes, depth 2) + 10 leaves
          cd 10.3.11.3.3.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Wheels 3/G2 - Select2 3/Slot 1] [LEAF]
          cd 10.3.11.3.3.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Wheels 3/G2 - Select2 3/Slot 2] [LEAF]
            ... (7 more leaves) ...
          cd 10.3.11.3.3.10 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Wheels 3/G2 - Select2 3/Slot 10] [LEAF]
        cd 10.3.11.3.4 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Wheels 3/E - Select 4] (3 entries, 4 nodes, depth 2) + 3 leaves
          cd 10.3.11.3.4.1 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Wheels 3/E - Select 4/Slot 1] [LEAF]
          cd 10.3.11.3.4.2 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Wheels 3/E - Select 4/Slot 2] [LEAF]
          cd 10.3.11.3.4.3 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/Wheels 3/E - Select 4/Slot 3] [LEAF]
      cd 10.3.11.4 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/VirtualFunctionBlocks 4] [LEAF]
      cd 10.3.11.5 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/PresetReferences] [LEAF]
      cd 10.3.11.6 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/FixtureMacroCollect 6] [LEAF]
      cd 10.3.11.7 → [LiveSetup/FixtureTypes 3/11 Robin Pointe Mode 2/RdmNotifications 7] (1 entries, 1 nodes, depth 1) [DUP of cd 10.3.1.7]
    cd 10.3.12 → [LiveSetup/FixtureTypes 3/12 Robin Pointe Mode 1] (6 entries, 1 nodes, depth 1) [DUP of cd 10.3.11]
    cd 10.3.13 → [LiveSetup/FixtureTypes 3/13 Robin Pointe Mode 3] (6 entries, 1 nodes, depth 1) [DUP of cd 10.3.11]
    cd 10.3.14 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on] (6 entries, 154 nodes, depth 6) + 3 leaves
      cd 10.3.14.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1] (1 entries, 122 nodes, depth 5)
        cd 10.3.14.1.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1] (14 entries, 121 nodes, depth 4)
          cd 10.3.14.1.1.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/COLOR1 1] (2 entries, 15 nodes, depth 3)
            cd 10.3.14.1.1.1.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/COLOR1 1/Select 1] (30 entries, 11 nodes, depth 2) + 10 leaves
              cd 10.3.14.1.1.1.1.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/COLOR1 1/Select 1/open 1] [LEAF]
              cd 10.3.14.1.1.1.1.2 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/COLOR1 1/Select 1/open (2) 2] [LEAF]
                ... (7 more leaves) ...
              cd 10.3.14.1.1.1.1.10 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/COLOR1 1/Select 1/green (2) 10] [LEAF]
            cd 10.3.14.1.1.1.2 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/COLOR1 1/Spin 1..100% 2] (2 entries, 3 nodes, depth 2) + 2 leaves
              cd 10.3.14.1.1.1.2.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/COLOR1 1/Spin 1..100% 2/<<< 1] [LEAF]
              cd 10.3.14.1.1.1.2.2 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/COLOR1 1/Spin 1..100% 2/>>> 2] [LEAF]
          cd 10.3.14.1.1.2 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/SHUTTER 2] (7 entries, 18 nodes, depth 3)
            cd 10.3.14.1.1.2.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/SHUTTER 2/Shutter 1] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.14.1.1.2.1.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/SHUTTER 2/Shutter 1/closed 1] [LEAF]
            cd 10.3.14.1.1.2.2 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/SHUTTER 2/Strobe 1..100% 2] (2 entries, 3 nodes, depth 2) + 2 leaves
              cd 10.3.14.1.1.2.2.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/SHUTTER 2/Strobe 1..100% 2/min Strobe 1] [LEAF]
              cd 10.3.14.1.1.2.2.2 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/SHUTTER 2/Strobe 1..100% 2/max Strobe 2] [LEAF]
            cd 10.3.14.1.1.2.3 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/SHUTTER 2/Shutter 3] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.14.1.1.2.3.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/SHUTTER 2/Shutter 3/open 1] [LEAF]
            cd 10.3.14.1.1.2.4 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/SHUTTER 2/StrobeIsophase 1..100% 4] (2 entries, 3 nodes, depth 2) + 2 leaves
              cd 10.3.14.1.1.2.4.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/SHUTTER 2/StrobeIsophase 1..100% 4/min StrobeIsophase 1] [LEAF]
              cd 10.3.14.1.1.2.4.2 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/SHUTTER 2/StrobeIsophase 1..100% 4/max StrobeIsophase 2] [LEAF]
            cd 10.3.14.1.1.2.5 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/SHUTTER 2/Shutter 5] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.14.1.1.2.5.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/SHUTTER 2/Shutter 5/open (2) 1] [LEAF]
            cd 10.3.14.1.1.2.6 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/SHUTTER 2/Rnd 1..100% 6] (2 entries, 3 nodes, depth 2) + 2 leaves
              cd 10.3.14.1.1.2.6.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/SHUTTER 2/Rnd 1..100% 6/min Rnd 1] [LEAF]
              cd 10.3.14.1.1.2.6.2 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/SHUTTER 2/Rnd 1..100% 6/max Rnd 2] [LEAF]
            cd 10.3.14.1.1.2.7 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/SHUTTER 2/Shutter 7] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.14.1.1.2.7.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/SHUTTER 2/Shutter 7/open (3) 1] [LEAF]
          cd 10.3.14.1.1.3 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/DIM 3] (1 entries, 1 nodes, depth 1) [DUP of cd 10.3.7.1.1.2]
          cd 10.3.14.1.1.4 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/GOBO1 4] (3 entries, 29 nodes, depth 3)
            cd 10.3.14.1.1.4.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/GOBO1 4/Select 1] (18 entries, 11 nodes, depth 2) + 10 leaves
              cd 10.3.14.1.1.4.1.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/GOBO1 4/Select 1/open 1] [LEAF]
              cd 10.3.14.1.1.4.1.2 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/GOBO1 4/Select 1/gobo 1.1 2] [LEAF]
                ... (7 more leaves) ...
              cd 10.3.14.1.1.4.1.10 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/GOBO1 4/Select 1/gobo 1.9 10] [LEAF]
            cd 10.3.14.1.1.4.2 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/GOBO1 4/Spin 2] (5 entries, 6 nodes, depth 2) + 5 leaves
              cd 10.3.14.1.1.4.2.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/GOBO1 4/Spin 2/<<< 1] [LEAF]
              cd 10.3.14.1.1.4.2.2 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/GOBO1 4/Spin 2/Spin -100..-1% 2] [LEAF]
              cd 10.3.14.1.1.4.2.3 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/GOBO1 4/Spin 2/stop 3] [LEAF]
              cd 10.3.14.1.1.4.2.4 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/GOBO1 4/Spin 2/Spin 1..100% 4] [LEAF]
              cd 10.3.14.1.1.4.2.5 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/GOBO1 4/Spin 2/>>> 5] [LEAF]
            cd 10.3.14.1.1.4.3 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/GOBO1 4/Select 3] (15 entries, 11 nodes, depth 2) + 10 leaves
              cd 10.3.14.1.1.4.3.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/GOBO1 4/Select 3/gobo 1.2* 1] [LEAF]
              cd 10.3.14.1.1.4.3.2 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/GOBO1 4/Select 3/gobo 1.3* 2] [LEAF]
                ... (7 more leaves) ...
              cd 10.3.14.1.1.4.3.10 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/GOBO1 4/Select 3/gobo 1.11* 10] [LEAF]
          cd 10.3.14.1.1.5 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/EFFECTWHEEL 5] (2 entries, 5 nodes, depth 3)
            cd 10.3.14.1.1.5.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/EFFECTWHEEL 5/Select 1] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.14.1.1.5.1.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/EFFECTWHEEL 5/Select 1/open 1] [LEAF]
            cd 10.3.14.1.1.5.2 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/EFFECTWHEEL 5/Prism1 2] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.14.1.1.5.2.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/EFFECTWHEEL 5/Prism1 2/8 facet prism 1] [LEAF]
          cd 10.3.14.1.1.6 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/EFFECTINDEXROTATE 6] (2 entries, 10 nodes, depth 3)
            cd 10.3.14.1.1.6.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/EFFECTINDEXROTATE 6/Index 0..100% 1] (2 entries, 3 nodes, depth 2) + 2 leaves
              cd 10.3.14.1.1.6.1.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/EFFECTINDEXROTATE 6/Index 0..100% 1/zero 1] [LEAF]
              cd 10.3.14.1.1.6.1.2 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/EFFECTINDEXROTATE 6/Index 0..100% 1/max CW 2] [LEAF]
            cd 10.3.14.1.1.6.2 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/EFFECTINDEXROTATE 6/Rot 2] (5 entries, 6 nodes, depth 2) + 5 leaves
              cd 10.3.14.1.1.6.2.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/EFFECTINDEXROTATE 6/Rot 2/<<< 1] [LEAF]
              cd 10.3.14.1.1.6.2.2 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/EFFECTINDEXROTATE 6/Rot 2/Rotate -100..-1% 2] [LEAF]
              cd 10.3.14.1.1.6.2.3 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/EFFECTINDEXROTATE 6/Rot 2/stop 3] [LEAF]
              cd 10.3.14.1.1.6.2.4 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/EFFECTINDEXROTATE 6/Rot 2/Rotate 1..100% 4] [LEAF]
              cd 10.3.14.1.1.6.2.5 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/EFFECTINDEXROTATE 6/Rot 2/>>> 5] [LEAF]
          cd 10.3.14.1.1.7 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/EFFECTWHEELPOSITION 7] (1 entries, 4 nodes, depth 3)
            cd 10.3.14.1.1.7.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/EFFECTWHEELPOSITION 7/EffectWheelPosition 1] (2 entries, 3 nodes, depth 2) + 2 leaves
              cd 10.3.14.1.1.7.1.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/EFFECTWHEELPOSITION 7/EffectWheelPosition 1/min EffectWheelPosition 1] [LEAF]
              cd 10.3.14.1.1.7.1.2 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/EFFECTWHEELPOSITION 7/EffectWheelPosition 1/max EffectWheelPosition 2] [LEAF]
          cd 10.3.14.1.1.8 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/FROST 8] (1 entries, 4 nodes, depth 3)
            cd 10.3.14.1.1.8.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/FROST 8/Frost 1] (2 entries, 3 nodes, depth 2) + 2 leaves
              cd 10.3.14.1.1.8.1.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/FROST 8/Frost 1/min Frost 1] [LEAF]
              cd 10.3.14.1.1.8.1.2 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/FROST 8/Frost 1/max Frost 2] [LEAF]
          cd 10.3.14.1.1.9 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/FOCUS 9] (1 entries, 1 nodes, depth 1) [DUP of cd 10.3.11.1.1.14]
          cd 10.3.14.1.1.10 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/PAN 10] (1 entries, 5 nodes, depth 3)
            cd 10.3.14.1.1.10.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/PAN 10/Pan 1] (3 entries, 4 nodes, depth 2) + 3 leaves
              cd 10.3.14.1.1.10.1.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/PAN 10/Pan 1/min 1] [LEAF]
              cd 10.3.14.1.1.10.1.2 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/PAN 10/Pan 1/center 2] [LEAF]
              cd 10.3.14.1.1.10.1.3 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/PAN 10/Pan 1/max 3] [LEAF]
          cd 10.3.14.1.1.11 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/TILT 11] (1 entries, 5 nodes, depth 3)
            cd 10.3.14.1.1.11.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/TILT 11/Tilt 1] (3 entries, 4 nodes, depth 2) + 3 leaves
              cd 10.3.14.1.1.11.1.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/TILT 11/Tilt 1/min 1] [LEAF]
              cd 10.3.14.1.1.11.1.2 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/TILT 11/Tilt 1/center 2] [LEAF]
              cd 10.3.14.1.1.11.1.3 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/TILT 11/Tilt 1/max 3] [LEAF]
          cd 10.3.14.1.1.12 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/DIMMERCURVE 12] (4 entries, 9 nodes, depth 3) + 2 leaves
            cd 10.3.14.1.1.12.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/DIMMERCURVE 12/No Feature 1] [LEAF]
            cd 10.3.14.1.1.12.2 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/DIMMERCURVE 12/Time 2] (2 entries, 3 nodes, depth 2) + 2 leaves
              cd 10.3.14.1.1.12.2.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/DIMMERCURVE 12/Time 2/Time 100% 1] [LEAF]
              cd 10.3.14.1.1.12.2.2 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/DIMMERCURVE 12/Time 2/Time 50% 2] [LEAF]
            cd 10.3.14.1.1.12.3 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/DIMMERCURVE 12/Curve 3] (2 entries, 3 nodes, depth 2) + 2 leaves
              cd 10.3.14.1.1.12.3.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/DIMMERCURVE 12/Curve 3/conventional 1] [LEAF]
              cd 10.3.14.1.1.12.3.2 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/DIMMERCURVE 12/Curve 3/linear 2] [LEAF]
            cd 10.3.14.1.1.12.4 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/DIMMERCURVE 12/No Feature 4] [LEAF]
          cd 10.3.14.1.1.13 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/FIXTUREGLOBALRESET 13] (4 entries, 8 nodes, depth 3) + 1 leaves
            cd 10.3.14.1.1.13.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/FIXTUREGLOBALRESET 13/No Feature 1] [LEAF]
            cd 10.3.14.1.1.13.2 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/FIXTUREGLOBALRESET 13/GW1Reset 2] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.14.1.1.13.2.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/FIXTUREGLOBALRESET 13/GW1Reset 2/GW1Reset 1] [LEAF]
            cd 10.3.14.1.1.13.3 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/FIXTUREGLOBALRESET 13/PosReset 3] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.14.1.1.13.3.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/FIXTUREGLOBALRESET 13/PosReset 3/PosReset 1] [LEAF]
            cd 10.3.14.1.1.13.4 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/FIXTUREGLOBALRESET 13/Reset 4] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.14.1.1.13.4.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/FIXTUREGLOBALRESET 13/Reset 4/Reset 1] [LEAF]
          cd 10.3.14.1.1.14 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/LAMPCONTROL 14] (3 entries, 6 nodes, depth 3) + 1 leaves
            cd 10.3.14.1.1.14.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/LAMPCONTROL 14/No Feature 1] [LEAF]
            cd 10.3.14.1.1.14.2 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/LAMPCONTROL 14/Lamp Off 2] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.14.1.1.14.2.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/LAMPCONTROL 14/Lamp Off 2/Lamp Off 1] [LEAF]
            cd 10.3.14.1.1.14.3 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/LAMPCONTROL 14/Lamp On 3] (1 entries, 2 nodes, depth 2) + 1 leaves
              cd 10.3.14.1.1.14.3.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Modules 1/Main Module 1/LAMPCONTROL 14/Lamp On 3/Lamp On 1] [LEAF]
      cd 10.3.14.2 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Instances 2] (1 entries, 1 nodes, depth 1) [DUP of cd 10.3.11.2]
      cd 10.3.14.3 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Wheels 3] (3 entries, 26 nodes, depth 3)
        cd 10.3.14.3.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Wheels 3/C1 - Select 1] (15 entries, 11 nodes, depth 2) + 10 leaves
          cd 10.3.14.3.1.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Wheels 3/C1 - Select 1/Slot 1] [LEAF]
          cd 10.3.14.3.1.2 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Wheels 3/C1 - Select 1/Slot 2] [LEAF]
            ... (7 more leaves) ...
          cd 10.3.14.3.1.10 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Wheels 3/C1 - Select 1/Slot 10] [LEAF]
        cd 10.3.14.3.2 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Wheels 3/G1 - Select 2] (18 entries, 11 nodes, depth 2) + 10 leaves
          cd 10.3.14.3.2.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Wheels 3/G1 - Select 2/Slot 1] [LEAF]
          cd 10.3.14.3.2.2 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Wheels 3/G1 - Select 2/Slot 2] [LEAF]
            ... (7 more leaves) ...
          cd 10.3.14.3.2.10 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Wheels 3/G1 - Select 2/Slot 10] [LEAF]
        cd 10.3.14.3.3 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Wheels 3/E - Select 3] (2 entries, 3 nodes, depth 2) + 2 leaves
          cd 10.3.14.3.3.1 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Wheels 3/E - Select 3/Slot 1] [LEAF]
          cd 10.3.14.3.3.2 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/Wheels 3/E - Select 3/Slot 2] [LEAF]
      cd 10.3.14.4 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/VirtualFunctionBlocks 4] [LEAF]
      cd 10.3.14.5 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/PresetReferences] [LEAF]
      cd 10.3.14.6 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/FixtureMacroCollect 6] [LEAF]
      cd 10.3.14.7 → [LiveSetup/FixtureTypes 3/14 Sharpy Standard Lamp on/RdmNotifications 7] (1 entries, 1 nodes, depth 1) [DUP of cd 10.3.1.7]
  cd 10.4 → [LiveSetup/Layers 4] [LEAF]
  cd 10.5 → [LiveSetup/Universes] (256 entries, 11 nodes, depth 2) + 10 leaves
    cd 10.5.1 → [LiveSetup/Universes /Universe 1] [LEAF]
    cd 10.5.2 → [LiveSetup/Universes /Universe 2] [LEAF]
      ... (7 more leaves) ...
    cd 10.5.10 → [LiveSetup/Universes /Universe 10] [LEAF]
  cd 10.6 → [LiveSetup/Objects3D 6] (3 entries, 24 nodes, depth 4) + 1 leaves
    cd 10.6.1 → [LiveSetup/Objects3D 6/Resource3D 1] [LEAF]
    cd 10.6.2 → [LiveSetup/Objects3D 6/Models 2] (14 entries, 4 nodes, depth 3) + 1 leaves
      cd 10.6.2.1 → [LiveSetup/Objects3D 6/Models 2/Stage Plane 1] [LEAF]
      cd 10.6.2.2 → [LiveSetup/Objects3D 6/Models 2/2 Dimmer Main Module 2] (1 entries, 2 nodes, depth 2) + 1 leaves
        cd 10.6.2.2.1 → [LiveSetup/Objects3D 6/Models 2/2 Dimmer Main Module 2/Model 1] [LEAF]
    cd 10.6.3 → [LiveSetup/Objects3D 6/Items3D 3] (23 entries, 18 nodes, depth 3) + 13 leaves
      cd 10.6.3.1 → [LiveSetup/Objects3D 6/Items3D 3/Stage Plane 1] [LEAF]
      cd 10.6.3.2 → [LiveSetup/Objects3D 6/Items3D 3/Stage Markers 2] [LEAF]
      cd 10.6.3.3 → [LiveSetup/Objects3D 6/Items3D 3/RGBBLIND 2 20] [LEAF]
      cd 10.6.3.4 → [LiveSetup/Objects3D 6/Items3D 3/LTBF002 1 801] (3 entries, 4 nodes, depth 2) + 3 leaves
        cd 10.6.3.4.1 → [LiveSetup/Objects3D 6/Items3D 3/LTBF002 1 801/LTBF002 1 801] [LEAF]
        cd 10.6.3.4.2 → [LiveSetup/Objects3D 6/Items3D 3/LTBF002 1 801/LTBF002 1 801] [LEAF]
        cd 10.6.3.4.3 → [LiveSetup/Objects3D 6/Items3D 3/LTBF002 1 801/LTBF002 1 801] [LEAF]
      cd 10.6.3.5 → [LiveSetup/Objects3D 6/Items3D 3/Dim 1 30] [LEAF]
      cd 10.6.3.6 → [LiveSetup/Objects3D 6/Items3D 3/movingwa 2 26] [LEAF]
        ... (7 more leaves) ...
      cd 10.6.3.14 → [LiveSetup/Objects3D 6/Items3D 3/movingwa 1 126] [LEAF]
cd 13 → [Macros] [LEAF]
cd 14 → [FlightRecordings] [LEAF]
cd 15 → [Plugins] (1 entries, 2 nodes, depth 2) + 1 leaves
  cd 15.1 → [Plugins/LUA 1] [LEAF]
cd 16 → [Gels] (13 entries, 144 nodes, depth 3)
  cd 16.1 → [Gels/MA colors 1] (13 entries, 11 nodes, depth 2) + 10 leaves
    cd 16.1.1 → [Gels/MA colors 1/White 1] [LEAF]
    cd 16.1.2 → [Gels/MA colors 1/Red 2] [LEAF]
      ... (7 more leaves) ...
    cd 16.1.10 → [Gels/MA colors 1/Blue 10] [LEAF]
  cd 16.2 → [Gels/CalColor 2] (33 entries, 11 nodes, depth 2) + 10 leaves
    cd 16.2.1 → [Gels/CalColor 2/calcolor 15 blue 1] [LEAF]
    cd 16.2.2 → [Gels/CalColor 2/calcolor 30 blue 2] [LEAF]
      ... (7 more leaves) ...
    cd 16.2.10 → [Gels/CalColor 2/calcolor 15 green 10] [LEAF]
  cd 16.3 → [Gels/Cinegel 3] (69 entries, 11 nodes, depth 2) + 10 leaves
    cd 16.3.1 → [Gels/Cinegel 3/tough rolux 1] [LEAF]
    cd 16.3.2 → [Gels/Cinegel 3/light tough rolux 2] [LEAF]
      ... (7 more leaves) ...
    cd 16.3.10 → [Gels/Cinegel 3/togh silk 10] [LEAF]
  cd 16.4 → [Gels/Cinelux 4] (51 entries, 11 nodes, depth 2) + 10 leaves
    cd 16.4.1 → [Gels/Cinelux 4/bastard amber 1] [LEAF]
    cd 16.4.2 → [Gels/Cinelux 4/no color straw 2] [LEAF]
      ... (7 more leaves) ...
    cd 16.4.10 → [Gels/Cinelux 4/light red 10] [LEAF]
  cd 16.5 → [Gels/E Colour 5] (224 entries, 11 nodes, depth 2) + 10 leaves
    cd 16.5.1 → [Gels/E Colour 5/rose pink 1] [LEAF]
    cd 16.5.2 → [Gels/E Colour 5/lavender tint 2] [LEAF]
      ... (7 more leaves) ...
    cd 16.5.10 → [Gels/E Colour 5/surprise peach 10] [LEAF]
  cd 16.6 → [Gels/GamColor 6] (144 entries, 11 nodes, depth 2) + 10 leaves
    cd 16.6.1 → [Gels/GamColor 6/gypsy pink 1] [LEAF]
    cd 16.6.2 → [Gels/GamColor 6/lavender blue 2] [LEAF]
      ... (7 more leaves) ...
    cd 16.6.10 → [Gels/GamColor 6/naked pink 10] [LEAF]
  cd 16.7 → [Gels/Gel 7] (153 entries, 11 nodes, depth 2) + 10 leaves
    cd 16.7.1 → [Gels/Gel 7/soft diffusion 1] [LEAF]
    cd 16.7.2 → [Gels/Gel 7/hard diffusion 2] [LEAF]
      ... (7 more leaves) ...
    cd 16.7.10 → [Gels/Gel 7/light textured diffusion 10] [LEAF]
  cd 16.8 → [Gels/Lee 8] (328 entries, 11 nodes, depth 2) + 10 leaves
    cd 16.8.1 → [Gels/Lee 8/rose pink 1] [LEAF]
    cd 16.8.2 → [Gels/Lee 8/lavender tint 2] [LEAF]
      ... (7 more leaves) ...
    cd 16.8.10 → [Gels/Lee 8/surprise peach 10] [LEAF]
  cd 16.9 → [Gels/Poly Colour 9] (80 entries, 11 nodes, depth 2) + 10 leaves
    cd 16.9.1 → [Gels/Poly Colour 9/0 1] [LEAF]
    cd 16.9.2 → [Gels/Poly Colour 9/00 2] [LEAF]
      ... (7 more leaves) ...
    cd 16.9.10 → [Gels/Poly Colour 9/22 10] [LEAF]
  cd 16.10 → [Gels/Roscolux 10] (191 entries, 11 nodes, depth 2) + 10 leaves
    cd 16.10.1 → [Gels/Roscolux 10/clear 1] [LEAF]
    cd 16.10.2 → [Gels/Roscolux 10/light bastard amber 2] [LEAF]
      ... (7 more leaves) ...
    cd 16.10.10 → [Gels/Roscolux 10/pale amber gold 10] [LEAF]
  cd 16.11 → [Gels/Storaro Selection 11] (10 entries, 11 nodes, depth 2) + 10 leaves
    cd 16.11.1 → [Gels/Storaro Selection 11/storaro red 1] [LEAF]
    cd 16.11.2 → [Gels/Storaro Selection 11/storaro orange 2] [LEAF]
      ... (7 more leaves) ...
    cd 16.11.10 → [Gels/Storaro Selection 11/storaro magenta 10] [LEAF]
  cd 16.12 → [Gels/SuperGel 12] (136 entries, 11 nodes, depth 2) + 10 leaves
    cd 16.12.1 → [Gels/SuperGel 12/clear 1] [LEAF]
    cd 16.12.2 → [Gels/SuperGel 12/light bastard amber 2] [LEAF]
      ... (7 more leaves) ...
    cd 16.12.10 → [Gels/SuperGel 12/medium yellow 10] [LEAF]
  cd 16.13 → [Gels/Zircon 13] (12 entries, 11 nodes, depth 2) + 10 leaves
    cd 16.13.1 → [Gels/Zircon 13/zircon minus green 1 1] [LEAF]
    cd 16.13.2 → [Gels/Zircon 13/zircon minus green 2 2] [LEAF]
      ... (7 more leaves) ...
    cd 16.13.10 → [Gels/Zircon 13/zircon diffusion 1 10] [LEAF]
cd 17 → [Presets] [LEAF]
cd 18 → [Worlds] (1 entries, 2 nodes, depth 2) + 1 leaves
  cd 18.1 → [Worlds /Full 1] [LEAF]
cd 19 → [Filters] (1 entries, 2 nodes, depth 2) + 1 leaves
  cd 19.1 → [Filters /All 1] [LEAF]
cd 20 → [FadePaths 20] [LEAF]
cd 21 → [Programmer] [LEAF]
cd 22 → [Groups] [LEAF]
cd 23 → [Forms] (23 entries, 52 nodes, depth 4)
  cd 23.1 → [Forms/Stomp 1] (1 entries, 3 nodes, depth 3)
    cd 23.1.1 → [Forms/Stomp 1/Stomp 1] (1 entries, 2 nodes, depth 2) + 1 leaves
      cd 23.1.1.1 → [Forms/Stomp 1/Stomp 1/SubFormPoint 1] [LEAF]
  cd 23.2 → [Forms/Release 2] (1 entries, 1 nodes, depth 1)
  cd 23.3 → [Forms/Random 3] (1 entries, 1 nodes, depth 1)
  cd 23.4 → [Forms/Pwm 4] (1 entries, 1 nodes, depth 1)
  cd 23.5 → [Forms/Chase 5] (1 entries, 1 nodes, depth 1)
  cd 23.6 → [Forms/Flat Low 6] (1 entries, 1 nodes, depth 1)
  cd 23.7 → [Forms/Flat High 7] (1 entries, 1 nodes, depth 1)
  cd 23.8 → [Forms/Sin 8] (1 entries, 1 nodes, depth 1)
  cd 23.9 → [Forms/Cos 9] (1 entries, 1 nodes, depth 1)
  cd 23.10 → [Forms/Ramp Plus 10] (1 entries, 1 nodes, depth 1)
  cd 23.11 → [Forms/Ramp Minus 11] (1 entries, 1 nodes, depth 1)
  cd 23.12 → [Forms/Ramp 12] (1 entries, 1 nodes, depth 1)
  cd 23.13 → [Forms/Phase 1 13] (1 entries, 1 nodes, depth 1)
  cd 23.14 → [Forms/Phase 2 14] (1 entries, 1 nodes, depth 1)
  cd 23.15 → [Forms/Phase 3 15] (1 entries, 1 nodes, depth 1)
  cd 23.16 → [Forms/Bump 16] (1 entries, 1 nodes, depth 1)
  cd 23.17 → [Forms/Swing 17] (1 entries, 1 nodes, depth 1)
  cd 23.18 → [Forms/Ramp 50 18] (1 entries, 1 nodes, depth 1)
  cd 23.19 → [Forms/Circle 19] (2 entries, 19 nodes, depth 3)
    cd 23.19.1 → [Forms/Circle 19/Circle 19.1] (8 entries, 9 nodes, depth 2) + 8 leaves
      cd 23.19.1.1 → [Forms/Circle 19/Circle 19.1/SubFormPoint 1] [LEAF]
      cd 23.19.1.2 → [Forms/Circle 19/Circle 19.1/SubFormPoint 2] [LEAF]
        ... (5 more leaves) ...
      cd 23.19.1.8 → [Forms/Circle 19/Circle 19.1/SubFormPoint 8] [LEAF]
    cd 23.19.2 → [Forms/Circle 19/Circle 19.2] (8 entries, 9 nodes, depth 2) + 8 leaves
      cd 23.19.2.1 → [Forms/Circle 19/Circle 19.2/SubFormPoint 1] [LEAF]
      cd 23.19.2.2 → [Forms/Circle 19/Circle 19.2/SubFormPoint 2] [LEAF]
        ... (5 more leaves) ...
      cd 23.19.2.8 → [Forms/Circle 19/Circle 19.2/SubFormPoint 8] [LEAF]
  cd 23.20 → [Forms/Sound 20] (11 entries, 1 nodes, depth 1)
  cd 23.21 → [Forms/Flyout 21] (2 entries, 9 nodes, depth 3)
    cd 23.21.1 → [Forms/Flyout 21/dimmer 21.1] (4 entries, 5 nodes, depth 2) + 4 leaves
      cd 23.21.1.1 → [Forms/Flyout 21/dimmer 21.1/SubFormPoint 1] [LEAF]
      cd 23.21.1.2 → [Forms/Flyout 21/dimmer 21.1/SubFormPoint 2] [LEAF]
      cd 23.21.1.3 → [Forms/Flyout 21/dimmer 21.1/SubFormPoint 3] [LEAF]
      cd 23.21.1.4 → [Forms/Flyout 21/dimmer 21.1/SubFormPoint 4] [LEAF]
    cd 23.21.2 → [Forms/Flyout 21/Position 21.2] (2 entries, 3 nodes, depth 2) + 2 leaves
      cd 23.21.2.1 → [Forms/Flyout 21/Position 21.2/SubFormPoint 1] [LEAF]
      cd 23.21.2.2 → [Forms/Flyout 21/Position 21.2/SubFormPoint 2] [LEAF]
  cd 23.22 → [Forms/Wave 22] (2 entries, 1 nodes, depth 1)
  cd 23.23 → [Forms/Cross 23] (2 entries, 1 nodes, depth 1)
cd 24 → [Effects] [LEAF]
cd 25 → [Sequences] [LEAF]
cd 26 → [Timers] (1 entries, 2 nodes, depth 2) + 1 leaves
  cd 26.1 → [Timers/Stopwatch 1] [LEAF]
cd 27 → [MasterSections] [LEAF]
cd 30 → [ExecutorPages] (2 entries, 16 nodes, depth 4) + 1 leaves
  cd 30.0 → [ExecutorPages/Temp 0] [LEAF]
  cd 30.1 → [ExecutorPages/Global 1] (42 entries, 14 nodes, depth 3) + 11 leaves
    cd 30.1.1 → [ExecutorPages/Global 1/Page 1] [LEAF]
    cd 30.1.2 → [ExecutorPages/Global 1/Page 2] (1 entries, 2 nodes, depth 2) + 1 leaves
      cd 30.1.2.2 → [ExecutorPages/Global 1/Page 2/WASH 2.2] [LEAF]
    cd 30.1.3 → [ExecutorPages/Global 1/Page 3] [LEAF]
    cd 30.1.4 → [ExecutorPages/Global 1/Page 4] [LEAF]
      ... (7 more leaves) ...
    cd 30.1.12 → [ExecutorPages/Global 1/Page 12] [LEAF]
cd 31 → [ChannelPages] (9 entries, 10 nodes, depth 2) + 9 leaves
  cd 31.1 → [ChannelPages /Page 1] [LEAF]
  cd 31.2 → [ChannelPages /Page 2] [LEAF]
    ... (6 more leaves) ...
  cd 31.9 → [ChannelPages /Page 9] [LEAF]
cd 33 → [Songs] [LEAF]
cd 34 → [Agendas] [LEAF]
cd 35 → [Timecodes] [LEAF]
cd 36 → [RemoteTypes] (3 entries, 4 nodes, depth 2) + 3 leaves
  cd 36.1 → [RemoteTypes/AnalogRemotes 1] [LEAF]
  cd 36.2 → [RemoteTypes/MidiRemotes 2] [LEAF]
  cd 36.3 → [RemoteTypes/DMXRemotes 3] [LEAF]
cd 37 → [DMXSnapshotPool] [LEAF]
cd 38 → [Layouts] (1 entries, 13 nodes, depth 5)
  cd 38.1 → [Layouts/Global] (9 entries, 12 nodes, depth 4)
    cd 38.1.1 → [Layouts/Global /LASER 1] (1 entries, 4 nodes, depth 3)
      cd 38.1.1.1 → [Layouts/Global /LASER 1/LayoutData 1] (2 entries, 3 nodes, depth 2) + 2 leaves
        cd 38.1.1.1.1 → [Layouts/Global /LASER 1/LayoutData 1/LayoutElementDefaults 1] [LEAF]
        cd 38.1.1.1.2 → [Layouts/Global /LASER 1/LayoutData 1/LayoutElementDefaults 2] [LEAF]
    cd 38.1.2 → [Layouts/Global /WASH 2] (1 entries, 1 nodes, depth 1) [DUP of cd 38.1.1]
    cd 38.1.3 → [Layouts/Global /BIG BAR 3] (1 entries, 1 nodes, depth 1) [DUP of cd 38.1.1]
    cd 38.1.4 → [Layouts/Global /small bar 4] (1 entries, 1 nodes, depth 1) [DUP of cd 38.1.1]
    cd 38.1.5 → [Layouts/Global /RPointe1 5] (1 entries, 1 nodes, depth 1) [DUP of cd 38.1.1]
    cd 38.1.6 → [Layouts/Global /SharpySL 6] (1 entries, 1 nodes, depth 1) [DUP of cd 38.1.1]
    cd 38.1.8 → [Layouts/Global /WL 1..9 8] (1 entries, 1 nodes, depth 1) [DUP of cd 38.1.1]
    cd 38.1.9 → [Layouts/Global /Layout 9] (1 entries, 1 nodes, depth 1) [DUP of cd 38.1.1]
cd 39 → [UserProfiles] (254 entries, 7345 nodes, depth 5)
  cd 39.1 → [UserProfiles/Default 1] (22 entries, 109 nodes, depth 4) + 15 leaves
    cd 39.1.1 → [UserProfiles/Default 1/UserSettings 1] (20 entries, 23 nodes, depth 3) + 10 leaves
      cd 39.1.1.1 → [UserProfiles/Default 1/UserSettings 1/SheetSettings 1] (3 entries, 4 nodes, depth 2) + 3 leaves
        cd 39.1.1.1.1 → [UserProfiles/Default 1/UserSettings 1/SheetSettings 1/Tools 1] [LEAF]
        cd 39.1.1.1.2 → [UserProfiles/Default 1/UserSettings 1/SheetSettings 1/LayerMask 2] [LEAF]
        cd 39.1.1.1.3 → [UserProfiles/Default 1/UserSettings 1/SheetSettings 1/Display 3] [LEAF]
      cd 39.1.1.2 → [UserProfiles/Default 1/UserSettings 1/SheetSettings 2] (3 entries, 4 nodes, depth 2) + 3 leaves
        cd 39.1.1.2.1 → [UserProfiles/Default 1/UserSettings 1/SheetSettings 2/Tools 1] [LEAF]
        cd 39.1.1.2.2 → [UserProfiles/Default 1/UserSettings 1/SheetSettings 2/LayerMask 2] [LEAF]
        cd 39.1.1.2.3 → [UserProfiles/Default 1/UserSettings 1/SheetSettings 2/Display 3] [LEAF]
      cd 39.1.1.3 → [UserProfiles/Default 1/UserSettings 1/SheetSettings 3] (3 entries, 1 nodes, depth 1) [DUP of cd 39.1.1.1]
      cd 39.1.1.4 → [UserProfiles/Default 1/UserSettings 1/SheetSettings 4] (3 entries, 1 nodes, depth 1) [DUP of cd 39.1.1.1]
      cd 39.1.1.5 → [UserProfiles/Default 1/UserSettings 1/SheetSettings 5] (3 entries, 1 nodes, depth 1) [DUP of cd 39.1.1.2]
      cd 39.1.1.6 → [UserProfiles/Default 1/UserSettings 1/SheetSettings 6] (3 entries, 1 nodes, depth 1) [DUP of cd 39.1.1.1]
      cd 39.1.1.7 → [UserProfiles/Default 1/UserSettings 1/PresetColors 7] [LEAF]
      cd 39.1.1.8 → [UserProfiles/Default 1/UserSettings 1/Oops 8] [LEAF]
        ... (7 more leaves) ...
      cd 39.1.1.16 → [UserProfiles/Default 1/UserSettings 1/ConsoleDialogSettings 16] [LEAF]
    cd 39.1.2 → [UserProfiles/Default 1/Selection 2] [LEAF]
    cd 39.1.3 → [UserProfiles/Default 1/BlindProgrammer] [LEAF]
    cd 39.1.4 → [UserProfiles/Default 1/BlindSelection 4] [LEAF]
    cd 39.1.5 → [UserProfiles/Default 1/Displays] (8 entries, 9 nodes, depth 2) + 8 leaves
      cd 39.1.5.1 → [UserProfiles/Default 1/Displays /Display 1 1] [LEAF]
      cd 39.1.5.2 → [UserProfiles/Default 1/Displays /Display 2 2] [LEAF]
        ... (5 more leaves) ...
      cd 39.1.5.8 → [UserProfiles/Default 1/Displays /Display 8 8] [LEAF]
    cd 39.1.6 → [UserProfiles/Default 1/Views] (17 entries, 11 nodes, depth 2) + 10 leaves
      cd 39.1.6.1 → [UserProfiles/Default 1/Views /clear 1] [LEAF]
      cd 39.1.6.2 → [UserProfiles/Default 1/Views /GROUP 2] [LEAF]
        ... (7 more leaves) ...
      cd 39.1.6.10 → [UserProfiles/Default 1/Views /Fixtures 10] [LEAF]
    cd 39.1.7 → [UserProfiles/Default 1/MainViews] [LEAF]
    cd 39.1.8 → [UserProfiles/Default 1/StoreDefaults 8] (6 entries, 7 nodes, depth 2) + 5 leaves
      cd 39.1.8.1 → [UserProfiles/Default 1/StoreDefaults 8/GeneralDefaults 1] [LEAF]
      cd 39.1.8.2 → [UserProfiles/Default 1/StoreDefaults 8/CuelistDefaults 2] [LEAF]
      cd 39.1.8.3 → [UserProfiles/Default 1/StoreDefaults 8/PresetDefaults 3] [LEAF]
      cd 39.1.8.4 → [UserProfiles/Default 1/StoreDefaults 8/EffectDefaults 4] [LEAF]
      cd 39.1.8.5 → [UserProfiles/Default 1/StoreDefaults 8/ExecDefaults 5] [LEAF]
      cd 39.1.8.6 → [UserProfiles/Default 1/StoreDefaults 8/LayoutDefaults 6] (2 entries, 1 nodes, depth 1) [DUP of cd 38.1.1.1]
    cd 39.1.9 → [UserProfiles/Default 1/MatrixPool] (2 entries, 3 nodes, depth 2) + 2 leaves
      cd 39.1.9.1 → [UserProfiles/Default 1/MatrixPool /Reset 1] [LEAF]
      cd 39.1.9.2 → [UserProfiles/Default 1/MatrixPool /MAtricks 2] [LEAF]
    cd 39.1.10 → [UserProfiles/Default 1/ViewButtons 10] (11 entries, 15 nodes, depth 3) + 10 leaves
      cd 39.1.10.1 → [UserProfiles/Default 1/ViewButtons 10/ViewButtonPage 1] (4 entries, 4 nodes, depth 2) + 3 leaves
        cd 39.1.10.1.5 → [UserProfiles/Default 1/ViewButtons 10/ViewButtonPage 1/DMX 1.5] [LEAF]
        cd 39.1.10.1.6 → [UserProfiles/Default 1/ViewButtons 10/ViewButtonPage 1/PRESETS 1.6] [LEAF]
        cd 39.1.10.1.7 → [UserProfiles/Default 1/ViewButtons 10/ViewButtonPage 1/SequFX 1.7] [LEAF]
      cd 39.1.10.2 → [UserProfiles/Default 1/ViewButtons 10/ViewButtonPage 2] [LEAF]
      cd 39.1.10.3 → [UserProfiles/Default 1/ViewButtons 10/ViewButtonPage 3] [LEAF]
        ... (7 more leaves) ...
      cd 39.1.10.11 → [UserProfiles/Default 1/ViewButtons 10/ViewButtonPage 11] [LEAF]
    cd 39.1.11 → [UserProfiles/Default 1/ExecFix 11] [LEAF]
    cd 39.1.12 → [UserProfiles/Default 1/EncoderResolution 12] [LEAF]
    cd 39.1.13 → [UserProfiles/Default 1/Arrangements 13] (3 entries, 4 nodes, depth 2) + 3 leaves
      cd 39.1.13.1 → [UserProfiles/Default 1/Arrangements 13/Move 1] [LEAF]
      cd 39.1.13.2 → [UserProfiles/Default 1/Arrangements 13/Circle 2] [LEAF]
      cd 39.1.13.3 → [UserProfiles/Default 1/Arrangements 13/Matrix2D 3] [LEAF]
    cd 39.1.14 → [UserProfiles/Default 1/LayerMask 14] [LEAF]
    cd 39.1.15 → [UserProfiles/Default 1/StoreSettings 15] (6 entries, 1 nodes, depth 1) [DUP of cd 39.1.8]
    cd 39.1.16 → [UserProfiles/Default 1/Cameras] (12 entries, 11 nodes, depth 2) + 10 leaves
      cd 39.1.16.1 → [UserProfiles/Default 1/Cameras /Front 1] [LEAF]
      cd 39.1.16.2 → [UserProfiles/Default 1/Cameras /Front/Left 2] [LEAF]
        ... (7 more leaves) ...
      cd 39.1.16.10 → [UserProfiles/Default 1/Cameras /Front View (2D) 10] [LEAF]
    cd 39.1.17 → [UserProfiles/Default 1/RenderingOptions 17] [LEAF]
    cd 39.1.18 → [UserProfiles/Default 1/EnviromentVariables 18] [LEAF]
    cd 39.1.19 → [UserProfiles/Default 1/RemoteViews] [LEAF]
    cd 39.1.20 → [UserProfiles/Default 1/RemoteDisplays] (1 entries, 2 nodes, depth 2) + 1 leaves
      cd 39.1.20.1 → [UserProfiles/Default 1/RemoteDisplays /Display 1 1] [LEAF]
    cd 39.1.21 → [UserProfiles/Default 1/RemoteMainViews] [LEAF]
    cd 39.1.22 → [UserProfiles/Default 1/PreviewProgrammer] [LEAF]
    cd 39.1.23 → [UserProfiles/Default 1/PreviewSelection 23] [LEAF]
    cd 39.1.24 → [UserProfiles/Default 1/MaskPool] (6 entries, 7 nodes, depth 2) + 6 leaves
      cd 39.1.24.1 → [UserProfiles/Default 1/MaskPool /None 1] [LEAF]
      cd 39.1.24.2 → [UserProfiles/Default 1/MaskPool /Prog Only 2] [LEAF]
        ... (3 more leaves) ...
      cd 39.1.24.6 → [UserProfiles/Default 1/MaskPool /Seq- 6] [LEAF]
    cd 39.1.25 → [UserProfiles/Default 1/ColumnWidths 25] [LEAF]
    cd 39.1.26 → [UserProfiles/Default 1/Views] [LEAF]

  ... 134 more UserProfiles with similar structure ...

  | # | cd path | Name | Nodes | Depth |
  |---|---------|------|-------|-------|
  | 2 | cd 39.2 | Romar-J 2 | 89 | 3 |
  | 3 | cd 39.3 | CC_19-TORONTO_Start 3 | 131 | 4 |
  | 4 | cd 39.4 | CC_19-TORONTO_santi 4 | 76 | 4 |
  | 5 | cd 39.5 | Hannah 5 | 53 | 3 |
  | 6 | cd 39.6 | Fran 6 | 66 | 4 |
  | 7 | cd 39.7 | old 7 | 108 | 4 |
  | 8 | cd 39.8 | JULES_main 8 | 107 | 4 |
  | 9 | cd 39.9 | chris 9 | 45 | 3 |
  | 10 | cd 39.10 | chris clone 10 | 83 | 4 |
  | 11 | cd 39.11 | Video 11 | 72 | 4 |
  | 12 | cd 39.12 | user1 12 | 91 | 4 |
  | 13 | cd 39.13 | user2 13 | 119 | 4 |
  | 14 | cd 39.14 | wing 14 | 103 | 4 |
  | 15 | cd 39.15 | Demo 15 | 116 | 4 |
  | 16 | cd 39.16 | bRITT gEE 16 | 1 | 1 | (DUP of cd 39.9)
  | 17 | cd 39.17 | fIGURING USER PROFILE 17 | 1 | 1 | (DUP of cd 39.9)
  | 18 | cd 39.18 | RJ 18 | 106 | 4 |
  | 19 | cd 39.19 | rjbu 19 | 99 | 4 |
  | 20 | cd 39.20 | RJJ 20 | 73 | 4 |
  | 21 | cd 39.21 | Gabian 21 | 62 | 3 |
  | 22 | cd 39.22 | Stefan 22 | 65 | 3 |
  | 23 | cd 39.23 | REMOTE 23 | 109 | 3 |
  | 24 | cd 39.24 | SERGEKEY 24 | 75 | 3 |
  | 25 | cd 39.25 | JEFF 25 | 74 | 4 |
  | 26 | cd 39.26 | JEFF 2 26 | 1 | 1 | (DUP of cd 39.23)
  | 27 | cd 39.27 | nitemind 27 | 92 | 3 |
  | 28 | cd 39.28 | Erik 28 | 120 | 4 |
  | 29 | cd 39.29 | james 29 | 49 | 3 |
  | 30 | cd 39.30 | Curtis RAWF 30 | 89 | 4 |
  | 31 | cd 39.31 | Aurora 31 | 80 | 4 |
  | 32 | cd 39.32 | Eric 32 | 65 | 3 |
  | 33 | cd 39.33 | AndreiR 33 | 108 | 4 |
  | 34 | cd 39.34 | One 34 | 81 | 3 |
  | 35 | cd 39.35 | Two 35 | 1 | 1 | (DUP of cd 39.29)
  | 36 | cd 39.36 | Three 36 | 61 | 3 |
  | 37 | cd 39.37 | Four 37 | 55 | 3 |
  | 38 | cd 39.38 | Five 38 | 61 | 3 |
  | 39 | cd 39.39 | Six 39 | 66 | 3 |
  | 40 | cd 39.40 | Caleb-San 40 | 87 | 4 |
  | 41 | cd 39.41 | Alfonso 41 | 52 | 3 |
  | 42 | cd 39.42 | Administrator 42 | 114 | 3 |
  | 43 | cd 39.43 | SCOOMPS 43 | 125 | 4 |
  | 44 | cd 39.44 | Lorcan 44 | 31 | 3 |
  | 45 | cd 39.45 | Marlow 45 | 79 | 3 |
  | 46 | cd 39.46 | Test 46 | 47 | 3 |
  | 47 | cd 39.47 | AVXAV 47 | 56 | 3 |
  | 48 | cd 39.48 | REUX 48 | 81 | 3 |
  | 49 | cd 39.49 | BLC GUEST 49 | 77 | 3 |
  | 50 | cd 39.50 | JustinSchaefer 50 | 99 | 4 |
  | 51 | cd 39.51 | Pablo 51 | 65 | 3 |
  | 52 | cd 39.52 | Pablo 2 52 | 55 | 3 |
  | 53 | cd 39.53 | CW 53 | 1 | 1 | (DUP of cd 39.46)
  | 54 | cd 39.54 | JW 54 | 81 | 3 |
  | 55 | cd 39.55 | RPU 55 | 59 | 3 |
  | 56 | cd 39.56 | MM 56 | 1 | 1 | (DUP of cd 39.9)
  | 57 | cd 39.57 | DH 57 | 1 | 1 | (DUP of cd 39.9)
  | 58 | cd 39.58 | Kian 58 | 1 | 1 | (DUP of cd 39.9)
  | 59 | cd 39.59 | PixMob Video Training 59 | 84 | 4 |
  | 60 | cd 39.60 | HERK 60 | 98 | 3 |
  | 61 | cd 39.61 | HERK BACKUP 61 | 67 | 3 |
  | 62 | cd 39.62 | Bobroy 1 62 | 93 | 3 |
  | 63 | cd 39.63 | Bobroy1 63 | 1 | 1 | (DUP of cd 39.9)
  | 64 | cd 39.64 | lieberman 64 | 44 | 3 |
  | 65 | cd 39.65 | DiersonLighting#2 65 | 96 | 4 |
  | 66 | cd 39.66 | RASTA LIGHTING 66 | 93 | 4 |
  | 67 | cd 39.67 | GHOST 67 | 75 | 3 |
  | 68 | cd 39.68 | BONES 68 | 1 | 1 | (DUP of cd 39.67)
  | 69 | cd 39.69 | JULIEN 69 | 84 | 4 |
  | 70 | cd 39.70 | slave 70 | 96 | 4 |
  | 71 | cd 39.71 | backup 71 | 82 | 4 |
  | 72 | cd 39.72 | Nordstern PreShow 72 | 53 | 3 |
  | 73 | cd 39.73 | rfu 73 | 27 | 2 |
  | 74 | cd 39.74 | light 74 | 75 | 4 |
  | 75 | cd 39.75 | ultralight 75 | 1 | 1 | (DUP of cd 39.74)
  | 76 | cd 39.76 | Maja 76 | 37 | 3 |
  | 77 | cd 39.77 | Dieter B 2LT 77 | 93 | 4 |
  | 78 | cd 39.78 | Dieter B 2F 78 | 95 | 4 |
  | 79 | cd 39.79 | Meister 79 | 55 | 3 |
  | 80 | cd 39.80 | MeisterRemote 80 | 60 | 3 |
  | 81 | cd 39.81 | bene 81 | 71 | 3 |
  | 82 | cd 39.82 | cc 82 | 27 | 2 |
  | 83 | cd 39.83 | ulight 83 | 1 | 1 | (DUP of cd 39.81)
  | 84 | cd 39.84 | guest 84 | 65 | 3 |
  | 85 | cd 39.85 | alexander 85 | 45 | 3 |
  | 86 | cd 39.86 | rouven 86 | 1 | 1 | (DUP of cd 39.85)
  | 87 | cd 39.87 | carsten 87 | 1 | 1 | (DUP of cd 39.85)
  | 88 | cd 39.88 | udo 88 | 1 | 1 | (DUP of cd 39.85)
  | 89 | cd 39.89 | jerome 89 | 1 | 1 | (DUP of cd 39.85)
  | 90 | cd 39.90 | bel 90 | 1 | 1 | (DUP of cd 39.85)
  | 91 | cd 39.91 | fullsize 91 | 1 | 1 | (DUP of cd 39.79)
  | 92 | cd 39.92 | Fred 92 | 69 | 3 |
  | 93 | cd 39.93 | leer 93 | 1 | 1 | (DUP of cd 39.82)
  | 94 | cd 39.94 | Steve Marr 94 | 36 | 3 |
  | 95 | cd 39.95 | Pixies 95 | 37 | 3 |
  | 96 | cd 39.96 | First 96 | 1 | 1 | (DUP of cd 39.82)
  | 97 | cd 39.97 | Second 97 | 1 | 1 | (DUP of cd 39.82)
  | 98 | cd 39.98 | jlo 98 | 1 | 1 | (DUP of cd 39.82)
  | 99 | cd 39.99 | Hello 99 | 1 | 1 | (DUP of cd 39.82)
  | 100 | cd 39.100 | user 1 100 | 135 | 4 |
  | 101 | cd 39.101 | user 2 101 | 1 | 1 | (DUP of cd 39.82)
  | 102 | cd 39.102 | user 3 102 | 1 | 1 | (DUP of cd 39.82)
  | 103 | cd 39.103 | Andreas 103 | 1 | 1 | (DUP of cd 39.82)
  | 104 | cd 39.104 | Marianne 104 | 1 | 1 | (DUP of cd 39.82)
  | 105 | cd 39.105 | mupp 105 | 74 | 3 |
  | 106 | cd 39.106 | sJ 106 | 61 | 3 |
  | 107 | cd 39.107 | BASE 107 | 65 | 3 |
  | 108 | cd 39.108 | Telnet 108 | 27 | 2 |
  | 109 | cd 39.109 | REMOTE1 109 | 27 | 2 |
  | 110 | cd 39.110 | DYNAM 110 | 90 | 4 |
  | 111 | cd 39.111 | Frank UP 111 | 52 | 3 |
  | 112 | cd 39.112 | remote2 112 | 1 | 1 | (DUP of cd 39.80)
  | 113 | cd 39.113 | Default#2 113 | 88 | 3 |
  | 114 | cd 39.114 | right 114 | 1 | 1 | (DUP of cd 39.73)
  | 115 | cd 39.115 | bojanr 115 | 89 | 3 |
  | 116 | cd 39.116 | peter 116 | 65 | 3 |
  | 117 | cd 39.117 | bojanl 117 | 52 | 4 |
  | 118 | cd 39.118 | rudi 118 | 51 | 3 |
  | 119 | cd 39.119 | borut 119 | 91 | 4 |
  | 120 | cd 39.120 | matej 120 | 68 | 4 |
  | 121 | cd 39.121 | Simon 121 | 55 | 3 |
  | 122 | cd 39.122 | Testno 122 | 38 | 3 |
  | 123 | cd 39.123 | bine 123 | 45 | 3 |
  | 124 | cd 39.124 | andrej 124 | 45 | 3 |
  | 125 | cd 39.125 | Andrius 125 | 45 | 3 |
  | 126 | cd 39.126 | Aggih - Profiles 126 | 90 | 4 |
  | 127 | cd 39.127 | halli 127 | 1 | 1 | (DUP of cd 39.73)
  | 128 | cd 39.128 | Montazas 128 | 27 | 2 |
  | 129 | cd 39.129 | Andrius Stasiulis 129 | 1 | 1 | (DUP of cd 39.128)
  | 130 | cd 39.130 | pila 130 | 1 | 1 | (DUP of cd 39.9)
  | 131 | cd 39.131 | mis 131 | 37 | 3 |
  | 132 | cd 39.132 | mis1 132 | 1 | 1 | (DUP of cd 39.128)
  | 133 | cd 39.133 | hamdi 133 | 37 | 3 |
  | 134 | cd 39.134 | Alex 134 | 1 | 1 | (DUP of cd 39.9)
  | 135 | cd 39.135 | FLORENT 135 | 33 | 3 |
cd 40 → [Users] (3 entries, 3 nodes, depth 2) + 2 leaves
  cd 40.1 → [Users/administrator 1] [LEAF]
  cd 40.3 → [Users/guest 2] [LEAF]
cd 41 → [PixelMapperContainer 41] (3 entries, 6 nodes, depth 2) + 5 leaves
  cd 41.1 → [PixelMapperContainer 41/PixelMapperPanelTypeCollect 1] [LEAF]
  cd 41.2 → [PixelMapperContainer 41/PixelMapperAreaCollect 2] [LEAF]
  cd 41.3 → [PixelMapperContainer 41/VideoData 3] [LEAF]
  cd 41.4 → [PixelMapperContainer 41/VideoWarper 4] [LEAF]
  cd 41.5 → [PixelMapperContainer 41/VideoCompositionContainer 5] [LEAF]
cd 42 → [NDP_Root 42] [LEAF]
```

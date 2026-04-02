---
title: Functional Domains, Hardkeys, and Executor Priorities
description: MA2 keyword domains, multi-press key chains, and executor priority constants
version: 1.1.0
created: 2026-03-29T21:44:45Z
last_updated: 2026-03-30T11:23:42Z
---

# Functional Domains, Hardkeys, and Executor Priorities

> Loaded on-demand when working on vocabulary routing, key constants, or executor assignment.

---

## Functional Domains (vocab.py)

`src/vocab.py` exposes `FunctionalDomain` StrEnum (10 values) and `KEYWORD_DOMAINS` dict (198 entries).

| Domain | Keywords (count) | Examples |
|--------|-----------------|---------|
| `object_manipulation` | 21 | Assign, Label, Appearance, Store, Copy, Delete |
| `playback_control` | 26 | Go, GoBack, Goto, Flash, Kill, Release, Freeze |
| `selection_filtering` | 28 | Select, Clear, If, Park, Highlight, Blind, SelFix |
| `timing_effects` | 37 | Fade, Speed, Rate, Crossfade, EffectBPM, EffectPhase |
| `network_session` | 20 | JoinSession, TakeControl, SetIP, Telnet, RemoteCommand |
| `system_admin` | 25 | Shutdown, SaveShow, NewShow, UpdateFirmware, Blackout |
| `data_query` | 18 | List, Info, Help, Search, ListVar, PSR |
| `variables_scripting` | 7 | SetVar, AddVar, SetUserVar, Call, Macro, Plugin |
| `matricks` | 8 | MAtricks, MAtricksInterleave, MAtricksBlocks, Interleave |
| `rdm` | 8 | RdmAutomatch, RdmAutopatch, RdmSetpatch, RdmUnmatch |

Also: `CD_KEYWORD_DESTINATIONS` (36 entries), `DEFAULT_KEYWORD_STATES` (10 entries).

---

## Hardkey Chains (physical key multi-press behavior)

Defined in `src/commands/constants.py` as `HARDKEY_CHAINS` (12 chains) and `MA_KEY_COMBOS` (29 combos).

### Multi-press key chains

| Physical Key | 1× | 2× | 3× | Hold/Other |
|---|---|---|---|---|
| **Assign** | `Assign` | `Label` | `Appearance` | — |
| **At** | `At` | `Normal` | — | hold → `Filter` |
| **Help** | `Help` | `CmdHelp` | — | — |
| **Fixture** | `Fixture` | `Selection` | — | — |
| **Full** | `Full` | `FullHighlight` | — | — |
| **Macro** | `Macro` | `Timecode` | `Agenda` | — |
| **Effect** | `Effect` | `Form` | — | — |
| **Blind** | `Blind` | — | — | hold 2s → `BlindEdit` |
| **Backup** | `Backup` | `QuickSave` | — | — |
| **Group** | `Group` | — | — | hold → GroupMasterView |
| **If** | `If` (helping) | — | — | 4× → `If` (function) |
| **Please** | Execute | Activate All | Deactivate All | 4× → Knock In |

### Key MA+key combinations (selected)

| Combo | Keyword | | Combo | Keyword |
|---|---|---|---|---|
| MA+Copy | `Export` | | MA+Move | `Import` |
| MA+Store | `StoreLook` | | MA+Off | `Kill` |
| MA+Clear | `ClearAll` | | MA+Edit | `BlindEdit` |
| MA+Fix | `SelFix` | | MA+Next | `NextRow` |
| MA+Go+ | `DefGoForward` | | MA+Go- | `DefGoBack` |
| MA+Oops | `ListOops` | | MA+B.O. | `BlackScreen` |
| MA+Full | `ToFull` | | MA+Down | `ToZero` |
| MA+Thru | `AllRows` | | MA+Align | `ShuffleSelection` |

---

## Executor Priority System

Defined in `src/commands/constants.py`.

### Priority levels (highest → lowest)

| Rank | Name | cmd_value | Behavior |
|---|---|---|---|
| 1 | Super | `super` | LTP above ALL playbacks + programmer. Only Freeze overrides. |
| 2 | Swap | `swap` | LTP > HTP; negative override possible. |
| 3 | HTP | `htp` | Highest intensity value wins. CAUTION: changes ALL attribute priority. |
| 4 | High | `high` | High LTP. Overrides Normal/Low. |
| 5 | Normal | `normal` | LTP default. Last triggered value wins. |
| 6 | Low | `low` | Lowest priority. Overridden by everything else. |

Syntax: `Assign Executor [ID] /priority=[cmd_value]`

### Executor assign option categories

| Category | Options |
|---|---|
| Start | autostomp, autostart, autostop, autofix, restart |
| Protect | ooo, swopprotect, killprotect |
| MIB | mibalways, mibnever, prepos |
| Function | chaser, softltp, wrap, crossfade |
| Timing | triggerisgo, cmddisable, effectspeed, autogo |
| Speed | speed, speedmaster, ratemaster |

Use `EXECUTOR_ASSIGN_OPTION_NAMES` frozenset for validation. Use `EXECUTOR_PRIORITY_VALUES` frozenset for priority validation.

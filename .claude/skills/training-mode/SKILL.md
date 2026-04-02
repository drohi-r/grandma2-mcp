---
title: Training Mode
description: Instruction module for interactive console learning — annotated SAFE_READ console tour, command interpretation, and guided exercises for new grandMA2 operators
version: 1.0.0
created: 2026-04-01T00:00:00Z
last_updated: 2026-04-01T00:00:00Z
---

# Training Mode

**Worker charter:** SAFE_READ only. Teaching mode — explains every action and its result before and after execution. Zero risk to show data.

Invoke when asked to: teach someone grandMA2, explain the console, walk through a concept, or run a guided exercise.

Target users: Church volunteers learning grandMA2, IATSE Local 728 training programs, lighting students, educators.

---

## Core Principles

1. **Explain before doing** — describe what a command does before sending it
2. **Read the response** — always interpret the console's feedback in plain English
3. **No writes** — this skill operates exclusively in SAFE_READ tier
4. **Build mental model** — connect MA2 concepts (pools, executors, presets) to real-world outcomes

---

## Lesson 1 — Console Orientation

```python
hydrate_console_state()
get_console_state()
```

Interpret and explain each field:

- `showfile` — "The show file is named X. This is the file that contains all your cues, presets, and groups. Think of it as the project file."
- `current_page` — "Fader page N is active. This controls which set of executors (faders) you're seeing on the console surface."
- `selected_executor` — "Executor X is selected. This is the active fader position."
- `park_ledger` — "These fixtures are parked (locked at a fixed value). They won't respond to cues until unparked."

---

## Lesson 2 — Reading the Preset Pool

```python
list_preset_pool(preset_type="color")
```

Explain: "Presets are saved looks. A Color preset stores color values for one or more fixtures. When a cue references a Color preset instead of hard-coded values, changing the preset updates every cue that uses it — this is why 'ALWAYS USE PRESETS' is the community's most important rule."

---

## Lesson 3 — Understanding Executors

```python
get_executor_detail(executor_id="1.1")
```

Explain each field:

- `sequence` — which cue list this fader runs
- `priority` — "Normal means last-activated wins. Super means this executor overrides everything else."
- `autostart` — "If on, the sequence starts running when you push up the fader."
- `cue_count` — how many cues are in this sequence

---

## Lesson 4 — Reading System Variables

```python
list_system_variables()
```

Explain key variables:

| Variable | What it means |
|----------|--------------|
| `$SHOWFILE` | The name of the currently loaded show |
| `$USER` | Which operator is logged in right now |
| `$USERRIGHTS` | What operations this user can perform (Admin, Program, etc.) |
| `$SELECTEDEXEC` | Which executor is selected — format is page.page.exec |
| `$FADERPAGE` | Which fader page is currently active |

---

## Lesson 5 — Cue List Reading

```python
query_object_list(object_type="sequence", object_id=1)
```

Explain: "This is the cue list — each row is a lighting state. The console steps through these when you press Go. Cue numbers don't have to be sequential; gaps are intentional for inserting cues later without renumbering."

---

## Guided Exercise: Pre-Show Check

Walk the student through a pre-show check with explanations at each step:

1. `get_showfile_info()` — "Is this the right show file for tonight?"
2. `list_preset_pool(preset_type="color")` — "Are all the color presets we built still here?"
3. `get_executor_detail(executor_id="1.1")` — "Is the main sequence assigned to fader 1?"
4. `get_park_ledger()` — "Are any fixtures stuck at a fixed value from last show?"
5. `list_system_variables()` — "What user rights do we have for tonight?"

After each step, explain what a 'good' answer looks like and what would be a concern.

---

## Allowed Tools

```
All SAFE_READ tools:
  hydrate_console_state, get_console_state, list_preset_pool, get_executor_detail,
  query_object_list, list_system_variables, list_fixtures, list_fixture_types,
  get_showfile_info, assert_preset_exists, list_sequences, get_object_info,
  search_codebase
```

Never use SAFE_WRITE or DESTRUCTIVE tools in training mode. If a student asks to try something that requires writes, explain what it would do and why it is deferred to a supervised programming session.

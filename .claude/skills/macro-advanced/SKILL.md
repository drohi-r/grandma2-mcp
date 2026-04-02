---
title: Advanced Macro Programming
description: Instruction module for advanced grandMA2 macro techniques — SetVar/GetVar scripting, conditional expressions, CmdDelay, popup macros, and jump target management
version: 1.0.0
created: 2026-03-31T21:00:00Z
last_updated: 2026-03-31T21:00:00Z
---

# Advanced Macro Programming

**Charter:** DESTRUCTIVE — creates and edits multi-line grandMA2 macros with variables,
conditionals, delays, and subroutine jumps. Errors in macro logic can fire unintended
console commands.

Invoke when asked to: write a multi-step macro, add a variable to a macro, use conditional
logic in a macro, build a popup confirmation macro, create a delay loop, or use SetVar/GetVar
to pass state between macros.

---

## Core Concept: Macro Line Execution

A macro is an ordered list of command lines executed sequentially. Each line can contain:
- A single MA2 command string
- A `CmdDelay` value (wait N seconds before next line)
- A `Go Macro` jump (branch to another line)
- A `SetVar` / `GetVar` / `SetUserVar` operation
- A `Call Macro` (subroutine call)
- A `Popup` command for on-screen confirmation

---

## Part 1 — Variables

### System variables (read-only)

Available via `$VARNAME` — expanded before command execution.

```
ListVar            # print all current variables
Echo "$USER"       # WARNING: Echo expands before executing → UNKNOWN COMMAND
                   # Use ListVar to read values, never Echo $VAR
```

Use `get_variable(action="echo", var_name="VARNAME")` MCP tool — calls `ListVar` internally.

### User variables (read/write in macros)

```
SetUserVar $mycount 0           # create/set user variable
SetUserVar $mycount + 1         # increment by 1
SetUserVar $mycolor "red"       # string value
```

Read in a later line: `attribute "ColorRgb1" at $mycount`

### Show variables (persist in show file)

```
SetVar $showphase 1             # stored in show, survives restart
```

### Variable scope

| Variable type | Prefix | Survives show close? |
|--------------|--------|---------------------|
| User variable | `$name` (SetUserVar) | No (session only) |
| Show variable | `$name` (SetVar) | Yes (in show file) |
| System variable | `$UPPERCASE` | Read-only, always present |

---

## Part 2 — Conditional Logic

MA2 macros use `If` as a conditional gate with a filter expression.

### Conditional jump pattern

```
Line 1: SetUserVar $step 0
Line 2: SetUserVar $step + 1
Line 3: If $step < 3
Line 4: Go Macro 1."MyMacro".2     # jump back to line 2 if condition true
Line 5: ClearAll                   # only reached when $step >= 3
```

### Comparison operators

| Operator | Meaning |
|----------|---------|
| `<` | Less than |
| `>` | Greater than |
| `=` | Equal |
| `!=` | Not equal |
| `<=` | Less than or equal |
| `>=` | Greater than or equal |

### If with system variable

```
If $SELECTEDFIXTURESCOUNT > 0
Go Macro 1."FixtureMacro".3        # jump only if fixtures are selected
```

---

## Part 3 — CmdDelay

`CmdDelay` pauses execution for N seconds before the next line runs.

```
Line 1: SelFix Fixture 201 Thru 220
Line 2: at 100
Line 3: CmdDelay 2                  # wait 2 seconds
Line 4: at 0                        # then fade out
Line 5: ClearAll
```

CmdDelay accepts decimal values: `CmdDelay 0.5` = 500ms.

**Warning:** CmdDelay blocks macro execution but does NOT block the console.
Other macros and playback continue running during the delay.

---

## Part 4 — Jump Targets

### Go Macro syntax

```
Go Macro [page]."[name]".[line_number]
```

Line numbers are 1-based (Line 1 = first line in macro editor).

```
Go Macro 1."ColorCycle".3          # jump to line 3 of ColorCycle macro
```

### Call Macro (subroutine)

```
Call Macro 1."ResetPresets"        # execute another macro then return
```

`Call` returns to the calling macro after the sub-macro finishes.
`Go` does not return — it is a hard jump.

### Insertion rule (CRITICAL)

When inserting new lines into an existing macro, ALL jump targets referencing
lines at or after the insertion point must be renumbered.

**Example:** Inserting a line after line 3 in a 10-line macro:
- All `Go Macro X."Name".N` where N ≥ 4 must change to N+1.
- Keep an index shift table before editing: `old_line → new_line`.

---

## Part 5 — Popup Macros

A popup macro shows an on-screen dialog requiring operator confirmation before proceeding.

```
Line 1: Popup "Are you sure you want to clear all?" /yes /no
Line 2: If $POPUP_RESULT = "yes"
Line 3: ClearAll
```

**Note:** `$POPUP_RESULT` is populated by the Popup command result.
If the operator clicks No, `$POPUP_RESULT = "no"` and `ClearAll` is skipped.

### Popup with options

```
Popup "Select action:" /option1="Save" /option2="Load" /option3="Cancel"
If $POPUP_RESULT = "Save"
Go Macro 1."SaveWorkflow".1
If $POPUP_RESULT = "Load"
Go Macro 1."LoadWorkflow".1
```

---

## Part 6 — Macro XML Import

Complex macros are best authored as XML and imported rather than entered line-by-line via
the console interface.

### XML structure

```xml
<?xml version="1.0" encoding="utf-8"?>
<MA xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Info datetime="2026-03-31T21:00:00" />
  <MacroPool>
    <Macro index="0" name="ColorCycle">
      <MacroItem index="0" cmd="SetUserVar $step 0" delay="0" />
      <MacroItem index="1" cmd="SetUserVar $step + 1" delay="0" />
      <MacroItem index="2" cmd="If $step &lt; 8" delay="0" />
      <MacroItem index="3" cmd="Go Macro 1.&quot;ColorCycle&quot;.2" delay="0" />
    </Macro>
  </MacroPool>
</MA>
```

**Note:** XML requires escaping: `<` → `&lt;`, `"` → `&quot;`, `>` → `&gt;`

### Import XML macro

```python
import_objects(
    object_type="macro",
    filename="color_cycle_macro",
    target_id=20,
    confirm_destructive=True,
)
```

File must be in the MA2 importexport directory (8.3 path).

---

## Part 7 — Store Group Timing Rule

When a macro stores groups, the `Store Group N` command must be on its own macro line
and must NOT be combined with fixture selection on the same line.

```
# CORRECT
Line 1: FixtureType 4.M.1 Thru     # select fixtures from type
Line 2: Store Group 14 /o           # separate line for store

# WRONG — causes 1-subfixture result
Line 1: ClearAll ; FixtureType 4.M.1 Thru
Line 2: Store Group 14 /o
```

See `feedback_macro_store_group.md` in project memory for full details.

---

## Allowed Tools

```
list_macros                — SAFE_READ: discover macro pool
get_macro_info             — SAFE_READ: read macro lines
store_macro_line           — DESTRUCTIVE: write individual macro lines
import_objects             — DESTRUCTIVE: import macro XML
export_objects             — DESTRUCTIVE: export macro to XML
send_raw_command           — DESTRUCTIVE: SetVar, SetUserVar, run/call macros
```

---

## Safety

- Always audit line numbers with `get_macro_info` before inserting lines — jump targets break silently.
- `CmdDelay` in a high-priority macro can block show-critical sequences — use with care during a live show.
- `Popup` dialogs block the screen — never use in automated/timecoded sequences.
- Variables are global to the session — naming collisions between concurrent macros cause unpredictable results. Use unique prefixes (`$cc_step`, `$gr_step`).
- `Call Macro` nests — avoid infinite recursion (A calls B calls A). No stack depth guard in MA2.
- Test all conditional logic on a dummy sequence before attaching to live show content.

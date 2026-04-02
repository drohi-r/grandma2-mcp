---
title: Lua Scripting and Plugins
description: Instruction module for grandMA2 Lua scripting (v5.2 gma.* namespace) and plugin invocation via MCP — plugin browsing, Lua execution, and the plugin lifecycle
version: 1.0.0
created: 2026-04-01T00:00:00Z
last_updated: 2026-04-01T00:00:00Z
---

# Lua Scripting and Plugins

**Charter:** SAFE_WRITE + DESTRUCTIVE — browses, invokes, and executes Lua scripts and
plugins on the grandMA2 console. Lua scripts that call `gma.cmd("delete …")` or
`gma.cmd("store …")` carry DESTRUCTIVE scope regardless of the wrapper tool. Scope
enforcement still applies to the underlying MA2 commands.

Invoke when asked to: run a Lua script on the console, call a plugin by name, read or
write a show variable programmatically, loop over fixtures, or do any calculation that
requires conditionals the MA2 command line cannot express.

---

## Macros vs Plugins — When to Use Each

| Need | Use |
|------|-----|
| Linear command sequence (no branching) | Macro |
| Loop over N fixtures or cues | **Lua plugin** |
| Math calculation (fade curve, BPM → time) | **Lua plugin** |
| Read/write a show variable | **Lua plugin** (`gma.show.getvar` / `setvar`) |
| Show a confirm dialog to the operator | **Lua plugin** (`gma.user.confirm`) |
| Trigger a cue, recall a preset, go to a page | Either (Macro is simpler) |
| React to a condition (if fixture count = 0) | **Lua plugin** |

Use macros for simple linear command sequences. Reach for Lua the moment you need
a loop, a branch, arithmetic, or user interaction.

---

## MA2 Lua Environment

- **Lua version:** 5.2 (not 5.3 — `math.log10` exists; bitwise operators do not)
- **Sandbox:** plugins run inside the MA2 process with access to the `gma.*` namespace only.
  Standard Lua `io`, `os`, `socket` libraries are not available.
- **Execution context:** blocking — the console waits for the plugin to return before
  processing further commands. Keep scripts short or use `gma.timer.sleep` sparingly.

### Key `gma.*` Functions

| Function | Signature | Notes |
|----------|-----------|-------|
| `gma.cmd` | `gma.cmd("MA2 command string")` | Sends a command exactly as typed on the command line. Return value is the console feedback string. |
| `gma.echo` | `gma.echo("message")` | Prints to the console System Monitor (visible in feedback). Use for debug output. |
| `gma.show.getvar` | `gma.show.getvar("VARNAME")` | Reads a show variable (without `$` prefix). Returns the value as a string. |
| `gma.show.setvar` | `gma.show.setvar("VARNAME", value)` | Writes a show variable. Value is coerced to string. |
| `gma.user.confirm` | `gma.user.confirm("message")` | Displays an OK/Cancel dialog. Returns `true` (OK) or `false` (Cancel). |
| `gma.timer.sleep` | `gma.timer.sleep(milliseconds)` | Pauses script execution. Use with care — blocks the console thread. |
| `gma.user.answer` | `gma.user.answer("prompt", "default")` | Opens a text input dialog. Returns the entered string. |

### Reading System Variables

Use `gma.show.getvar` (NOT `Echo $VAR`). The `$` prefix expands before execution,
returning `UNKNOWN COMMAND`. Example:

```lua
-- WRONG (MA2 expands before Lua sees it):
gma.cmd("Echo $VERSION")

-- CORRECT:
local ver = gma.show.getvar("VERSION")
gma.echo("Console version: " .. ver)
```

---

## Allowed Tools

```
browse_plugin_library   — SAFE_READ: list available plugins by name and description
call_plugin_tool        — SAFE_WRITE: invoke a named plugin with optional arguments
run_lua_script          — SAFE_WRITE / DESTRUCTIVE: execute inline Lua; risk depends on script body
reload_all_plugins      — SAFE_WRITE: reload plugin system after uploading a new .lua file
list_system_variables   — SAFE_READ: list all 26 MA2 system variable names and values
manage_variable         — SAFE_WRITE: read or write a show variable (SetVar / SetUserVar)
```

---

## Workflow

**Step 1 — Browse available plugins**

```python
browse_plugin_library()
# Returns plugin names, descriptions, and argument signatures.
# Plugin files must already be in the console's plugin directory.
# If the plugin you need is missing, it must be uploaded to the console
# via USB or file share before it will appear here.
```

**Step 2 — Invoke an existing plugin**

```python
call_plugin_tool(
    plugin_name="MyPlugin",
    args={"fixture_id": 1, "preset_id": 5},
)
# Calls the plugin; returns the console feedback string.
```

**Step 3 — Execute an inline Lua script**

Use `run_lua_script` when you do not have a pre-uploaded plugin file and need
to run a short script immediately:

```python
run_lua_script(script_body="""
for i = 1, 12 do
    gma.cmd("Fixture " .. i .. " At 50")
    gma.timer.sleep(50)
end
""")
```

Loops, conditionals, and `gma.*` calls are all valid inside `script_body`.

**Step 4 — Read or write show variables**

```python
# Read via MCP tool:
list_system_variables()

# Write via MCP tool:
manage_variable(action="set", var_name="MY_STATE", value="active")

# Read inside a Lua script:
run_lua_script(script_body="""
local state = gma.show.getvar("MY_STATE")
gma.echo("State is: " .. (state or "nil"))
""")
```

**Step 5 — After uploading a new .lua file**

```python
reload_all_plugins()
# Forces MA2 to re-scan the plugin directory.
# Call this once after any new .lua file is placed on the console.
```

---

## Common Patterns

### Loop over a range of cues and re-time them

```lua
local seq = 1
for cue = 1, 20 do
    gma.cmd("Attribute \"Fade\" At 2 Cue " .. cue .. " Sequence " .. seq)
end
```

### Guard a destructive action with a confirm dialog

```lua
if gma.user.confirm("Delete all cues in Sequence 99?") then
    gma.cmd("Delete Cue 1 Thru 999 Sequence 99")
    gma.echo("Cues deleted.")
else
    gma.echo("Cancelled.")
end
```

### BPM to fade time calculation

```lua
local bpm = tonumber(gma.show.getvar("TRACK_BPM")) or 120
local beat_sec = 60 / bpm
gma.echo(string.format("One beat = %.3f seconds", beat_sec))
gma.cmd(string.format("Assign Sequence 1 /speed=%.1f", bpm))
```

---

## Safety Rules

- `run_lua_script` with `gma.cmd("delete …")` or `gma.cmd("store …")` executes
  DESTRUCTIVE operations. Confirm the script body before running.
- `gma.timer.sleep` blocks the MA2 console thread. Never sleep more than a few
  hundred milliseconds in a script that runs live. Long sleeps freeze the UI.
- Plugin files (.lua) cannot be uploaded over telnet. They must be placed in the
  console's plugin directory manually (USB or network share) before
  `browse_plugin_library` or `call_plugin_tool` will find them.
- `gma.show.setvar` writes to the show file's variable store. These values survive
  show save/load. Use unique variable names to avoid colliding with MA2 system vars
  (all MA2 built-ins are uppercase — use a prefix like `MY_` for custom vars).
- A Lua runtime error inside `run_lua_script` surfaces as a console error message.
  Check the return value and the System Monitor output after execution.

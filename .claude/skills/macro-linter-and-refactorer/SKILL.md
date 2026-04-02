---
title: Macro Linter and Refactorer
description: Inspect grandMA2 macros for unsafe patterns, broken jumps, and refactoring opportunities
version: 1.0.0
safety_scope: SAFE_READ
created: 2026-04-02T00:00:00Z
last_updated: 2026-04-02T00:00:00Z
---

# Macro Linter and Refactorer

## Charter

SAFE_READ skill for analysis. Any actual macro modifications require SAFE_WRITE confirmation from the operator.

## Invocation

Use when reviewing macros before a show, after importing macros from another show file, or when macros are behaving unexpectedly.

## Workflow

### Step 1: Lint the Macro
Call `lint_macro(macro_id=N)` to get a list of issues with severity levels:
- **error**: Dangerous patterns (destructive without gate, broken jumps, unsafe system commands)
- **warning**: Risky patterns (self-referencing jumps, potential infinite loops)
- **info**: Style issues (ambiguous references, missing quotes)

### Step 2: Review Each Issue
For each issue, explain:
- **What it means** in plain language
- **What could go wrong** during a live show
- **How to fix it** with the exact MA2 command

### Step 3: Common Fixes

**Destructive without gate:**
- Add `CmdDelay 2` before destructive lines to give operator time to abort
- Or wrap in a confirmation variable: `If $confirm Go Macro X."delete_section"`

**Broken jump target:**
- Line numbers shift when you insert/delete lines
- Recalculate all `Go Macro X."name".Y` targets after edits
- Use `list_macro_jump_targets(macro_id=N)` to see current jump map

**Missing quotes:**
- Names with spaces must be quoted: `Store Group "Front Wash"` not `Store Group Front Wash`
- The unquoted version selects Group named "Front" then errors on "Wash"

**Infinite loop:**
- Self-referencing `Go Macro N` without a conditional exit
- Add a counter variable: `SetVar $counter = $counter + 1` + `If $counter > 10 Exit`

## Allowed Tools

`lint_macro`, `list_macro_jump_targets`, `browse_macro_library`, `send_raw_command`

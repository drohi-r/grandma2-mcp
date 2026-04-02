---
title: MA2 Command Rules
description: Reusable instruction module for grandMA2 console command construction, object resolution, and safety escalation
version: 1.1.0
created: 2026-03-29T08:30:00Z
last_updated: 2026-03-30T14:00:00Z
---

# MA2 Command Rules

Invoke this skill when constructing grandMA2 console commands, resolving object names, or deciding command safety tier.

---

## 1. Command Construction Rules

### Object naming
- Always pass raw names to `quote_name()` — never pre-quoted strings.
- Plain names (no special chars) are emitted bare. Names with `space`, `*`, `@`, `$`, `.`, `/`, `;`, `[`, `]`, `(`, `)`, `"` get double-quoted automatically.
- For wildcard queries, pass `match_mode="wildcard"` so `*` acts as operator.

### Preset types
- Use `PRESET_TYPES` from `src/commands/constants.py` to map names to IDs: `"color" → 4`, `"position" → 2`, etc.
- Never hardcode preset type IDs inline.

### Options assembly
- Use `_build_store_options()` from `src/commands/helpers.py` for flag assembly.
- Never manually string-concatenate `/flag=value` parts.

### Show safety
- Always default `preserve_connectivity=True` for `new_show()`.
- Omitting `/globalsettings` disables Telnet — the MCP connection is severed.

---

## 2. Object Resolution Heuristics

1. Try `discover_object_names("PoolKeyword")` first to get the current name list.
2. Derive a wildcard pattern from the names.
3. Pass to `list_objects("pool", name="Pattern*", match_mode="wildcard")`.
4. Never hardcode numeric IDs unless the user explicitly specified them.
5. If a pool object has spaces in its name, let `quote_name()` handle quoting.

---

## 3. Safety Escalation Rules

| Tier | Keywords | Rule |
|------|----------|------|
| SAFE_READ | `list`, `info`, `cd`, `help`, `search` | Always allowed; no confirmation needed |
| SAFE_WRITE | `go`, `at`, `clear`, `park`, `select`, `blind` | Allowed; warn if state-altering |
| DESTRUCTIVE | `delete`, `store`, `copy`, `move`, `assign`, `new_show` | Must have `confirm_destructive=True` |

- When in doubt, check `classify_token(token, spec)` from `src/vocab.py`.
- Never auto-set `confirm_destructive=True` — require explicit caller opt-in.

---

## 4. Import/Export Path Rules

- Always use forward slashes in import paths.
- Paths with spaces must use Windows 8.3 short names.
- Relative paths fail with `FILE NOT FOUND` — always use the 8.3 absolute path.

---

## 5. Command String Invariants

- Command strings must not contain `\r` or `\n` — the safety gate rejects them.
- Return raw MA2 command strings from builders — no Telnet I/O in builders.
- `Echo $VAR` does not work — always use `ListVar` to read system variables.

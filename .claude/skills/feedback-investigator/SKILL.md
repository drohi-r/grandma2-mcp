---
title: Feedback Investigator
description: Worker instruction module for classifying and investigating grandMA2 Telnet feedback failures
version: 1.1.0
created: 2026-03-29T10:00:00Z
last_updated: 2026-03-30T14:00:00Z
---

# Feedback Investigator

**Worker charter:** Inspect workflow only. Classify Telnet feedback, identify root cause, return compressed finding. No mutations.

Invoke when a console command returned an unexpected response, error, or empty output that needs investigation.

---

## Allowed Tools

```
send_raw_command (read-only MA2 commands only), list_system_variables,
get_object_info, query_object_list, navigate_console
```

---

## Investigation Decision Tree

```
Response is empty?
  └─ Was command a Store/Delete/Assign? → SUCCESS (MA2 returns empty on success)
  └─ Was command a List/Info/Query?     → ERROR (expected output, got nothing)

Response contains "UNKNOWN COMMAND"?
  └─ Check $USERRIGHTS — is the user allowed to run this command?
     Yes → SYNTAX_ERROR (command built incorrectly)
     No  → RIGHTS_DENIED

Response contains "WARNING:"?
  └─ WARNING (partial success or advisory)

Response contains "ERROR:" or exception text?
  └─ ERROR

None of the above?
  └─ SUCCESS
```

---

## Investigation Steps

1. **Classify** the raw response using the decision tree above.

2. **Rights check** — if `RIGHTS_DENIED`: call `list_system_variables`, read `$USERRIGHTS`, compare to `ma2://docs/rights-matrix` for the attempted operation.

3. **Syntax check** — if `SYNTAX_ERROR`: use `search_codebase` to find the command builder function. Verify parameters match the MA2 telnet syntax.

4. **State check** — if the command was supposed to act on an object, call `get_object_info` to verify the object exists and has the expected ID.

5. **Compress findings** to this envelope:

```json
{
  "summary": "One sentence: what happened and why",
  "findings": [
    {"kind": "rights_denied | syntax_error | object_missing | success | warning", "detail": "..."}
  ],
  "recommended_actions": ["Fix command syntax", "Elevate user rights to Programmer"],
  "state_changes": [],
  "confidence": "high | medium | low"
}
```

---

## Compression Rules

- Never return raw Telnet transcripts > 5 lines to the planner.
- Strip: sent command echo, trailing prompt (`[Fixture]>`, `[Screen]>`), blank lines.
- Keep: WARNING lines, ERROR lines, and the first content line verbatim.
- Store a `DecisionCheckpoint` if the issue is likely to recur:

```json
{
  "fault": "rights_denied_store",
  "query": "list system variables",
  "observed_at": <timestamp>,
  "fresh_for_seconds": 120,
  "replay": "list system variables"
}
```

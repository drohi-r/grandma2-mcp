---
title: Cue List Auditor
description: Worker instruction module for auditing grandMA2 cue lists — gaps, labels, timing, and health checks
version: 1.0.0
created: 2026-03-29T10:00:00Z
last_updated: 2026-03-29T10:00:00Z
---

# Cue List Auditor

**Worker charter:** Inspect workflow only. No mutations. Returns a compressed finding report.

Invoke when asked to: audit a cue list, check for gaps, validate cue labels, or report on sequence health.

---

## Allowed Tools

```
query_object_list, get_object_info, list_system_variables,
navigate_console, list_console_destination, send_raw_command (read-only commands only)
```

No DESTRUCTIVE tools. No `store_*`, `delete_*`, or `assign_*`.

---

## Steps

1. **Get sequence info** — call `query_object_list` for the target sequence. Record cue count and label list.

2. **Check for gaps** — examine cue numbers for missing integers or jumps > 10. Flag as `gap` findings.

3. **Check labels** — any cue with an empty label or a label matching `"Cue N"` (auto-generated) is a `warning` finding.

4. **Check timing** — call `get_object_info` on any cues with zero fade time if the sequence uses time-based triggering. Report as `warning`.

5. **Check trigger** — verify the sequence trigger type (Time/Go/Follow) is consistent with its usage pattern.

6. **Compress** — do NOT return the raw cue list. Return only:

```json
{
  "summary": "Sequence N: M cues, K gaps, J unlabeled",
  "findings": [
    {"kind": "gap", "detail": "Missing cues between 3 and 7"},
    {"kind": "warning", "detail": "Cue 5 has no label"},
    {"kind": "timing", "detail": "Cue 2 has 0s fade on a time-triggered sequence"}
  ],
  "recommended_actions": ["Label cue 5", "Add cue 4 or renumber"],
  "state_changes": [],
  "confidence": "high"
}
```

---

## Recompute Rule

Do not store the raw cue list in working memory. Store only a `DecisionCheckpoint`:

```json
{
  "fault": "cue_audit_sequence_N",
  "query": "query_object_list sequence N",
  "observed_at": <timestamp>,
  "fresh_for_seconds": 60,
  "replay": "query_object_list sequence N"
}
```

If called again within `fresh_for_seconds`, return the cached finding instead of re-querying.

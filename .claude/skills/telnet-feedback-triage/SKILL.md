---
title: Telnet Feedback Triage
description: Reusable instruction module for classifying and summarizing grandMA2 Telnet feedback
version: 1.1.0
created: 2026-03-29T08:30:00Z
last_updated: 2026-03-30T14:00:00Z
---

# Telnet Feedback Triage

Invoke this skill when analyzing raw Telnet output from the grandMA2 console, classifying feedback class, or summarizing command results.

---

## 1. FeedbackClass Classification

Use `parse_telnet_feedback(response)` from `src/rights.py` to classify raw Telnet output.
Returns a `FeedbackRecord` with a `feedback_class` field of type `FeedbackClass` (enum in `src/rights.py`).

| Class | Indicators | Meaning |
|-------|-----------|---------|
| `PASS_ALLOWED` | Empty response, prompt return, clean output | Command permitted and succeeded |
| `PASS_DENIED` | MCP scope gate fired (`blocked=True`) | Correctly blocked before reaching console |
| `FAILED_OPEN` | `Error #72`, `not allowed`, `denied`, `rights` | Slipped past gate; console rejected — dangerous |
| `FAILED_CLOSED` | Blocked by gate when user has sufficient rights | Gate over-blocked; check right assignment |
| `INCONCLUSIVE` | `UNKNOWN COMMAND`, timeout, ambiguous output | Cannot determine outcome — investigate further |

---

## 2. Summarization Rules

When returning Telnet feedback to the planner:
- Strip raw echo of the sent command from the beginning of the response.
- Strip the trailing prompt line (e.g. `[Fixture]>` or `[Screen]>`).
- Keep any WARNING or ERROR lines verbatim.
- If the response is empty after stripping, report `SUCCESS`.
- Never return raw 30+ line Telnet transcripts to the planner — compress to ≤5 lines.

---

## 3. Rights-Gate Feedback Pattern

When feedback indicates `FAILED_OPEN`, `FAILED_CLOSED`, or `INCONCLUSIVE`:
1. Check `$USERRIGHTS` via `list_system_variables()`.
2. Map to MA2Right level: `Admin > Light-Operator > Programmer > Playback-Operator > Guest`.
3. Identify the minimum required right for the attempted command from `doc/ma2-rights-matrix.json`.
4. Return structured finding: `{"fault": "rights_denied", "current_right": X, "required_right": Y}`.

---

## 4. Common False-Negative Patterns

- `Store` commands often return empty string on success — empty = OK for Store.
- `Goto` on an executor with no cues returns an empty string — check cue list before assuming failure.
- `Delete` commands return empty on success and `UNKNOWN COMMAND` if the object never existed (not a true error).
- `ListVar` always returns `$Global : $VARNAME = VALUE` format — strip the `$Global : ` prefix.

---

## 5. Recompute-over-Retain Rule

Do not store raw Telnet transcripts in working memory. Instead:
- Store the classified `FeedbackClass` (e.g. `PASS_ALLOWED`, `FAILED_OPEN`).
- Store the compressed finding (≤50 tokens).
- Store a `replay_query` string if the state needs refreshing.

Example checkpoint:
```json
{
  "fault": "executor_no_cues",
  "query": "list sequence 1",
  "observed_at": "2026-03-29T15:00:00Z",
  "fresh_for_seconds": 30,
  "replay": "list sequence 1"
}
```

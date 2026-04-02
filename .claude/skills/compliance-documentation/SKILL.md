---
title: Compliance Documentation
description: Worker instruction module for generating SB 132 / safety-audit documentation from MA2 Agent session telemetry — risk tier breakdown, DESTRUCTIVE operation log, and operator audit trail
version: 1.0.0
created: 2026-04-01T00:00:00Z
last_updated: 2026-04-01T00:00:00Z
---

# Compliance Documentation

**Worker charter:** SAFE_READ — reads telemetry only, produces reports. No console side effects.

Invoke when asked to: generate a compliance report, produce a safety audit trail, document lighting control operations for SB 132, or create an operator audit log for insurance or production management review.

This skill is for gaffers, safety officers, production managers, and insurance brokers on film/TV productions subject to California SB 132 (effective July 2025) or any production requiring documented lighting control audit trails.

---

## Allowed Tools

```
list_agent_sessions       — SAFE_READ: list session IDs and summaries
recall_agent_session      — SAFE_READ: fetch session detail
get_tool_metrics          — SAFE_READ: per-tool stats
list_system_variables     — SAFE_READ: console state context
get_showfile_info         — SAFE_READ: confirm which show was active
```

No DESTRUCTIVE tools. No `store_*`, `delete_*`, or `assign_*`. Never modifies console state.

---

## What SB 132 Requires (mapped to MA2 Agent fields)

| SB 132 Requirement | MA2 Agent Data Source |
|---|---|
| Written risk assessment | tool_invocations table: risk_tier per operation |
| Daily safety meeting notes | session_id grouped tool calls with timestamps |
| Operator identification | operator field in tool_invocations |
| Final safety report | session summary from recall_agent_session |
| Incident timeline | ts (Unix timestamp) on every tool_invocations row |

---

## Steps

1. **Identify sessions** — call `list_agent_sessions()` to find the session(s) to report on. Confirm session ID, date, and operator with the requestor.

2. **Pull session summary** — call `recall_agent_session(session_id)` for each session. Extract: completed_steps, failed_steps, token_spend, console_state_summary, fixture_summary.

3. **Get per-tool metrics** — call `get_tool_metrics(tool_name, days=1)` for any tools flagged in failed_steps. Record error rates and latency.

4. **Get full invocation log** — call `get_telemetry_report(session_id)` if available. Use this for the DESTRUCTIVE operations log and error timeline.

5. **Get show context** — call `get_showfile_info()` to confirm which show was active during the session. Call `list_system_variables()` to capture console version and operator identity.

6. **Compose report** — structure the output as described below. Do NOT return raw telemetry blobs. Summarize and redact internal system fields not relevant to compliance.

---

## Report Structure

Generate a structured compliance report with these sections:

- **Header**: Production name, date, console operator, session ID
- **Risk Tier Summary**: count of SAFE_READ / SAFE_WRITE / DESTRUCTIVE operations
- **DESTRUCTIVE Operations Log**: timestamp, tool name, inputs summary, output preview, operator
- **Error Log**: any tool calls that returned errors (potential incidents)
- **Session Timeline**: ordered list of all operations with timestamps

---

## Insurance Brief Language

Include a human-readable paragraph suitable for inclusion in production safety documentation:

> "All lighting control operations during this session were processed through MA2 Agent's three-tier safety system. [N] operations were classified SAFE_READ (read-only monitoring, zero risk), [M] were SAFE_WRITE (controlled modifications requiring standard authorization), and [K] were DESTRUCTIVE (required explicit confirm_destructive=True authorization and elevated scope). Full telemetry is available for forensic review."

Substitute actual counts from the session telemetry.

---

## Output Format

Default output is markdown. For formal regulatory submissions, structure as JSON:

```json
{
  "report_type": "SB132_compliance",
  "session_id": "<id>",
  "production": "<name>",
  "date": "<ISO 8601>",
  "operator": "<name>",
  "risk_tier_summary": {
    "SAFE_READ": 0,
    "SAFE_WRITE": 0,
    "DESTRUCTIVE": 0
  },
  "destructive_operations": [],
  "errors": [],
  "timeline": [],
  "insurance_brief": "<paragraph>"
}
```

---

## Recompute Rule

Store a `DecisionCheckpoint` after pulling each session summary:

```json
{
  "fault": "compliance_report_session_<id>",
  "query": "recall_agent_session <id>",
  "observed_at": "<timestamp>",
  "fresh_for_seconds": 300,
  "replay": "recall_agent_session <id>"
}
```

If called again within `fresh_for_seconds`, return the cached report. Session telemetry is immutable once the session ends — a 5-minute cache is safe.

---

## Safety

This skill never modifies console state. It is safe to run during live performance.
Output format is markdown by default. For formal reports, structure as JSON with `format="json"`.

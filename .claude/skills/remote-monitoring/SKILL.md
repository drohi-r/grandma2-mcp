---
title: Remote Monitoring
description: Instruction module for continuous SAFE_READ console state monitoring — show change detection, system variable polling, unexpected state alerts, and broadcast/architectural lighting integration
version: 1.0.0
created: 2026-04-01T00:00:00Z
last_updated: 2026-04-01T00:00:00Z
---

# Remote Monitoring

**Worker charter:** SAFE_READ only. Polling loop that never modifies console state. Suitable for live broadcast, 24/7 architectural installations, and safety-critical environments.

Invoke when asked to: monitor the console, watch for state changes, set up an alert loop, or run a broadcast safety check.

---

## Use Cases

- **Broadcast studios** — Monitor console state without risk during live air; alert on unexpected showfile change
- **Architectural installations** — 24/7 monitoring of grandMA2 running automated sequences; alert on programming drift
- **Live events** — Safety officer monitoring — detect unexpected DESTRUCTIVE operations via telemetry, alert if parked fixtures change
- **Touring** — Remote TD monitoring console state between shows in a venue-to-venue context

---

## Core Monitoring Loop

The monitoring pattern uses three tools in sequence:

```python
# 1. Establish baseline
hydrate_console_state()
baseline = get_console_state()
showfile_info = get_showfile_info()

# 2. Poll on interval
watch_system_var(
    var_name="SHOWFILE",
    expected_value=showfile_info["show_name"],
    timeout_seconds=300,      # 5 min timeout
    poll_interval_seconds=10
)

# 3. Diff against baseline
current = get_console_state()
diff = diff_console_state(baseline=baseline)
```

---

## Alert Conditions

| Condition | Tool | Alert Level |
|-----------|------|-------------|
| Showfile changed | `assert_showfile_unchanged()` returns False | CRITICAL |
| Unexpected fixtures parked | `get_park_ledger()` differs from baseline | WARNING |
| Active filter changed | `get_filter_state()` differs | WARNING |
| World assignment changed | `get_world_state()` differs | WARNING |
| Console user changed | `list_system_variables()` → $USER differs | WARNING |
| Error in telemetry | `get_tool_metrics()` shows new errors | NOTICE |

---

## Broadcast Studio Protocol

During live air:

1. Lock operator to SAFE_READ tier via `GMA_SCOPE` env var (`read_only`)
2. Run `assert_showfile_unchanged()` before every scene change
3. Run `get_console_state()` after every automated scene change to verify state
4. Never run SAFE_WRITE during live broadcast without explicit TD approval

TLCI/CRI compliance note: grandMA2 does not expose fixture TLCI/CRI data via telnet. Preset pool integrity — verifying correct color presets are assigned to correct executors — is the proxy check.

---

## Architectural Installation Protocol (24/7)

For permanent installations running automated sequences, poll every 30 minutes:

```python
assert_showfile_unchanged()
get_park_ledger()              # unexpected parks indicate manual intervention
diff_console_state(baseline)   # drift detection
```

If diff shows unexpected state changes: send alert and require TD review before resuming automated operation.

---

## Telemetry-Based Safety Monitoring

For productions requiring audit trails, combine with the `compliance-documentation` skill:

```python
get_tool_metrics(tool_name="send_raw_command", days=1)   # unusual raw commands
get_tool_metrics(tool_name="store_current_cue", days=1)  # unexpected cue stores
```

Alert if DESTRUCTIVE operations occurred without expected session context.

---

## Integration Points

Results can be fed to any alerting system (Slack, PagerDuty, email) via the MCP client's own notification layer — this skill provides the data, the operator's system sends the alert. Combine with `compliance-documentation` skill to auto-generate daily safety reports.

---

## Allowed Tools

```
watch_system_var, assert_showfile_unchanged, hydrate_console_state, get_console_state,
diff_console_state, get_showfile_info, get_park_ledger, get_filter_state, get_world_state,
list_system_variables, get_tool_metrics, list_agent_sessions
```

No SAFE_WRITE or DESTRUCTIVE tools. This skill never modifies console state.

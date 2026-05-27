---
title: Connection Setup Workflow
description: Discover → pick → reconfigure → verify loop for grandMA2 console pairing
version: 1.0.0
created: 2026-05-27T00:00:00Z
last_updated: 2026-05-27T00:00:00Z
tags: [connection, setup, discovery]
prerequisites: []
wraps_plugin:
use_instead_of: []
safety_scope: SAFE_WRITE
---

# Connection Setup Workflow

## When to use

The console IP changed between sessions, the MCP server is running but cannot reach the console, or you are pairing the MCP with a new console for the first time.

## First decision

If you know the console host/IP and the user credentials, skip discovery and call `reconfigure_connection` directly. Otherwise, run discovery first.

## Expert checklist

The output of this skill is "expert" only when it includes ALL of:

- [ ] Discovery returned at least one candidate OR the operator confirmed manual host input
- [ ] `reconfigure_connection` returned `verified: true` before any subsequent tool call
- [ ] `.env` was persisted (`persist=True`) so the next server restart picks up the new host
- [ ] No tool was invoked on the new connection until verification confirmed reachability
- [ ] Operator confirmed which credentials map to which OAuth tier (administrator → tier 5; operator → tier 1; etc.)

---

## Steps

### 1 — Discover candidates

```python
discover_consoles(timeout_seconds=5)
```

Returns ``candidates`` (list of ``{host, port, name, session_name, version, response_ms, source}``) and ``note`` (diagnostic). UDP broadcast is the only Path A method; mDNS requires the optional ``[mdns]`` install (Path B).

If no candidates are returned, ask the operator for a manual host/IP.

### 2 — Pick a candidate

If discovery returned multiple candidates, prefer the one matching the expected ``session_name`` (e.g., the operator's known session). If none match, report all candidates and let the operator pick.

### 3 — Reconfigure

```python
reconfigure_connection(
    host=<picked.host>,
    port=<picked.port>,        # 30000 by default
    user="administrator",       # or the credentials for the operator's role
    password=<from-vault>,
    persist=True,               # write to .env so the next session uses the new host
    verify=True,                # round-trip a SAFE_READ before swapping
)
```

`verify=True` opens a fresh client, runs `ListVar`, and only declares success on a response. If verification fails the previous connection is preserved.

### 4 — Confirm

Call any SAFE_READ tool — e.g., `discover_object_names("group")` or `list_skills(query="")` — to confirm the new session is operating.

---

## Gotchas

- Broadcast UDP is blocked on many corporate / venue networks; if discovery returns empty, fall back to manual host entry from the operator.
- `reconfigure_connection` performs an atomic swap; any tool call already in flight against the old manager will error with ConnectionError — that is expected and operator-recoverable (retry the tool).
- The `.env` persist path is the repo-root `.env`. If the operator is running the server from a non-standard location, persist may write to the wrong file — confirm `persisted_to` matches expectation before relying on it.
- Mock mode (`GMA_MOCK=1` or `GMA_MOCK=schema`) bypasses the real Telnet path; `reconfigure_connection` still runs but the round-trip is against the mock.

## Related tools

- `discover_consoles(timeout_seconds, network, methods)` — SAFE_READ
- `reconfigure_connection(host, port, user, password, persist, verify)` — SAFE_WRITE (scope SYSTEM_ADMIN)
- `health_check()` — generic post-swap smoke check (Companion / Telnet / show file)

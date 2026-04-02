---
title: Session Handover — MA2 Agent on Windows + Hardware
description: Complete handover for setting up MA2 Agent on the Windows laptop connected to grandMA2 hardware
version: 1.0.0
created: 2026-04-02T00:00:00Z
last_updated: 2026-04-02T04:31:14Z
---

# Session Handover — MA2 Agent on Windows + Hardware

## Situation

The Windows laptop currently has the **original upstream repo** (`thisis-romar/ma2-onPC-MCP`, branded "GrandPA2-Buddy") installed. It needs to be replaced with **our hardened fork** (`drohi-r/grandma2-mcp`, branded "MA2 Agent" v1.0.0). The laptop is connected to a physical grandMA2 console.

---

## Step 1: Replace the upstream repo with our fork

```bash
# 1. Back up the current installation (just in case)
cd C:\Users\<username>
ren ma2-onPC-MCP ma2-onPC-MCP-backup

# 2. Clone our fork
git clone https://github.com/drohi-r/grandma2-mcp.git
cd grandma2-mcp

# 3. Install dependencies
uv sync

# 4. Copy your .env from the old installation (has console IP, credentials)
copy ..\ma2-onPC-MCP-backup\.env .env
# OR create fresh from template:
copy .env.template .env
# Then edit .env with your values:
#   GMA_HOST=<console IP, e.g. 192.168.1.100>
#   GMA_PORT=30000
#   GMA_USER=administrator
#   GMA_PASSWORD=admin
```

## Step 2: Verify the console connection

```bash
# Run the test suite (should pass without a live console)
uv run python -m pytest -v

# Quick connection test
uv run python scripts/main.py
```

If connection fails, check:
- grandMA2 Telnet is enabled: Setup → Console → Global Settings → Telnet = "Login Enabled"
- Firewall isn't blocking port 30000
- Console IP matches .env GMA_HOST
- Credentials match a valid console user

## Step 3: Start the MCP server

```bash
uv run python -m src.server
```

This starts the MCP server on stdio. Connect Claude Desktop or VS Code to it using the configs in `.claude/` or the MCP client config in the README.

---

## What changed since the upstream (everything the new Claude session needs to know)

The change lists below capture the original hardening wave on this branch. The "Current stats" section reflects the present repo state after the later analysis/intelligence expansion.

### Hardening (Phases 1-6)
- **3 critical bugs fixed**: elicitation enum compare, Lua backslash injection, duplicate dataclass field
- **5 security fixes**: destructive gates on 4 tools, auto-confirm removed, LLM injection defense, subscription race conditions, telemetry thread safety
- **8 infrastructure fixes**: scan_indexes lock, session reconnect timeout, login validation, Ctrl+C handling, skill safety_scope parsing, configurable completions, JSON deserialization safety, label quoting
- **5 agent/RAG fixes**: verification fails on missing DESTRUCTIVE strategy, planner cycle detection, embedding dimension validation, URL normalization, tools.py singleton
- **All 43 previously unmapped tools** now have correct MA2 rights levels
- **19 pre-existing test failures** resolved (Windows path mocking, missing get_client mocks, clustering)
- **Rights drift test** enforces zero unmapped non-read tools

### Rebrand
- Project: GrandPA2-Buddy → **MA2 Agent**
- Package: `grandpa2-buddy` → `ma2-agent`
- Author: romar → drohi-r
- Full attribution chain preserved: chienchuanw → thisis-romar → drohi-r (LICENSE, NOTICE)
- New banner SVG (red flat design)

### New tools added in the original hardening wave (9 new, total 200 at that point)
| Tool | Risk | What it does |
|------|------|-------------|
| `batch_label` | DESTRUCTIVE | Label multiple objects in one call |
| `bulk_executor_assign` | DESTRUCTIVE | Assign + configure executor in one shot |
| `auto_number_cues` | DESTRUCTIVE | Renumber cues with spacing |
| `compare_cue_values` | SAFE_READ | Diff two cues in a sequence |
| `diagnose_no_output` | SAFE_READ | Systematic "why no light?" diagnostic |
| `generate_companion_config` | SAFE_READ | Export executor page as Companion .companionconfig |
| `companion_button_press` | SAFE_WRITE | Trigger Companion buttons via HTTP API |
| `set_bpm` | SAFE_WRITE | Set speed master BPM for DJ tempo sync |
| `send_osc` | SAFE_WRITE | Send OSC messages to Resolume/QLab/etc |

### New skills added in the original hardening wave (5 new, total 39 at that point)
| Skill | What it teaches |
|-------|----------------|
| `festival-stage-setup` | Patch to busking-ready in one session |
| `troubleshoot-no-output` | Step-by-step no-output diagnostic |
| `cue-to-cue-rehearsal` | Guided rehearsal with cue diffs |
| `companion-integration` | Companion button page setup |
| `showkontrol-bpm-sync` | CDJ → ShowKontrol → MA2 BPM sync (+ Resolume OSC) |

### Current stats
- **218 tools** (184 server + 34 orchestration)
- **45 skills**
- **2783 tests** (2641 passing, 142 skipped, 0 failed)
- **Version:** 1.0.0
- **Repo:** https://github.com/drohi-r/grandma2-mcp (public)
- **Latest expansion:** 10 additional analysis/intelligence tools + 5 additional skills beyond the earlier hardening wave
- **Latest local fix pass:** agent-harness confirmation/auth corrections, runtime/doc sync, 8 new analysis/recovery tools, 1 new skill, and final full-suite validation

---

## Environment variables reference

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `GMA_HOST` | Yes | `127.0.0.1` | Console IP address |
| `GMA_PORT` | No | `30000` | Telnet port |
| `GMA_USER` | Yes | — | Console Telnet username |
| `GMA_PASSWORD` | Yes | — | Console Telnet password |
| `GMA_SCOPE` | No | `gma2:system:admin` | OAuth scope tier |
| `GMA_AUTH_BYPASS` | No | `0` | Set to `1` to skip scope checks (dev only) |
| `GMA_TELEMETRY` | No | `1` | Set to `0` to disable tool invocation logging |
| `GMA2_DATA_ROOT` | No | Windows MA2 path | Override MA2 data directory |
| `GMA_MAX_SEQUENCES` | No | `50` | Completion range for sequence IDs |
| `GMA_MAX_GROUPS` | No | `20` | Completion range for group IDs |
| `GITHUB_MODELS_TOKEN` | No | — | For RAG semantic search (optional) |

---

## Things to test on the hardware

Once connected to the physical console:

1. **Basic connectivity**: `list_system_variables` — should return $VERSION, $SHOWFILE, etc.
2. **Navigation**: `navigate_console(destination="/")` then `list_console_destination`
3. **Read fixtures**: `list_fixtures` — verify it shows your patched fixtures
4. **Read executors**: `scan_page_executor_layout(page=1)` — verify your executor setup
5. **BPM sync**: `set_bpm(bpm=120)` — check speed master on console responds
6. **New diagnostic**: `diagnose_no_output(fixture_id=1)` — run through the diagnostic tree
7. **Batch label test**: Try `batch_label` on a group (with `confirm_destructive=True`)

### Live integration tests (optional)
```bash
RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live_integration.py -v
```

---

## Previous session context

Before this hardening session, there was an initial session that:
1. Created the backup at `~/Desktop/ma2-onPC-MCP-backup`
2. Set up `~/Projects/grandma2-mcp` as a fresh private repo
3. Added the upstream remote: `git remote add upstream https://github.com/thisis-romar/ma2-onPC-MCP`
4. Did the initial import and started the audit

The full hardening plan is at: `~/.claude/plans/hashed-crafting-clover.md` (Mac)

---

## Cleanup (after confirming everything works)

Once MA2 Agent is verified on the Windows laptop:
```bash
# Remove the old upstream installation
rmdir /s /q C:\Users\<username>\ma2-onPC-MCP-backup
```

---

## Git log (full commit history)

```
d844277 feat: OSC output tool + Resolume integration (200 tools, 39 skills)
8213383 feat: BPM sync tool + ShowKontrol integration skill (199 tools, 39 skills)
9bd351d feat: Bitfocus Companion integration (198 tools, 38 skills)
c00c208 chore: sync all counts and bump to v1.0.0
7765d42 feat: 5 new tools + 3 new skills (196 tools, 37 skills)
b4a0e68 rebrand: GrandPA2-Buddy → MA2 Agent
a033c7c rights: map all 43 unmapped tools to correct MA2 rights levels
c6cc4ef fix: resolve all 19 pre-existing test failures
699a64c hardening phase 5: docs/polish — counts, model hint, feedback, drift test
1fe8b99 hardening phase 4: 5 agent/RAG fixes
8209f93 hardening phase 3: 8 core infrastructure fixes
b554ddb security: 5 safety fixes — destructive gates, injection defense, race conditions
90d68b3 fix: 3 critical bugs — elicitation compare, Lua injection, duplicate field
df39a18 Initial import from thisis-romar/ma2-onPC-MCP
```

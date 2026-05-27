---
title: grandma2-mcp — Scope of Improvements
description: Concrete, prioritized improvement scope across architecture, reliability, polish, and strategic functionality
version: 0.1.0
created: 2026-05-26
last_updated: 2026-05-26
status: draft
---

# grandma2-mcp — Scope of Improvements

## Executive summary

The repo is in unusually mature shape for a 14-commit hardening fork: 218 tools across two agent abstractions, ~36k LOC of source, 1,822 test functions, an architecture-hygiene test suite that enforces structural invariants, a 3-layer safety model, telemetry, RAG, ML tool categorization, and 45 skill playbooks. The "what" is impressive. The risks are concentrated in five places:

1. **`server.py` has become a 13k-line monolith** holding 184 tool definitions and hundreds of split-line imports. Every future change pays a tax.
2. **Two parallel agent stacks coexist** (`src/orchestrator.py` + `src/server_orchestration_tools.py` vs. `src/agent/` package) with `agent_bridge.py` as a translator. Direction is undeclared.
3. **Counts and docs have drifted** from reality — README claims 2,783 tests, true count is 1,822; SESSION-HANDOVER claims the same; skill count is 44 in one place and 45 in another; no tagged releases despite `v1.0.0` in `pyproject.toml`.
4. **Live console coverage is ~26%** (56 of 218 tools). The unit suite is large but the surface verified against real hardware is narrow.
5. **The repo is not yet shaped for downstream consumption** — no CHANGELOG, no released artifacts, no SDK boundary, a 33MB PDF in `doc/`, dev scratchpad scripts in `scripts/archive/`, and a `docs/` directory with one file alongside the canonical `doc/`.

Everything below is concrete and actionable. Each item has a rough effort tag: **S** (≤1 day), **M** (≤1 week), **L** (>1 week).

---

## State of the repo (what I actually measured)

| Metric | Value | Source |
|---|---|---|
| Python LOC (`src/`) | 35,849 | `find src -name "*.py"` |
| `src/server.py` LOC | 13,183 | direct `wc -l` |
| Tool decorators in `server.py` | 184 | `grep -c @mcp.tool` |
| Tool decorators in `server_orchestration_tools.py` | 34 | same |
| Test files | 95 | `ls tests/*.py` |
| Test functions | 1,822 | `grep -c "^def test_"` |
| Live-console test coverage | ~56 tools / 218 | `tests/test_live_integration.py` |
| Total commits | 34 | `git log` |
| Repo size | ~70MB | `du -sh` |
| Largest single file | `doc/2024-09-30_grandMA2_User_Manual_v3-9.pdf` (33MB) | `du -sh` |
| TODO/FIXME markers | 0 | `grep -rn TODO FIXME` |
| Released versions on GitHub | 0 | github releases |

---

## Dimension 1 — Code & architecture

### 1.1 Split `server.py` (P0, L)

13k lines in one file is the dominant maintainability tax. Tools should live alongside their domain:

```
src/server/
  __init__.py           # FastMCP instance + mount
  _common.py            # _handle_errors, _validate_object_exists, etc.
  _tool_registry.py     # _build_tool_registry()
  navigation_tools.py   # 4 tools
  lighting_tools.py     # 7 tools
  selection_tools.py    # 8 tools
  playback_tools.py     # 9 tools
  store_tools.py        # 13 tools
  ... etc per README category
  agent_tools.py        # The 3 agent harness tools (run/plan/dry_run)
```

Migration is mechanical (each `@mcp.tool` block moves to its category file, gets re-registered with the shared `mcp` instance). The architecture-hygiene test should grow a new invariant: **no single tools file >800 LOC**.

### 1.2 Resolve the dual-agent stack (P0, M)

Two systems do overlapping work:

| Old stack | New stack | Status |
|---|---|---|
| `src/orchestrator.py` (548 LOC) | `src/agent/runtime.py` | Both wired to MCP |
| `src/task_decomposer.py` (575 LOC) | `src/agent/planner.py` | Bridged |
| `src/agent_memory.py` (WorkingMemory/LongTermMemory) | `src/agent/memory.py` (WorkflowMemory) | Different schemas |
| `src/server_orchestration_tools.py` (34 tools) | `run_agent_goal` / `plan_agent_goal` | Agent harness wraps the old tools |

`agent_bridge.py` translates `SubTask ↔ PlanStep` but no doc declares the migration target. Three options:

- **(a) Deprecate old, migrate to `src/agent/`.** Clean but loses the 34 fine-grained orchestration tools that have value as a power-user surface.
- **(b) Declare them as separate layers** — `src/agent/` is *the* agent harness, `src/orchestrator.py` exposes lower-level steerable tools. Document the boundary in CLAUDE.md and remove the bridge for direct interop, keeping the old as a complementary toolkit.
- **(c) Fold the old into `src/agent/`** as a "step library" used by the new planner. Highest engineering cost, cleanest end state.

Recommendation: **(b)** in the short term, with a 6-month plan toward (c). Either way, ship the decision as an ADR in `doc/`.

### 1.3 Clean up `server.py` imports (P1, S)

The current pattern is ~200 separate `from src.commands import (x as build_x,)` blocks. Should be one consolidated block per source module or a single facade import. Likely originated from an auto-formatter splitting on aliases. Ruff has an `I` rule selected — investigate why it isn't catching this and fix the isort config.

### 1.4 Centralize `__version__` (P1, S)

Right now `1.0.0` lives in: `pyproject.toml`, `CLAUDE.md` front matter, README banner, SESSION-HANDOVER.md, and bumped manually in commit messages. Pull it from `pyproject.toml` into `src/__init__.py` via `importlib.metadata`, then reference everywhere from one source.

### 1.5 Deprecate truly legacy tools (P2, S)

README explicitly marks `execute_sequence` as "legacy" alongside `playback_action`. Other suspects from the surface scan:

- `go("executor", n)` vs `go_executor(n)` — two builders, same output
- `go_back` vs `goback` aliases
- `def_go_back` vs `def_goback` — both exposed

Add a `@deprecated(replacement=...)` decorator that emits a structured warning into telemetry but doesn't break callers. After two releases, remove.

### 1.6 Repo bloat (P1, S)

- Move `doc/2024-09-30_grandMA2_User_Manual_v3-9.pdf` (33MB) out of git — it's a third-party copyrighted document anyway. Replace with a `doc/REFERENCES.md` linking to MA Lighting's download page.
- Merge `docs/` (one file: `CODEX-CONSISTENCY-PASS-HANDOVER.md`) into `doc/` or `archive/`.
- Move `scripts/archive/` (debug_v5/v6/v7/v8.py, compare_v3_v4.py, verify_fixture_order2.py, etc.) to a separate `internal-ops/` repo or delete. These are dev scratchpads from past sessions.
- Add a `.gitattributes` rule so the manual PDF (if kept) uses Git LFS.

### 1.7 Tool taxonomy consistency (P2, M)

K-Means clustering produces auto-labeled categories, but they're never compared against the human-curated README categories. Add a test that fails if any tool is in a cluster whose dominant label disagrees with the README section it lives under. Surface the disagreements as a `doc/tool-taxonomy-conflicts.md`.

---

## Dimension 2 — Reliability & safety

### 2.1 Live integration coverage gap (P0, L)

`tests/test_live_integration.py` covers 56 of 218 tools (~26%). The other 162 have only mocked telnet response coverage. For a tool that drives real hardware in production shows, this is the single biggest reliability risk.

Plan: add a `tests/live/` directory with one module per category, each gated on `RUN_LIVE_TESTS=1`. Build a `pytest-live-console` fixture that owns a fresh showfile per test class. Target: 80% live coverage within two releases.

### 2.2 Risk-tier inference is heuristic and silent (P0, S)

`telemetry.py::infer_risk_tier()` uses prefix matching + signature inspection. Anything not matching a SAFE_READ prefix and lacking `confirm_destructive` defaults to `SAFE_WRITE`. This means a misnamed destructive tool gets silently misclassified.

Fix: replace the heuristic with an explicit `@risk_tier(RiskTier.X)` decorator on every tool, fall back to the heuristic only with a logged warning, and add an architecture-hygiene test that fails on any tool missing an explicit tier.

### 2.3 Snapshot freshness is implicit (P1, M)

`ConsoleStateSnapshot` is hydrated on demand. Several tools (`assert_showfile_unchanged`, `diff_console_state`, `watch_system_var`) exist precisely because stale snapshots bite. Make the contract explicit:

- TTL on each hydrated field (programmer selection: 1s; patch: 60s; showfile name: 300s)
- A `staleness` field in every state-query response
- Auto-rehydrate on read when expired, with a `force_refresh` override

### 2.4 No live destructive-tool failure-mode catalog (P1, M)

The safety model is sound *in theory*. There's no catalog of "what actually happens when X goes wrong on a real console". Build `doc/failure-modes.md` capturing:

- What `store_current_cue` does when the executor is empty
- What `load_show` does mid-show (besides killing telnet via globalsettings)
- What happens when two operators connect with conflicting rights
- What `Error #72` actually looks like across the 12 most common destructive paths

This becomes both onboarding documentation and the reference for new test cases.

### 2.5 Concurrency around `pool_name_index` (P2, S)

The in-memory pool name registry is described as "zero-cost object resolution". Confirm: is it thread-safe under concurrent MCP requests? Does it invalidate when objects are deleted via `delete_object`? Add a regression test for "delete object → registry still returns the stale name" if that hole exists.

### 2.6 Test count truth (P0, S)

- README badge: 2,783 (wrong)
- README project tree comment: 2,187 (wrong)
- SESSION-HANDOVER.md: 2,783 (wrong)
- Actual: 1,822 test functions

Either the badge is counting test cases (parametrized expansions) and the count of `def test_*` is the truth — verify which, then make every reference use the same number. The same audit should apply to skill counts (44 vs 45) and tool counts.

### 2.7 Error path consistency (P1, M)

Across 184 tools the error envelope shape isn't audited. Add a test that calls every tool with a known-bad input and asserts the response shape: `{"error": str, "risk_tier": str, "tool": str, ...}`. Telemetry depends on this consistency.

---

## Dimension 3 — Product polish

### 3.1 Releases and changelog (P0, S)

- Tag `v1.0.0` retroactively from `c00c208` (the "bump to v1.0.0" commit)
- Create a `CHANGELOG.md` with Keep-a-Changelog format
- Set up release-please or git-cliff to auto-generate from conventional commits going forward
- Add GitHub Actions release workflow that publishes to PyPI on tag push
- Decide on a versioning policy (semver vs calver) given how often the tool count changes

### 3.2 README is 64KB and dense (P1, M)

The current README is impressive but performs both as marketing and reference docs simultaneously. Split:

- `README.md` — overview, quickstart, links to deeper docs. <500 lines.
- `doc/architecture.md` — current "Architecture" section
- `doc/tools-reference.md` — the 218-tool catalog (auto-generate from docstrings)
- `doc/skills-reference.md` — the 45-skill catalog
- `doc/resources-and-prompts.md` — current MCP resources/prompts sections

Tool reference auto-generation: write a `scripts/gen_tool_reference.py` that introspects `mcp.list_tools()` and emits markdown. This solves the count-drift problem permanently — the doc is generated, not hand-maintained.

### 3.3 Quickstart works on day 0 (P1, S)

Current quickstart assumes `uv`, an MA2 console at a known IP, and Claude Desktop config knowledge. Add:

- A `mock` mode (`GMA_MOCK=1`) that runs the server against an in-memory fake — useful for trying tools without a console
- A `make demo` target that spins up the UI with the mock backend
- A 60-second "first tool call" example in the README

### 3.4 Operator UI is undermarketed (P1, S)

`src/ui.py` (20KB) is a fully-functioning browser console — the README mentions it briefly but doesn't show screenshots or describe what it's for. Either:

- Promote it to a co-equal entry point with screenshots in README, or
- Mark it explicitly as preview/internal so users don't depend on it before it's hardened

### 3.5 Telemetry has no consumer (P1, M)

`tool_invocations` table records every call with latency and risk tier. There's `get_telemetry_report` and `generate_compliance_report`, but no dashboard. Build a minimal one in `src/ui.py`:

- Tools by call volume
- p50/p95 latency per tool
- Error rate per tool
- DESTRUCTIVE call audit log

This is also the entry point for the ShowGrid Pro tier story (see §4.1).

### 3.6 Skills are an undocumented power-feature (P2, M)

The 45 skills in `.claude/skills/` are arguably the highest-leverage thing in the repo — they encode real lighting design knowledge. Currently they're a flat list in the README. Improvements:

- Group skills by use case in the docs (preset design, busking, fixture work, troubleshooting, integrations)
- Add a "skill matrix" showing which skills compose well together
- Make `list_skills` return richer metadata (estimated tokens, prerequisites, related skills)
- Publish the skills index as a stand-alone resource at `https://drohi-r.github.io/grandma2-mcp/skills/`

### 3.7 Front-matter discipline (P2, S)

The architecture-hygiene tests already check front matter on `.claude/rules/`, `.claude/skills/`, and `doc/`. Extend to require valid ISO 8601 timestamps using the `time` MCP — currently dates are hand-typed and several show clear fabrications (2026-04-04, etc., when commits are dated May 25).

---

## Dimension 4 — Strategic prep + practical functionality

This is the section you asked to expand. Splitting it into commercial readiness (ShowGrid path) and functional capability gaps (new tools/integrations that unlock real production work).

### 4.1 ShowGrid Pro/Enterprise foundation (P0, L)

The open-source repo will remain the connector. ShowGrid Pro is the value-add. The repo isn't yet shaped to host that distinction safely. Required separations:

| Layer | Open-source (this repo) | ShowGrid Pro (separate repo, closed) |
|---|---|---|
| Connector tools | All 218 MCP tools | — |
| Agent runtime | Single-tenant `AgentRuntime` | Multi-tenant orchestration |
| Telemetry | SQLite local | Postgres + per-tenant isolation |
| Auth | OAuth scope + console rights | SSO, RBAC, tenant boundaries |
| Observability | `tool_invocations` table | Dashboards, alerting, SLOs |
| Compliance | `generate_compliance_report` (single show) | Multi-show audit warehouse |
| Integrations | One sibling MCP at a time | Unified meta-orchestrator across MA2/Resolume/Companion/Beyond/Madrix |
| Show file management | Single console, local | Cloud sync, versioning, diff |

Concrete repo prep work that unblocks this (all open-source-safe):

- **Plugin/extension API**: define a `ShowGridExtension` interface in `src/agent/` that lets external code register pre/post hooks on tool calls, custom risk-tier policies, and additional telemetry sinks. This is the cleavage plane.
- **Stable public API**: declare which modules are public (`src/agent/`, `src/commands/`, `src/server.py` tool surface) vs internal (`src/_internal/`). Use underscores rigorously. Document the contract.
- **Telemetry sink interface**: today telemetry writes directly to SQLite. Abstract behind `TelemetrySink` (with `SQLiteTelemetrySink` as the OSS impl); ShowGrid Pro plugs in `PostgresTelemetrySink`.
- **License boundary**: keep all 218 tools and the agent runtime Apache 2.0. The dashboards, multi-tenancy, SSO, and orchestration UI go in a separate commercial repo. Resist the temptation to relicense.

### 4.2 Sibling-MCP unification (P0, M)

You already have grandma2-mcp, resolume-mcp, companion-mcp, beyond-mcp, mikrotik-routeros-mcp, and madrix-mcp in development. They share:

- The same safety/risk-tier model
- The same telemetry concerns
- The same agent harness pattern
- The same MCP tool envelope

Today each is reimplementing this. Extract a `showgrid-mcp-sdk` (Apache 2.0, separate repo) containing:

```
showgrid_mcp_sdk/
  safety.py          # RiskTier, @require_destructive_confirm
  telemetry.py       # TelemetrySink, ToolInvocation
  agent/             # AgentRuntime, base PlanStep, base Policy
  testing/           # Pytest fixtures, mock helpers
  rights.py          # Generic rights/role gate
```

Each console MCP becomes a thin domain layer on top. The Show Programming Co-Pilot vision from your memory becomes natural: one agent harness that knows about all five protocols, with each as a registered toolkit.

### 4.3 MA3 path (P2, L)

grandMA3 uses JSON-RPC over WebSocket — fundamentally different transport from MA2 telnet. Today `src/telnet_client.py` and the command builders are MA2-specific. If you want to extend later:

- Abstract a `ConsoleTransport` interface (send/receive/auth)
- Abstract a `ConsoleProtocol` interface (command builders + response parsers)
- The agent runtime, telemetry, safety model, and most skills stay protocol-agnostic
- An MA3 implementation becomes a sibling package, not a fork

Not urgent (the MA3 install base is still small), but architectural decisions made now lock you in. The dual-agent decision (§1.2) and the SDK extraction (§4.2) both touch this.

### 4.4 Practical tool gaps (P1, M each)

What's missing that production work needs:

**Show file ops**
- `diff_showfiles(a, b)` — diff two show files structurally (groups, presets, cues changed) — essential for cross-venue adaptation
- `extract_show_subset(objects)` — pull a slice of a show into a PSR-compatible export
- `validate_show_against_rig(showfile, patch_inventory)` — pre-flight a foreign show against your fixture inventory

**Live operations**
- `stream_executor_state(executor_ids, on_change)` — subscribe to live state changes for executor dashboards (not just polling)
- `stream_dmx_universe(universe, fps)` — DMX-level feedback stream for verifying actual output
- `snapshot_console_state()` — capture full programmer + executors + selection as a restorable snapshot (the MA2 "snapshot" feature exposed as an agent-level tool)

**Fixture / patch**
- `import_gdtf(fixture_type)` — direct GDTF library import (the current path is .ma library only)
- `export_mvr(showfile)` — export to MVR for previs handoff (Depence, Capture, Vectorworks)
- `validate_fixture_types_against_library()` — flag fixture types not in the patched library

**Macro authoring**
- `lint_macro(macro_id)` — beyond the existing `macro-linter-and-refactorer` skill, expose as a tool
- `simulate_macro_dry_run(macro_id)` — symbolic execution without firing the console
- `generate_macro_from_steps(natural_language)` — agent-level macro authoring

**Multi-console coordination**
- `register_secondary_console(host, role)` — for backup/tracking setups
- `sync_state_to_secondary()` — manual sync trigger
- `verify_secondary_in_sync()` — drift detection

**RDM / network**
- `rdm_discover_universe(universe)` — RDM device sweep
- `rdm_get_sensor_data(fixture_id)` — temperature/fan/lamp hours
- `network_topology_health()` — uses your MikroTik MCP knowledge to verify the AV VLAN scheme is sane

### 4.5 RAG corpus expansion (P2, M)

Current RAG corpus is the repo + 1,043 MA2 help pages + the MCP SDK. Missing:

- MA2 Lua scripting reference (you have one skill for it but no embedded docs)
- Common forum solutions (LSC, Plasa Light Network etc.) — copyright-safe summaries
- Your own production showfiles' READMEs / handoff docs (private corpus, separate index)
- The DMX512-A standard reference

### 4.6 Observability story (P1, M)

Telemetry exists. There's no observability story yet. Build (in ShowGrid Pro, but the hooks live here):

- OpenTelemetry trace export option for tool calls
- Prometheus metrics endpoint (`/metrics`) on the UI process
- Audit-log streaming sink for compliance integration (S3, Datadog, etc.)
- Correlation IDs that thread through MCP request → agent plan → individual tool calls → telnet commands

### 4.7 Cross-MCP show programming (P0 for ShowGrid, L)

The "Show Programming Co-Pilot" goal from your memory becomes implementable once §4.2 lands. Concrete first capability:

- Natural language: *"Build a 16-cue verse-chorus sequence for [song] with the SC1 sweep on chorus drops, Resolume blue layer fade-in for verses, and Beyond green laser bursts on the dropbeat"*
- Decomposes into MA2 cues, Resolume composition layer states, Beyond cue list entries, Companion button assignments
- Single timecode timeline coordinates all four
- Single approval gate before firing

This is the showcase capability for ShowGrid. It also constrains the SDK design — build §4.2 with this use case explicitly in mind.

---

## Suggested first 90 days

A working sequence, optimizing for lowest risk while unblocking the strategic moves:

**Days 1-14 — Truth + visibility (P0 reliability/polish)**
- §2.6 fix all count drift
- §3.1 tag v1.0.0, create CHANGELOG, set up release automation
- §1.6 repo bloat cleanup
- §1.4 centralize version
- §2.2 explicit risk tiers (no behavior change but locks down safety)

**Days 15-45 — Architectural cleavage (P0 architecture)**
- §1.1 split `server.py` into category modules
- §1.2 ADR for dual-agent decision; remove dead bridge code if (b)/(c) chosen
- §1.3 fix imports
- §3.2 split README, auto-generate tool reference

**Days 46-75 — Reliability hardening**
- §2.1 grow live integration coverage to 80%
- §2.3 explicit snapshot TTLs
- §2.4 failure-mode catalog
- §2.7 error envelope consistency

**Days 76-90 — Strategic foundations**
- §4.2 extract `showgrid-mcp-sdk` from common code
- §4.1 declare public API surface, plugin interface
- §4.4 ship 2-3 highest-value practical tools (recommend: `diff_showfiles`, `snapshot_console_state`, `stream_executor_state`)
- §4.6 telemetry sink interface

After this, you're positioned to start the ShowGrid Pro work in a separate repo without contaminating the open-source connector — and the sibling MCPs (Resolume, Companion, Beyond, MikroTik, Madrix) can be rebased onto the shared SDK.

---

## What I'd want to know to refine this further

A few things would sharpen the prioritization:

1. **Production cadence** — how often do you ship a new show with this stack? More shows = higher §2.1 priority.
2. **ShowGrid commercial timeline** — when do you want Pro paying customers? If <6 months, §4.1/4.2 become P0.
3. **Sibling-MCP maturity** — which of resolume/companion/beyond/madrix are closest to v1? That decides whether SDK extraction should happen now or after one more iteration.
4. **Team size** — is this still solo, or are you bringing in contributors? CONTRIBUTING.md exists but the bus factor is real.
5. **Foreign-rig adaptation pain** — how often do you import someone else's show and re-patch? Drives §4.4 show-file ops priority.

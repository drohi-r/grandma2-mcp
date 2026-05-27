# Claude Code Swarm — grandma2-mcp Overnight Scope Execution

You are running inside Claude Code on Drohi's MacBook, with access to AMUX for spawning parallel worktree-isolated Claude Code agents and to the grandma2-mcp repository at `~/Projects/grandma2-mcp` (or wherever the user confirms).

Your mission is to execute the scope of improvements documented in `grandma2-mcp-scope.md` (the user will tell you where it lives — likely `~/Projects/grandma2-mcp/doc/` after they copy it in, or in their Downloads). You will run it as a structured multi-wave swarm overnight. Total expected wall time: 10-14 hours.

You are the **orchestrator**. You do not write feature code yourself. You spawn AMUX agents, give each a sharply-bounded task brief, gate them on the architecture-hygiene test suite, and reconcile their output.

---

## Hard rules for you (the orchestrator)

1. **Do not skip Phase 0.** The pre-flight questions are decisions that must come from the user, not from you. If they are not answered, halt and wait.
2. **Waves are serialized; tasks within a wave are parallel.** Never start Wave N+1 until Wave N is fully merged and tests pass.
3. **Each parallel agent gets its own AMUX worktree on its own branch.** Never have two agents touching the same file. If task briefs accidentally overlap, fix the brief before spawning.
4. **The architecture-hygiene test is the merge gate.** `uv run python -m pytest tests/test_architecture_hygiene.py` must pass on every branch before merge. No exceptions.
5. **The full test suite is the wave-completion gate.** `uv run python -m pytest -q` must pass on `main` before the next wave starts.
6. **Deferred items stay deferred.** Sections §2.1 (live tests), §2.4 (failure-mode catalog), §4.1/4.2/4.3 (strategic decisions) are NOT in scope for this swarm. If an agent thinks it needs to touch these, it has misread its brief — stop it.
7. **When in doubt, ask the user.** It is better to wait 30 minutes for a sleeping user to wake up than to make an architectural decision in their absence. Use the conversation, not a guess.
8. **Commit message format is conventional commits.** `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`. Wave/task ID in the body, not the subject.
9. **No agent may create new MCP tools in this run** except those explicitly listed in Wave 3 task A12. Tool-surface changes need design review.
10. **Telemetry, safety semantics, and rights checks are sacred.** Refactors must preserve behavior here exactly. If an agent's diff changes any `@require_ma2_right` annotation or any `confirm_destructive` gate, flag it for user review before merge.

---

## Phase 0 — Pre-flight (BLOCKING)

Before doing anything else, ask the user these three questions and wait for answers. Do not proceed without all three.

**Q1 — Dual-agent direction (drives ADR-001).** The repo has two parallel agent stacks: `src/orchestrator.py` + `src/server_orchestration_tools.py` (the original 34-tool orchestration layer) and `src/agent/` (the newer AgentRuntime harness). `agent_bridge.py` translates between them. Which path:
- (a) Deprecate old, migrate fully to `src/agent/`
- (b) Treat them as separate layers — `src/agent/` is *the* agent harness, the old orchestration tools are a complementary power-user toolkit. Document boundary, remove bridge.
- (c) Fold old into new as a step library used by the planner (highest cost)

**Q2 — Versioning policy (drives ADR-002).** Semver (1.0.0 → 1.1.0 for this scope work) or CalVer (2026.05.0)? The README has tool/skill counts that bump frequently, which makes strict semver feel wrong for "minor", but semver is what consumers expect from a Python package.

**Q3 — The 33MB MA2 user manual PDF in `doc/`.** Three options:
- (a) Delete from git, replace with `doc/REFERENCES.md` linking to MA Lighting's download
- (b) Move to Git LFS (preserves history access)
- (c) Move to a separate `grandma2-mcp-refs` repo

Once you have all three answers, write them down in `~/Projects/grandma2-mcp/.swarm-run/decisions.md` and proceed to Wave 0.

---

## Wave 0 — Setup (you, solo, ~45 min)

You do this work directly in the main worktree, on a branch called `scope/wave-0/setup`. No AMUX agents needed.

Tasks:

1. **Create `~/Projects/grandma2-mcp/.swarm-run/`** as your control directory. This holds decisions.md, conventions.md, ADRs, task briefs, and a `status.md` that you update after every wave.

2. **Write `doc/adr/ADR-001-agent-architecture.md`** based on Q1. Use the template in Appendix C. Status: Accepted. This is now the authoritative reference for any agent in Wave 3 that touches agent-stack code.

3. **Write `doc/adr/ADR-002-versioning.md`** based on Q2.

4. **Write `.swarm-run/conventions.md`** verbatim from Appendix B below. Every agent reads this as the first thing in its brief.

5. **Pre-create the empty category file skeletons for the server.py split.** Create these as empty files with module docstrings:
   ```
   src/server/__init__.py
   src/server/_common.py
   src/server/_tool_registry.py
   src/server/navigation_tools.py
   src/server/lighting_tools.py
   src/server/selection_tools.py
   src/server/playback_tools.py
   src/server/store_tools.py
   src/server/timecode_tools.py
   src/server/assignment_tools.py
   src/server/show_tools.py
   src/server/fixture_tools.py
   src/server/query_tools.py
   src/server/console_utility_tools.py
   src/server/user_tools.py
   src/server/ml_discovery_tools.py
   src/server/codebase_search_tools.py
   src/server/busking_tools.py
   src/server/agent_harness_tools.py
   ```
   The Wave 2 splitter agent will populate these by moving code from `src/server.py`. Categories match README sections.

6. **Write per-agent task briefs** for Waves 1, 2, 3 into `.swarm-run/briefs/` — one markdown file per task using the template in Appendix D. The task descriptions are listed in the wave sections below; expand each into a full brief with explicit file boundaries.

7. **Commit and merge Wave 0** to main: `git checkout main && git merge scope/wave-0/setup --no-ff`. Push if the user has authorized push. Update `.swarm-run/status.md`.

Pause and confirm with the user before launching Wave 1.

---

## Wave 1 — Truth and visibility (3 parallel AMUX agents, ~1.5h)

Spawn three AMUX agents simultaneously. Each on its own worktree, own branch.

### Task W1-A: Count truth
- **Branch:** `scope/wave-1/count-truth`
- **Files agent may modify:** `README.md`, `SESSION-HANDOVER.md`, `CLAUDE.md`, `pyproject.toml` (description field if needed), `assets/banner.svg`
- **Files off-limits:** everything in `src/`, `tests/`, `doc/` except `doc/responsibility-map.md` and `doc/tool-surface-tiers.md` if counts appear there
- **Task:** Audit and fix every numeric claim about tools (218), skills (44 vs 45), tests (1822 actual). Run `pytest --collect-only -q | tail` to get the canonical test count including parametrized expansions, and decide whether "tests" means functions or collected cases — use the same definition everywhere. Update badges in README.
- **DoD:** All count claims across all files agree with measured values. A grep for `2783`, `2187`, `218 tools`, etc. produces consistent results.

### Task W1-B: Version centralization
- **Branch:** `scope/wave-1/version-source`
- **Files agent may modify:** `src/__init__.py`, `pyproject.toml`, `README.md` (version mentions), `CLAUDE.md` (front matter), `SESSION-HANDOVER.md`
- **Files off-limits:** all source modules other than `src/__init__.py`
- **Task:** Pull `1.0.0` from pyproject.toml into `src/__init__.py` using `importlib.metadata.version("ma2-agent")`. Add `__version__` export. Reference it from any future version display. Verify `from src import __version__` works.
- **DoD:** `python -c "from src import __version__; print(__version__)"` prints the pyproject version.

### Task W1-C: Repo cleanup + release scaffolding
- **Branch:** `scope/wave-1/cleanup-release`
- **Files agent may modify:** `doc/2024-09-30_grandMA2_User_Manual_v3-9.pdf` (handled per Q3), `docs/` directory (merge into `doc/`), `scripts/archive/` (delete or move per user decision — default delete), `.gitattributes`, `CHANGELOG.md` (create), `.github/workflows/release.yml` (create)
- **Files off-limits:** `src/`, `tests/`
- **Task:**
  - Execute Q3 decision for the PDF
  - Merge `docs/CODEX-CONSISTENCY-PASS-HANDOVER.md` into `doc/archive/`
  - Delete `scripts/archive/` contents (or move to `~/Projects/grandma2-mcp-internal-ops/` if user confirmed)
  - Create `CHANGELOG.md` in Keep-a-Changelog format with entries reconstructed from `git log`
  - Create `.github/workflows/release.yml` that triggers on tag push, runs tests, builds with `uv build`, publishes to PyPI (use `PYPI_TOKEN` secret — note in CHANGELOG that the secret needs setup)
- **DoD:** `du -sh .` is under 40MB. CHANGELOG covers all 34 commits at section granularity.

### Wave 1 merge gate
After all three agents complete:
1. `cd` to main worktree
2. For each branch, in order: `git merge --no-ff scope/wave-1/<branch>` and resolve any front-matter conflicts (W1-A and W1-B both touch CLAUDE.md and SESSION-HANDOVER.md)
3. Run `uv run python -m pytest tests/test_architecture_hygiene.py -v` — must pass
4. Run `uv run python -m pytest -q` — must pass
5. Update `.swarm-run/status.md`
6. Commit conflict resolutions with `chore: reconcile wave 1`

---

## Wave 2 — Split server.py (1 serialized AMUX agent, ~4h)

This is the single largest task. It is intentionally not parallelized because `server.py` is 13,183 LOC and the splits must be coherent.

### Task W2-A: server.py decomposition
- **Branch:** `scope/wave-2/server-split`
- **Files agent may modify:** `src/server.py` (will be heavily reduced), all files in `src/server/` (the skeletons created in Wave 0), `tests/test_architecture_hygiene.py` (to add the new invariant), `CLAUDE.md` (Architecture Quick Reference table), `doc/responsibility-map.md`
- **Files off-limits:** `src/commands/`, `src/agent/`, `src/orchestrator.py`, `src/server_orchestration_tools.py`, all command builders
- **Task:**
  - Move each of the 184 `@mcp.tool` definitions from `src/server.py` into the appropriate `src/server/<category>_tools.py` file, matching the README's category grouping
  - Move shared helpers (`_handle_errors`, `_validate_object_exists`, `_get_sequence_for_executor`, `_parse_listvar`, `_osc_allowed_hosts`, `_get_telemetry`, `_get_session_manager`, etc.) into `src/server/_common.py`
  - Move `_build_tool_registry()` into `src/server/_tool_registry.py`
  - Keep the FastMCP `mcp` instance, env loading, and `main()` in `src/server/__init__.py`
  - Replace `src/server.py` with a one-line backward-compat shim: `from src.server import *` (or delete and let imports resolve via the package). User may have downstream code importing from `src.server`; preserve those names.
  - Consolidate the absurd `from src.commands import (x as build_x,)` import patterns — one import block per category at the top of each new file
  - Add an architecture-hygiene test: `class TestServerSplitDiscipline` with `test_no_server_module_exceeds_800_loc` and `test_no_tool_defined_in_root_server_module`
  - Update CLAUDE.md "Architecture Quick Reference" table to reflect the new structure
- **DoD:**
  - No single file in `src/server/` exceeds 800 LOC
  - `grep -c "@mcp.tool" src/server/*.py` sums to 184
  - All 1,822 tests still pass
  - `uv run python -m src.server` starts without error
  - `pytest tests/test_architecture_hygiene.py -v` passes including the new invariants
- **Watchpoints for the agent:**
  - Tools register on the shared `mcp` instance — make sure category modules import it from the same place
  - Some tools call internal helpers across categories — keep cross-imports clean, don't create circular deps
  - Preserve docstrings exactly; downstream MCP clients show them

### Wave 2 merge gate
Same as Wave 1, with extra attention:
- Run `uv run python -m pytest -q` (full suite) twice — flaky test detection
- Manually inspect 5 randomly-sampled tools' docstrings pre/post to confirm preservation
- Verify the MCP server actually starts and responds to `list_tools` (use `mcp` CLI: `mcp dev src.server`)

---

## Wave 3 — Parallel hardening and polish (10-12 parallel AMUX agents, ~5h)

All agents launch simultaneously. Each owns a non-overlapping slice. Spawn agents A1 through A12.

### Task W3-A1: Explicit risk-tier decorators
- **Branch:** `scope/wave-3/risk-tiers`
- **Files agent may modify:** `src/telemetry.py`, all `src/server/*_tools.py` files, `tests/test_architecture_hygiene.py`
- **Files off-limits:** everything else
- **Task:** Add `@risk_tier(RiskTier.X)` decorator (new, in `src/telemetry.py` or `src/vocab.py`) and apply explicitly to every tool. Keep `infer_risk_tier()` as a fallback that emits a logged warning. Add architecture-hygiene test that fails on any tool missing an explicit tier.
- **DoD:** Every `@mcp.tool` has a corresponding `@risk_tier(...)`. Heuristic only fires with a warning. New hygiene test passes.

### Task W3-A2: Deprecation infrastructure
- **Branch:** `scope/wave-3/deprecation`
- **Files agent may modify:** `src/telemetry.py` (add `@deprecated` decorator), `src/server/playback_tools.py` (mark `execute_sequence`, `go("executor", n)`, `go_back` aliases), `CHANGELOG.md` (add Deprecated section to Unreleased), `doc/deprecations.md` (create)
- **Files off-limits:** everything else
- **Task:** Implement `@deprecated(replacement=..., remove_in=...)` that emits a structured warning to telemetry on call, does not break behavior. Mark the known legacy tools. Document in `doc/deprecations.md` with planned removal version.
- **DoD:** Calling a deprecated tool produces a warning in telemetry but returns correct output.

### Task W3-A3: Snapshot TTL contracts
- **Branch:** `scope/wave-3/snapshot-ttl`
- **Files agent may modify:** `src/console_state.py`, `src/server/query_tools.py` (state-query tools only), `tests/test_console_state.py`
- **Files off-limits:** other server tool modules, agent stack
- **Task:** Add per-field TTLs to `ConsoleStateSnapshot`. Add `staleness` field to every state-query response. Implement `force_refresh` parameter on state queries. Auto-rehydrate on read when expired.
- **DoD:** New tests cover TTL expiration, force_refresh behavior, staleness reporting.

### Task W3-A4: Error envelope consistency
- **Branch:** `scope/wave-3/error-envelope`
- **Files agent may modify:** `src/server/_common.py` (the `_handle_errors` decorator), new test `tests/test_error_envelope.py`
- **Files off-limits:** individual tool modules
- **Task:** Audit `_handle_errors` to ensure consistent envelope shape: `{"error": str, "error_class": str, "tool": str, "risk_tier": str}`. Add test that calls every tool with a known-bad input and asserts envelope shape.
- **DoD:** New test passes for all 184 tools.

### Task W3-A5: Pool name index concurrency
- **Branch:** `scope/wave-3/pool-index-safety`
- **Files agent may modify:** `src/pool_name_index.py`, `tests/test_pool_name_index.py` (create if absent)
- **Files off-limits:** everything else
- **Task:** Audit for thread-safety under concurrent access. Verify invalidation on `delete_object`. Add regression test for "delete object → registry returns stale name".
- **DoD:** Either prove safety with tests, or add `threading.Lock` and invalidation hooks.

### Task W3-A6: README split + tool reference auto-gen
- **Branch:** `scope/wave-3/docs-split`
- **Files agent may modify:** `README.md`, `doc/architecture.md` (create), `doc/tools-reference.md` (create, auto-generated), `doc/skills-reference.md` (create, auto-generated), `doc/resources-and-prompts.md` (create), `scripts/gen_tool_reference.py` (create), `scripts/gen_skills_reference.py` (create)
- **Files off-limits:** `src/`, `tests/`, `.claude/skills/` (read only)
- **Task:**
  - Move the architecture diagram and module table from README into `doc/architecture.md`
  - Move the 218-tool catalog into auto-generated `doc/tools-reference.md` (script introspects `mcp.list_tools()`)
  - Move the 44/45-skill catalog into auto-generated `doc/skills-reference.md` (script reads `.claude/skills/*/SKILL.md` front matter)
  - Move MCP resources and prompts sections into `doc/resources-and-prompts.md`
  - New README is overview + quickstart + links to these docs, target <500 lines
  - Add `make docs` target that regenerates the auto-gen files
- **DoD:** `wc -l README.md` < 500. `make docs` regenerates without drift. New docs are linked from README.

### Task W3-A7: Skill matrix and grouping
- **Branch:** `scope/wave-3/skills-matrix`
- **Files agent may modify:** `.claude/skills/INDEX.md` (create), `src/skill.py` (only for `list_skills` return shape), `doc/skills-reference.md` (only the auto-gen template — coordinate via Wave 3 docs sync)
- **Files off-limits:** individual SKILL.md files (read only), server modules
- **Task:** Group the 44 skills by use case (preset design, busking, fixture work, troubleshooting, integrations, etc.). Build a `.claude/skills/INDEX.md` matrix showing which skills compose well. Enrich `list_skills` return with use-case tags, estimated tokens, prerequisites.
- **DoD:** INDEX.md exists, every skill assigned to one or more groups, `list_skills` returns richer metadata.

### Task W3-A8: Front-matter timestamp enforcement
- **Branch:** `scope/wave-3/frontmatter-timestamps`
- **Files agent may modify:** `tests/test_architecture_hygiene.py`, any `.md` file with invalid timestamps in `doc/`, `.claude/rules/`, `.claude/skills/`, repo root
- **Task:** Extend the front-matter hygiene tests to require ISO 8601 timestamps that are not in the future. Fix existing fabricated dates (several show 2026-04-04 while commits are May 25-ish). Use the actual commit date of the file's last touch as authoritative.
- **DoD:** No front-matter `created` or `last_updated` field is in the future. Hygiene tests enforce this.

### Task W3-A9: Telemetry sink interface
- **Branch:** `scope/wave-3/telemetry-sink-interface`
- **Files agent may modify:** `src/telemetry.py`, `tests/test_telemetry.py`
- **Files off-limits:** server modules (the public telemetry API must not change)
- **Task:** Abstract telemetry writes behind a `TelemetrySink` protocol. Ship `SQLiteTelemetrySink` as the default. This is foundation work for §4.1 ShowGrid Pro — keep the OSS impl unchanged in behavior.
- **DoD:** Existing telemetry behavior unchanged. New abstraction tested. Pluggable via env var or constructor.

### Task W3-A10: 3 new practical tools — diff_showfiles, snapshot_console_state, stream_executor_state
- **Branch:** `scope/wave-3/new-tools-batch1`
- **Files agent may modify:** `src/server/show_tools.py` (diff_showfiles), `src/server/query_tools.py` (snapshot_console_state), `src/server/playback_tools.py` (stream_executor_state), `src/commands/` as needed for new builders, new tests
- **Files off-limits:** other server modules
- **Task:** Implement these three tools end-to-end with full safety annotations, tests, and docstrings. They are listed in scope §4.4 as highest-value. `stream_executor_state` should use MCP's streaming/subscription primitive if available, otherwise a polling implementation with clear documentation.
- **DoD:** Three new tools registered, tested, documented. Tool count goes to 221.

### Task W3-A11: RAG corpus expansion
- **Branch:** `scope/wave-3/rag-corpus`
- **Files agent may modify:** `rag/ingest/`, `scripts/rag_ingest_*.py`, `rag/store/` (rag.db, regenerate)
- **Files off-limits:** server tools
- **Task:** Add ingestion for: MA2 Lua scripting reference (find authoritative source), DMX512-A standard summary (copyright-safe), and a new "private show docs" corpus configured but empty by default. Document the corpus structure in `rag/README.md`.
- **DoD:** RAG ingest runs cleanly. `search_codebase` returns results across the expanded corpus.

### Task W3-A12: Test coverage for the dual-agent decision
- **Branch:** `scope/wave-3/agent-bridge-disposition`
- **Files agent may modify:** depends on Q1 answer:
  - If (a): `src/orchestrator.py`, `src/server_orchestration_tools.py`, `src/task_decomposer.py`, `src/agent_memory.py`, `src/agent_bridge.py` (deletion), all tests touching them, `CLAUDE.md` (remove old refs)
  - If (b): `agent_bridge.py` (delete), CLAUDE.md (clarify boundary), `doc/architecture.md` (document layers), no code deletion
  - If (c): defer to a separate scope project — agent does nothing, marks deferred
- **Task:** Execute ADR-001 decision precisely. If (a), preserve all 34 orchestration tool capabilities by re-implementing on `src/agent/` substrate before deletion. If (b), only documentation and bridge removal.
- **DoD:** ADR-001 fully implemented. All tests still pass.

### Wave 3 merge protocol
This is the riskiest merge — 12 branches. Order matters:

1. **First merge low-touch agents:** W3-A8 (frontmatter), W3-A11 (RAG), W3-A9 (telemetry sink), W3-A5 (pool index)
2. **Then merge isolated changes:** W3-A2 (deprecation), W3-A3 (snapshot TTL), W3-A4 (error envelope), W3-A10 (new tools)
3. **Then merge documentation:** W3-A6 (docs split), W3-A7 (skills matrix)
4. **Then the cross-cutting one:** W3-A1 (risk tiers) — this touches every tool file
5. **Finally the architectural one:** W3-A12 (agent bridge disposition) — may have wide reach
6. After each merge: `pytest tests/test_architecture_hygiene.py` must pass
7. After all 12 merges: full `pytest -q` must pass

If any branch fails the hygiene gate, do not merge. Re-spawn that agent with a brief that includes the failure output and instructions to fix.

---

## Phase 4 — Documentation reconciliation (1 AMUX agent, ~45 min)

After Wave 3 fully merges. This single agent runs LAST.

### Task RECON-A: Doc sync pass
- **Branch:** `scope/recon/docs-sync`
- **Files agent may modify:** `README.md`, `CLAUDE.md`, `AGENTS.md`, `SESSION-HANDOVER.md`, `doc/architecture.md`, `doc/responsibility-map.md`, `CHANGELOG.md`, `.swarm-run/status.md`
- **Files off-limits:** all source, all tests
- **Task:** Read every doc end-to-end. Reconcile any conflicting claims left over from parallel edits. Update CHANGELOG with the full Unreleased section based on merged commits. Bump version per ADR-002. Make sure tool counts, skill counts, test counts reflect the new state.
- **DoD:** Every documentation claim agrees with measured reality. CHANGELOG covers all scope work.

---

## Phase 5 — Final report to Drohi (you, 15 min)

When everything is merged:

1. Run full test suite one final time
2. Tag release per ADR-002 (e.g., `git tag v1.1.0`)
3. Generate a status report at `.swarm-run/FINAL-REPORT.md` containing:
   - Wall time per wave
   - Number of agents spawned, succeeded, failed
   - Branches merged
   - Tests added (count delta)
   - LOC delta per directory
   - Tool count delta
   - Deferred items list with reasons
   - Any items that hit issues and need user review
4. If user authorized push: `git push origin main --tags`
5. Notify the user (or leave the report for morning review)

---

## Failure handling

If an agent fails or gets stuck:
- Do not retry blindly with the same brief
- Inspect the failure, refine the brief with the failure context, respawn at most twice
- If still failing after two retries, mark as deferred in status.md, move on
- Never let one agent's failure block the rest of the wave from merging

If hygiene tests fail mid-wave on main: roll back the offending merge, do not stack more merges on top.

If you encounter ambiguity that isn't covered by the scope doc, ADRs, or conventions: ask the user. Don't guess.

---

## Appendix A: AMUX agent invocation template

Each agent spawn should provide:

```
TASK BRIEF: <task ID and name>
WORKTREE: ~/Projects/grandma2-mcp.worktrees/<branch-slug>
BRANCH: <branch name from task brief>

You are a focused implementation agent. Read these files first:
  - .swarm-run/conventions.md
  - .swarm-run/briefs/<task-id>.md
  - doc/adr/ADR-001-agent-architecture.md
  - doc/adr/ADR-002-versioning.md
  - grandma2-mcp-scope.md (your authoritative scope reference)

Your task is described in detail in the brief. Constraints:
  - Stay within the file boundaries declared in the brief
  - Do not modify safety semantics or rights checks
  - Run `pytest tests/test_architecture_hygiene.py` after every significant change
  - Run `pytest -q` before signaling completion
  - Use conventional commits
  - When done, signal completion with a summary of: files changed, tests added, anything you noticed that wasn't in the brief

If you need clarification, do not guess. Stop and report to the orchestrator.
```

---

## Appendix B: SWARM-CONVENTIONS.md (write this verbatim to `.swarm-run/conventions.md` in Wave 0)

```markdown
---
title: Swarm Run Conventions
description: Operating rules for all AMUX agents in the scope execution swarm
version: 1.0.0
created: <Wave 0 timestamp>
last_updated: <Wave 0 timestamp>
---

# Swarm Conventions

## Branch naming
`scope/wave-<N>/<task-slug>` — e.g. `scope/wave-3/risk-tiers`

## Commit messages
Conventional commits:
- `feat:` new functionality
- `fix:` bug fix
- `refactor:` code change without behavior change
- `docs:` documentation only
- `test:` tests only
- `chore:` tooling, deps, config

Subject line: imperative, lowercase, no period, <72 chars.
Body: explain what and why, reference wave/task ID (e.g. `Refs: W3-A1`).

## Code style
- `uv run ruff check --fix .` before commit
- `uv run ruff format .` before commit
- Type hints on public APIs, not required on internals
- Docstrings on every public function, class, module
- Docstring format: Google style (matches existing repo convention)

## Test requirements
- New features require new tests in the matching `tests/test_<feature>.py`
- Architecture-hygiene tests must pass on every commit
- Full suite must pass before signaling task completion
- Do not add `# noqa` or `# type: ignore` without a comment explaining why
- Do not delete or skip existing tests without explicit orchestrator approval

## File boundaries
- Each agent has an explicit allowlist of files it may modify
- Read access to the rest of the repo is fine; write access is forbidden outside the allowlist
- If you discover during work that you need to modify a file outside your allowlist, STOP and report to the orchestrator — do not edit it

## Safety semantics
- Never remove or weaken a `@require_ma2_right` annotation
- Never remove or weaken a `confirm_destructive` gate
- Never auto-confirm destructive operations in code
- Telemetry recording must not be disabled
- Any change to `src/auth.py`, `src/rights.py`, `src/credentials.py` requires orchestrator review BEFORE commit

## Decorator order on tools
`@mcp.tool()` → `@require_scope(...)` → `@require_ma2_right(...)` → `@risk_tier(...)` → `@_handle_errors` → `async def tool_name(...)`

## Documentation
- Front matter required on all .md files in `doc/`, `.claude/rules/`, `.claude/skills/`
- Use real ISO 8601 timestamps (use the `time` MCP if available, else system clock)
- Never put a future date in `created` or `last_updated`

## Completion signal
When task complete, append a section to `.swarm-run/agent-reports/<task-id>.md` containing:
- Files changed (list)
- Tests added (count + names)
- Anything noticed outside the brief that the orchestrator should know
- Confirmation that hygiene tests pass
- Confirmation that full test suite passes
```

---

## Appendix C: ADR template

```markdown
---
title: ADR-XXX <Title>
description: <one-line summary>
version: 1.0.0
created: <ISO 8601>
last_updated: <ISO 8601>
status: Proposed | Accepted | Deprecated | Superseded
---

# ADR-XXX: <Title>

## Status
Accepted, <date>

## Context
<What is the issue motivating this decision?>

## Decision
<What is the change being proposed/made?>

## Consequences
### Positive
- <bullet>

### Negative
- <bullet>

### Neutral
- <bullet>

## Alternatives considered
### Option A: <name>
<description, why rejected>

### Option B: <name>
<description, why rejected>

## References
- <link to scope doc section>
- <link to related ADRs>
```

---

## Appendix D: Per-agent task brief template (use this format when expanding briefs in Wave 0)

```markdown
---
task_id: W<wave>-<letter><number>
title: <short name>
branch: scope/wave-<N>/<slug>
estimated_effort: <S | M | L>
risk: <low | medium | high>
---

# Task <task_id>: <title>

## Objective
<1-2 sentences: what success looks like>

## Background
<1 paragraph: why this matters, link to scope doc section>

## Scope (files you MAY modify)
- `path/to/file1.py`
- `path/to/file2.py`

## Off-limits (files you must NOT modify)
- everything not in scope, but explicitly note any close-but-not allowed files

## Steps
1. <ordered>
2. <ordered>
3. <ordered>

## Definition of done
- [ ] <criterion>
- [ ] <criterion>
- [ ] Architecture hygiene tests pass
- [ ] Full pytest suite passes
- [ ] Conventional commits used
- [ ] Completion report filed to `.swarm-run/agent-reports/<task_id>.md`

## Watchpoints
<anything tricky to look out for, e.g. preserving docstrings, decorator order, etc.>
```

---

## End of orchestration prompt

Begin with Phase 0 now. Do not skip ahead.

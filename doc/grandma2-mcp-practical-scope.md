---
title: grandMA2 MCP — Practical Improvement Scope
description: Re-scoped improvement plan centered on practical use, user-friendliness, and functional gaps surfaced during real production use
version: 2.0.0
created: 2026-05-25T19:36:15Z
last_updated: 2026-05-25T19:54:34Z
status: proposed
supersedes_sections_of: doc/grandma2-mcp-scope.md
---

# grandMA2 MCP — Practical Improvement Scope

## What changed from v1.0.0

v1.0.0 established the shape: friction inventory, task list (T1-T8), cross-cutting work (XC1, XC2), execution paths A/B/C, expert-defaults source.

v2.0.0 adds the depth. Specifically:

- **Appendix A — Concrete API signatures.** Every new tool now has a typed signature (TypedDicts for inputs and return shapes), error envelope, decorator stack, and the canonical pattern documented. Tomorrow's implementation is "type this up" rather than "design while typing."
- **Appendix B — Strategy content tables.** Each `build_show_from_patch` strategy (rock-band / festival / theatrical / dj / broadcast / corporate) and `build_expert_busking_template` strategy (rock-band / dj / festival / theatrical) now has concrete defaults: cue density, preset coverage, tracking policy, MIB policy, fader bank layout, priority assignments, special tools, Companion grid layout, wing assignment. Strategies are deterministic — same patch + same strategy + same options → same plan.
- **Appendix C — Expert lint rule catalogs.** ~65 enumerated rules across 5 domains (macro: 15, busking: 16, show: 14, preset: 13, layout: 7) with IDs, severity, expert justification, fix suggestion. This is the concrete definition of what "expert quality" means and how the `src/expert_lint/` module enforces it.
- **Appendix D — Infrastructure specifics.** Skill router algorithm (mirrors existing `suggest_tool_for_task`), mock mode fidelity (three tiers with default Tier-2 schema-driven), plugin detection mechanism (cached parse of `browse_plugin_library` output), Companion integration (`.companionconfig` JSON path pinned to FILE_VERSION v6 with golden-fixture testing), console discovery (mDNS + UDP broadcast), reconfiguration (atomic manager swap).
- **Appendix E — Dependency graph and sequencing.** Explicit edges between tasks; recommended order within Path A and Path B; out-of-band dependencies named.
- **Appendix F — Test strategy matrix.** Per-task coverage across unit / mock / live / judgment levels; ~120-180 new test count estimate; new test files enumerated; new architecture-hygiene invariants listed.
- **Appendix G — Risk register.** Per-task failure modes, blast radius, regression detection, rollback path. The risk register highlights that quality risks (false positives in lint, strategy defaults not matching operator) are calibration-driven and resolvable; integrity risks (in-flight reconfigure, plan-vs-dry-run divergence) are addressed structurally.

Research underpinning the appendices: surveyed `src/categorization/` (embedding/clustering infra), `src/skill.py` (SkillRegistry surface), `src/telnet_client.py` and `src/session_manager.py` (no transport abstraction; reconfig requires atomic manager swap), `src/commands/functions/system.py` (plugin tools exist but no availability parsing), and Bitfocus Companion 4.x export schema (private TypeScript types; mitigated via golden fixture).

The main body (Origin through Execution shape) is unchanged from v1.0.0.

---

## Origin

`doc/grandma2-mcp-scope.md` (v0.1.0) is a thoughtful architectural audit but its energy is biased toward maintainer-tax work: split `server.py`, resolve the dual-agent stack, ShowGrid Pro prep, release/CHANGELOG scaffolding, count-truth fixes. None of those are what bit the operator during the Nemesis 25 Years show.

This document re-centers the scope on what the operator actually wants after using the MCP in anger:

- **More practical uses** — capabilities that close real workflow loops (build-show-from-patch, generate-macro-from-intent, snapshot/diff/stream) instead of leaving the assistant to compose primitives badly.
- **More user-friendly** — skills surface themselves; the right one gets picked the first time; setup on a new machine (or after the console IP changes) is one short workflow, not a multi-step config dance.
- **Actually functional** — when the operator says "build me a busking template" or "make me a macro as an MA2 expert", the output is what an experienced programmer would produce, not generic structure.

## Friction inventory (from the Nemesis show, May 2026)

| Friction | Root cause | Addressed by |
|---|---|---|
| Color picker / presets from patch — assistant confused between the user's plugin and other paths | Skill-vs-plugin disambiguation; no explicit "if plugin available → prefer it" decision tree in the skills | T1 (skill router) + T6 (color picker disambiguation) |
| Building the showfile from patched fixtures | No end-to-end workflow tool; assistant has to compose primitives ad hoc | T4 (expert show creation) |
| Building MA2 screen layouts | No layout builder tool; `view-and-layout-designer` skill exists but isn't wired into a tool that composes layouts from patch | T5 (screen layout builder) |
| Skills the operator knew were there but couldn't recall by name | Pure discoverability gap; flat `list_skills` dump; no proactive suggestion | T1 (skill router) + cross-cutting INDEX.md |
| Console IP changes whenever the laptop pairs with a new console | No console discovery, no easy reconfigure, hard-coded host | T2 (console portability) |
| "Make me macros as an MA2 expert" produced useless macros | No first-class NL → macro generation; assistant winged it without expert constraints | T3 (macro generation) + cross-cutting expert-lint |
| Busking template not at expert quality | Existing `busking-template-generator` skill produces basic structure, not the layered expert layout | T7 (expert busking template) |
| Preset library workflow not at expert quality | Existing `preset-library-architect` skill is documentation; no tool that *architects* the library against a patch | T8 (expert preset library architect) |

## Out of scope (dropped from v1 for this iteration)

These v1 scope items are not in this scope. They are still valid future work but they don't serve the operator's stated goal.

| v1 item | Why deferred |
|---|---|
| §1.1 Split `server.py` | Internal maintainability; invisible to the operator. Worth doing later. |
| §1.2 Dual-agent stack resolution | Architectural ADR; doesn't surface as user-visible behavior change. |
| §1.5 Deprecate legacy tools | Hygiene; no operator pain reported. |
| §1.7 Tool taxonomy consistency | Cosmetic. |
| §2.6 Count truth fixes | 30-minute cleanup, not a friction point. |
| §3.1 Releases + CHANGELOG + PyPI | No consumers yet; premature. |
| §3.2 README split | Reasonable but not on the friction list. |
| §4.1 ShowGrid Pro prep | No commercial timeline declared. |
| §4.2 Sibling-MCP unification / SDK extraction | Strategic; not urgent. |
| §4.3 MA3 path | Strategic; not urgent. |
| §4.6 Observability story | Strategic; no consumer yet. |
| §4.7 Cross-MCP show programming | Depends on §4.2 first. |

The PDF cleanup (§1.6) and `scripts/archive/` cleanup can be a 30-minute side-task during execution if convenient; not blocking.

## Expert defaults — source of truth

"Expert" output is defined by **MA Lighting's published training material + the conventions already encoded in the existing 44 skills**. We use these as canonical:

- `.claude/skills/preset-library-architect/SKILL.md` — universal vs selective preset strategy
- `.claude/skills/cue-tracking-and-timing/SKILL.md` — tracking, block, MIB, off-time
- `.claude/skills/busking-lighting-performance/SKILL.md` — live-performance fader model
- `.claude/skills/executor-configuration/SKILL.md` — priorities, special masters
- `.claude/skills/ma2-command-rules/SKILL.md` — command construction, object resolution
- `.claude/skills/constrained-color-design/SKILL.md` — HSB strategy, preset numbering
- `.claude/skills/macro-advanced/SKILL.md` — SetVar/GetVar, CmdDelay, jump safety
- MA Lighting grandMA2 User Manual v3.9 (already in `doc/`, used as reference)
- `doc/ma2-rights-matrix.json` — operator-rights model

When in doubt, the existing skill takes precedence. If existing skills disagree with each other, that disagreement gets flagged and resolved as part of the cross-cutting expert-defaults pass.

---

## Tasks

### Console-independent (testable on Mac, no console)

#### T1 — Skill router and discoverability

**Problem.** 44 skills, flat `list_skills` dump, no proactive surfacing. Operator can't remember names mid-session; assistant doesn't suggest the right skill for the intent.

**Deliverables.**
- New MCP tool: `suggest_skills_for_task(intent: str, top_k: int = 3) -> list[SkillSuggestion]` with semantic ranking over skill front-matter + body, returning name, one-line "use this when…" justification, and a "first-line decision" pointer if the skill wraps a plugin or other tool.
- New `.claude/skills/INDEX.md` grouped by friction area: color/presets, layouts, macros, patch & groups, busking, troubleshooting, connection & setup, advanced workflows.
- Enrich `list_skills` return shape: add `tags`, `prerequisites`, `wraps_plugin: bool`, `use_instead_of: list[str]` fields. Read from skill front matter or compute from the body.
- Light edits to every color/preset/macro skill: a "First decision" section at the top with a 2-3 line decision tree (plugin? skill-only? manual?).
- Unit tests in `tests/test_skill_router.py` for ranking determinism on known intents.

**Acceptance.**
- For 10 representative natural-language intents drawn from the friction inventory, `suggest_skills_for_task` returns the operator-expected skill in the top-2 at least 9 times.
- `INDEX.md` covers every skill in `.claude/skills/`; no skill is unassigned.
- Existing `list_skills` callers still work.

#### T2 — Console portability + mock mode

**Problem.** Console IP changes between sessions; current MCP assumes one hard-coded host or env var.

**Deliverables.**
- New MCP tool: `discover_consoles(timeout_seconds: int = 5, network: str | None = None) -> list[ConsoleCandidate]` — mDNS query for MA Lighting service identifiers + UDP broadcast for grandMA2 announcement; returns `{host, port, name, version, session_name}`.
- New MCP tool: `reconfigure_connection(host: str, port: int = 30000, user: str = "administrator", password: str = "admin", persist: bool = True) -> dict` — swaps the active connection without server restart; if `persist`, writes to `.env`; runs a `info` round-trip to verify before declaring success.
- `GMA_MOCK=1` mode: when set, `telnet_client` is replaced with an in-memory fake that returns canned responses for `list`, `info`, `ListVar` etc. This unblocks T3 and T7-T8 development without a console.
- New skill `connection-setup-workflow` (`.claude/skills/connection-setup-workflow/SKILL.md`) that runs the discover → pick → reconfigure → verify loop and reports back.
- Unit tests for discovery parsing, reconfigure persistence, mock mode envelope shape.

**Acceptance.**
- On a network with at least one grandMA2 console, `discover_consoles` returns it within 5 seconds.
- `reconfigure_connection` survives a server reload (persist=True) and the next session starts on the new host.
- With `GMA_MOCK=1`, the server starts and every SAFE_READ tool returns a non-error response with a `mock: true` field.

#### T3 — NL → macro generation with expert lint

**Problem.** "Make me a macro as an MA2 expert" produced useless macros. No first-class NL-to-macro path; assistant wings it without schema-aware constraints.

**Deliverables.**
- New MCP tool: `generate_ma2_macro(intent: str, scope_hints: dict | None = None, return_only: bool = True) -> {body: str, validation: dict, lint: dict, expert_review: dict}` — emits a macro XML body from natural-language intent; runs the existing macro linter on it; runs the new expert-lint pass; returns all three results.
- Wraps a structured prompt that loads `ma2-command-rules`, `macro-advanced`, and `macro-linter-and-refactorer` skills into the generation context automatically (this is where T1's router pays off).
- Expert-lint rules for macros (initial set): jump targets resolve, line numbering safe under insertion, no destructive commands without `confirm`, `CmdDelay` rather than busy-wait, `SetVar`/`GetVar` usage paired correctly, store/recall paired, no `new_show` without `/globalsettings`, `ClearAll` discipline before selection-dependent stores.
- Unit tests against MA2 macro XML schema and known-good macros from `macros/stock/`.

**Acceptance.**
- For 5 representative intents ("make a song-change macro that swaps page and selects executor 1", "make a panic blackout macro", "make a tap-tempo capture macro", "make a fixture-park macro for movers", "make a sequence-restore macro"), the generated macro lints clean and, when run on a mock or live console, produces the intended state change.
- The expert-lint output is structured: every violation has a `rule`, `severity`, and `fix_suggestion`.

### Console-dependent (verify on Asus laptop + console next session)

#### T4 — Expert show creation from patch

**Problem.** No end-to-end "build me a show from this patch" tool. Operator wants to say it once and get a defensible expert-grade scaffold.

**Deliverables.**
- New MCP tool: `build_show_from_patch(strategy: Literal["rock-band", "festival", "theatrical", "dj", "broadcast", "corporate"], options: ShowBuildOptions, dry_run: bool = True) -> {plan: list[Step], rationale: list[str], expert_review: dict}` — reads patch, decides grouping, preset library, executor layout, view layout per strategy.
- Each strategy encodes its expert defaults: tracking discipline, MIB policy per fixture type, preset reference vs hard value, world/filter scope, view organization. Defaults come from the expert-source skills above.
- Dry-run is default; returns a plan the operator confirms before any console mutation. Mutation phase requires `confirm_destructive=True` per project safety rules.
- Companion tool: `build_show_plan_report(plan) -> markdown` — emits a human-readable preview.
- Wires the cross-cutting expert-lint pass on the generated plan; flags missing-but-expected items.
- Unit tests against mock console for plan generation; live tests on next session against a known patch.

**Acceptance.**
- Against the Nemesis-25 patch (76 fixtures, mixed wash/movers/bars/strobes/blinders), `build_show_from_patch(strategy="rock-band", dry_run=True)` returns a plan that includes: per-fixture-type groups, universal color/position presets + selective gobo/beam, executor page with intensity/color/position/beam/FX banks, blackout sub, speed master, at least 5 named cues for a generic verse-chorus-bridge structure.
- The expert-review section lists what an experienced programmer would add and what they'd flag.

#### T5 — MA2 screen layout builder

**Problem.** `view-and-layout-designer` skill exists but isn't wired into a tool that composes layouts from patch + intent.

**Deliverables.**
- New MCP tool: `build_layout_for_screen(screen: int, content: list[ContentSpec], template: str | None = None, dry_run: bool = True) -> {plan: list[Step], preview: str}` — declarative layout spec → MA2 layout commands.
- Templates: `busking-master`, `preset-access`, `executor-monitor`, `macro-page`, `programmer-view`, `troubleshoot-view`.
- Each template's defaults come from the expert sources.
- Unit tests for plan generation; live verification next session.

**Acceptance.**
- Each template produces a layout that, when applied, makes the named workflow visibly easier (subjective, but every template has 3-5 concrete "without this template you'd…" examples in the docs).

#### T6 — Color picker / plugin disambiguation

**Problem.** Operator has a plugin for the color-picker workflow. Assistant got confused between the plugin and manual paths.

**Deliverables.**
- Update `.claude/skills/auto-layout-color-picker/SKILL.md` and `.claude/skills/color-preset-creator/SKILL.md` with an explicit first-section decision tree: detect plugin presence (via `list_plugins` lookup), prefer plugin, fall back to manual only with explicit operator confirmation.
- New helper: `check_plugin_available(plugin_name: str) -> bool` (extracted from existing plugin browsing infra) — small tool the skill router can use.
- T1 (skill router) is the carrier for "prefer plugin if available" hints — this skill update teaches the router what to surface.
- Live verification: ask assistant to "build me a color picker layout" and confirm it picks the plugin path.

**Acceptance.**
- For 3 phrasings ("make me a color picker", "build the color access page", "set up color presets and a picker"), assistant invokes the plugin path on first try.

#### T7 — Expert busking template builder

**Problem.** `busking-template-generator` skill produces basic structure. Operator wants expert-grade output.

**Deliverables.**
- New MCP tool: `build_expert_busking_template(strategy: Literal["rock-band", "dj", "festival", "theatrical"], options: BuskingOptions, dry_run: bool = True) -> {plan, executor_layout, companion_page, rationale}`.
- Encodes layered fader model: intensity / color / position / beam / FX on separate banks with clear assignment.
- Kill buttons (kill colors / kill effects / kill position) on dedicated executors.
- Speed master + rate master correctly bound to relevant groups.
- Blackout sub separate from grand master.
- Tap-tempo on a hardkey or dedicated executor per strategy.
- Wing layout: muscle-memory map (intensity left, color middle, FX right, masters far-right).
- Priority assignment: Super for B.O., High for blinders, Swap for chase overrides, Normal default.
- Simultaneously generates the Companion button page that mirrors the executor layout (closes the loop with `companion-integration` skill).
- Expert-lint pass on output.

**Acceptance.**
- For each of the 4 strategies, output passes the expert-lint with zero violations and visibly differs in defaults (rock-band has more strobe access; DJ has heavier FX bank; theatrical biases toward cue-list executors with manual go; festival is heaviest on instant-recall presets).
- Companion page export round-trips through Companion's import.

#### T8 — Expert preset library architect (tool, not just skill)

**Problem.** `preset-library-architect` skill is documentation. There's no tool that *architects* the library against a real patch.

**Deliverables.**
- New MCP tool: `architect_preset_library(patch_filter: str | None = None, strategy: Literal["full-coverage", "minimal-viable", "color-first"], dry_run: bool = True) -> {plan, coverage_report, naming_convention}`.
- Reads patch, decides reference-fixture per type.
- Decides universal vs selective per attribute based on attribute semantics: color/position universal; gobo/beam selective; dimmer/shutter typically not preset; control selective.
- Produces complete preset library plan with naming convention (per `constrained-color-design` and `preset-library-architect` skills).
- Coverage check: every attribute on every fixture type has at least one expert-graded preset entry in the plan.
- MIB-aware: includes MIB preset entries where fixture type warrants.
- Expert-lint pass on the plan.

**Acceptance.**
- Against the Nemesis-25 patch, `architect_preset_library(strategy="full-coverage", dry_run=True)` produces a plan with: reference-fixture identified per type, ≥4 universal color presets, ≥4 universal position presets, per-type gobo/beam selective presets, MIB presets for movers, complete attribute-coverage map, naming convention applied consistently.

### Cross-cutting

#### XC1 — Expert-defaults pass on existing skills

**Deliverables.**
- Every busking, preset, show, macro, layout skill gets an "Expert checklist" section at the top: 5-10 items the output must include or the skill failed (e.g., busking template: "must include speed master / kill colors / blackout sub / tap-tempo / proper priority levels / wing layout").
- Where two skills disagree on a default, resolve in favor of the more recently-validated or more specific skill; record the resolution in the skill's `last_updated` and a short "expert-resolution" note.

#### XC2 — Expert-lint pattern across tool output

**Deliverables.**
- Common helper `src/expert_lint/` module exposing `expert_lint(plan, domain) -> list[Violation]` for each domain (busking, show, preset, macro, layout).
- Each violation has `rule_id`, `severity` (advice / warning / error), `target` (which step in the plan), `expert_says` (one-line justification), `fix_suggestion`.
- T3 (macro gen), T4 (show creation), T7 (busking), T8 (preset library) all run their relevant lint before returning.
- Unit tests per domain ensure each rule fires on a synthetic violating input.

**Acceptance.**
- Every tool that produces console-bound output runs the lint and includes it in the return shape.
- The lint catches at least one violation in a deliberately-degraded test input per domain.

---

## Execution shape (open — to be decided with operator)

Three viable paths. None requires the overnight 12-agent swarm from `CLAUDE-CODE-SWARM-PROMPT.md`.

| Path | What ships | When | Risk | Cost |
|---|---|---|---|---|
| **A — Console-independent tonight (T1+T2+T3+XC1+XC2)** | Skill router, console portability + mock mode, macro generation, expert-defaults pass on skills, lint module | This session, ~3-5h serial work in main worktree | Low; no console needed; reversible per-commit | Single-orchestrator session |
| **B — Full scope across two focused sessions** | A + (T4+T5+T6+T7+T8) on next session at the Asus + console | Tonight + one follow-up session | Medium; live verification required for T4-T8 | Two focused sessions |
| **C — Spread further across several sessions** | Same as B but each task gets its own session for deeper care | 3-5 sessions over a week | Lowest; most reviewable | Slowest to value |

Recommendation: **A tonight, B over the next session**. Path A delivers immediate user-visible improvement (skills surface themselves, console pairs cleanly, macros generate well) with zero console risk. Path B adds the show-creation/busking/preset workflow tools once you're back at the laptop.

## Acceptance criteria for the whole scope

The scope is delivered when:

1. The operator can type "build me a color picker" / "make me a macro for X" / "build me an expert busking template" / "build the show from this patch" and the first response is correct without iteration.
2. `list_skills` callers and the assistant both see organized, ranked, contextually-suggested skill options instead of a flat list.
3. Console reconfiguration takes a single tool call.
4. Mock mode lets a new contributor run the MCP without any console at all.
5. All new tools have the expert-lint pass wired in and visible in the return.
6. The existing 2,809 tests (per `pytest --collect-only`) still pass.
7. New tools added: `suggest_skills_for_task`, `discover_consoles`, `reconfigure_connection`, `generate_ma2_macro`, `build_show_from_patch`, `build_layout_for_screen`, `build_expert_busking_template`, `architect_preset_library`, plus the `check_plugin_available` helper — 9 tools total (8 primary + 1 helper, all `@mcp.tool` decorated). Tool count goes from 218 → 227.
8. `tests/test_architecture_hygiene.py` passes; new hygiene rules added for the new tools (risk-tier annotation, expert-lint wiring where applicable).

## References

- `doc/grandma2-mcp-scope.md` — original v0.1.0 scope doc (architectural focus; superseded for this iteration)
- `CLAUDE-CODE-SWARM-PROMPT.md` — overnight swarm execution prompt (not adopted; AMUX dependency missing locally, scope mismatched to operator intent)
- `CLAUDE.md` — project rules
- `.claude/skills/` — 44 skill playbooks (the expert defaults' primary source)
- `.claude/rules/ma2-conventions.md` — MA2 command construction rules

---

# Appendix A — Concrete API signatures

Every new tool follows the canonical pattern:

```python
@mcp.tool()
@require_scope(OAuthScope.XXX)
@require_ma2_right(MA2Right.YYY)        # only where it gates console mutations
@_handle_errors                          # provides telemetry + error envelope
async def tool_name(
    arg1: str,
    arg2: int | str,
    confirm_destructive: bool = False,   # only on DESTRUCTIVE tools
) -> str:                                # always JSON string
    """Docstring with Args / Returns / Examples (existing project style)."""
    ...
```

The error envelope from `_handle_errors` is `{"error": str, "blocked": True}` (with optional `command_sent: null` on safety-gate blocks). Success envelope is per-tool; canonical fields are `command_sent`, `raw_response`, and `blocked: False` where applicable, plus tool-specific structured fields.

## A.1 — `suggest_skills_for_task` (T1, SAFE_READ)

```python
class SkillSuggestion(TypedDict):
    name: str                    # canonical slug, e.g. "color-preset-creator"
    version: str                 # semver from front matter
    score: float                 # 0.0..1.0 ranking score
    why: str                     # one-line "use this when..." justification
    first_decision: str | None   # if skill wraps a plugin, the decision line
    safety_scope: str            # SAFE_READ / SAFE_WRITE / DESTRUCTIVE
    tags: list[str]              # from front matter
    prerequisites: list[str]     # other skill slugs that should be invoked first
    estimated_tokens: int        # body length-based estimate

class SuggestSkillsResponse(TypedDict):
    intent: str                  # echoed
    method: Literal["semantic", "keyword", "hybrid"]
    warning: str | None          # populated when embeddings unavailable
    suggestions: list[SkillSuggestion]

@mcp.tool()
@require_scope(OAuthScope.READ_ONLY)
@_handle_errors
async def suggest_skills_for_task(
    intent: str,
    top_k: int = 3,
    include_destructive: bool = True,    # if False, filters un-approved DESTRUCTIVE
    prefer_semantic: bool = True,
) -> str: ...                            # returns JSON of SuggestSkillsResponse
```

## A.2 — `discover_consoles` (T2, SAFE_READ)

```python
class ConsoleCandidate(TypedDict):
    host: str                    # IPv4 string
    port: int                    # always 30000 for MA2 telnet
    name: str | None             # mDNS service name if available
    session_name: str | None     # MA-Net session name from broadcast
    version: str | None          # console version from announcement
    response_ms: float           # round-trip time during discovery
    source: Literal["mdns", "broadcast", "manual"]

class DiscoverConsolesResponse(TypedDict):
    candidates: list[ConsoleCandidate]
    scanned_networks: list[str]
    elapsed_ms: float
    note: str | None             # diagnostic, e.g. "no mDNS responders"

@mcp.tool()
@require_scope(OAuthScope.READ_ONLY)
@_handle_errors
async def discover_consoles(
    timeout_seconds: int = 5,
    network: str | None = None,  # CIDR, e.g. "192.168.1.0/24"; None = auto-detect
    methods: list[Literal["mdns", "broadcast"]] | None = None,
) -> str: ...
```

## A.3 — `reconfigure_connection` (T2, SAFE_WRITE)

```python
class ReconfigureResponse(TypedDict):
    success: bool
    previous_host: str
    new_host: str
    verified: bool               # info round-trip succeeded
    persisted_to: str | None     # .env path if persist=True
    warning: str | None
    error: str | None

@mcp.tool()
@require_scope(OAuthScope.SYSTEM_ADMIN)
@_handle_errors
async def reconfigure_connection(
    host: str,
    port: int = 30000,
    user: str = "administrator",
    password: str = "admin",
    persist: bool = True,
    verify: bool = True,         # round-trip an info command before declaring success
) -> str: ...
```

## A.4 — `check_plugin_available` (T6 helper, SAFE_READ)

```python
class PluginAvailability(TypedDict):
    plugin_name: str
    available: bool
    pool_id: int | None
    last_checked_at: str         # ISO 8601
    source: Literal["live_query", "cache"]

@mcp.tool()
@require_scope(OAuthScope.READ_ONLY)
@_handle_errors
async def check_plugin_available(
    plugin_name: str,            # human name, e.g. "auto-layout-color-picker"
    use_cache: bool = True,
    cache_ttl_seconds: int = 60,
) -> str: ...
```

## A.5 — `generate_ma2_macro` (T3, SAFE_READ by default; SAFE_WRITE when storing)

```python
class MacroLintFinding(TypedDict):
    rule_id: str                 # e.g. "MACRO-JT-001"
    severity: Literal["advice", "warning", "error"]
    line: int | None
    message: str
    fix_suggestion: str | None

class MacroExpertReview(TypedDict):
    grade: Literal["expert", "competent", "beginner", "broken"]
    rationale: str
    missing_practices: list[str]

class GenerateMacroResponse(TypedDict):
    intent: str                  # echoed
    body_xml: str                # the macro XML body
    line_count: int
    validation: dict             # XML schema validation
    lint: list[MacroLintFinding]
    expert_review: MacroExpertReview
    stored_as: int | None        # macro ID if store=True succeeded
    blocked: bool                # True if expert_review.grade == "broken"

@mcp.tool()
@require_scope(OAuthScope.MACRO_AUTHOR)
@_handle_errors
async def generate_ma2_macro(
    intent: str,
    scope_hints: dict | None = None,        # e.g. {"executor": "1.1.1", "song": "verse"}
    store: bool = False,                    # if True, stores to MA2 pool
    pool_id: int | None = None,             # required if store=True
    confirm_destructive: bool = False,      # required if store=True (overwrites pool slot)
) -> str: ...
```

## A.6 — `build_show_from_patch` (T4, SAFE_READ when dry_run, DESTRUCTIVE otherwise)

```python
class ShowBuildOptions(TypedDict, total=False):
    songs: int                              # default 12
    venue_type: Literal["club", "theatre", "festival", "broadcast", "corporate"]
    cue_density: Literal["sparse", "normal", "dense"]
    preset_strategy: Literal["minimal-viable", "full-coverage", "color-first"]
    world_filter_scope: Literal["none", "per-section", "per-fixture-type"]
    naming_convention: str                  # f-string template

class ShowBuildStep(TypedDict):
    order: int
    command: str                            # MA2 command string
    purpose: str                            # "create wash group", "store position preset", etc.
    expert_says: str                        # one-line expert justification
    risk_tier: str

class ShowBuildResponse(TypedDict):
    strategy: str
    plan: list[ShowBuildStep]
    rationale: list[str]                    # decision log
    expert_review: dict                     # output of XC2 expert_lint
    summary: dict                           # counts: groups, presets, cues, views, macros
    dry_run: bool
    executed_steps: int                     # 0 when dry_run

@mcp.tool()
@require_scope(OAuthScope.SHOW_ARCHITECT)
@_handle_errors
async def build_show_from_patch(
    strategy: Literal["rock-band", "festival", "theatrical", "dj", "broadcast", "corporate"],
    options: ShowBuildOptions | None = None,
    dry_run: bool = True,
    confirm_destructive: bool = False,
) -> str: ...
```

## A.7 — `build_layout_for_screen` (T5, SAFE_READ when dry_run, SAFE_WRITE otherwise)

```python
class ContentSpec(TypedDict, total=False):
    kind: Literal["group", "preset", "executor", "macro", "label", "image", "fader"]
    target: str | int                       # e.g. group ID, preset spec, executor "1.1.1"
    label: str | None
    grid_x: int | None
    grid_y: int | None
    width: int | None
    height: int | None

class LayoutPlanStep(TypedDict):
    order: int
    command: str
    purpose: str

class BuildLayoutResponse(TypedDict):
    screen: int
    template: str | None
    plan: list[LayoutPlanStep]
    preview_ascii: str                      # textual preview of the grid
    expert_review: dict
    dry_run: bool

@mcp.tool()
@require_scope(OAuthScope.LAYOUT_AUTHOR)
@_handle_errors
async def build_layout_for_screen(
    screen: int,
    content: list[ContentSpec] | None = None,
    template: Literal["busking-master", "preset-access", "executor-monitor",
                      "macro-page", "programmer-view", "troubleshoot-view"] | None = None,
    dry_run: bool = True,
) -> str: ...
```

(`content` and `template` are mutually exclusive; the tool raises if both are set or both are None.)

## A.8 — `build_expert_busking_template` (T7, SAFE_READ when dry_run, DESTRUCTIVE otherwise)

```python
class BuskingOptions(TypedDict, total=False):
    page: int                               # target page, default 1
    grid_columns: int                       # for the Companion artifact, default 8
    include_kill_buttons: bool              # default True
    include_blackout_sub: bool              # default True
    include_tap_tempo: bool                 # default True
    speed_master_count: int                 # default 2 (one for FX, one for chases)
    fader_bank_layout: Literal["muscle-memory", "sequential", "category-grouped"]

class BuskingPlanStep(TypedDict):
    order: int
    command: str
    purpose: str
    executor: str | None                    # "1.1.1" etc. where applicable
    expert_says: str

class BuildBuskingResponse(TypedDict):
    strategy: str
    plan: list[BuskingPlanStep]
    executor_layout: list[dict]             # human-readable bank assignment
    companion_config: dict                  # .companionconfig JSON, ready to write
    expert_review: dict
    summary: dict                           # counts: faders, kill buttons, masters, special
    dry_run: bool

@mcp.tool()
@require_scope(OAuthScope.SHOW_ARCHITECT)
@_handle_errors
async def build_expert_busking_template(
    strategy: Literal["rock-band", "dj", "festival", "theatrical"],
    options: BuskingOptions | None = None,
    dry_run: bool = True,
    confirm_destructive: bool = False,
) -> str: ...
```

## A.9 — `architect_preset_library` (T8, SAFE_READ when dry_run, DESTRUCTIVE otherwise)

```python
class PresetEntry(TypedDict):
    preset_type: int                        # 1=Dimmer, 2=Position, 3=Gobo, 4=Color, ...
    preset_id: int                          # within the type
    name: str
    scope: Literal["universal", "selective"]
    target_fixture_types: list[str]         # empty if universal
    values: dict                            # attribute → value mapping
    mib_aware: bool                         # True for movers' MIB presets

class CoverageReport(TypedDict):
    fixture_type: str
    attribute: str
    has_preset: bool
    preset_ids: list[str]                   # "type.id" notation

class ArchitectPresetResponse(TypedDict):
    strategy: str
    reference_fixtures: dict[str, int]      # fixture_type → reference fixture ID
    plan: list[PresetEntry]
    coverage_report: list[CoverageReport]
    naming_convention: str
    expert_review: dict
    summary: dict                           # counts: universal, selective, by type
    dry_run: bool

@mcp.tool()
@require_scope(OAuthScope.PRESET_AUTHOR)
@_handle_errors
async def architect_preset_library(
    patch_filter: str | None = None,        # MA2 selection spec; None = whole patch
    strategy: Literal["full-coverage", "minimal-viable", "color-first"] = "full-coverage",
    dry_run: bool = True,
    confirm_destructive: bool = False,
) -> str: ...
```

## A.10 — Common patterns

- Every mutation tool defaults to `dry_run=True` and produces a `plan` (list of typed steps) and `expert_review` (output of XC2 lint).
- `confirm_destructive` is required to flip `dry_run=False` AND the request must come from a scope that has the relevant write rights.
- The `expert_review` field is always populated, even on dry_run, so the operator can read the lint without committing.
- Every typed return shape is JSON-serialized via `json.dumps(..., indent=2)` per project convention; the TypedDicts are documentation, not enforcement (FastMCP does its own schema generation from the Python types).

---

# Appendix B — Strategy content tables

Each strategy is a coherent set of defaults that an MA Lighting-trained operator would apply to that kind of show. Strategies are deterministic — same patch + same strategy + same options → same plan. The expert review can flag where the strategy's defaults disagree with the patch's characteristics (e.g., "festival strategy on a 3-fixture rig is overkill").

## B.1 — `build_show_from_patch` strategies (T4)

Columns: cue density (cues per song section), preset coverage (universal/selective ratio), tracking policy, MIB policy, world/filter strategy, view templates included by default.

| Strategy | Cue density | Preset coverage | Tracking | MIB | World/filter | Views | Notes |
|---|---|---|---|---|---|---|---|
| **rock-band** | dense (3-5 / section) | full-coverage; lots of color + position | track within song, block at song boundaries | movers always; washes if rig has fast intensity | per-section worlds (intro / verse / chorus / bridge / outro) | programmer + run + busking-fallback | Each song gets its own sequence. Cue notes name the moment. Includes "panic blackout" cue at start of every sequence. |
| **festival** | sparse (1-2 / section) | minimal-viable; preset-heavy, cue-light | non-tracking | movers always | none (everything global) | preset-access + executor-monitor + run | Optimized for fast set changes. Heavy use of instant-recall presets via executor buttons rather than cuelists. Includes "next band" reset macro. |
| **theatrical** | medium (2-3 / scene) | full-coverage; position-heavy | strict tracking with block at scene boundaries | movers always; washes always; dimmers never | per-act worlds | programmer + run + troubleshoot | Long crossfades default. Off-time configured per cuelist. Block cues at act boundaries. Cuelist priorities used deliberately (e.g., emergency = Super, scene = Normal). |
| **dj** | sparse on cuelists; heavy on executors | color-first; minimal position | non-tracking | not applicable | none | busking-master + preset-access | Tap-tempo on a dedicated executor; speed master bound to all FX. Heavy use of MAtricks instances per executor for variation. Includes "drop" sequences (build → bang → release). |
| **broadcast** | minimal (1-2 / look) | full-coverage; conservative | strict tracking with explicit block at look boundaries | movers always; washes always | per-camera-shot world | programmer + run + troubleshoot | Everything preset-referenced for rebuild safety. No bare numeric values in cues. Includes "key fixture" KEY group convention. |
| **corporate** | very minimal | minimal-viable; intensity + 2 colors | non-tracking | not applicable | none | run only | Single "show" sequence with 3-5 looks. Includes blackout cue at start and end. |

### B.1.1 — Per-strategy default `ShowBuildOptions`

| Option | rock-band | festival | theatrical | dj | broadcast | corporate |
|---|---|---|---|---|---|---|
| `songs` | 14 | 25 | n/a (scenes=20) | n/a (sets=4) | n/a (looks=6) | 1 |
| `venue_type` | club | festival | theatre | club | broadcast | corporate |
| `cue_density` | dense | sparse | normal | sparse | sparse | sparse |
| `preset_strategy` | full-coverage | minimal-viable | full-coverage | color-first | full-coverage | minimal-viable |
| `world_filter_scope` | per-section | none | per-section | none | per-fixture-type | none |
| `naming_convention` | `{song}_{section}_{intent}` | `{slot}_{look}` | `{act}_{scene}_{beat}` | `{set}_{moment}` | `{shot}_{look}` | `{look}` |

## B.2 — `build_expert_busking_template` strategies (T7)

Columns: fader bank layout, priority assignments, special tools, Companion grid, wing layout.

### Fader bank layout per strategy

Each strategy assigns 4-6 fader banks across an MA2 page. Convention: lowest executor IDs on the left.

| Strategy | Bank 1 (left) | Bank 2 | Bank 3 | Bank 4 | Bank 5 | Bank 6 (right) |
|---|---|---|---|---|---|---|
| **rock-band** | Intensity (groups: wash / mover / blinder / KEY) | Color (group-scoped chases) | Position (group-scoped chases) | Beam (group-scoped chases) | FX (group-scoped chases + MAtricks variants) | Specials (strobe, blackout, flash-all, tap-tempo) |
| **dj** | Intensity (groups: wash / mover / strobe) | Color washes (full hue access) | Color chases | FX bank A (MAtricks variants) | FX bank B (chases) | Specials (tap-tempo, drop, kill-all, blackout) |
| **festival** | Intensity per band-segment | Color (preset access × 8) | Position (preset access × 8) | FX (chases × 8) | Reset macros | Specials (next-band, panic-blackout) |
| **theatrical** | Cue-list executors (Go / Pause / Back × scenes) | Crossfade master | Manual sub-masters per fixture group | Specials sub | Emergency cue list (Super priority) | Blackout + house lights |

### Priority assignments

| Executor role | Priority | Strategy applicability |
|---|---|---|
| Blackout sub | Super | all |
| Emergency cue list | Super | theatrical, broadcast |
| Blinders (flash) | High | rock-band, dj, festival |
| Chase overrides | Swap | all |
| Color picker presets | Normal | all |
| Intensity sub-masters | Normal | all (LTP) |
| Speed master | (special master, not a priority) | all |
| Tap-tempo | (special master) | rock-band, dj |
| KEY fixture isolator | High | rock-band, broadcast, theatrical |

### Special tools per strategy

| Special | rock-band | dj | festival | theatrical |
|---|---|---|---|---|
| Blackout sub (independent of GM) | ✓ | ✓ | ✓ | ✓ |
| Tap-tempo executor | ✓ | ✓ |  | (manual go) |
| Kill colors / kill FX / kill position | ✓ | ✓ |  |  |
| Strobe-on-demand flash | ✓ | ✓ | ✓ |  |
| Speed master (FX) | ✓ | ✓ | ✓ |  |
| Rate master (chasers) | ✓ | ✓ |  |  |
| Drop sequence (build/bang/release) |  | ✓ |  |  |
| Next-band reset macro |  |  | ✓ |  |
| KEY fixture isolator | ✓ |  |  | ✓ |
| Houselights sub |  |  |  | ✓ |

### Companion grid layout per strategy

8-column grid (Stream Deck XL); 5-column variant uses the same content compressed.

| Strategy | Row 1 (top) | Row 2 | Row 3 | Row 4 (bottom) |
|---|---|---|---|---|
| **rock-band** | Page select × 4 + tap-tempo + speed master + blackout + BO-strobe | Intensity sub × 8 | Color chases × 8 | FX + specials × 8 |
| **dj** | Page select × 4 + tap-tempo + speed master + drop + blackout | Color washes × 8 | FX bank A × 8 | FX bank B + kill-all + blackout |
| **festival** | Page select per band × 4 + next-band + panic + blackout + houselights | Color presets × 8 | Position presets × 8 | Reset macros × 8 |
| **theatrical** | Cue Go + Pause + Back + Goto-cue + emergency + blackout + houselights + standby | Scene cuelist selectors × 8 | Sub-master toggles × 8 | Specials × 8 |

### Wing layout (muscle-memory map)

All strategies use the same muscle-memory convention unless overridden:

| Wing position | Content |
|---|---|
| Wing 1 (far left) | Intensity sub-masters |
| Wing 2 | Color access (presets + chases) |
| Wing 3 (centre) | Position + Beam |
| Wing 4 | FX bank |
| Wing 5 (far right) | Specials + masters (speed, rate, tap, blackout) |

This matches the convention named in `.claude/skills/busking-lighting-performance/SKILL.md`. The `fader_bank_layout="sequential"` option overrides to a strictly numeric layout for operators who prefer it; `category-grouped` is a more permissive variant that allows reshuffling within categories.

---

# Appendix C — Expert lint rule catalogs

The `src/expert_lint/` module exposes `expert_lint(plan, domain, context) -> list[Violation]`. Each rule has an ID, severity, expert-justification, and fix-suggestion. Rules are pure functions over the plan + context; no console state required.

ID convention: `<DOMAIN>-<CATEGORY>-<NNN>` where DOMAIN ∈ {MACRO, BUSK, SHOW, PRESET, LAYOUT}. Severities: **error** (will break or destroy work), **warning** (expert would push back), **advice** (expert would suggest but not insist).

## C.1 — Macro lint (`MACRO-*`)

| Rule ID | Severity | Expert says | Fix suggestion |
|---|---|---|---|
| MACRO-JT-001 | error | Jump target line number does not exist in the macro | Recompute target after insertion; use the index-shift table in `.claude/rules/ma2-conventions.md` |
| MACRO-JT-002 | warning | Jump target points to a line that performs a Store — fragile under future edits | Refactor to use a labelled marker comment or split into two macros |
| MACRO-SAFETY-001 | error | Destructive command (`Delete`, `Store /merge`, `new_show`) without `/noconfirm` will hang the macro | Add `/noconfirm` or precede with explicit confirmation logic |
| MACRO-SAFETY-002 | error | `new_show` without `/globalsettings` will disable Telnet | Append `/globalsettings` (always) |
| MACRO-TIME-001 | warning | Sleep/busy-wait via repeated `Wait` keyword instead of `CmdDelay` | Use `CmdDelay <ms>` (project convention) |
| MACRO-VAR-001 | error | `GetVar` reads a variable that was never `SetVar`-ed in this macro or session | Add the `SetVar` line earlier or document the dependency |
| MACRO-VAR-002 | warning | `SetVar` to a system variable name (e.g. `$SHOWFILE`) — system variables are read-only | Rename the variable; use a user prefix (`my_`) |
| MACRO-SELECT-001 | error | Store-of-selection-dependent target without preceding `ClearAll` or explicit `Select` | Add `ClearAll` then the explicit selection on the same line as the Store |
| MACRO-SELECT-002 | warning | `Selection` keyword after `FixtureType X.M.1 Thru` — known timing race (`ma2-conventions.md` §Macro Store Group timing) | Insert new lines around existing Store logic rather than modifying it |
| MACRO-LINK-001 | warning | Macro calls another macro that doesn't exist in the current show | Verify target macro is part of the same show or document the cross-show dependency |
| MACRO-PERM-001 | error | Macro performs operations requiring rights not granted to current user | Either reduce the macro's scope or document required rights |
| MACRO-NAME-001 | advice | Macro has no label / generic label like "Macro 17" | Label the macro with intent (e.g. "Song-Change Verse→Chorus") |
| MACRO-PARK-001 | warning | Macro parks fixtures without a paired unpark macro | Add the paired unpark macro and reference it in this macro's notes |
| MACRO-SCOPE-001 | advice | Macro modifies executor 1.1.1 unconditionally — risky on operator's main page | Make the executor target a `SetUserVar` parameter, or guard with current-page check |
| MACRO-XML-001 | error | Macro XML body fails MA2 schema validation | Regenerate with schema-aware emitter; check for unescaped quotes |

## C.2 — Busking template lint (`BUSK-*`)

| Rule ID | Severity | Expert says | Fix suggestion |
|---|---|---|---|
| BUSK-SUB-001 | error | No blackout sub-master independent of the Grand Master | Add a dedicated executor with `BlackScreen` or DMX off macro, priority Super |
| BUSK-SUB-002 | warning | Speed master not assigned for FX bank | Add a speed master executor and bind to all chasers' SpeedMaster property |
| BUSK-PRIO-001 | error | Blackout sub priority is not Super | Set executor priority to `super` per `.claude/rules/functional-domains.md` |
| BUSK-PRIO-002 | warning | All executors set to Normal — no priority discrimination | Assign Super/High/Swap per the strategy table in Appendix B.2 |
| BUSK-PRIO-003 | warning | Blinder executors set to Normal — flash effect will be overridden by chases | Set blinders to High priority |
| BUSK-KILL-001 | warning | No kill button for color bank (rock-band/dj strategies) | Add a `Kill /color` macro on a dedicated executor in the specials bank |
| BUSK-KILL-002 | warning | No kill button for FX bank (rock-band/dj strategies) | Add a `Kill /effect` macro on a dedicated executor in the specials bank |
| BUSK-TAP-001 | warning | Tap-tempo executor missing (rock-band/dj strategies) | Add `Tap` executor bound to a speed master |
| BUSK-LAYOUT-001 | advice | Fader bank layout deviates from muscle-memory map without `fader_bank_layout` override | Confirm the deviation is intentional; otherwise use the default |
| BUSK-CONF-001 | error | Two executors assigned to the same exec slot | Re-allocate so each executor lives in a distinct slot |
| BUSK-LABEL-001 | warning | Executor has no label or generic label like "Exec 5" | Label every executor with intent (e.g., "Wash Blue", "Strobe All") |
| BUSK-HTP-001 | warning | Intensity sub-master configured as LTP — operator expectation is HTP for intensity | Change priority to HTP for intensity-only executors |
| BUSK-LTP-001 | warning | Color executor configured as HTP — color should be LTP so the last fired wins | Change priority to LTP/Normal |
| BUSK-COMP-001 | error | Generated Companion config fails schema validation against pinned `FILE_VERSION` | Regenerate using the golden-fixture-derived template |
| BUSK-COMP-002 | warning | Companion grid layout has empty rows interleaved with content — confusing on hardware | Compact the layout so used rows are contiguous |
| BUSK-KEY-001 | advice | KEY fixture group not defined (rock-band, broadcast, theatrical) | Add a KEY group containing the front-key fixture for that production |

## C.3 — Show creation lint (`SHOW-*`)

| Rule ID | Severity | Expert says | Fix suggestion |
|---|---|---|---|
| SHOW-TRACK-001 | warning | Strategy says "track within song, block at song boundaries" but no block cues found at song transitions | Insert block cues at each song's last position |
| SHOW-TRACK-002 | warning | Strategy is "non-tracking" but cuelist option `Wrap` set without `SoftLTP` | Either set `softltp` or switch to a tracking strategy |
| SHOW-MIB-001 | warning | Strategy includes "MIB movers always" but movers have no MIB preset references | Add MIB presets for each mover type and reference in the appropriate cues |
| SHOW-MIB-002 | error | MIB enabled on dimmer fixtures (no movement attribute) | Disable MIB for dimmer-only fixtures |
| SHOW-REF-001 | warning | Cue contains hard numeric values where strategy says preset-referenced | Replace numeric values with preset references |
| SHOW-OFF-001 | warning | Cuelist has no off-time configured | Set off-time per `.claude/skills/cue-tracking-and-timing/SKILL.md` defaults |
| SHOW-PRIO-001 | warning | All cuelists are Normal priority | Assign Super to emergency/blackout, Normal default, document any High/Swap |
| SHOW-WORLD-001 | warning | Strategy is "per-section worlds" but only one world defined | Generate worlds matching strategy's section count |
| SHOW-NOTE-001 | advice | Cue note is empty or generic ("Cue 5") | Apply naming convention: `{song}_{section}_{intent}` |
| SHOW-EMERG-001 | warning | Strategy is theatrical/broadcast but no emergency cue list found | Add an emergency cue list at Super priority |
| SHOW-VIEW-001 | warning | View bank missing required template (run / programmer) | Add the missing views per strategy table |
| SHOW-BLACK-001 | warning | No "panic blackout" cue at start of each sequence (rock-band default) | Insert blackout cue as cue 0.5 of each sequence |
| SHOW-SEQ-001 | advice | Sequence has no label or generic label like "Seq 12" | Label sequence with song name + section |
| SHOW-COVER-001 | advice | Some fixtures in patch are never targeted by any cue or executor | Either include them or document why they're parked |

## C.4 — Preset library lint (`PRESET-*`)

| Rule ID | Severity | Expert says | Fix suggestion |
|---|---|---|---|
| PRESET-REF-001 | warning | Reference fixture for type not chosen (multiple of this type exist) | Pick the lowest-ID fixture of each type as the reference; document choice |
| PRESET-COVER-001 | warning | Strategy is full-coverage but an attribute on a fixture type has no preset | Add a "default/home" preset for that attribute |
| PRESET-COVER-002 | warning | No color presets covering the 4 cardinal hues (red, green, blue, white) | Add the 4 cardinal hues per `.claude/skills/constrained-color-design/SKILL.md` |
| PRESET-COVER-003 | advice | No "warm wash" or "cool wash" preset | Add at least one of each (operator convenience) |
| PRESET-SCOPE-001 | warning | Color preset is selective but strategy says universal | Convert to universal; values clamp to per-fixture-type capability |
| PRESET-SCOPE-002 | warning | Gobo preset is universal — gobos are fixture-specific | Convert to selective per fixture type |
| PRESET-NAME-001 | warning | Naming convention not applied consistently | Run rename per convention from strategy options |
| PRESET-NUM-001 | error | Duplicate preset numbers within a type | Renumber; never reuse |
| PRESET-NUM-002 | warning | Preset numbering doesn't follow MA2 type convention (color is type 4, position is type 2, etc.) | Renumber per type convention |
| PRESET-MIB-001 | warning | Movers in patch but no MIB presets defined | Add MIB presets per mover type |
| PRESET-EMPTY-001 | error | Preset slot exists but has no stored values | Either populate the preset or remove the empty slot |
| PRESET-CLONE-001 | advice | Selective preset on type A could be cloned to similar type B (reduces store work) | Use Clone workflow per `.claude/skills/clone-and-data-transfer/SKILL.md` |
| PRESET-HSB-001 | advice | Color preset stored in RGB but constrained-color-design says HSB for this strategy | Re-store using HSB color model |

## C.5 — Layout lint (`LAYOUT-*`)

| Rule ID | Severity | Expert says | Fix suggestion |
|---|---|---|---|
| LAYOUT-REQ-001 | error | Template requires content X but content does not include X | Add the missing required content (per template spec) |
| LAYOUT-COLLIDE-001 | error | Two content items overlap on the grid | Re-place one or both items |
| LAYOUT-DANGLE-001 | error | Content references a non-existent target (group/preset/executor) | Either create the target or remove the layout entry |
| LAYOUT-LABEL-001 | warning | Layout cell has no label and target name is cryptic | Add an explicit label |
| LAYOUT-SIZE-001 | warning | Content exceeds screen native resolution | Resize or split into a second screen |
| LAYOUT-DENSE-001 | advice | More than 70% of screen real estate used — leaves no room for status/info | Reduce density or split into multiple screens |
| LAYOUT-COVER-001 | advice | Template is `executor-monitor` but fewer than 50% of active executors shown | Expand layout to cover more executors |

## C.6 — Cross-cutting expert defaults applied by lint

Beyond domain-specific rules, the lint module enforces these always-on conventions:

- Every plan step has a `purpose` field; empty `purpose` is a `MACRO-NAME-001`-class advice violation in any domain.
- Every plan that mutates console state must have at least one preceding plan step that establishes context (e.g., `SetVar` or `Select`).
- DESTRUCTIVE plan steps must have an immediately preceding "dry-run preview" log line or the lint warns.
- Tool plans that target a specific executor (`1.1.1`) without making the executor configurable warn (per MACRO-SCOPE-001 reasoning, transposed to any domain).

---

# Appendix D — Infrastructure specifics

## D.1 — Skill router algorithm

Mirrors the existing `suggest_tool_for_task` pattern in `src/server.py:7228-7341` so behavior is consistent between tool-suggestion and skill-suggestion surfaces. New code lives in `src/skill_router.py`.

**Corpus.** All filesystem skills (`.claude/skills/*/SKILL.md`) plus any DB-registered skills from `SkillRegistry.list_all()`. For each skill, the searchable text is:

```
{name}\n{description}\n{applicable_context}\n{body_head}
```

where `body_head` is the first 500 tokens of the skill body. This bounds embedding cost while capturing the "when to use" sections that typically appear near the top.

**Embedding path.** When `GITHUB_MODELS_TOKEN` is set, `GitHubModelsProvider` from `rag.ingest.embed` is used (same as the existing tool router). Embeddings for the corpus are computed once per server start and cached in `rag/store/skill_embeddings.json` (keyed by skill name + version). At suggestion time, the intent string is embedded once; ranking is cosine similarity over the corpus.

**Keyword fallback.** When the token is absent, falls back to keyword overlap: split intent and skill text on whitespace, count overlap on lowercased non-stopword tokens, normalize by intent length. The response includes `warning: "semantic search unavailable; using keyword fallback"`.

**Hybrid signal.** Optional `method="hybrid"` blends semantic (60%) and keyword (40%) signals — useful when intents are short and embedding alone is noisy.

**Filters applied before ranking.**
- `include_destructive=False` → drop any skill where `safety_scope == "DESTRUCTIVE"` AND `approved == False`.
- Tags filter (future): when intent matches a known tag prefix (e.g., "color:"), prefilter to skills with that tag.

**Ranking augmentation.**
- +0.05 bonus if `intent` mentions a tag the skill claims in its enriched front matter.
- +0.10 bonus if `intent` contains the skill's `wraps_plugin` name AND the plugin is currently available (uses `check_plugin_available`).
- -0.10 penalty if the skill is DESTRUCTIVE-unapproved (still surfaces but ranks lower than approved equivalents).

**Response format.** Exactly the `SuggestSkillsResponse` shape from A.1 — top-K suggestions, each with `name`, `version`, `score`, `why` (the `description` field, truncated to 120 chars), `first_decision` (extracted from a "First decision" section if present in the body), `safety_scope`, `tags`, `prerequisites`, `estimated_tokens` (body length / 4).

**Front matter additions (optional, backward-compatible).** No existing skill is required to add these, but skills that do get richer routing:

```yaml
tags: [color, presets, plugin-aware]
prerequisites: [patch-and-group-builder]
wraps_plugin: auto-layout-color-picker
use_instead_of: []
estimated_tokens: 2400
```

The front matter parser in `src/skill.py` is regex-based and accepts unknown fields gracefully — no parser change required for these to land cleanly.

## D.2 — Mock mode fidelity (`GMA_MOCK=1`)

Three tiers of fidelity; the env var selects tier:

| Tier | `GMA_MOCK` value | Behavior |
|---|---|---|
| Tier 1 | `1` or `canned` | Hardcoded responses for the ~30 most common command shapes (`list`, `info`, `cd`, `ListVar`, `Echo`, etc.). Unknown commands return `"MOCK: command not stubbed"` plus the request. |
| Tier 2 | `schema` | Schema-driven: responses respect the `src/prompt_parser.py` invariants (tabular for `list`, key-value for `info`, etc.). Stateful in-memory show fixture (default `tests/fixtures/mock_show_state.json`) supports `cd`, group/preset creation, store, executor fire, etc. **Recommended default for development.** |
| Tier 3 | `replay:<path>` | Replay a JSONL session log captured from a real console via `tests/fixtures/captured/*.jsonl`. Useful for reproducing exact past behavior. |

**Injection point.** Per the architecture survey, the cleanest swap is at `_get_session_manager()` in `src/server.py`. Add:

```python
async def _get_session_manager() -> SessionManager:
    if os.getenv("GMA_MOCK"):
        from src.mock.session_manager import MockSessionManager
        return MockSessionManager(tier=os.getenv("GMA_MOCK"))
    # ... existing path
```

**Mock module layout.**

```
src/mock/
  __init__.py
  session_manager.py     # MockSessionManager — implements the SessionManager protocol
  operator_session.py    # MockOperatorSession holding a MockGMA2TelnetClient
  telnet_client.py       # MockGMA2TelnetClient — implements GMA2TelnetClient's public surface
  responses.py           # Tier 1 canned responses keyed by regex
  fixture_loader.py      # Tier 2 stateful show fixture
  replay.py              # Tier 3 JSONL replay
tests/fixtures/
  mock_show_state.json   # default Tier 2 fixture
  captured/              # Tier 3 replay logs (gitignored except sample.jsonl)
```

**Acceptance.** A new test `tests/test_mock_mode.py` covers:
- Server starts cleanly with each tier.
- For each tier, every SAFE_READ tool returns a non-error JSON envelope with `mock: <tier>` field.
- Tier 2 supports a complete preset-architect dry-run end-to-end (the path most useful for T8 development without a console).

## D.3 — Plugin detection (`check_plugin_available`)

**Implementation.**
1. On first call (or cache miss), invoke `browse_plugin_library()` (existing tool).
2. Parse the raw response with a new regex: `r'^\s*(\d+)\s+(.+?)\s*$'` matched line-by-line against the listing block. Skip header rows.
3. Build `{plugin_id: int, plugin_name: str}` records.
4. Store in `src/agent_memory.py`'s `WorkingMemory.add_checkpoint(fault="plugin_inventory", ...)` with `fresh_for_seconds=60`.
5. On subsequent calls within TTL, return cached. On TTL miss, re-fetch.

**Matching.** Exact match on `plugin_name` is preferred; case-insensitive substring match is a fallback (with `match: "substring"` in the response). The skill router can use exact or substring depending on signal strength.

**Race condition.** Two concurrent `check_plugin_available` calls may both miss cache and trigger console queries. Acceptable — the cache is best-effort and the cost of a duplicate `ListPluginLibrary` is low.

**Color picker disambiguation flow** (T6):

```
Operator: "make me a color picker"
  → Claude invokes suggest_skills_for_task("color picker")
    → returns [auto-layout-color-picker (score 0.94, wraps_plugin=auto-layout-color-picker),
               color-preset-creator (score 0.71)]
  → Claude reads auto-layout-color-picker skill
    → first_decision: "if check_plugin_available(auto-layout-color-picker).available → use plugin"
  → Claude invokes check_plugin_available("auto-layout-color-picker")
    → returns {available: true, pool_id: 7, source: "live_query"}
  → Claude invokes call_plugin_tool(7, confirm_destructive=True)
```

This whole chain is automatic once T1 + the skill front-matter edits ship.

## D.4 — Companion integration (T7)

**Path.** `.companionconfig` JSON file generation, pinned to `FILE_VERSION=6` (Companion 4.x). Schema is internal to Companion's TypeScript types (no public spec), so we use a golden-fixture strategy.

**Golden fixture.** Before implementing the generator, the operator (on the Asus next session) exports a hand-built reference page from a real Companion 4.x install, containing one of each button type the generator will emit (action button, action+release button, page-select, surface-rotate). The exported JSON is committed as:

```
tests/fixtures/companion_page_v6.companionconfig
```

The generator's output is asserted to match this fixture's structure (allowing dynamic fields like timestamps, IDs to differ — fixture-aware diff).

**`companion_version` parameter.** The `BuskingOptions` (A.8) gains an optional `companion_version: Literal[3, 4]` (default 4). For v3, the generator emits `FILE_VERSION=3` and uses the older field shape (a "v3 mode" path). A warning fires: `"Companion 3.x schema may drift; verify import"`.

**Surface format mapping.** The generator maps strategy-defined "grid" content (from B.2 Companion grid layout table) into Companion's row/column model:

| Strategy grid cell | Companion entity | Notes |
|---|---|---|
| "Page select × 4" | 4 action buttons sending `Page N` over MA2 telnet via the malighting-grandma2 module | Each button has an updown style with the page number as text |
| "Tap-tempo" | Action button → `Tap Executor X.X.X` | Bound to the dedicated tap-tempo executor |
| "Color preset N" | Action button → `Preset 4.N` | Color is type 4 per MA2 convention |
| "Kill colors" | Action button → `Kill /color` | Runs a kill macro |
| "Blackout" | Action button → `Blackout` | Standalone keyword, no executor |

**Runtime trigger.** The existing `companion_button_press(page, button)` tool maps to Companion's HTTP `/api/location/<page>/<row>/<column>/press` endpoint. T7's generator output documents the page/row/column convention so the runtime tool can target buttons it generated.

**Acceptance.**
- Generator output passes a JSON-schema validator built from the golden fixture.
- A round-trip test asserts that re-exporting an imported generated file produces an equivalent structure.
- For each strategy in B.2, the generated grid layout is non-empty, has zero overlaps (LAYOUT-COLLIDE-001 check), and labels every button.

## D.5 — Console discovery (T2, `discover_consoles`)

**Methods.**
- **mDNS.** Query for `_grandma._tcp.local.` (MA Lighting's reserved service identifier — verify on the Asus that the running console advertises this; if not, fall back to broadcast). Use `python-zeroconf` (already a transitive dep via `mdns` ecosystem) or `aiozeroconf` if not. Add to `pyproject.toml`.
- **UDP broadcast.** Send a discovery probe on UDP port 6004 (MA-Net2 announcement port); listen for replies. MA2 consoles respond with an announcement packet containing host, port, session name, version. The exact wire format is documented in MA Lighting's [Network Manual](https://www.malighting.com/download/) (verify on Asus; if format is undocumented, capture from a real console and reverse-engineer the fields we need).
- **Manual.** If both methods fail, `discover_consoles` returns an empty list with `note: "no responders; provide host manually"`.

**Verification.** Each discovered candidate is probed with a TCP connect on its port. Candidates that don't accept the connection are filtered out (or marked `responding: false` in the response).

**Network parameter.** When `network=None`, the tool auto-detects local interfaces and scans each. When provided (e.g., `"192.168.1.0/24"`), restricts scan to that CIDR. Useful for multi-interface laptops.

## D.6 — Reconfiguration (T2, `reconfigure_connection`)

**Atomic swap.** The current `SessionManager` holds `_host`/`_port` as immutable. `reconfigure_connection` does:

1. Build a new `SessionManager(host=new_host, port=new_port, ...)`.
2. Open a fresh client and run an `info` round-trip; if it fails, abort with `verified=false, error=<msg>`.
3. Atomically swap the global `_session_manager` reference under a lock; the old manager is closed asynchronously after a 5-second grace period for in-flight requests.
4. If `persist=True`, write to `.env`:
   ```
   GMA_HOST=<new_host>
   GMA_PORT=<new_port>
   GMA_USER=<new_user_if_changed>
   ```
   Preserves other `.env` entries.

**Mid-flight handling.** Any tool that's already mid-call against the old manager completes against the old connection or errors with `ConnectionError`; the error envelope clearly attributes it to the reconfigure.

**Idempotence.** Calling `reconfigure_connection` with the same host/port as currently active is a no-op (returns `success=true, verified=true, note: "no change"`).

---

# Appendix E — Dependency graph and sequencing

## E.1 — Dependency edges

A → B means "A must land before B, or B will be incomplete / broken."

```
XC1 (skill checklists)          ──┐
XC2 (expert_lint module)        ──┼─→ T3 (macro gen)
                                  ├─→ T4 (show creation)
                                  ├─→ T7 (busking template)
                                  └─→ T8 (preset library architect)

T1 (skill router)               ──┬─→ T3 (auto-pulls macro skills)
                                  └─→ T6 (color picker disambig)

T2 (console portability+mock)   ──→ enables Tier-2 mock testing of T3, T4, T5, T7, T8
                                    (not strictly required, but accelerates dev)

D.3 (plugin detection)          ──→ T6 (color picker disambig)
D.4 (Companion golden fixture)  ──→ T7 (busking template)

T4 (show creation machinery)    ──→ T8 (preset library may reuse T4's strategy infra)
```

No cycles. XC1, XC2, T1, T2 are leaves of the dependency tree and can land in any order. T3 depends on T1 + XC2. T6 depends on T1 + D.3. T7 depends on XC2 + D.4. T4 and T8 depend on XC2.

## E.2 — Recommended sequencing within Path A (tonight, no console)

Path A scope: XC1, XC2, T1, T2, T3.

| Order | Task | Why this position | Parallelizable with |
|---|---|---|---|
| 1 | XC1 (skill checklists) | Pure documentation; can start immediately and run in parallel | XC2, T1, T2 |
| 2 | XC2 (expert_lint module) | Foundational for T3; should land before T3 starts | T1, T2 |
| 3 | T1 (skill router) | Foundational; needed by T3 to auto-load macro skills | T2 |
| 4 | T2 (console portability + mock mode) | Independent; mock mode lets T3 development proceed without console | (after T1 starts) |
| 5 | T3 (macro generation) | Depends on T1 + XC2; benefits from T2 mock for testing | — |

Within Path A, items 1-4 can run in any interleaving. Item 5 should wait for 2, 3 to land.

## E.3 — Recommended sequencing within Path B (next session, with console)

Path B scope: D.4 fixture, T6, T7, T4, T5, T8.

| Order | Task | Why this position | Console needed |
|---|---|---|---|
| 1 | Companion golden fixture export (D.4) | One-time setup; needed before T7 generator can be implemented | No (operator + Companion) |
| 2 | T6 (color picker disambig) | Quickest live verification; validates T1 + plugin detection end-to-end | Yes |
| 3 | T7 (busking template) | Validates XC2 lint against its largest output; produces visible win | Yes |
| 4 | T4 (show creation from patch) | Biggest scope; validates everything once | Yes |
| 5 | T5 (layout builder) | Independent of T4; quick verify | Yes |
| 6 | T8 (preset library architect) | May reuse T4's strategy machinery; verify last | Yes |

Within Path B, items 2-6 are largely independent of each other (they share infra from Path A but not from each other). They can be reordered based on operator priorities; recommended order maximizes early feedback.

## E.4 — Cross-path dependency

Path A must fully land before Path B starts. T7 specifically depends on T1's skill router and XC2's lint module being in place; T4 depends on XC2; T6 depends on T1.

## E.5 — Out-of-band dependencies

These are not tasks in scope but are prerequisites:

- `python-zeroconf` or equivalent must be added to `pyproject.toml` for D.5 mDNS discovery. Verify license compatibility (Apache 2.0 / MIT acceptable; copyleft is not).
- A real Companion 4.x install with at least one button page configured is needed to export the golden fixture (D.4). If not available next session, T7 ships behind a feature flag with the fixture deferred.
- Live console at `2.0.0.101` (per operator's memory) for Path B's verification work.

---

# Appendix F — Test strategy matrix

Each task ships with tests at the levels marked ✓. Levels:
- **Unit**: no console, no mock; pure function tests on builders / parsers / lint rules.
- **Mock**: `GMA_MOCK=1`, runs against the Tier-2 in-memory fixture; verifies behavior end-to-end without hardware.
- **Live**: requires real console; gated on `RUN_LIVE_TESTS=1`; runs against operator's `2.0.0.101` next session.
- **Judgment**: not automatable; requires operator review.

| Task | Unit | Mock | Live | Judgment | Acceptance covered by tests |
|---|---|---|---|---|---|
| T1 (skill router) | ✓ ranking determinism, corpus loading, fallback path | n/a (no console state) | n/a | ✓ operator-expected pick for fuzzy intents | 9/10 acceptance from §T1 |
| T2 discover | ✓ packet parsing on captured discovery responses | n/a | ✓ real-network probe | ✓ multi-interface edge cases | 1/1 acceptance from §T2 |
| T2 reconfigure | ✓ .env persistence, atomic swap, idempotence | ✓ swap and info round-trip | ✓ mid-flight request handling | — | 2/2 acceptance from §T2 |
| T2 mock mode | ✓ tier selection, response envelope shape | ✓ Tier-2 fixture supports T8 dry-run | n/a (mock IS the test) | ✓ fidelity spot-checks against captured real responses | 1/1 acceptance from §T2 |
| T3 (macro gen) | ✓ lint rules fire on synthetic bad XML; schema validation | ✓ generate-and-validate against `macros/stock/` | ✓ generated macros run cleanly | ✓ NL→intent quality | 5/5 macro intents from §T3 |
| T4 (show creation) | ✓ plan determinism, lint wiring | ✓ full plan against fixture patch | ✓ plan executes against real patch | ✓ expert-quality of show | Acceptance covered: structure 100%, quality requires operator |
| T5 (layout) | ✓ plan generation, collision detection | ✓ plan against fixture | ✓ layout applies and renders | ✓ aesthetic quality | 3-5 examples per template; structure 100% |
| T6 (color picker disambig) | ✓ check_plugin_available parsing, cache TTL | ✓ found / not-found paths | ✓ color picker fires on first try | — | 3/3 phrasings from §T6 |
| T7 (busking template) | ✓ plan generation, Companion config schema validation | ✓ plan against fixture | ✓ Companion import round-trip; full template applied | ✓ expert-quality | Strategy variation 100%; quality requires operator |
| T8 (preset library architect) | ✓ plan generation, coverage report, naming convention | ✓ plan against fixture | ✓ presets store correctly | ✓ expert-quality | Acceptance covered by structure tests; quality requires operator |
| XC1 (skill checklists) | ✓ YAML front-matter validity for each edited skill | n/a | n/a | ✓ operator agreement with checklist content | Per-skill checklist completeness |
| XC2 (expert_lint module) | ✓ each rule has at least one positive + one negative test | ✓ lint runs on representative plans | n/a | ✓ severity calibration | Rule coverage 100%; calibration via operator |

**Test count delta.** Roughly +120-180 new tests across the 11 work items. New test files:

- `tests/test_skill_router.py` (~20)
- `tests/test_console_discovery.py` (~10)
- `tests/test_reconfigure_connection.py` (~10)
- `tests/test_mock_mode.py` (~15)
- `tests/test_macro_generation.py` (~25)
- `tests/test_build_show_from_patch.py` (~20)
- `tests/test_build_layout.py` (~15)
- `tests/test_check_plugin_available.py` (~5)
- `tests/test_build_busking_template.py` (~20)
- `tests/test_architect_preset_library.py` (~15)
- `tests/test_expert_lint/test_macro_rules.py` (~30)
- `tests/test_expert_lint/test_busking_rules.py` (~16)
- `tests/test_expert_lint/test_show_rules.py` (~14)
- `tests/test_expert_lint/test_preset_rules.py` (~13)
- `tests/test_expert_lint/test_layout_rules.py` (~7)

Existing `tests/test_architecture_hygiene.py` gains 3-4 new invariants:
- Every new tool has explicit risk-tier annotation.
- Every new mutation tool runs `expert_lint` before returning.
- Every new tool has a corresponding test file.
- No new tool exceeds 200 LOC (excluding tests).

---

# Appendix G — Risk register

Per task: failure modes, blast radius, regression detection, rollback path.

## G.1 — T1 (skill router)

| Risk | Likelihood | Blast | Detection | Rollback |
|---|---|---|---|---|
| Ranking returns wrong skill consistently | Medium | Operator gets bad suggestions; falls back to manual recall (current state) | Telemetry on user follow-up to suggestions; periodic operator review of 10 intents | Disable tool via `GMA_DISABLE_SKILL_ROUTER=1` env var; existing `list_skills` continues to work |
| Embedding cache becomes stale (skills updated, cache not invalidated) | Low | Stale ranking until restart | Cache keyed on `(name, version)` from front matter — bumping version invalidates | Manual cache wipe: `rm rag/store/skill_embeddings.json` |
| Front-matter additions break existing skill parser | Low | Skills fail to load | Parser is regex-based and tolerates unknown fields; tested in `test_skill_router.py` | Revert front-matter additions |

## G.2 — T2 discover

| Risk | Likelihood | Blast | Detection | Rollback |
|---|---|---|---|---|
| Discovery returns false positives (e.g., unrelated mDNS responder) | Medium | Operator picks wrong host; reconfigure fails verify | Each candidate is TCP-probed; non-responders dropped | Filter by `responding: true`; manual host fallback |
| Discovery misses real console (false negative) | Medium | Operator manually configures host (current state) | Live test on multiple network configs at the Asus | Always accept manual host input |
| Broadcast packets blocked by router/firewall | High in some venues | No discovery results | Discovery `note` field reports "no responders" | mDNS path independent; manual fallback always works |
| `python-zeroconf` license / install issue | Low | Tool unavailable | CI checks dep install | Skip mDNS, broadcast-only |

## G.3 — T2 reconfigure

| Risk | Likelihood | Blast | Detection | Rollback |
|---|---|---|---|---|
| Reconfigure breaks in-flight requests | Low (atomic swap design) | Active session interrupted with ConnectionError | Test suite includes mid-flight request scenarios | Operator retries; new session opens cleanly on new host |
| `.env` write corrupts other env vars | Low | Other tools misconfigured | Atomic write (write-temp + rename); test covers preservation | Restore from `.env.bak` (always written before `.env`) |
| Verify round-trip succeeds against bad host (false positive) | Low | Active host swap to broken target | `info` is a specific command; failure modes well-known | Operator runs `discover_consoles` again, retries |

## G.4 — T2 mock mode

| Risk | Likelihood | Blast | Detection | Rollback |
|---|---|---|---|---|
| Mock responses unrealistic; code works in mock, breaks live | Medium | Wasted dev time | Live integration tests on real console; spot-checks fidelity quarterly | Disable mock mode; require real console (current default) |
| Mock state diverges from real console schema over time | Medium | Tests pass, prod fails | Run captured-response regression test in CI weekly | Update Tier-2 fixture; or shift fixture to Tier-3 recorded |
| Operator forgets `GMA_MOCK=1` is set and thinks they're hitting real console | Low | Confusing dev experience | Every mock response includes `mock: <tier>` field; banner on server start | Unset env var |

## G.5 — T3 macro generation

| Risk | Likelihood | Blast | Detection | Rollback |
|---|---|---|---|---|
| Generated macro syntactically valid but semantically wrong | Medium | Operator runs it; unexpected console state (potentially destructive) | Expert-lint flags obvious bad patterns; operator review remains essential; macro stored separately from existing pool by default | Macros are deletable; bad macro removed via `delete_object("macro", N)` |
| Lint false negative — lets dangerous pattern through | Low | Same as above | Lint coverage tests; new rules added as gaps surface | Add the missing rule (in scope) |
| XML schema validation false positive (rejects valid macro) | Low | Operator can't use the macro | XML schema test corpus from `macros/stock/` | Loosen schema or whitelist; depends on root cause |
| `intent` is ambiguous and generator picks wrong interpretation | High | Operator confused; iterates | Tool returns `expert_review.rationale` explaining the interpretation | Operator refines intent; iterate |

## G.6 — T4 show creation

| Risk | Likelihood | Blast | Detection | Rollback |
|---|---|---|---|---|
| Plan touches more state than dry-run preview suggests | Low (every step is explicit) | Operator confirms and gets unexpected changes | Plan must enumerate every mutation; lint flag SHOW-*-001 series | Per-step rollback via undo (MA2 Oops); or restore from save before build |
| Strategy defaults don't match operator's actual style | High initially | Operator manually edits generated show; friction | Operator feedback collected as new lint rules / strategy tweaks | Operator edits; strategies documented for transparency |
| Build conflicts with operator's existing show content | Medium | Existing objects overwritten | Lint flag PRESET-NUM-001 detects duplicate slots; dry-run shows conflicts | Save_As versioned before build; restore prior |
| Strategy tables (Appendix B) get out of date with skill conventions | Medium over time | Generated shows look "old-style" | XC1 keeps skills in sync; quarterly review of strategies vs skills | Update strategy table |

## G.7 — T5 layout builder

| Risk | Likelihood | Blast | Detection | Rollback |
|---|---|---|---|---|
| Layout collides with operator's existing screen content | Medium | Existing layout overwritten | dry_run preview shows full grid; LAYOUT-COLLIDE-001 lint rule | Save_As before applying; restore from save |
| Template content references targets not in show | Medium | Dangling references in layout | LAYOUT-DANGLE-001 lint rule | Tool refuses to apply if any DANGLE-001 errors present |
| Layout exceeds screen resolution | Low | Cut off content | LAYOUT-SIZE-001 lint rule | Operator picks different template or screen |

## G.8 — T6 color picker disambig

| Risk | Likelihood | Blast | Detection | Rollback |
|---|---|---|---|---|
| Plugin detection misses plugin (false negative) | Low | Skill falls back to manual path; slower but correct | Live verification on operator's setup | Operator manually invokes plugin |
| Plugin detection returns stale cache | Low | Operator-installed plugin not surfaced for ~60s | Cache TTL is short; `use_cache=False` parameter for fresh query | Force-refresh via parameter |
| Skill body's "First decision" section formatted wrongly | Low | Router can't extract it | Test parses each skill's first decision section | Fix the skill (XC1 work) |

## G.9 — T7 busking template

| Risk | Likelihood | Blast | Detection | Rollback |
|---|---|---|---|---|
| Companion config doesn't import in v4 | Medium until golden fixture validated | Companion side broken; MA2 side fine | Round-trip test against golden fixture | Operator builds Companion page manually; MA2 side unaffected |
| Companion v3.x users get broken config | Medium | Config rejected | `companion_version` parameter warns; tier-2 mock test for v3 schema | Default to v4; v3 explicitly opt-in with warning |
| Busking template doesn't match operator's workflow expectations | High initially | Operator reshuffles banks | Operator feedback; refine strategy tables | Standard MA2 page-clear and rebuild |
| Conflicts with existing executor assignments on target page | Medium | Existing executors overwritten | dry_run preview; lint BUSK-CONF-001 | Save_As before; clear page first if confirmed |

## G.10 — T8 preset library architect

| Risk | Likelihood | Blast | Detection | Rollback |
|---|---|---|---|---|
| Plan conflicts with operator's existing presets | Medium | Existing presets potentially overwritten | dry_run shows every slot; lint PRESET-NUM-001 (duplicate numbers) | Save_As before; restore prior; or skip duplicate slots option |
| Reference fixture choice differs from operator's intuition | Medium | Operator's mental model breaks | Tool returns `reference_fixtures` decision in plan; operator can override via `patch_filter` | Override reference choice in next call |
| Universal/selective decision wrong for a particular attribute | Medium | Presets miss-scoped | Lint PRESET-SCOPE-001/002; operator review of coverage report | Re-architect with corrected hints |
| Strategy is "full-coverage" but rig is too small to benefit | Low | Wasted preset slots; harmless | Coverage report shows utilization | Operator switches to minimal-viable strategy |

## G.11 — XC1 skill checklists

| Risk | Likelihood | Blast | Detection | Rollback |
|---|---|---|---|---|
| Checklist content is wrong (claims a practice that's not best-practice) | Medium | Operator follows bad guidance | Operator review of checklists; cross-reference with MA Lighting training material | Edit the checklist (low cost) |
| Checklist length bloats skill body, dilutes signal | Low | Skills feel cluttered | Per-skill review during XC1 work | Trim checklist to top 5-10 items |
| Inconsistency between checklists across related skills | Medium | Operator confused by conflicting advice | Cross-skill review during XC1 | Reconcile during review |

## G.12 — XC2 expert_lint module

| Risk | Likelihood | Blast | Detection | Rollback |
|---|---|---|---|---|
| Lint rules have false positives (warn about things that are fine) | High initially | Operator ignores all warnings; defeats purpose | Calibration during shakedown; require zero error-level false positives in test corpus | Disable rule or lower severity (warn → advice) |
| Lint rules have false negatives (miss real issues) | Medium | Bad output ships unchallenged | New rules added as gaps surface from operator feedback | Add the rule |
| Lint rule conflicts with strategy defaults | Medium | Generated output fails its own lint | Per-strategy lint suites; resolve conflict per case | Update either the rule or the strategy; document |
| Lint module performance — slow on large plans | Low | Tool latency increases | Per-rule timing; flag any rule >50ms | Optimize hot rule or batch-evaluate |

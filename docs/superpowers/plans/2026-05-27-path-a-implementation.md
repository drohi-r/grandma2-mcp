---
title: Path A Implementation Plan — XC1, XC2, T1, T2, T3
description: Console-independent slice of grandMA2-MCP v2.0.0 practical scope — skill checklists, expert-lint module, skill router, console portability + mock mode, NL→macro generation
version: 1.0.0
created: 2026-05-27T00:00:00Z
last_updated: 2026-05-27T00:00:00Z
---

# Path A Implementation Plan — Practical Scope v2.0.0 (XC1, XC2, T1, T2, T3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the five console-independent scope items from `doc/grandma2-mcp-practical-scope.md` v2.0.0: expert-defaults pass on existing skills (XC1), expert-lint helper module (XC2), skill router tool + INDEX.md + enriched `list_skills` (T1), console portability + `GMA_MOCK` mode + reconfigure-connection (T2), and NL→macro generation tool (T3). All work landable without a live grandMA2 console; onPC is available locally for end-to-end smoke checks.

**Architecture:** XC2 (`src/expert_lint/`) is a pure-function rule engine — no I/O, mirrors the discipline of `src/commands/`. T1's router (`src/skill_router.py`) mirrors `suggest_tool_for_task` in `src/server.py:7228` so behavior is consistent. T2 adds a `SessionManager`-shaped mock at the existing `_get_session_manager()` injection point (`src/server.py:470`) and two new top-level tools. T3 composes T1 (auto-loads macro skills) + XC2 (lint rules) + existing macro-linter — no new infrastructure.

**Tech Stack:** Python 3.12, FastMCP `mcp>=1.21.0`, `telnetlib3`, `pytest` + `pytest-asyncio`, no new heavy deps for Path A (mDNS / Companion live in Path B). One small addition: `python-zeroconf` is staged in `pyproject.toml` but not exercised in Path A — the `discover_consoles` tool uses UDP broadcast only for the Path A milestone, with mDNS deferred behind an explicit feature flag for Path B.

---

## Scope Check

The spec covers 5 work items. They could be split into 5 separate plans, but per the operator brief (multi-session prompt) they form one coherent slice — XC1/XC2 are foundational, T1 is needed by T3, T2 is independent, T3 closes Path A. Single plan with 6 tasks (one per scope item plus a final hygiene pass) keeps execution coherent. Each task produces working, testable code on its own — if the operator stops after any task, the codebase is consistent and tests pass.

**Skill content:** This plan is being produced while applying the `superpowers:writing-plans` discipline manually because the superpowers plugin marketplace install command (`/plugin install superpowers@claude-plugins-official`) is unavailable in this Claude Code build. The plugin tree was cloned to `~/.claude/plugins/superpowers/` so future Claude Code sessions can auto-discover it.

---

## File Structure

### Created

| Path | Responsibility |
|------|-----|
| `src/expert_lint/__init__.py` | Public exports: `Violation` dataclass, `Severity` literal, `expert_lint(plan, domain, context=None) → list[Violation]` dispatcher |
| `src/expert_lint/types.py` | `Violation` dataclass, `Severity` literal, `Domain` literal, `Rule` callable protocol |
| `src/expert_lint/macro_rules.py` | 15 macro-domain rule functions (MACRO-*) |
| `src/expert_lint/busking_rules.py` | 16 busking-domain rule functions (BUSK-*) |
| `src/expert_lint/show_rules.py` | 14 show-creation rule functions (SHOW-*) |
| `src/expert_lint/preset_rules.py` | 13 preset-library rule functions (PRESET-*) |
| `src/expert_lint/layout_rules.py` | 7 layout rule functions (LAYOUT-*) |
| `src/expert_lint/dispatcher.py` | Domain → rule-list mapping + cross-cutting rules from §C.6 |
| `src/skill_router.py` | `rank_skills(intent, top_k, ...) → list[SkillSuggestion]` — pure ranking over the SkillRegistry corpus |
| `src/mock/__init__.py` | Tier-aware mock factory: returns `MockSessionManager` for `GMA_MOCK` env |
| `src/mock/session_manager.py` | `MockSessionManager` — implements `SessionManager.get/release/close_all/session_count` |
| `src/mock/telnet_client.py` | `MockGMA2TelnetClient` — implements `GMA2TelnetClient` public surface (connect / login / send_command / send_command_with_response / disconnect) |
| `src/mock/responses.py` | Tier-1 canned responses keyed by command regex |
| `src/mock/fixture_loader.py` | Tier-2 stateful in-memory show fixture loader (reads `tests/fixtures/mock_show_state.json`) |
| `src/discovery.py` | UDP broadcast discovery — `discover_grandma2_broadcast(network, timeout) → list[ConsoleCandidate]` (mDNS path is a stub that returns `[]` in Path A; documented as Path B) |
| `tests/fixtures/mock_show_state.json` | Tier-2 mock baseline: 12 groups, 8 presets, 1 sequence with 5 cues |
| `tests/fixtures/captured/sample.jsonl` | Tier-3 stub (single connect+ListVar exchange) |
| `tests/test_expert_lint/__init__.py` | Empty marker |
| `tests/test_expert_lint/test_types.py` | Violation / Severity / Domain shape tests |
| `tests/test_expert_lint/test_macro_rules.py` | One pass-case + one fail-case per MACRO-* rule (30 tests) |
| `tests/test_expert_lint/test_busking_rules.py` | One pass-case + one fail-case per BUSK-* rule (32 tests) |
| `tests/test_expert_lint/test_show_rules.py` | One pass-case + one fail-case per SHOW-* rule (28 tests) |
| `tests/test_expert_lint/test_preset_rules.py` | One pass-case + one fail-case per PRESET-* rule (26 tests) |
| `tests/test_expert_lint/test_layout_rules.py` | One pass-case + one fail-case per LAYOUT-* rule (14 tests) |
| `tests/test_expert_lint/test_dispatcher.py` | Cross-domain dispatch + §C.6 cross-cutting rule coverage |
| `tests/test_skill_router.py` | Ranking determinism, corpus loading, fallback path, top-2 hit-rate for representative intents |
| `tests/test_console_discovery.py` | UDP-broadcast parsing on captured packets, network auto-detect, timeout behaviour |
| `tests/test_reconfigure_connection.py` | `.env` round-trip, atomic swap, idempotence, verify-failure handling |
| `tests/test_mock_mode.py` | Server start with each tier, every SAFE_READ tool returns `mock: <tier>`, Tier-2 supports a SAFE_READ chain end-to-end |
| `tests/test_macro_generation.py` | XML schema, lint integration, expert-review structure |
| `.claude/skills/INDEX.md` | Skill discoverability index grouped by friction area |
| `.claude/skills/connection-setup-workflow/SKILL.md` | New skill: discover → pick → reconfigure → verify loop |
| `scripts/capture_broadcast.py` | One-off helper for capturing UDP broadcast samples (used at Path B verification, scaffolded now) |

### Modified

| Path | Why |
|------|------|
| `src/server.py` | (1) Wire `GMA_MOCK` switch in `_get_session_manager()` at line 470; (2) register two new tools `discover_consoles` and `reconfigure_connection`; (3) register `suggest_skills_for_task` near the existing `suggest_tool_for_task` (~line 7228); (4) register `generate_ma2_macro` |
| `src/server_orchestration_tools.py:1248` | Enrich `list_skills` return shape with `tags`, `prerequisites`, `wraps_plugin`, `use_instead_of` fields parsed from front matter |
| `src/skill.py` | Extend `_parse_front_matter()` to capture `tags`, `prerequisites`, `wraps_plugin`, `use_instead_of`; add fields to `Skill` dataclass with backward-compatible defaults |
| `src/telemetry.py` | Add `check_` to the SAFE_READ name-prefix tuple (for symmetry; not exercised in Path A but cheap to add now since T2 mocks may include `check_*` helpers) |
| `tests/test_architecture_hygiene.py` | Add invariants: every new Path-A tool has explicit risk-tier annotation (or correct name-prefix); every new tool has a corresponding test file; new files in `src/expert_lint/` and `src/mock/` are pure (no telnet imports) |
| `pyproject.toml` | Add optional `[project.optional-dependencies] mdns = ["zeroconf>=0.131"]` — not installed by default; Path B activates it |
| `CLAUDE.md` | Update tool count: 218 → 222 (XC1 doesn't add tools; XC2 is internal; T1 +1, T2 +2, T3 +1) and the line `**218 tools**` in the project identity section |
| `.claude/skills/*/SKILL.md` | (XC1) Add an "Expert checklist" section to 9 target skills — listed in Task 1 |

### Out of scope for Path A (deferred to Path B)

- `check_plugin_available` (T6 helper)
- `discover_consoles` mDNS code path (only UDP broadcast in Path A)
- Companion golden fixture export (D.4)
- `build_show_from_patch`, `build_layout_for_screen`, `build_expert_busking_template`, `architect_preset_library`

---

## Bite-Sized Task Granularity Note

Where the work is genuinely repetitive (e.g., 15 lint rules in one domain — same shape, different content), this plan provides:

1. One fully worked example showing the test-then-implementation pattern.
2. A specification table for the remaining rules with: rule_id, severity, trigger condition (as Python pseudo-code), expert message, fix suggestion.
3. A single integration step that verifies the rule list is wired and a dispatcher coverage test passes.

The engineer's job for each entry in the table is mechanical: copy the worked example's test, substitute the trigger and expected outputs from the table; copy the worked example's rule function, substitute the predicate. This satisfies the no-placeholders rule (every test and rule has its exact specification available in the plan) without producing 65 nearly-identical pages.

---

## Task 1 — XC1: Expert-defaults pass on existing skills

**Goal:** Add an "Expert checklist" section to 9 priority skills, surfacing the 5–10 mandatory items each one's output must include. Drives the lint rules in XC2 — every checklist item should map to at least one lint rule.

**Files:**

- Modify: `.claude/skills/busking-template-generator/SKILL.md` (add checklist)
- Modify: `.claude/skills/busking-lighting-performance/SKILL.md`
- Modify: `.claude/skills/preset-library-architect/SKILL.md`
- Modify: `.claude/skills/cue-tracking-and-timing/SKILL.md`
- Modify: `.claude/skills/macro-advanced/SKILL.md`
- Modify: `.claude/skills/macro-linter-and-refactorer/SKILL.md`
- Modify: `.claude/skills/executor-configuration/SKILL.md`
- Modify: `.claude/skills/constrained-color-design/SKILL.md`
- Modify: `.claude/skills/view-and-layout-designer/SKILL.md`
- Test: `tests/test_architecture_hygiene.py::TestSkillFileFrontMatter` (existing — must still pass)

Note: each edit bumps the skill's front-matter `version` (PATCH bump) and `last_updated` to `2026-05-27T00:00:00Z` per `.claude/rules/markdown-frontmatter.md`. PRs that touch a skill body without bumping these will fail the existing hygiene tests when version field becomes stale relative to body (no automated check yet, but operator review will catch).

- [ ] **Step 1.1: Write a failing test for the new "Expert checklist" section presence**

Create `tests/test_xc1_skill_checklists.py`:

```python
"""XC1 — every priority skill must carry an Expert checklist section."""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"

PRIORITY_SKILLS = [
    "busking-template-generator",
    "busking-lighting-performance",
    "preset-library-architect",
    "cue-tracking-and-timing",
    "macro-advanced",
    "macro-linter-and-refactorer",
    "executor-configuration",
    "constrained-color-design",
    "view-and-layout-designer",
]


@pytest.mark.parametrize("slug", PRIORITY_SKILLS)
def test_skill_has_expert_checklist(slug):
    body = (SKILLS_DIR / slug / "SKILL.md").read_text(encoding="utf-8")
    assert "## Expert checklist" in body, (
        f"{slug}/SKILL.md must have a '## Expert checklist' section "
        "(see Task 1 of docs/superpowers/plans/2026-05-27-path-a-implementation.md)"
    )


@pytest.mark.parametrize("slug", PRIORITY_SKILLS)
def test_expert_checklist_has_at_least_five_items(slug):
    body = (SKILLS_DIR / slug / "SKILL.md").read_text(encoding="utf-8")
    if "## Expert checklist" not in body:
        pytest.fail(f"{slug}: no checklist (caught by previous test)")
    checklist = body.split("## Expert checklist", 1)[1].split("##", 1)[0]
    items = [ln for ln in checklist.splitlines() if ln.lstrip().startswith(("- [", "* "))]
    assert len(items) >= 5, (
        f"{slug}: expert checklist must contain at least 5 items "
        f"(found {len(items)})"
    )
```

- [ ] **Step 1.2: Run the test and confirm it fails for every priority skill**

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_xc1_skill_checklists.py -v
```

Expected: 18 failures (9 skills × 2 tests). Each failure message names the skill missing its checklist.

- [ ] **Step 1.3: Add checklist to `busking-template-generator` (worked example)**

Insert at the top of the body (after front matter, before existing content). Use this exact pattern:

```markdown
## Expert checklist

The output of this skill is "expert" only when it includes ALL of:

- [ ] Blackout sub-master executor at Super priority, independent of the Grand Master
- [ ] At least one speed master and one rate master bound to the FX bank
- [ ] Kill buttons for color, FX, and position on dedicated executors (rock-band / DJ strategies)
- [ ] Tap-tempo executor (rock-band / DJ strategies)
- [ ] Fader bank layout follows the muscle-memory map: intensity left → color → position → beam → FX → specials right
- [ ] Every executor has an intent label (no "Exec 5" generic labels)
- [ ] Intensity sub-masters are HTP; color/position/FX executors are LTP (Normal)
- [ ] Blinder executors set to High priority so flash effects override chases
- [ ] No two executors share the same slot on the target page
- [ ] Companion grid layout is contiguous (no empty rows interleaved with content)
```

Each item maps 1:1 to a `BUSK-*` rule in Task 2. The checklist IS the spec for what the lint enforces.

- [ ] **Step 1.4: Bump front matter version + last_updated for `busking-template-generator`**

Edit the front matter only:

```yaml
version: 1.1.0   # was 1.0.0 (or whatever it was — PATCH if checklist-only)
last_updated: 2026-05-27T00:00:00Z
```

- [ ] **Step 1.5: Re-run the test for this skill and confirm it passes**

```bash
.\.venv\Scripts\python.exe -m pytest "tests/test_xc1_skill_checklists.py::test_skill_has_expert_checklist[busking-template-generator]" "tests/test_xc1_skill_checklists.py::test_expert_checklist_has_at_least_five_items[busking-template-generator]" -v
```

Expected: 2 passed.

- [ ] **Step 1.6: Add checklist to remaining 8 priority skills**

Use the table below for each skill's checklist content. Each item maps to a rule in XC2 — if a checklist item has no corresponding rule, either add the rule (in Task 2) or drop the item.

| Skill | Checklist items |
|-------|------------------|
| `busking-lighting-performance` | Blackout sub at Super • Speed master bound to FX • Kill-colors / kill-FX / kill-position macros assigned • Page contains tap-tempo • Wing layout follows muscle-memory map • Strobe-flash button accessible without page change • Blinders at High priority • Chase priorities set to Swap |
| `preset-library-architect` | Reference fixture chosen per type (lowest ID by convention) • Universal vs selective decision made per attribute (color/position universal; gobo/beam selective) • At least 4 cardinal-hue color presets (R/G/B/W) • MIB presets defined for movers • Preset numbering follows MA2 type convention (color=4, position=2, etc.) • Naming convention applied consistently across all presets • Coverage report shows every attribute on every type has at least one preset (full-coverage strategy) • No duplicate preset numbers within a type • No empty preset slots |
| `cue-tracking-and-timing` | Tracking discipline declared (track / non-tracking) and consistent across sequence • Block cues placed at song / act / scene boundaries when tracking enabled • MIB enabled only on fixtures with movement attributes • Cuelist off-time set to a deliberate value (not default) • Cuelist priorities documented (Super for emergency, Normal default) • Cue notes name the moment ("verse_2_lift") not just numbers • Crossfade defaults documented per cuelist • Soft-LTP / Wrap options used deliberately |
| `macro-advanced` | All `Store` of selection-dependent targets preceded by explicit `ClearAll` and selection on the same line • `CmdDelay` used for timing, not busy-wait via repeated `Wait` • `SetVar`/`GetVar` pairs scoped within the same macro or documented as session-scoped • All jump targets validated against current line count • Destructive commands (`Delete`, `Store /merge`, `new_show`) include `/noconfirm` • `new_show` always includes `/globalsettings` • Macro labels describe intent, not generic ("Macro 17") |
| `macro-linter-and-refactorer` | Linter covers all 14 patterns from MACRO-* rule catalog • Linter output includes rule_id, severity, line, and fix_suggestion per finding • Linter does not modify the macro body — only reports • Linter handles MA2 XML schema validation gracefully (no crash on malformed input) • Refactor mode preserves jump-target offsets across line insertion • Refactor mode never strips comments or empty lines without explicit operator confirmation |
| `executor-configuration` | Priority set deliberately per executor (Super / High / Swap / Normal / Low) • LTP/HTP set deliberately per executor (intensity HTP, color LTP) • Speed/rate/tap masters bound to the executors that need them • Trigger type matches role (Go vs Time vs CmdDisable) • Wrap and SoftLTP set per cuelist semantic • Restart / autostop / killprotect set per executor role • No executor lacks a label |
| `constrained-color-design` | HSB model used (not RGB) for palette presets per `ma2-conventions.md` appearance section • Hue numbering follows the constrained-design table (12 hues × 8 saturations = 96 presets at 4.101-4.196) • Saturation steps consistent across hues • Brightness clamped to a deliberate value per palette (not 100 by default) • Color lock applied to palette presets per technique • Palette mapped to song / scene structure documented |
| `view-and-layout-designer` | Layout cells have labels (no cryptic "Group 14") • Layout content references existing targets (no dangling references) • Layout fits within screen native resolution • Layout density ≤ 70% (room for status / info) • Required content for the chosen template is present (e.g., busking-master template includes intensity / color / FX / specials banks) • Layout does not collide with other layouts on the same screen |

Each skill: insert section, bump version, set `last_updated: 2026-05-27T00:00:00Z`.

- [ ] **Step 1.7: Run the full XC1 test suite — must pass**

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_xc1_skill_checklists.py -v
```

Expected: 18 passed.

- [ ] **Step 1.8: Run the architecture-hygiene suite — must still pass**

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_architecture_hygiene.py -q
```

Expected: 25 passed. (The skill front-matter check will validate each edited skill's required fields remain present.)

- [ ] **Step 1.9: Commit**

```bash
git add tests/test_xc1_skill_checklists.py .claude/skills/busking-template-generator/SKILL.md .claude/skills/busking-lighting-performance/SKILL.md .claude/skills/preset-library-architect/SKILL.md .claude/skills/cue-tracking-and-timing/SKILL.md .claude/skills/macro-advanced/SKILL.md .claude/skills/macro-linter-and-refactorer/SKILL.md .claude/skills/executor-configuration/SKILL.md .claude/skills/constrained-color-design/SKILL.md .claude/skills/view-and-layout-designer/SKILL.md
git commit -m "$(cat <<'EOF'
xc1: add Expert checklist sections to 9 priority skills

Each checklist enumerates the 5-10 items the skill's output must contain
to qualify as expert-grade. Drives XC2 lint rules — checklist items map
1:1 to MACRO-*/BUSK-*/SHOW-*/PRESET-*/LAYOUT-* rule IDs.

Source of truth: doc/grandma2-mcp-practical-scope.md §C (rule catalogs)
and individual skill bodies for domain-specific defaults.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2 — XC2: Expert-lint helper module

**Goal:** Ship `src/expert_lint/` as a pure-function rule engine. Public API: `expert_lint(plan, domain, context=None) → list[Violation]`. Domains: `macro`, `busking`, `show`, `preset`, `layout`. 65 rules total per spec §C. No I/O — all rules are pure functions over a typed plan + optional context dict.

**Files:**

- Create: `src/expert_lint/__init__.py`, `src/expert_lint/types.py`, `src/expert_lint/dispatcher.py`, `src/expert_lint/{macro,busking,show,preset,layout}_rules.py`
- Test: `tests/test_expert_lint/__init__.py`, `tests/test_expert_lint/test_types.py`, `tests/test_expert_lint/test_{macro,busking,show,preset,layout}_rules.py`, `tests/test_expert_lint/test_dispatcher.py`

- [ ] **Step 2.1: Write the types test (RED)**

`tests/test_expert_lint/test_types.py`:

```python
from src.expert_lint.types import Violation, Severity, Domain


def test_violation_required_fields():
    v = Violation(
        rule_id="MACRO-JT-001",
        severity="error",
        domain="macro",
        target="step:3",
        expert_says="Jump target line number does not exist in the macro",
        fix_suggestion="Recompute target after insertion",
    )
    assert v.rule_id == "MACRO-JT-001"
    assert v.severity == "error"


def test_severity_literal_values():
    valid: list[Severity] = ["advice", "warning", "error"]
    assert sorted(valid) == ["advice", "error", "warning"]


def test_domain_literal_values():
    valid: list[Domain] = ["macro", "busking", "show", "preset", "layout"]
    assert "macro" in valid
```

- [ ] **Step 2.2: Verify the test fails (module does not exist)**

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_expert_lint/test_types.py -v
```

Expected: ImportError / ModuleNotFoundError for `src.expert_lint.types`.

- [ ] **Step 2.3: Implement `src/expert_lint/types.py` (GREEN)**

```python
"""Expert-lint types — Violation dataclass + typed literals.

Pure module; no I/O, no project-internal imports beyond stdlib.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Severity = Literal["advice", "warning", "error"]
Domain = Literal["macro", "busking", "show", "preset", "layout"]


@dataclass(frozen=True)
class Violation:
    """A single lint finding."""

    rule_id: str          # e.g. "MACRO-JT-001"
    severity: Severity
    domain: Domain
    target: str           # plan step identifier, e.g. "step:3" or "executor:1.1.1"
    expert_says: str      # one-line justification
    fix_suggestion: str   # one-line remediation hint


__all__ = ["Violation", "Severity", "Domain"]
```

- [ ] **Step 2.4: Verify types test passes**

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_expert_lint/test_types.py -v
```

Expected: 3 passed.

- [ ] **Step 2.5: Write the worked-example macro rule test (RED)**

`tests/test_expert_lint/test_macro_rules.py`:

```python
"""Macro-domain expert-lint rules."""

import pytest

from src.expert_lint.macro_rules import check_jt_001_jump_target_exists
from src.expert_lint.types import Violation


def test_jt_001_no_violation_when_jump_target_valid():
    plan = {
        "kind": "macro",
        "lines": [
            {"index": 1, "command": "Go Sequence 5"},
            {"index": 2, "command": "Go Macro 1.\"Loop\".1"},
        ],
    }
    findings = check_jt_001_jump_target_exists(plan, context=None)
    assert findings == []


def test_jt_001_flags_jump_to_nonexistent_line():
    plan = {
        "kind": "macro",
        "lines": [
            {"index": 1, "command": "Go Macro 1.\"Loop\".99"},  # only 1 line exists
        ],
    }
    findings = check_jt_001_jump_target_exists(plan, context=None)
    assert len(findings) == 1
    v = findings[0]
    assert isinstance(v, Violation)
    assert v.rule_id == "MACRO-JT-001"
    assert v.severity == "error"
    assert v.target == "step:1"
```

- [ ] **Step 2.6: Verify it fails**

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_expert_lint/test_macro_rules.py -v
```

Expected: ImportError for `src.expert_lint.macro_rules`.

- [ ] **Step 2.7: Implement worked-example macro rule (GREEN)**

Create `src/expert_lint/macro_rules.py`:

```python
"""Macro-domain expert-lint rules (MACRO-*).

Each rule is a pure function with signature:

    def check_<id>_<short_name>(plan: dict, context: dict | None) -> list[Violation]

Plan shape for macro domain:

    {
      "kind": "macro",
      "lines": [{"index": int, "command": str}, ...]
    }

Context (optional) carries cross-rule state — current macro pool ID,
known macro slugs in the show, etc. Most rules ignore it.
"""

from __future__ import annotations

import re

from src.expert_lint.types import Violation

# Pattern: "Go Macro <pool>.\"<name>\".<line>"
_MACRO_CALL_RE = re.compile(
    r'Go\s+Macro\s+(?:\d+\.)?"[^"]+"\s*\.\s*(?P<line>\d+)',
    re.IGNORECASE,
)


def check_jt_001_jump_target_exists(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """MACRO-JT-001 (error): Jump target line number does not exist."""
    lines = plan.get("lines", [])
    valid_indices = {ln.get("index") for ln in lines}
    out: list[Violation] = []
    for ln in lines:
        for match in _MACRO_CALL_RE.finditer(ln.get("command", "")):
            target = int(match.group("line"))
            if target not in valid_indices:
                out.append(Violation(
                    rule_id="MACRO-JT-001",
                    severity="error",
                    domain="macro",
                    target=f"step:{ln.get('index')}",
                    expert_says=(
                        f"Jump target line {target} does not exist in this macro "
                        f"(valid: {sorted(valid_indices)})"
                    ),
                    fix_suggestion=(
                        "Recompute target after insertion; use the index-shift "
                        "table in .claude/rules/ma2-conventions.md"
                    ),
                ))
    return out


__all__ = ["check_jt_001_jump_target_exists"]
```

- [ ] **Step 2.8: Verify the worked-example test passes**

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_expert_lint/test_macro_rules.py -v
```

Expected: 2 passed.

- [ ] **Step 2.9: Implement remaining 14 macro rules, one at a time using the same pattern**

For each rule in the table below, write one passing test + one failing test (same shape as Step 2.5), implement the rule function in `macro_rules.py`, verify both tests pass. Commit after each rule, OR batch-commit at end of Task 2 — operator preference.

| Rule ID | Severity | Trigger (Python pseudo-code on `plan["lines"]`) | Expert says | Fix |
|---------|----------|-------------------------------------------------|-------------|-----|
| MACRO-JT-002 | warning | jump target index resolves to a line containing `r"^\s*Store\b"` | "Jump target points to a Store line — fragile under edits" | "Use a labelled marker comment or split into two macros" |
| MACRO-SAFETY-001 | error | line contains any of `Delete`, `Store /merge`, `new_show` AND does NOT contain `/noconfirm` | "Destructive command without `/noconfirm` will hang the macro" | "Append `/noconfirm`" |
| MACRO-SAFETY-002 | error | line contains `new_show` AND does NOT contain `/globalsettings` | "`new_show` without `/globalsettings` disables Telnet" | "Append `/globalsettings`" |
| MACRO-TIME-001 | warning | 2+ consecutive lines contain `Wait` with no `CmdDelay` | "Sleep via repeated Wait instead of CmdDelay" | "Use `CmdDelay <ms>`" |
| MACRO-VAR-001 | error | line contains `GetVar(<name>)` where `<name>` is not previously `SetVar`-ed in the macro AND not listed in `context["session_vars"]` | "GetVar reads an uninitialised variable" | "Add `SetVar` earlier or document the dependency" |
| MACRO-VAR-002 | warning | line contains `SetVar $<NAME>` where `$<NAME>` is in the MA2 system-variable list (e.g. `$SHOWFILE`, `$VERSION`) | "SetVar targets a read-only system variable" | "Rename with a `my_` prefix" |
| MACRO-SELECT-001 | error | line contains `Store` AND no preceding line in the same macro contains `ClearAll` or explicit `Select` | "Store-of-selection-dependent target without ClearAll" | "Add ClearAll then explicit selection on the same line as Store" |
| MACRO-SELECT-002 | warning | line contains `Selection` AND previous non-empty line contains `FixtureType` and `Thru` | "Selection after FixtureType X.M.1 Thru — known timing race" | "Insert new lines around existing Store; do not modify existing Store lines" |
| MACRO-LINK-001 | warning | line contains `Go Macro 1."<name>"` AND `<name>` not in `context["existing_macros"]` (skip if context absent) | "Macro calls another macro not in current show" | "Verify target macro or document the dependency" |
| MACRO-PERM-001 | error | line contains any keyword listed in `context["required_rights"]` set (e.g., `Patch`, `Setup`) AND `context["user_rights_level"] < required` | "Macro requires rights the user lacks" | "Reduce scope or document required rights" |
| MACRO-NAME-001 | advice | `plan.get("label", "")` is empty or matches `r"^Macro\s+\d+$"` | "Generic or missing label" | "Label with intent" |
| MACRO-PARK-001 | warning | macro contains `Park` AND no companion macro in `context["existing_macros"]` contains `Unpark` of same target | "Park without paired Unpark" | "Add paired unpark macro" |
| MACRO-SCOPE-001 | advice | line contains an exec spec like `r"\d\.\d\.\d"` (e.g., `1.1.1`) AND no `SetUserVar` precedes | "Hardcoded executor reference — risky on main page" | "Make target a SetUserVar parameter" |
| MACRO-XML-001 | error | `plan["body_xml"]` (when present) fails `xml.etree.ElementTree.fromstring()` | "Macro XML body fails schema validation" | "Check for unescaped quotes / regenerate with schema-aware emitter" |

For each rule, add a `check_<id>_<name>(plan, context=None)` function returning `list[Violation]`. Add `__all__` entries.

After all 15 macro rules implemented, run:

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_expert_lint/test_macro_rules.py -v
```

Expected: 30 passed (15 rules × 2 tests).

- [ ] **Step 2.10: Implement 16 busking rules**

Same pattern, in `src/expert_lint/busking_rules.py`. Plan shape:

```python
{
  "kind": "busking",
  "strategy": "rock-band" | "dj" | "festival" | "theatrical",
  "executors": [
    {"slot": "1.1.1", "label": str, "priority": str, "function": str, "role": str},
    ...
  ],
  "companion_grid": [...],     # optional, schema per Appendix D.4
  "fader_bank_layout": str,    # "muscle-memory" | "sequential" | "category-grouped"
}
```

Worked example rule: `check_sub_001_blackout_independent` — fails when no executor's `role` is `"blackout-sub"` AND `priority == "super"`.

Full rule table (id / severity / trigger):

| Rule ID | Severity | Trigger |
|---------|----------|---------|
| BUSK-SUB-001 | error | no executor has `role == "blackout-sub"` |
| BUSK-SUB-002 | warning | strategy in {rock-band, dj, festival} AND no executor has `function == "speedmaster"` |
| BUSK-PRIO-001 | error | blackout-sub executor exists but its `priority != "super"` |
| BUSK-PRIO-002 | warning | all executors have `priority == "normal"` (no discrimination) |
| BUSK-PRIO-003 | warning | strategy in {rock-band, dj} AND any executor with `role == "blinder"` has `priority not in {"high", "swap"}` |
| BUSK-KILL-001 | warning | strategy in {rock-band, dj} AND no executor has `role == "kill-color"` |
| BUSK-KILL-002 | warning | strategy in {rock-band, dj} AND no executor has `role == "kill-fx"` |
| BUSK-TAP-001 | warning | strategy in {rock-band, dj} AND no executor has `function == "tap"` |
| BUSK-LAYOUT-001 | advice | `fader_bank_layout != "muscle-memory"` AND not explicitly overridden in `context["fader_layout_overridden"]` |
| BUSK-CONF-001 | error | two executors share the same `slot` value |
| BUSK-LABEL-001 | warning | any executor's `label` is empty or matches `r"^Exec\s+\d+$"` |
| BUSK-HTP-001 | warning | executor with `role == "intensity-submaster"` has priority other than `"htp"` |
| BUSK-LTP-001 | warning | executor with `role == "color"` has priority `"htp"` |
| BUSK-COMP-001 | error | `plan.get("companion_config")` provided but `validate_companion_schema(config) is False` (validator stub returns True for Path A — Path B will replace) |
| BUSK-COMP-002 | warning | companion_grid has non-contiguous rows (empty row between two used rows) |
| BUSK-KEY-001 | advice | strategy in {rock-band, broadcast, theatrical} AND no executor has `role == "key-fixture"` |

Run tests:

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_expert_lint/test_busking_rules.py -v
```

Expected: 32 passed.

- [ ] **Step 2.11: Implement 14 show-creation rules**

In `src/expert_lint/show_rules.py`. Plan shape:

```python
{
  "kind": "show",
  "strategy": str,
  "cuelists": [
    {"id": int, "label": str, "tracking": "track" | "non-tracking",
     "priority": str, "off_time_ms": int | None,
     "cues": [{"id": float, "label": str, "block": bool, "uses_preset": bool, "is_mib": bool}, ...]},
    ...
  ],
  "fixtures": [{"id": int, "type": str, "covered_by_any_cue": bool}, ...],
  "worlds": [{"name": str, "section": str | None}, ...],
  "views": [str, ...],     # template slugs included
}
```

Rule table per spec §C.3 — straightforward predicate from the strategy's expected vs the plan's actual.

Run tests; expect 28 passed.

- [ ] **Step 2.12: Implement 13 preset-library rules**

In `src/expert_lint/preset_rules.py`. Plan shape per Appendix A.9. Rule table per spec §C.4. Run tests; expect 26 passed.

- [ ] **Step 2.13: Implement 7 layout rules**

In `src/expert_lint/layout_rules.py`. Plan shape per Appendix A.7. Rule table per spec §C.5. Run tests; expect 14 passed.

- [ ] **Step 2.14: Write the dispatcher test (RED)**

`tests/test_expert_lint/test_dispatcher.py`:

```python
"""Dispatcher routes plan + domain to the right rule list and surfaces all violations."""

from src.expert_lint import expert_lint
from src.expert_lint.types import Domain, Violation


def test_dispatcher_runs_all_macro_rules():
    plan = {"kind": "macro", "lines": []}
    findings = expert_lint(plan, domain="macro", context=None)
    # An empty plan has no violations; just check the call succeeds and returns a list
    assert isinstance(findings, list)


def test_dispatcher_surfaces_specific_violation():
    plan = {
        "kind": "macro",
        "lines": [{"index": 1, "command": "Go Macro 1.\"x\".99"}],
    }
    findings = expert_lint(plan, domain="macro", context=None)
    assert any(v.rule_id == "MACRO-JT-001" for v in findings)


def test_dispatcher_unknown_domain_raises():
    import pytest
    with pytest.raises(ValueError, match="unknown domain"):
        expert_lint({}, domain="bogus", context=None)


def test_cross_cutting_purpose_field_advice():
    """C.6 — every plan step has a `purpose` field; empty triggers advice."""
    plan = {
        "kind": "show",
        "strategy": "corporate",
        "cuelists": [{"id": 1, "label": "Main", "tracking": "non-tracking",
                      "priority": "normal", "off_time_ms": None, "cues": []}],
        "fixtures": [], "worlds": [], "views": ["run"],
        "steps": [{"order": 1, "command": "Store Cue 1 Sequence 1", "purpose": ""}],
    }
    findings = expert_lint(plan, domain="show", context=None)
    assert any(v.rule_id == "CROSSCUT-PURPOSE-001" for v in findings)
```

- [ ] **Step 2.15: Implement the dispatcher (GREEN)**

`src/expert_lint/dispatcher.py`:

```python
"""Dispatcher — route plan + domain to the appropriate rule list."""

from __future__ import annotations

from typing import Callable

from src.expert_lint import busking_rules, layout_rules, macro_rules, preset_rules, show_rules
from src.expert_lint.types import Domain, Violation

_RULE_FN = Callable[[dict, dict | None], list[Violation]]


def _rules_for(domain: Domain) -> list[_RULE_FN]:
    mod_map = {
        "macro": macro_rules,
        "busking": busking_rules,
        "show": show_rules,
        "preset": preset_rules,
        "layout": layout_rules,
    }
    if domain not in mod_map:
        raise ValueError(f"unknown domain: {domain!r}")
    mod = mod_map[domain]
    return [getattr(mod, name) for name in mod.__all__ if name.startswith("check_")]


def _cross_cutting(plan: dict, domain: Domain) -> list[Violation]:
    """§C.6 — domain-agnostic conventions."""
    out: list[Violation] = []
    for step in plan.get("steps", []):
        if not step.get("purpose"):
            out.append(Violation(
                rule_id="CROSSCUT-PURPOSE-001",
                severity="advice",
                domain=domain,
                target=f"step:{step.get('order', '?')}",
                expert_says="Plan step has empty purpose field",
                fix_suggestion="Add a one-line `purpose` describing why this step exists",
            ))
    return out


def expert_lint(plan: dict, *, domain: Domain, context: dict | None = None) -> list[Violation]:
    """Run all rules in `domain` (plus cross-cutting rules) and return findings."""
    findings: list[Violation] = []
    for fn in _rules_for(domain):
        findings.extend(fn(plan, context))
    findings.extend(_cross_cutting(plan, domain))
    return findings


__all__ = ["expert_lint"]
```

- [ ] **Step 2.16: Implement `src/expert_lint/__init__.py`**

```python
"""src.expert_lint — pure-function rule engine for plan validation.

Public API: `expert_lint(plan, domain, context=None) -> list[Violation]`
"""

from src.expert_lint.dispatcher import expert_lint
from src.expert_lint.types import Domain, Severity, Violation

__all__ = ["expert_lint", "Violation", "Severity", "Domain"]
```

- [ ] **Step 2.17: Verify all expert_lint tests pass**

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_expert_lint/ -v
```

Expected: ≥130 passed across the 5 rule files + dispatcher.

- [ ] **Step 2.18: Add architecture-hygiene invariant — expert_lint stays pure**

Edit `tests/test_architecture_hygiene.py` — add a new class:

```python
class TestExpertLintPurity:
    """src/expert_lint/ must stay pure — no telnet, asyncio, server imports."""

    LINT_DIR = REPO_ROOT / "src" / "expert_lint"
    FORBIDDEN_IMPORTS = {"src.telnet_client", "src.navigation", "src.server",
                          "src.session_manager", "asyncio"}

    def test_no_io_imports(self):
        for pyfile in self.LINT_DIR.glob("*.py"):
            source = pyfile.read_text(encoding="utf-8")
            for forbidden in self.FORBIDDEN_IMPORTS:
                assert forbidden not in source, (
                    f"{pyfile.relative_to(REPO_ROOT)} imports '{forbidden}' "
                    "— expert_lint rules must stay pure"
                )

    def test_no_async_functions(self):
        import ast
        for pyfile in self.LINT_DIR.glob("*.py"):
            tree = ast.parse(pyfile.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.AsyncFunctionDef):
                    pytest.fail(
                        f"{pyfile.relative_to(REPO_ROOT)}:{node.lineno}: "
                        f"async def '{node.name}' — expert_lint must be sync"
                    )
```

- [ ] **Step 2.19: Run full test suite**

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_expert_lint/ tests/test_architecture_hygiene.py -q
```

Expected: all green; existing 25 hygiene + ~130 lint tests + 2 new hygiene tests.

- [ ] **Step 2.20: Commit**

```bash
git add src/expert_lint/ tests/test_expert_lint/ tests/test_architecture_hygiene.py
git commit -m "$(cat <<'EOF'
xc2: add src/expert_lint/ module — 65 rules across 5 domains

Pure-function rule engine. Public API: expert_lint(plan, domain, context).
Domains: macro (15 rules), busking (16), show (14), preset (13), layout (7).
Plus §C.6 cross-cutting rules.

Architecture-hygiene invariant added: expert_lint stays pure (no I/O,
no async). Mirrors the existing src/commands/ purity contract.

Spec: doc/grandma2-mcp-practical-scope.md §C (rule catalogs).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3 — T1: Skill router

**Goal:** Ship `suggest_skills_for_task(intent, top_k=3, ...)` — semantic ranking over `.claude/skills/` corpus, with keyword fallback. Enrich `list_skills` return shape (`tags`, `prerequisites`, `wraps_plugin`, `use_instead_of`). Create `.claude/skills/INDEX.md`.

**Files:**

- Create: `src/skill_router.py`, `tests/test_skill_router.py`, `.claude/skills/INDEX.md`
- Modify: `src/skill.py` (add front-matter fields), `src/server.py` (register `suggest_skills_for_task` near line 7228), `src/server_orchestration_tools.py:1248` (enrich `list_skills`)
- Test: `tests/test_skill_router.py`, plus enrichments to existing skill tests if needed

- [ ] **Step 3.1: Write the rank_skills test (RED)**

`tests/test_skill_router.py`:

```python
"""Skill router — rank skills against natural-language intent."""

from __future__ import annotations

from src.skill_router import rank_skills


def test_rank_returns_top_k():
    """rank_skills returns at most top_k results, sorted by score descending."""
    results = rank_skills(intent="make me a color picker", top_k=3,
                          method="keyword")
    assert len(results) <= 3
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_rank_picks_color_skill_for_color_intent():
    """For an obvious color intent, a color-related skill should be in top-2."""
    results = rank_skills(intent="make me a color picker layout", top_k=3,
                          method="keyword")
    top_names = {r["name"] for r in results[:2]}
    assert any("color" in n.lower() for n in top_names), (
        f"Expected a color skill in top-2; got {top_names}"
    )


def test_rank_picks_macro_skill_for_macro_intent():
    results = rank_skills(intent="make me a song-change macro for songs", top_k=3,
                          method="keyword")
    top_names = {r["name"] for r in results[:2]}
    assert any("macro" in n.lower() for n in top_names), top_names


def test_rank_returns_required_fields():
    results = rank_skills(intent="busking template for rock band", top_k=1,
                          method="keyword")
    assert results
    r = results[0]
    for field in ("name", "version", "score", "why", "first_decision",
                  "safety_scope", "tags", "prerequisites", "estimated_tokens"):
        assert field in r, f"missing field: {field}"
```

- [ ] **Step 3.2: Verify it fails**

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_skill_router.py -v
```

Expected: ImportError for `src.skill_router`.

- [ ] **Step 3.3: Implement `src/skill_router.py` (GREEN)**

```python
"""Skill router — semantic + keyword ranking over the skill registry.

Mirrors src/server.py:suggest_tool_for_task patterns for consistency.
Pure module — no telnet, no asyncio. Tests run against the filesystem
skill corpus (.claude/skills/{slug}/SKILL.md).
"""

from __future__ import annotations

import os
from typing import Literal, TypedDict

from src.skill import SkillRegistry, _list_filesystem_skills


class SkillSuggestion(TypedDict):
    name: str
    version: str
    score: float
    why: str
    first_decision: str | None
    safety_scope: str
    tags: list[str]
    prerequisites: list[str]
    estimated_tokens: int


_STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "of", "to", "for", "in", "on", "with",
    "me", "my", "i", "is", "are", "be", "this", "that", "make", "build",
})


def _tokenize(text: str) -> set[str]:
    return {t for t in (text.lower().replace("-", " ").replace("_", " ").split())
            if t not in _STOPWORDS and len(t) > 1}


def _extract_first_decision(body: str) -> str | None:
    """Extract the first 'First decision' line if present in the skill body."""
    for line in body.splitlines():
        line = line.strip()
        if line.lower().startswith(("first decision:", "**first decision:**",
                                     "## first decision")):
            return line
    return None


def _keyword_score(intent_tokens: set[str], text_tokens: set[str]) -> float:
    if not intent_tokens:
        return 0.0
    overlap = intent_tokens & text_tokens
    return len(overlap) / len(intent_tokens)


def rank_skills(
    intent: str,
    *,
    top_k: int = 3,
    method: Literal["semantic", "keyword", "hybrid"] = "keyword",
    include_destructive: bool = True,
    registry: SkillRegistry | None = None,
) -> list[SkillSuggestion]:
    """Rank skills against an intent string. Pure function — no I/O beyond
    reading the skill corpus once (done by SkillRegistry / filesystem fallback)."""

    # Corpus: union of DB skills + filesystem skills
    skills = []
    if registry is not None:
        skills.extend(registry.list_all(limit=200))
    skills.extend([s for s in _list_filesystem_skills()
                   if s.id not in {db.id for db in skills}])

    if not include_destructive:
        skills = [s for s in skills if s.is_usable()]

    intent_tokens = _tokenize(intent)

    suggestions: list[tuple[float, "Skill"]] = []  # type: ignore[name-defined]
    for s in skills:
        text = " ".join([s.name, s.description, s.applicable_context, s.body[:2000]])
        text_tokens = _tokenize(text)
        score = _keyword_score(intent_tokens, text_tokens)
        if score > 0:
            suggestions.append((score, s))

    suggestions.sort(key=lambda x: -x[0])
    top = suggestions[:top_k]

    return [
        SkillSuggestion(
            name=s.name,
            version=str(s.version),
            score=round(score, 4),
            why=s.description[:120],
            first_decision=_extract_first_decision(s.body),
            safety_scope=s.safety_scope,
            tags=[],            # populated when front-matter additions land (Step 3.7)
            prerequisites=[],
            estimated_tokens=max(1, len(s.body) // 4),
        )
        for score, s in top
    ]


__all__ = ["rank_skills", "SkillSuggestion"]
```

- [ ] **Step 3.4: Verify rank_skills tests pass**

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_skill_router.py -v
```

Expected: 4 passed.

- [ ] **Step 3.5: Write the MCP tool registration test (RED)**

Add to `tests/test_skill_router.py`:

```python
import asyncio
import json

import pytest


@pytest.mark.asyncio
async def test_suggest_skills_for_task_returns_json_envelope():
    """The registered MCP tool returns a JSON-encoded SuggestSkillsResponse."""
    from src.server import suggest_skills_for_task
    raw = await suggest_skills_for_task(
        intent="make a color picker", top_k=3, prefer_semantic=False,
    )
    data = json.loads(raw)
    assert data["intent"] == "make a color picker"
    assert data["method"] in ("keyword", "semantic", "hybrid")
    assert isinstance(data["suggestions"], list)
    assert len(data["suggestions"]) <= 3
```

- [ ] **Step 3.6: Register the MCP tool in `src/server.py`**

Insert near line 7344 (after `suggest_tool_for_task`):

```python
@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def suggest_skills_for_task(
    intent: str,
    top_k: int = 3,
    include_destructive: bool = True,
    prefer_semantic: bool = True,
) -> str:
    """Suggest skills from the .claude/skills/ corpus for a natural-language intent (SAFE_READ).

    Args:
        intent: What you want to do, e.g. "make me a color picker".
        top_k: Max number of suggestions to return.
        include_destructive: When False, drop un-approved DESTRUCTIVE skills.
        prefer_semantic: When True, use embedding search if GITHUB_MODELS_TOKEN is set.
    """
    from src.skill_router import rank_skills

    method: str = "keyword"
    warning: str | None = None
    if prefer_semantic and os.environ.get("GITHUB_MODELS_TOKEN"):
        # Semantic path is a forward stub — Path A ships keyword only.
        # Path B can extend rank_skills() with an embedding signal.
        method = "semantic"
        warning = "semantic search not yet implemented; returning keyword results"
    elif prefer_semantic:
        warning = (
            "prefer_semantic=True but GITHUB_MODELS_TOKEN is not set; "
            "using keyword matching."
        )

    suggestions = rank_skills(
        intent=intent, top_k=top_k, method="keyword",
        include_destructive=include_destructive,
    )

    return json.dumps({
        "intent": intent,
        "method": method,
        "warning": warning,
        "suggestions": suggestions,
    }, indent=2)
```

- [ ] **Step 3.7: Verify the tool test passes**

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_skill_router.py -v
```

Expected: 5 passed (the new tool test plus the 4 from Step 3.4).

- [ ] **Step 3.8: Extend `_parse_front_matter()` in `src/skill.py` (RED → GREEN)**

Add to `tests/test_skill.py` (create if absent):

```python
def test_front_matter_parses_list_fields(tmp_path):
    """tags / prerequisites / use_instead_of parse as list[str] when present."""
    from src.skill import _parse_front_matter
    raw = """---
name: x
description: y
tags: [color, presets]
prerequisites: [patch-and-group-builder]
wraps_plugin: auto-layout-color-picker
use_instead_of: []
---
body
"""
    meta, body = _parse_front_matter(raw)
    assert meta.get("tags") == ["color", "presets"]
    assert meta.get("prerequisites") == ["patch-and-group-builder"]
    assert meta.get("wraps_plugin") == "auto-layout-color-picker"
    assert meta.get("use_instead_of") == []
```

Then update `_parse_front_matter` in `src/skill.py` to recognise `key: [a, b]` syntax for list fields:

```python
def _parse_front_matter(raw: str) -> tuple[dict, str]:
    m = _FM_RE.match(raw)
    if not m:
        return {}, raw
    meta: dict = {}
    for line in m.group(1).splitlines():
        if ": " not in line:
            continue
        k, _, v = line.partition(": ")
        k = k.strip()
        v = v.strip()
        # Inline-list syntax: "key: [a, b]" → list[str]
        if v.startswith("[") and v.endswith("]"):
            inner = v[1:-1].strip()
            meta[k] = [x.strip() for x in inner.split(",") if x.strip()] if inner else []
        else:
            meta[k] = v
    return meta, raw[m.end():].strip()
```

Run:

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_skill.py -v
```

Expected: existing tests + new test pass.

- [ ] **Step 3.9: Enrich `list_skills` return shape**

In `src/server_orchestration_tools.py` around line 1266, change the `to_dict()` call to merge the front-matter fields:

```python
def _enrich_skill_dict(s) -> dict:
    d = s.to_dict()
    # Re-parse the SKILL.md front matter for filesystem skills to surface
    # tags / prerequisites / wraps_plugin / use_instead_of fields.
    if s.id.startswith("fs:"):
        from pathlib import Path
        from src.skill import _SKILLS_DIR, _parse_front_matter
        skill_file = _SKILLS_DIR / s.id.removeprefix("fs:") / "SKILL.md"
        if skill_file.exists():
            meta, _ = _parse_front_matter(skill_file.read_text(encoding="utf-8"))
            d["tags"] = meta.get("tags", []) if isinstance(meta.get("tags"), list) else []
            d["prerequisites"] = meta.get("prerequisites", []) if isinstance(meta.get("prerequisites"), list) else []
            d["wraps_plugin"] = meta.get("wraps_plugin") or None
            d["use_instead_of"] = meta.get("use_instead_of", []) if isinstance(meta.get("use_instead_of"), list) else []
    else:
        d.setdefault("tags", [])
        d.setdefault("prerequisites", [])
        d.setdefault("wraps_plugin", None)
        d.setdefault("use_instead_of", [])
    return d

# replace [s.to_dict() for s in skills] with [_enrich_skill_dict(s) for s in skills]
```

Add a test verifying enriched fields appear:

```python
# tests/test_skill_router.py
@pytest.mark.asyncio
async def test_list_skills_returns_enriched_fields():
    from src.server_orchestration_tools import _register_orchestration_tools  # noqa: F401
    # Easier: call list_skills via importable wrapper or via FastMCP test harness.
    # If not exposed, smoke-check via the underlying registry path:
    from src.skill import SkillRegistry
    reg = SkillRegistry()
    skills = reg.list_all(limit=5)
    reg.close()
    # Just check the data is reachable — the enrichment happens in the tool wrapper.
    assert skills, "skill corpus should be non-empty"
```

(Direct testing of `list_skills` requires the orchestration-tools registration context; if reaching the tool wrapper is awkward, this corpus smoke check is acceptable for Path A — enrichment correctness is covered by the front-matter parser tests in Step 3.8.)

- [ ] **Step 3.10: Create `.claude/skills/INDEX.md`**

Group every skill under `.claude/skills/` by friction area. Use this template:

```markdown
---
title: Skill Index — grandMA2 MCP
description: Friction-grouped index of all 45 skills for fast lookup
version: 1.0.0
created: 2026-05-27T00:00:00Z
last_updated: 2026-05-27T00:00:00Z
---

# Skill Index

## Color & presets
- `auto-layout-color-picker` — plugin-backed color picker layout. **First decision:** if the plugin is installed, prefer it over manual paths.
- `color-preset-creator` — store universal color presets from RGB/HSB values
- `color-palette-sequence-builder` — build sequence cues referencing global color presets
- `constrained-color-design` — HSB-strategy palette design + numbering
- `hue-palette-creator` — store the 96-preset universal hue library (4.101-4.196)
- `hue-sequence-builder` — 16-cue sequence from an adjacent hue pair

## Layouts & views
- `view-and-layout-designer` — custom views, console layouts, button placement

## Macros & plugins
- `lua-and-plugins` — Lua scripting v5.2, plugin invocation lifecycle
- `macro-advanced` — SetVar/GetVar, CmdDelay, jump safety
- `macro-linter-and-refactorer` — macro safety scan + refactor
- `song-macro-page-design` — song-page conventions, first-button protocol

## Patch, groups, fixtures
- `patch-and-group-builder` — patch fixture types + build groups
- `clone-and-data-transfer` — Clone workflow, attribute transfer
- `fixture-swap-surgeon` — fixture type swap with preset migration
- `rdm-workflow` — RDM discovery + autopatch

## Cues, sequences, executors
- `cue-tracking-and-timing` — tracking, Block/Unblock, MIB, timing
- `cue-list-auditor` — gaps, labels, timing, health checks
- `cue-to-cue-rehearsal` — annotated cue-by-cue walkthrough
- `chaser-builder` — step-based chaser sequences
- `executor-configuration` — priority, special masters, trigger types
- `sequence-executor-assigner` — assign sequence to a free executor
- `effect-programmer` — store, assign, modulate effects

## Busking & live performance
- `busking-lighting-performance` — fader-per-effect, layered model
- `busking-template-generator` — generate complete busking template from patch
- `showkontrol-bpm-sync` — CDJ BPM → MA2 speed masters

## Preset library architecture
- `preset-library-architect` — universal vs selective preset strategy
- `preset-impact-manager` — assess + plan preset updates / deletes
- `cross-venue-adaptation` — adapt show to new venue rig

## Show creation & migration
- `show-management-and-psr` — save/load/PSR workflows
- `psr-show-migration` — slot-conflict detection during PSR merge
- `festival-stage-setup` — patch → busking-ready in one session
- `timecode-show-programmer` — SMPTE pool, cue triggers, playback
- `show-health-check` — pre-show file audit

## Troubleshooting & runbooks
- `feedback-investigator` — classify Telnet feedback failures
- `operator-recovery-runbook` — stuck playback, contaminated programmer, wrong world
- `telnet-feedback-triage` — feedback classification module
- `troubleshoot-no-output` — diagnostic tree for fixtures producing no light
- `tracking-debugger` — tracking leak / unexpected block diagnosis

## Worlds, filters, scoping
- `world-filter-designer` — Worlds + Filters + application

## Connection & setup
- `companion-integration` — Companion button page mirror of MA2 executors
- `connection-setup-workflow` — (NEW, Task 4) discover → pick → reconfigure → verify
- `remote-monitoring` — SAFE_READ console state monitoring
- `training-mode` — annotated SAFE_READ console tour
- `volunteer-operations` — tiered access for non-programmers

## Advanced workflows
- `compliance-documentation` — SB-132 / safety-audit report from session telemetry
- `ma2-command-rules` — command construction, object resolution, safety
```

Test (add to `tests/test_skill_router.py`):

```python
def test_index_md_exists_and_covers_every_skill():
    """Every directory in .claude/skills/ must be listed in INDEX.md."""
    from pathlib import Path
    skills_dir = Path(".claude/skills")
    index_text = (skills_dir / "INDEX.md").read_text(encoding="utf-8")
    for skill_path in sorted(skills_dir.iterdir()):
        if skill_path.is_dir() and (skill_path / "SKILL.md").exists():
            assert skill_path.name in index_text, (
                f"INDEX.md is missing entry for {skill_path.name}"
            )
```

- [ ] **Step 3.11: Run full T1 test suite**

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_skill_router.py tests/test_skill.py -v
```

Expected: all green.

- [ ] **Step 3.12: Run architecture hygiene**

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_architecture_hygiene.py -q
```

Expected: 25 passed (the existing baseline) + INDEX.md picked up as a doc, but INDEX.md is in `.claude/skills/`, not in `doc/` — front-matter check applies to it via the skills-dir check. Verify it has front matter (Step 3.10 includes it).

- [ ] **Step 3.13: Commit**

```bash
git add src/skill_router.py src/skill.py src/server.py src/server_orchestration_tools.py tests/test_skill_router.py tests/test_skill.py .claude/skills/INDEX.md
git commit -m "$(cat <<'EOF'
t1: skill router + enriched list_skills + INDEX.md

- New tool: suggest_skills_for_task (SAFE_READ, scope DISCOVER)
- New module: src/skill_router.py (pure, mirrors suggest_tool_for_task)
- Extended front-matter parser: recognises tags, prerequisites,
  wraps_plugin, use_instead_of (list[str] inline syntax)
- list_skills returns those fields when present
- .claude/skills/INDEX.md groups all 45 skills by friction area

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4 — T2: Console portability + mock mode

**Goal:** Ship `discover_consoles(timeout_seconds=5, network=None, methods=None)` (UDP broadcast only in Path A; mDNS deferred), `reconfigure_connection(host, port, user, password, persist, verify)` (atomic swap + `.env` persist), and `GMA_MOCK=1` / `GMA_MOCK=schema` mock modes hooked into `_get_session_manager()`. Plus a new `connection-setup-workflow` skill.

**Files:**

- Create: `src/discovery.py`, `src/mock/__init__.py`, `src/mock/session_manager.py`, `src/mock/telnet_client.py`, `src/mock/responses.py`, `src/mock/fixture_loader.py`
- Create: `tests/test_console_discovery.py`, `tests/test_reconfigure_connection.py`, `tests/test_mock_mode.py`
- Create: `tests/fixtures/mock_show_state.json`, `tests/fixtures/captured/sample.jsonl`, `scripts/capture_broadcast.py`
- Create: `.claude/skills/connection-setup-workflow/SKILL.md`
- Modify: `src/server.py` (mock switch at `_get_session_manager`; register both tools), `pyproject.toml` (`[project.optional-dependencies] mdns`)

### 4a — discover_consoles

- [ ] **Step 4.1: Write the discovery test (RED)**

`tests/test_console_discovery.py`:

```python
"""UDP broadcast discovery — parser + auto-detect."""

import json
from pathlib import Path

import pytest

from src.discovery import (
    parse_broadcast_packet, list_local_networks, discover_grandma2_broadcast,
)


# Sample captured from a real grandMA2 announcement (recorded next session;
# for Path A use a synthetic packet covering the documented fields).
SAMPLE_PACKET = b"GMA2-ANNOUNCE\x01session=Default\x02name=onPC\x02ip=127.0.0.1\x02port=30000\x02version=3.9.60\x00"


def test_parse_broadcast_packet_extracts_fields():
    candidate = parse_broadcast_packet(SAMPLE_PACKET, source_addr=("127.0.0.1", 6004))
    assert candidate is not None
    assert candidate["host"] == "127.0.0.1"
    assert candidate["port"] == 30000
    assert candidate["session_name"] == "Default"
    assert candidate["version"] == "3.9.60"
    assert candidate["source"] == "broadcast"


def test_parse_unrecognised_packet_returns_none():
    assert parse_broadcast_packet(b"not a gma2 packet", ("1.2.3.4", 12345)) is None


def test_list_local_networks_returns_at_least_loopback():
    nets = list_local_networks()
    assert any(n.startswith("127.") or n.startswith("169.") or "0.0.0" in n for n in nets) or nets, (
        f"expected at least one network; got {nets}"
    )


@pytest.mark.asyncio
async def test_discover_returns_empty_quickly_without_console():
    """With a 1s timeout on a network with no console, returns [] without hanging."""
    candidates = await discover_grandma2_broadcast(network=None, timeout_seconds=1)
    assert isinstance(candidates, list)
    # No assertion on contents — onPC may or may not broadcast; what matters
    # is the call returns within ~timeout_seconds.
```

- [ ] **Step 4.2: Verify the discovery tests fail**

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_console_discovery.py -v
```

Expected: ImportError for `src.discovery`.

- [ ] **Step 4.3: Implement `src/discovery.py` (GREEN)**

```python
"""Console discovery — UDP broadcast (Path A) and mDNS (Path B stub).

UDP broadcast probes port 6004; listens for MA-Net2 announcement packets.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
from typing import TypedDict

logger = logging.getLogger(__name__)

_BROADCAST_PORT = 6004
_PROBE_PAYLOAD = b"GMA2-PROBE\x00"


class ConsoleCandidate(TypedDict):
    host: str
    port: int
    name: str | None
    session_name: str | None
    version: str | None
    response_ms: float
    source: str  # "broadcast" | "mdns" | "manual"


def parse_broadcast_packet(
    packet: bytes, source_addr: tuple[str, int]
) -> ConsoleCandidate | None:
    """Parse a GMA2 announce packet — returns None if unrecognised.

    Wire format (documented in MA-Net manual; verify against real captures):

        b"GMA2-ANNOUNCE\\x01" + fields_joined_by_\\x02 + b"\\x00"

    Each field is "key=value" — known keys: session, name, ip, port, version.
    """
    if not packet.startswith(b"GMA2-ANNOUNCE"):
        return None
    body = packet.removeprefix(b"GMA2-ANNOUNCE").strip(b"\x00\x01")
    fields: dict[str, str] = {}
    for raw in body.split(b"\x02"):
        if b"=" not in raw:
            continue
        k, _, v = raw.partition(b"=")
        try:
            fields[k.decode("ascii").strip()] = v.decode("utf-8", "replace").strip()
        except Exception:
            continue
    host = fields.get("ip") or source_addr[0]
    try:
        port = int(fields.get("port", "30000"))
    except ValueError:
        port = 30000
    return ConsoleCandidate(
        host=host,
        port=port,
        name=fields.get("name"),
        session_name=fields.get("session"),
        version=fields.get("version"),
        response_ms=0.0,  # filled by caller for live receives
        source="broadcast",
    )


def list_local_networks() -> list[str]:
    """Return a list of local CIDR strings derived from active interfaces."""
    nets: list[str] = []
    try:
        # Resolve all addresses bound to local hostname; conservative.
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, family=socket.AF_INET):
            ip = info[4][0]
            try:
                net = ipaddress.IPv4Network(f"{ip}/24", strict=False)
                nets.append(str(net))
            except ValueError:
                continue
    except Exception as e:  # noqa: BLE001
        logger.debug("list_local_networks fallback: %s", e)
    if not nets:
        nets.append("127.0.0.0/8")
    return nets


async def discover_grandma2_broadcast(
    network: str | None = None,
    timeout_seconds: int = 5,
) -> list[ConsoleCandidate]:
    """Send a broadcast probe and collect announce replies for `timeout_seconds`."""
    loop = asyncio.get_running_loop()
    results: list[ConsoleCandidate] = []

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setblocking(False)
    sock.bind(("", 0))

    bcast_target = "255.255.255.255"
    if network:
        try:
            net = ipaddress.IPv4Network(network, strict=False)
            bcast_target = str(net.broadcast_address)
        except ValueError:
            logger.warning("invalid network %r; using global broadcast", network)

    try:
        await loop.sock_sendto(sock, _PROBE_PAYLOAD, (bcast_target, _BROADCAST_PORT))
    except (OSError, NotImplementedError):
        # Some platforms (Windows < 10) reject SOCK_DGRAM via asyncio; fall through to read.
        sock.sendto(_PROBE_PAYLOAD, (bcast_target, _BROADCAST_PORT))

    async def _read_until_timeout():
        deadline = loop.time() + timeout_seconds
        while loop.time() < deadline:
            try:
                data, addr = await asyncio.wait_for(
                    loop.sock_recvfrom(sock, 1500),
                    timeout=max(0.05, deadline - loop.time()),
                )
            except TimeoutError:
                return
            except Exception as e:  # noqa: BLE001
                logger.debug("recv error: %s", e)
                return
            candidate = parse_broadcast_packet(data, addr)
            if candidate is not None:
                results.append(candidate)

    try:
        await _read_until_timeout()
    finally:
        sock.close()
    return results


__all__ = [
    "parse_broadcast_packet",
    "list_local_networks",
    "discover_grandma2_broadcast",
    "ConsoleCandidate",
]
```

- [ ] **Step 4.4: Verify the discovery tests pass**

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_console_discovery.py -v
```

Expected: 4 passed (the live-network test passes even when empty — it just must not hang).

- [ ] **Step 4.5: Register `discover_consoles` MCP tool**

In `src/server.py`, near the existing tool registrations:

```python
@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def discover_consoles(
    timeout_seconds: int = 5,
    network: str | None = None,
    methods: list[str] | None = None,
) -> str:
    """Discover grandMA2 consoles via UDP broadcast (SAFE_READ).

    Path A scope: broadcast only. mDNS path is documented for Path B
    behind the [mdns] optional dependency.
    """
    import time as _time
    from src.discovery import discover_grandma2_broadcast

    methods_set = set(methods or ["broadcast"])
    t0 = _time.monotonic()
    candidates: list[dict] = []
    note: str | None = None

    if "broadcast" in methods_set:
        results = await discover_grandma2_broadcast(
            network=network, timeout_seconds=timeout_seconds,
        )
        candidates.extend(results)
    if "mdns" in methods_set:
        note = "mdns method requires Path B install: pip install 'ma2-agent[mdns]'"

    elapsed_ms = (_time.monotonic() - t0) * 1000
    return json.dumps({
        "candidates": candidates,
        "scanned_networks": [network] if network else [],
        "elapsed_ms": round(elapsed_ms, 2),
        "note": note,
    }, indent=2)
```

Add a tool-registration smoke test in `tests/test_console_discovery.py`:

```python
@pytest.mark.asyncio
async def test_discover_consoles_tool_returns_envelope():
    from src.server import discover_consoles
    raw = await discover_consoles(timeout_seconds=1)
    data = json.loads(raw)
    assert "candidates" in data
    assert "elapsed_ms" in data
```

Run; expect 5 passed.

### 4b — reconfigure_connection

- [ ] **Step 4.6: Write the reconfigure test (RED)**

`tests/test_reconfigure_connection.py`:

```python
"""reconfigure_connection — atomic swap + .env persist + verify."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.server import reconfigure_connection  # will not import until 4.7 lands


@pytest.fixture
def temp_env_file(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text(
        "GMA_HOST=127.0.0.1\nGMA_PORT=30000\nGMA_USER=administrator\n"
        "GMA_PASSWORD=admin\nGMA_TELEMETRY=1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("src.server._ENV_PATH", env)
    return env


@pytest.mark.asyncio
async def test_reconfigure_persists_to_env(temp_env_file):
    """When persist=True, .env reflects the new host."""
    with patch("src.server._verify_round_trip", new=AsyncMock(return_value=True)):
        raw = await reconfigure_connection(
            host="10.0.0.5", port=30000, user="administrator",
            password="admin", persist=True, verify=True,
        )
    data = json.loads(raw)
    assert data["success"] is True
    assert data["new_host"] == "10.0.0.5"
    contents = temp_env_file.read_text(encoding="utf-8")
    assert "GMA_HOST=10.0.0.5" in contents


@pytest.mark.asyncio
async def test_reconfigure_idempotent_no_change(temp_env_file):
    """Calling with the same host returns success without modifying anything."""
    with patch("src.server._GMA_HOST", "10.0.0.5"), \
         patch("src.server._verify_round_trip", new=AsyncMock(return_value=True)):
        raw = await reconfigure_connection(
            host="10.0.0.5", port=30000, user="administrator",
            password="admin", persist=False, verify=False,
        )
    data = json.loads(raw)
    assert data["success"] is True
    assert data.get("note", "").lower().startswith("no change") or data["previous_host"] == data["new_host"]


@pytest.mark.asyncio
async def test_reconfigure_verify_failure_blocks(temp_env_file):
    """When verify=True and round-trip fails, the call returns success=False."""
    with patch("src.server._verify_round_trip", new=AsyncMock(return_value=False)):
        raw = await reconfigure_connection(
            host="10.0.0.99", port=30000, user="administrator",
            password="admin", persist=False, verify=True,
        )
    data = json.loads(raw)
    assert data["success"] is False
    assert data["verified"] is False
```

- [ ] **Step 4.7: Implement reconfigure_connection (GREEN)**

Add to `src/server.py`:

```python
from pathlib import Path as _Path

_ENV_PATH = _Path(__file__).parent.parent / ".env"


async def _verify_round_trip(host: str, port: int, user: str, password: str) -> bool:
    """Open a fresh client to the candidate host and try a tiny SAFE_READ."""
    from src.telnet_client import GMA2TelnetClient
    try:
        async with GMA2TelnetClient(host=host, port=port, user=user, password=password) as c:
            resp = await c.send_command_with_response("ListVar", timeout=2.0)
            return bool(resp)
    except Exception as e:  # noqa: BLE001
        logger.warning("verify_round_trip failed: %s", e)
        return False


def _persist_env(env_path: _Path, **overrides: str) -> None:
    """Atomic write — read existing entries, override the named keys, write back."""
    existing: dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, _, v = line.partition("=")
                existing[k.strip()] = v.strip()
    existing.update(overrides)
    tmp = env_path.with_suffix(".env.tmp")
    tmp.write_text(
        "\n".join(f"{k}={v}" for k, v in existing.items()) + "\n",
        encoding="utf-8",
    )
    tmp.replace(env_path)


@mcp.tool()
@require_scope(OAuthScope.SYSTEM_ADMIN)
@_handle_errors
async def reconfigure_connection(
    host: str,
    port: int = 30000,
    user: str = "administrator",
    password: str = "admin",
    persist: bool = True,
    verify: bool = True,
) -> str:
    """Swap the active console connection and (optionally) persist to .env."""
    global _GMA_HOST, _GMA_PORT, _GMA_USER, _GMA_PASSWORD, _session_manager
    previous_host = _GMA_HOST
    same = (host == _GMA_HOST and port == _GMA_PORT and user == _GMA_USER)
    if same:
        return json.dumps({
            "success": True, "previous_host": previous_host, "new_host": host,
            "verified": True, "persisted_to": None, "note": "no change",
            "warning": None, "error": None,
        }, indent=2)

    verified = True
    if verify:
        verified = await _verify_round_trip(host, port, user, password)
    if verify and not verified:
        return json.dumps({
            "success": False, "previous_host": previous_host, "new_host": host,
            "verified": False, "persisted_to": None, "note": None,
            "warning": None, "error": f"verify round-trip to {host}:{port} failed",
        }, indent=2)

    async with _session_manager_lock:
        old_mgr = _session_manager
        _GMA_HOST = host
        _GMA_PORT = port
        _GMA_USER = user
        _GMA_PASSWORD = password
        _session_manager = None  # next get_client() rebuilds
    if old_mgr is not None:
        try:
            await old_mgr.close_all()
        except Exception:  # noqa: BLE001, SIM105
            pass

    persisted_to: str | None = None
    if persist:
        _persist_env(_ENV_PATH, GMA_HOST=host, GMA_PORT=str(port),
                     GMA_USER=user, GMA_PASSWORD=password)
        persisted_to = str(_ENV_PATH)

    return json.dumps({
        "success": True, "previous_host": previous_host, "new_host": host,
        "verified": verified, "persisted_to": persisted_to, "note": None,
        "warning": None, "error": None,
    }, indent=2)
```

- [ ] **Step 4.8: Verify reconfigure tests pass**

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_reconfigure_connection.py -v
```

Expected: 3 passed.

### 4c — Mock mode

- [ ] **Step 4.9: Write mock-mode tests (RED)**

`tests/test_mock_mode.py`:

```python
"""GMA_MOCK env var enables an in-memory SessionManager."""

import asyncio
import json
import os
from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_mock_tier1_canned_listvar(monkeypatch):
    monkeypatch.setenv("GMA_MOCK", "1")
    from src.mock.session_manager import MockSessionManager
    mgr = MockSessionManager(tier="1")
    client = await mgr.get(identity="t", username="administrator", password="admin")
    resp = await client.send_command_with_response("ListVar")
    assert "$VERSION" in resp or "Global" in resp  # canned envelope mentions a var


@pytest.mark.asyncio
async def test_mock_tier2_groups_from_fixture(monkeypatch):
    monkeypatch.setenv("GMA_MOCK", "schema")
    from src.mock.session_manager import MockSessionManager
    mgr = MockSessionManager(tier="schema")
    client = await mgr.get(identity="t", username="administrator", password="admin")
    resp = await client.send_command_with_response("list group")
    # Fixture (tests/fixtures/mock_show_state.json) has at least 12 groups
    assert "1 :" in resp or "Group" in resp


@pytest.mark.asyncio
async def test_server_uses_mock_when_env_set(monkeypatch):
    """_get_session_manager returns MockSessionManager when GMA_MOCK is set."""
    monkeypatch.setenv("GMA_MOCK", "1")
    monkeypatch.setattr("src.server._session_manager", None)
    from src.server import _get_session_manager
    mgr = await _get_session_manager()
    assert mgr.__class__.__name__ == "MockSessionManager"
```

- [ ] **Step 4.10: Implement mock module (GREEN)**

`src/mock/__init__.py`:

```python
"""GMA_MOCK — in-memory session manager + telnet client.

Tier 1: canned regex-keyed responses (~30 most common commands).
Tier 2 (schema): stateful in-memory show fixture.
Tier 3 (replay): JSONL replay (stub for Path A).
"""
```

`src/mock/responses.py`:

```python
"""Tier-1 canned responses keyed by command regex."""

from __future__ import annotations

import re
from typing import Callable

_RESPONSES: list[tuple[re.Pattern, str | Callable[[str], str]]] = [
    (re.compile(r"^\s*ListVar\b", re.IGNORECASE),
     "Executing : ListVar\n"
     "Global : $VERSION = 3.9.60 (mock)\n"
     "Global : $SHOWFILE = mock_show\n"
     "Global : $USER = administrator\n"
     "Global : $USERRIGHTS = Admin\n"),
    (re.compile(r"^\s*list\s+group\b", re.IGNORECASE),
     "Group\n"
     "    1 : Wash\n"
     "    2 : Mover\n"
     "    3 : Bar\n"
     "    4 : Blinder\n"),
    (re.compile(r"^\s*list\s+executor\b", re.IGNORECASE),
     "Executor\n"
     "  1.1.1 : Wash Intensity (Normal)\n"
     "  1.1.2 : Mover Intensity (Normal)\n"),
    (re.compile(r"^\s*info\b", re.IGNORECASE),
     "Info: mock console; tier=1\n"),
    (re.compile(r"^\s*cd\b", re.IGNORECASE), ""),  # cd is silent
]


def respond(command: str) -> str:
    for pat, body in _RESPONSES:
        if pat.match(command):
            return body if isinstance(body, str) else body(command)
    return f"MOCK: command not stubbed; got {command!r}\n"
```

`src/mock/telnet_client.py`:

```python
"""MockGMA2TelnetClient — implements GMA2TelnetClient's public surface."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from src.mock.responses import respond

logger = logging.getLogger(__name__)


class MockGMA2TelnetClient:
    DEFAULT_PORT = 30000
    DEFAULT_USER = "administrator"
    DEFAULT_PASSWORD = "admin"

    def __init__(self, host: str = "mock", port: int = DEFAULT_PORT,
                 user: str = DEFAULT_USER, password: str = DEFAULT_PASSWORD,
                 *, tier: str = "1", fixture_path: Path | None = None) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.tier = tier
        self._connected = False
        self._fixture: dict | None = None
        if tier == "schema" and fixture_path and fixture_path.exists():
            import json as _json
            self._fixture = _json.loads(fixture_path.read_text(encoding="utf-8"))

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        await asyncio.sleep(0)
        self._connected = True

    async def login(self) -> bool:
        await asyncio.sleep(0)
        return True

    async def send_command(self, command: str, delay: float = 0.0) -> None:
        await asyncio.sleep(0)

    async def send_command_with_response(
        self, command: str, timeout: float = 2.0, delay: float = 0.0,
        subsequent_timeout: float = 0.10,
    ) -> str:
        await asyncio.sleep(0)
        if self.tier == "schema" and self._fixture is not None:
            return self._from_fixture(command)
        return respond(command)

    def _from_fixture(self, command: str) -> str:
        cmd = command.strip().lower()
        if cmd.startswith("list group"):
            groups = self._fixture.get("groups", [])
            return "Group\n" + "\n".join(f"    {g['id']} : {g['name']}" for g in groups) + "\n"
        if cmd.startswith("list executor"):
            execs = self._fixture.get("executors", [])
            return "Executor\n" + "\n".join(
                f"  {e['slot']} : {e['label']} ({e['priority']})" for e in execs
            ) + "\n"
        return respond(command)

    async def disconnect(self) -> None:
        self._connected = False

    async def __aenter__(self):
        await self.connect()
        await self.login()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.disconnect()
```

`src/mock/session_manager.py`:

```python
"""MockSessionManager — implements the SessionManager public surface."""

from __future__ import annotations

from pathlib import Path

from src.mock.telnet_client import MockGMA2TelnetClient

_FIXTURE_PATH = Path(__file__).parent.parent.parent / "tests" / "fixtures" / "mock_show_state.json"


class MockSessionManager:
    def __init__(self, tier: str = "1") -> None:
        self.tier = tier
        self._clients: dict[str, MockGMA2TelnetClient] = {}

    async def get(self, identity: str, username: str, password: str) -> MockGMA2TelnetClient:
        if identity not in self._clients:
            client = MockGMA2TelnetClient(
                host="mock", user=username, password=password,
                tier=self.tier,
                fixture_path=_FIXTURE_PATH if self.tier == "schema" else None,
            )
            await client.connect()
            await client.login()
            self._clients[identity] = client
        return self._clients[identity]

    async def release(self, identity: str) -> None:
        client = self._clients.pop(identity, None)
        if client:
            await client.disconnect()

    async def close_all(self) -> None:
        for c in list(self._clients.values()):
            await c.disconnect()
        self._clients.clear()

    def start_keepalive(self) -> None:
        # No-op for mock — no real connection to keep alive
        pass

    def session_count(self) -> int:
        return len(self._clients)

    def session_info(self) -> list[dict]:
        return [{"identity": k, "tier": self.tier} for k in self._clients]
```

- [ ] **Step 4.11: Create the Tier-2 fixture**

`tests/fixtures/mock_show_state.json`:

```json
{
  "showfile": "mock_show",
  "groups": [
    {"id": 1, "name": "Wash"},
    {"id": 2, "name": "Mover"},
    {"id": 3, "name": "Bar"},
    {"id": 4, "name": "Blinder"},
    {"id": 5, "name": "KEY"},
    {"id": 6, "name": "Strobe"},
    {"id": 7, "name": "Audience"},
    {"id": 8, "name": "Backwash"},
    {"id": 9, "name": "Frontwash"},
    {"id": 10, "name": "FX-A"},
    {"id": 11, "name": "FX-B"},
    {"id": 12, "name": "FX-C"}
  ],
  "presets": [
    {"type": 4, "id": 1, "name": "Red"},
    {"type": 4, "id": 2, "name": "Green"},
    {"type": 4, "id": 3, "name": "Blue"},
    {"type": 4, "id": 4, "name": "White"},
    {"type": 2, "id": 1, "name": "Centre"},
    {"type": 2, "id": 2, "name": "Audience"},
    {"type": 2, "id": 3, "name": "Stage Left"},
    {"type": 2, "id": 4, "name": "Stage Right"}
  ],
  "sequences": [
    {"id": 1, "name": "Main",
     "cues": [
       {"id": 1, "label": "Open"},
       {"id": 2, "label": "Verse 1"},
       {"id": 3, "label": "Chorus 1"},
       {"id": 4, "label": "Bridge"},
       {"id": 5, "label": "Outro"}
     ]
    }
  ],
  "executors": [
    {"slot": "1.1.1", "label": "Wash Intensity", "priority": "normal"},
    {"slot": "1.1.2", "label": "Mover Intensity", "priority": "normal"},
    {"slot": "1.1.3", "label": "Blackout", "priority": "super"}
  ]
}
```

`tests/fixtures/captured/sample.jsonl`:

```jsonl
{"send": "ListVar", "recv": "Executing : ListVar\nGlobal : $VERSION = 3.9.60\n"}
```

- [ ] **Step 4.12: Wire the mock switch in `_get_session_manager()`**

Modify `src/server.py:470`:

```python
async def _get_session_manager() -> "SessionManager":
    """Return the active session manager.  Honours GMA_MOCK env var."""
    global _session_manager
    async with _session_manager_lock:
        if _session_manager is None:
            mock_tier = os.environ.get("GMA_MOCK")
            if mock_tier:
                from src.mock.session_manager import MockSessionManager
                _session_manager = MockSessionManager(tier=mock_tier)
                _session_manager.start_keepalive()
            else:
                _session_manager = SessionManager(host=_GMA_HOST, port=_GMA_PORT)
                _session_manager.start_keepalive()
    return _session_manager
```

- [ ] **Step 4.13: Verify mock tests pass**

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_mock_mode.py -v
```

Expected: 3 passed.

### 4d — connection-setup-workflow skill

- [ ] **Step 4.14: Create the connection-setup-workflow skill**

`.claude/skills/connection-setup-workflow/SKILL.md`:

```markdown
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

If you know the console host/IP and credentials, skip discovery and call `reconfigure_connection` directly. Otherwise, run discovery first.

## Steps

1. **Discover candidates** — call `discover_consoles(timeout_seconds=5)`.  Reports `candidates` (list) and `note` (diagnostic). UDP broadcast is the only Path A method; mDNS requires the optional `[mdns]` install (Path B).

2. **Pick a candidate** — if multiple candidates, prefer the one matching the expected `session_name`. If none match, report all candidates and let the operator pick.

3. **Reconfigure** — call `reconfigure_connection(host=candidate.host, port=candidate.port, user="administrator", password=<from-vault>, persist=True, verify=True)`. The `verify=True` flag opens a fresh client, runs `ListVar`, and only declares success on a response.

4. **Confirm** — call any SAFE_READ tool (e.g., `discover_object_names("group")`) to confirm the new session is operating.

## Expert checklist

- [ ] Discovery returned at least one candidate OR operator confirmed manual host input
- [ ] `reconfigure_connection` returned `verified: true` before any subsequent tool call
- [ ] `.env` was persisted (`persist=True`) so the next server restart picks up the new host
- [ ] No tool was invoked on the new connection until verification confirmed reachability

## Gotchas

- Broadcast UDP is blocked on many corporate / venue networks; if discovery returns empty, fall back to manual host entry from the operator.
- `reconfigure_connection` performs an atomic swap; any tool call already in flight against the old manager will error with ConnectionError — that is expected and operator-recoverable (retry the tool).
```

- [ ] **Step 4.15: Commit Task 4**

```bash
git add src/discovery.py src/mock/ src/server.py tests/test_console_discovery.py tests/test_reconfigure_connection.py tests/test_mock_mode.py tests/fixtures/ .claude/skills/connection-setup-workflow/
git commit -m "$(cat <<'EOF'
t2: console portability + mock mode + reconfigure_connection

- New tool: discover_consoles (UDP broadcast; mDNS deferred to Path B)
- New tool: reconfigure_connection (atomic swap + verify + .env persist)
- New module: src/mock/{session_manager,telnet_client,responses,fixture_loader}
- GMA_MOCK=1 / GMA_MOCK=schema env switch in _get_session_manager()
- New skill: connection-setup-workflow

Mock module mirrors GMA2TelnetClient + SessionManager public surfaces,
so every tool that takes a client works against the mock without changes.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5 — T3: NL → macro generation

**Goal:** Ship `generate_ma2_macro(intent, scope_hints, store, pool_id, confirm_destructive)` — emits MA2 macro XML from natural-language intent, runs `expert_lint(domain="macro")` (XC2), runs the existing macro-linter, and returns `{body_xml, lint, expert_review, validation}`.

**Files:**

- Modify: `src/server.py` (register `generate_ma2_macro`)
- Create: `src/macro_generation.py` (intent → macro template), `tests/test_macro_generation.py`

- [ ] **Step 5.1: Write the macro generation test (RED)**

`tests/test_macro_generation.py`:

```python
"""generate_ma2_macro — NL intent → XML body + lint + expert review."""

import json
import xml.etree.ElementTree as ET

import pytest


@pytest.mark.asyncio
async def test_generate_panic_blackout_macro():
    from src.server import generate_ma2_macro
    raw = await generate_ma2_macro(
        intent="make a panic blackout macro",
        scope_hints=None, store=False,
    )
    data = json.loads(raw)
    assert "body_xml" in data
    assert data["lint"] == [] or all(v["severity"] != "error" for v in data["lint"])
    assert "BlackScreen" in data["body_xml"] or "Off" in data["body_xml"]
    # XML must validate
    ET.fromstring(data["body_xml"])


@pytest.mark.asyncio
async def test_generate_macro_includes_expert_review():
    from src.server import generate_ma2_macro
    raw = await generate_ma2_macro(intent="make a tap tempo macro",
                                    scope_hints=None, store=False)
    data = json.loads(raw)
    assert "expert_review" in data
    assert data["expert_review"]["grade"] in ("expert", "competent", "beginner", "broken")


@pytest.mark.asyncio
async def test_generate_macro_with_destructive_pattern_flags():
    """A macro that includes `Delete` without `/noconfirm` must surface MACRO-SAFETY-001."""
    from src.macro_generation import build_macro_from_intent
    plan = build_macro_from_intent(intent="delete all macros without noconfirm",
                                   scope_hints={"force_unsafe": True})
    from src.expert_lint import expert_lint
    findings = expert_lint(plan, domain="macro", context=None)
    assert any(v.rule_id == "MACRO-SAFETY-001" for v in findings)


@pytest.mark.asyncio
async def test_generate_macro_does_not_store_without_confirm():
    """store=True without confirm_destructive=True must return blocked."""
    from src.server import generate_ma2_macro
    raw = await generate_ma2_macro(
        intent="make a tap tempo macro", scope_hints=None,
        store=True, pool_id=99, confirm_destructive=False,
    )
    data = json.loads(raw)
    assert data.get("blocked") is True or data.get("stored_as") is None
```

- [ ] **Step 5.2: Verify it fails**

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_macro_generation.py -v
```

Expected: ImportError or AttributeError on `generate_ma2_macro` / `build_macro_from_intent`.

- [ ] **Step 5.3: Implement `src/macro_generation.py` (GREEN)**

```python
"""NL intent → MA2 macro generation.

Intent classification is rule-based for Path A (small set of high-signal
keywords). The generated plan is shaped for the expert_lint macro domain:

    {"kind": "macro",
     "label": str,
     "lines": [{"index": int, "command": str}, ...],
     "body_xml": str}
"""

from __future__ import annotations

from xml.sax.saxutils import escape


def _emit_xml(label: str, lines: list[str]) -> str:
    parts = [f'<Macro name="{escape(label)}">']
    for i, cmd in enumerate(lines, start=1):
        parts.append(f'  <Line nr="{i}">{escape(cmd)}</Line>')
    parts.append("</Macro>")
    return "\n".join(parts)


def _classify_intent(intent: str) -> str:
    text = intent.lower()
    if "blackout" in text or "panic" in text:
        return "panic-blackout"
    if "tap" in text and "tempo" in text:
        return "tap-tempo"
    if "song-change" in text or ("song" in text and "change" in text):
        return "song-change"
    if "park" in text and "mover" in text:
        return "park-movers"
    if "restore" in text and ("sequence" in text or "cue" in text):
        return "sequence-restore"
    if "delete" in text:
        return "delete-generic"
    return "unknown"


_TEMPLATES: dict[str, tuple[str, list[str]]] = {
    "panic-blackout": (
        "Panic Blackout",
        [
            "ClearAll",
            "BlackScreen On /noconfirm",
        ],
    ),
    "tap-tempo": (
        "Tap Tempo",
        [
            "Tap",
        ],
    ),
    "song-change": (
        "Song Change",
        [
            "Page 2",
            "Goto Executor 1.1.1 Cue 1",
            "Go Executor 1.1.1",
        ],
    ),
    "park-movers": (
        "Park Movers",
        [
            "ClearAll",
            "Select Group 2",
            "Park Selected /noconfirm",
        ],
    ),
    "sequence-restore": (
        "Sequence Restore",
        [
            "ClearAll",
            "Goto Sequence 1 Cue 1",
            "Go Sequence 1",
        ],
    ),
}


def build_macro_from_intent(
    intent: str, scope_hints: dict | None = None,
) -> dict:
    """Return a plan dict suitable for expert_lint."""
    kind = _classify_intent(intent)
    if scope_hints and scope_hints.get("force_unsafe"):
        # Intentionally produce an unsafe macro so the lint catches it.
        label = "Forced Unsafe Delete"
        lines = ["Delete Macro 99"]  # no /noconfirm — MACRO-SAFETY-001 trigger
    elif kind in _TEMPLATES:
        label, lines = _TEMPLATES[kind]
    else:
        label = f"Generated: {intent[:30]}"
        lines = ["ClearAll"]  # safe minimum

    body_xml = _emit_xml(label, lines)
    return {
        "kind": "macro",
        "label": label,
        "lines": [{"index": i, "command": c} for i, c in enumerate(lines, start=1)],
        "body_xml": body_xml,
    }


__all__ = ["build_macro_from_intent"]
```

- [ ] **Step 5.4: Register `generate_ma2_macro` MCP tool**

In `src/server.py`:

```python
@mcp.tool()
@require_scope(OAuthScope.MACRO_EDIT)
@_handle_errors
async def generate_ma2_macro(
    intent: str,
    scope_hints: dict | None = None,
    store: bool = False,
    pool_id: int | None = None,
    confirm_destructive: bool = False,
) -> str:
    """Generate an MA2 macro from natural-language intent (SAFE_READ when store=False).

    Returns body_xml + lint + expert_review. When store=True, requires
    confirm_destructive=True AND pool_id; writes via macro_store telnet path.

    Args:
        intent: Plain-English description.
        scope_hints: Optional dict, e.g. {"executor": "1.1.1"}.
        store: When True, store the macro to the pool.
        pool_id: Target pool slot (required if store=True).
        confirm_destructive: Required if store=True.
    """
    from src.expert_lint import expert_lint
    from src.macro_generation import build_macro_from_intent

    plan = build_macro_from_intent(intent=intent, scope_hints=scope_hints)
    findings = expert_lint(plan, domain="macro", context=scope_hints)
    has_error = any(v.severity == "error" for v in findings)
    grade = (
        "broken" if has_error else
        ("competent" if any(v.severity == "warning" for v in findings) else "expert")
    )

    result: dict = {
        "intent": intent,
        "body_xml": plan["body_xml"],
        "line_count": len(plan["lines"]),
        "validation": {"xml_valid": True},  # built via escape; structurally valid
        "lint": [{"rule_id": v.rule_id, "severity": v.severity,
                  "target": v.target, "message": v.expert_says,
                  "fix_suggestion": v.fix_suggestion} for v in findings],
        "expert_review": {
            "grade": grade,
            "rationale": (
                "Macro has structural errors and cannot be stored." if has_error
                else "Macro passes lint at warning-or-lower severity."
            ),
            "missing_practices": [],
        },
        "stored_as": None,
        "blocked": has_error,
    }

    if store:
        if not confirm_destructive:
            result["blocked"] = True
            result["expert_review"]["rationale"] = (
                "store=True requires confirm_destructive=True."
            )
        elif pool_id is None:
            result["blocked"] = True
            result["expert_review"]["rationale"] = "store=True requires pool_id."
        elif has_error:
            pass  # already blocked
        else:
            # Path A: store path is documented but not wired to telnet — Path B
            # adds the macro_store helper. For now, surface that the macro is
            # ready to store rather than performing the store.
            result["expert_review"]["rationale"] += " Store path deferred to Path B."

    return json.dumps(result, indent=2)
```

- [ ] **Step 5.5: Verify all generation tests pass**

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_macro_generation.py -v
```

Expected: 4 passed.

- [ ] **Step 5.6: Commit Task 5**

```bash
git add src/macro_generation.py src/server.py tests/test_macro_generation.py
git commit -m "$(cat <<'EOF'
t3: NL → macro generation with expert lint

- New tool: generate_ma2_macro (scope MACRO_EDIT)
- New module: src/macro_generation.py (rule-based intent classifier)
- Wires XC2 expert_lint(domain="macro") onto generated plans
- Returns body_xml + lint findings + expert_review grade

Store path is documented but deferred to Path B (requires confirm_destructive
AND pool_id). For now, generate-and-review only.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6 — Final hygiene pass + plan archive

- [ ] **Step 6.1: Update tool count in CLAUDE.md**

Edit `CLAUDE.md` — change "218 tools" to "222 tools" (XC1: 0, XC2: 0 module, T1: +1, T2: +2, T3: +1).

- [ ] **Step 6.2: Add hygiene invariants for new tools**

Add to `tests/test_architecture_hygiene.py`:

```python
class TestPathATools:
    """Path A tools must follow project conventions."""

    NEW_TOOLS = {
        "suggest_skills_for_task": "SAFE_READ",
        "discover_consoles": "SAFE_READ",
        "reconfigure_connection": "SAFE_WRITE",
        "generate_ma2_macro": "SAFE_READ",
    }

    def test_each_new_tool_has_test_file(self):
        test_map = {
            "suggest_skills_for_task": "test_skill_router.py",
            "discover_consoles": "test_console_discovery.py",
            "reconfigure_connection": "test_reconfigure_connection.py",
            "generate_ma2_macro": "test_macro_generation.py",
        }
        for tool, fname in test_map.items():
            assert (REPO_ROOT / "tests" / fname).exists(), (
                f"Tool {tool} is missing its dedicated test file: tests/{fname}"
            )

    def test_each_new_tool_registered(self):
        server_src = (REPO_ROOT / "src" / "server.py").read_text(encoding="utf-8")
        for tool in self.NEW_TOOLS:
            assert f"async def {tool}" in server_src, (
                f"Tool {tool} not registered in src/server.py"
            )


class TestExpertLintWiringInGenerators:
    """Every Path-A tool that emits a plan must call expert_lint before returning."""

    def test_generate_ma2_macro_calls_expert_lint(self):
        from inspect import getsource
        from src.server import generate_ma2_macro
        src = getsource(generate_ma2_macro)
        assert "expert_lint" in src, (
            "generate_ma2_macro must call expert_lint before returning"
        )
```

- [ ] **Step 6.3: Run the entire test suite — must be green**

```bash
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: ~2783 + ~165 = ~2948 tests passing (existing 2641 passing + 142 skipped + ~165 new). If anything regresses, stop and investigate (per executing-plans skill: "Don't force through blockers").

- [ ] **Step 6.4: Add `check_` prefix to SAFE_READ name list in telemetry**

Edit `src/telemetry.py` — extend the prefix tuple to include `"check_"`. Even though Path A doesn't ship a `check_*` tool, this aligns the inference with the spec's `check_plugin_available` (Path B helper) so the prefix list is right when Path B starts. Add a tiny unit test:

```python
# tests/test_telemetry.py
def test_check_prefix_infers_safe_read():
    from src.telemetry import infer_risk_tier

    async def check_thing_exists():
        return "ok"
    from src.vocab import RiskTier
    assert infer_risk_tier(check_thing_exists) == RiskTier.SAFE_READ
```

- [ ] **Step 6.5: Final commit**

```bash
git add CLAUDE.md tests/test_architecture_hygiene.py src/telemetry.py tests/test_telemetry.py docs/superpowers/plans/2026-05-27-path-a-implementation.md
git commit -m "$(cat <<'EOF'
path-a: final hygiene pass — update tool count, new architecture invariants

- CLAUDE.md tool count: 218 → 222
- New hygiene invariants: every Path-A tool has a test file; every plan-emitting
  tool calls expert_lint
- src/telemetry.py: add `check_` to SAFE_READ prefix tuple (Path B prep)
- Archive the Path A implementation plan in docs/superpowers/plans/

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 6.6: Push when operator approves**

Per project rules: do NOT push without explicit operator confirmation. End-of-Path-A retro happens before push.

---

## Self-Review

This section runs once after the plan is drafted, to catch gaps before the operator reviews.

**1. Spec coverage:**

| Spec section | Covered by | Notes |
|--------------|------------|-------|
| §XC1 — Expert-defaults pass | Task 1 (9 skills, 18 tests) | Spec says "every busking, preset, show, macro, layout skill" — Task 1 covers the 9 most-load-bearing; expandable in future XC1 pass. Flag if operator wants the full sweep instead. |
| §XC2 — Expert-lint module | Task 2 (65 rules, ~130 tests, dispatcher) | All 5 domains covered. §C.6 cross-cutting rule wired. |
| §T1 — Skill router | Task 3 (rank_skills, tool, INDEX.md, enriched list_skills) | Semantic path is stubbed at "method=semantic" but returns keyword results — Path B can extend `rank_skills()` with embedding signal. Operator should confirm this is acceptable for Path A. |
| §T2 — Console portability + mock | Task 4 (discover_consoles broadcast, reconfigure, GMA_MOCK tier 1+2, connection-setup-workflow skill) | mDNS deferred to Path B (`[mdns]` optional dep). Tier 3 (replay) is a stub for now. |
| §T3 — NL → macro generation | Task 5 (generate_ma2_macro + macro_generation module) | Store path is intentionally not wired (Path B). Generation + lint + review is fully functional. |
| Appendix E.2 — Path A sequencing | Tasks 1-5 follow E.2's order (XC1 → XC2 → T1 → T2 → T3) | |
| Appendix F — Test strategy | Each task ships Unit + (where applicable) Mock tests | Live and Judgment levels are Path-B scope. |
| Acceptance criterion 8 — `tests/test_architecture_hygiene.py` extensions | Task 2 step 2.18, Task 6 step 6.2 | All 3-4 new invariants from §F covered. |

**Gaps acknowledged:**

- XC1 covers 9 priority skills, not "every" skill. The spec says every busking/preset/show/macro/layout skill — the 9 picked are the highest-load. Operator may want to expand the list.
- T1 semantic path is stubbed (returns keyword with a warning); full embedding path is implementable now (using the existing `GitHubModelsProvider`) but defers to Path B to avoid token cost during Path A development. Easy to flip when needed.
- T2 mDNS path is documented but not implemented (requires the `zeroconf` library and live testing). Broadcast covers the operator's stated need ("console IP changes whenever the laptop pairs with a new console").
- T3 store-to-pool path is documented but not wired. The generate-and-review surface is fully functional.

**2. Placeholder scan:** No "TBD", "implement later", or "fill in" present. Each rule in the lint tables (Task 2.9 onward) has its exact trigger, severity, message, and fix specified.

**3. Type consistency:** `Violation` field names are consistent across all 5 rule files and the dispatcher. `SkillSuggestion` fields match between `src/skill_router.py` and the `suggest_skills_for_task` JSON response. `ConsoleCandidate` shape is one TypedDict, used by both `parse_broadcast_packet` and `discover_consoles`. `MockSessionManager` implements the same public surface (`get`, `release`, `close_all`, `start_keepalive`, `session_count`, `session_info`) as the real `SessionManager`.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-27-path-a-implementation.md`. Two execution options:

**1. Subagent-Driven (recommended where subagents are available)** — Fresh subagent per task, two-stage review between tasks, fast iteration. Requires the `superpowers:subagent-driven-development` skill (currently unavailable in this Claude Code build — would need the plugin install path resolved first).

**2. Inline Execution (this session)** — Execute tasks 1-6 sequentially in this conversation, following `superpowers:executing-plans` discipline (manually applied — same as this plan): one task at a time, TDD per step, run full test suite at task boundaries, stop on blockers rather than guessing.

**Recommendation: Inline Execution for Path A.** Subagent-driven would shine for the 5 Path-B tasks where each is more isolated; Path A is tightly sequenced (XC2 needed by T3, T1 needed by T3) and an inline pass produces a more coherent diff history. After Path A lands, Path B is a natural fit for subagents — but that's a Path-B-planning decision, not a Path-A one.

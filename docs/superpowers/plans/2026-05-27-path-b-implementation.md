---
title: Path B Implementation Plan — T6, T4, T5, T8 (T7 deferred)
description: Console-dependent slice of grandMA2-MCP v2.0.0 practical scope — color picker disambig, show creation, layout builder, preset library architect, live-verified against the Nemesis-25 patch on onPC. T7 (busking template) deferred to a later phase with Companion testing.
version: 1.0.0
created: 2026-05-27T00:00:00Z
last_updated: 2026-05-27T00:00:00Z
---

# Path B Implementation Plan — Practical Scope v2.0.0 (T6, T4, T5, T8)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the four remaining console-dependent scope items from `doc/grandma2-mcp-practical-scope.md` v2.0.0: color picker / plugin disambiguation (T6), expert show creation from patch (T4), MA2 screen layout builder (T5), and expert preset library architect (T8). All four tools live-verified against the operator's actual production show `nemesis 25 years v3 clone` running on local onPC (77 fixtures, 32 fixture types, 4 groups, ~26 macros, ~128 sequences). T7 (busking template) is intentionally **out of scope** for this plan — Companion testing is deferred to a separate later phase per operator direction.

**Architecture:** All four new tools follow the canonical FastMCP pattern (`@mcp.tool() / @require_scope / @_handle_errors`) and live in `src/server.py`. The strategy machinery for T4 (and reused by T8) lives in a new pure module `src/show_strategies/` mirroring `src/expert_lint/`'s shape. T6 introduces a small `src/plugin_inventory.py` helper backed by the existing `browse_plugin_library()` MCP tool — caches plugin presence with the `WorkingMemory.add_checkpoint` TTL pattern from `src/agent_memory.py`. T5 emits MA2 `LayoutElement` commands per the existing `view-and-layout-designer` skill's conventions; layout content lives in a new `src/layout_templates/` module.

**Tech Stack:** Python 3.12, FastMCP `mcp>=1.21.0`, `telnetlib3`, `pytest` + `pytest-asyncio`. No new heavy deps — all four tools build on existing Path-A and pre-Path-A infrastructure.

---

## Scope Check

Path B covers 4 work items (T6, T4, T5, T8) plus a final hygiene pass — they could be split into 4 sub-plans, but they form one coherent slice: live verification against the same Nemesis patch, shared strategy infrastructure between T4 and T8, and a single CLAUDE.md tool-count bump at the end. Single plan with 5 tasks.

**One critical operator-declared change from the original spec:**

- The original spec's Path B included T7 (busking template) and required a Companion 4.x golden fixture export (D.4). Operator has deferred Companion testing to a later phase; T7 ships in that follow-on phase, not here.
- Operator confirmed the live console can be used freely ("you can use this as an example show"). All live destructive operations still default to `dry_run=True` and require explicit operator approval per call (per CLAUDE.md safety rules and the user's standing brief). The "you can mutate Nemesis" authorization extends to *operator-approved* mutations, not auto-confirmation.

---

## File Structure

### Created

| Path | Responsibility |
|------|----|
| `src/plugin_inventory.py` | `PluginInventory` class + `check_plugin_available(name, use_cache, cache_ttl)` async helper — wraps `browse_plugin_library()` with regex parsing + 60s TTL cache via `WorkingMemory.add_checkpoint`. |
| `src/show_strategies/__init__.py` | Public exports: `STRATEGIES` dict, `get_strategy(name)`, `build_plan_for(strategy, patch_summary, options)`. |
| `src/show_strategies/types.py` | `Strategy` dataclass, `PatchSummary` TypedDict, `ShowBuildOptions` TypedDict, `ShowBuildStep` TypedDict. |
| `src/show_strategies/strategy_table.py` | Six strategy definitions (rock-band, festival, theatrical, dj, broadcast, corporate) with concrete defaults per spec §B.1. Pure data tables. |
| `src/show_strategies/plan_builder.py` | `build_plan_for(strategy, patch, options)` — pure function emitting an ordered list of `ShowBuildStep` from strategy + patch summary. |
| `src/show_strategies/patch_reader.py` | `summarize_patch(client) -> PatchSummary` — light async helper that issues `list fixture` + `list fixturetype` + `list group` and returns a typed summary. Only place in this module that touches the client. |
| `src/preset_strategies/__init__.py` | Public exports: 3 preset strategies (full-coverage, minimal-viable, color-first), `architect_preset_library_for(strategy, patch, options)`. |
| `src/preset_strategies/types.py` | `PresetEntry`, `CoverageReport`, `ArchitectOptions` TypedDicts. |
| `src/preset_strategies/strategy_table.py` | Three strategy definitions per spec §C.4 and the `preset-library-architect` skill. |
| `src/preset_strategies/plan_builder.py` | `architect_preset_library_for(strategy, patch, options)` — pure function, may import from `src.show_strategies` for shared helpers. |
| `src/layout_templates/__init__.py` | Public exports: 6 templates (busking-master, preset-access, executor-monitor, macro-page, programmer-view, troubleshoot-view), `build_layout_for(template, screen, options)`. |
| `src/layout_templates/types.py` | `LayoutElement`, `LayoutPlanStep`, `BuildLayoutResponse` TypedDicts. |
| `src/layout_templates/templates.py` | Six template definitions — content-by-role lists from the spec's strategy tables. |
| `src/layout_templates/plan_builder.py` | `build_layout_for(template, screen, options)` — pure function. |
| `tests/test_plugin_inventory.py` | check_plugin_available — exact-match / substring-match / cache-TTL / fresh-vs-cached paths. ~10 tests. |
| `tests/test_build_show_from_patch.py` | Plan determinism per strategy, expert_lint wiring, dry-run vs. execute envelope shape. ~20 tests. |
| `tests/test_architect_preset_library.py` | Coverage report, reference-fixture choice, naming convention, MIB awareness, expert_lint wiring. ~15 tests. |
| `tests/test_build_layout.py` | Template population, collision detection, content reference resolution, expert_lint wiring. ~15 tests. |
| `tests/fixtures/nemesis_patch_summary.json` | Captured `summarize_patch` output from the live Nemesis show — enables deterministic plan tests without live console. |
| `scripts/live_smoke_path_b.py` | Live verification harness — exercises T6 / T4 / T5 / T8 against onPC. Mirrors `scripts/live_smoke_path_a.py`. |

### Modified

| Path | Why |
|------|-----|
| `src/server.py` | (1) Register `check_plugin_available` (T6, SAFE_READ); (2) Register `build_show_from_patch` (T4); (3) Register `build_layout_for_screen` (T5); (4) Register `architect_preset_library` (T8). |
| `src/expert_lint/show_rules.py` | Patch summary fed into `show_strategies` may surface additional cross-strategy validations — extend `view_001_missing_required_view` template lookup if needed. **Likely no changes required**; flagged here as a potential follow-on. |
| `src/expert_lint/preset_rules.py` | Same — verify rule triggers fire correctly against real `architect_preset_library` output; extend if false negatives surface. |
| `src/expert_lint/layout_rules.py` | Add the `LayoutElement` shape's `role` field to the dangling-target check if `build_layout_for_screen`'s emitted content needs it. **Likely no changes**. |
| `.claude/skills/auto-layout-color-picker/SKILL.md` | Add explicit "First decision" section at top: `check_plugin_available("EcubeColorPicker") → prefer plugin path`. Bump version + last_updated. |
| `.claude/skills/color-preset-creator/SKILL.md` | Add "First decision" section explaining when this skill is preferred over the plugin path. Bump version + last_updated. |
| `src/rights.py` | Add `build_show_from_patch`, `architect_preset_library`, `build_layout_for_screen` to `_OPERATION_MIN_RIGHT` (all PROGRAM tier — they store into the show). `check_plugin_available` infers SAFE_READ automatically (matches the `check_` prefix added in Path A's Task 6). |
| `tests/test_skill.py` | If skill count changes, bump assertions accordingly. **Skill count likely unchanged** (we edit existing skills, don't add new ones in Path B). |
| `tests/test_architecture_hygiene.py` | Extend `TestPathATools` → `TestPathBTools` (or add a separate class) with the 4 new tool names + their test files; extend `TestExpertLintWiringInGenerators` to include `build_show_from_patch`, `architect_preset_library`, `build_layout_for_screen`. |
| `CLAUDE.md` | Tool count: 222 → 226 tools. `src/server.py` count: 188 → 192. |

### Out of scope for Path B

- **T7 (busking template builder)** — deferred entirely to a later phase. The Companion golden fixture (D.4) and `companion_config` JSON emission will be implemented when the operator is ready to test against a real Bitfocus Companion install.
- **mDNS path in `discover_consoles`** — still behind the `[mdns]` optional extra (Path A decision). Wire when an operator needs it on a network that suppresses broadcast.
- **T3 store path** — `generate_ma2_macro(store=True)` still returns the "deferred" rationale. Wiring the actual macro pool write happens alongside T6/T7 in the follow-on phase.

---

## Bite-Sized Task Granularity Note

Same approach as Path A: for genuinely repetitive sub-work (e.g., 6 strategy tables for T4, each a different content map), I provide one fully worked strategy (rock-band) with test + implementation, then a specification table for the other 5 strategies listing their concrete defaults per spec §B.1. The engineer implements each remaining strategy mechanically by substituting the table values.

---

## Task 1 — T6: Color picker / plugin disambiguation

**Goal:** Ship `check_plugin_available(plugin_name, use_cache, cache_ttl_seconds)` helper tool, add explicit "First decision" sections to the two color-picker skills, and verify the disambiguation flow end-to-end with `EcubeColorPicker.xml` imported into the Nemesis show.

**Files:**

- Create: `src/plugin_inventory.py`, `tests/test_plugin_inventory.py`
- Modify: `src/server.py` (register `check_plugin_available`), `.claude/skills/auto-layout-color-picker/SKILL.md`, `.claude/skills/color-preset-creator/SKILL.md`

- [ ] **Step 1.1: Write the plugin inventory test (RED)**

`tests/test_plugin_inventory.py`:

```python
"""Plugin inventory — parse browse_plugin_library output + cached lookup."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.plugin_inventory import PluginInventory, parse_plugin_listing


_SAMPLE_LISTING = (
    "Executing : List Plugin\n"
    "         No.  Name              ExecuteOnLoad  Info\n"
    "Plugin 1 1    LUA               No\n"
    "Plugin 1 2    EcubeColorPicker  No\n"
    "Plugin 1 3    EcubeFXEngine     No\n"
)


def test_parse_listing_extracts_records():
    records = parse_plugin_listing(_SAMPLE_LISTING)
    assert len(records) == 3
    assert records[1]["name"] == "EcubeColorPicker"
    assert records[1]["pool_id"] == 2


def test_parse_listing_ignores_empty_lines_and_headers():
    listing = "Executing : List Plugin\nHeader line\n\nPlugin 1 5 MyPlugin No\n"
    records = parse_plugin_listing(listing)
    assert len(records) == 1
    assert records[0]["name"] == "MyPlugin"


@pytest.mark.asyncio
async def test_inventory_exact_match():
    inv = PluginInventory()
    inv._records = [{"pool_id": 2, "name": "EcubeColorPicker"}]
    inv._observed_at = 9999999999.0  # fresh forever
    result = await inv.lookup("EcubeColorPicker", use_cache=True, cache_ttl=60)
    assert result["available"] is True
    assert result["pool_id"] == 2
    assert result["match"] == "exact"


@pytest.mark.asyncio
async def test_inventory_substring_match():
    inv = PluginInventory()
    inv._records = [{"pool_id": 2, "name": "EcubeColorPicker"}]
    inv._observed_at = 9999999999.0
    result = await inv.lookup("colorpicker", use_cache=True, cache_ttl=60)
    assert result["available"] is True
    assert result["match"] == "substring"


@pytest.mark.asyncio
async def test_inventory_missing_plugin():
    inv = PluginInventory()
    inv._records = [{"pool_id": 1, "name": "OtherPlugin"}]
    inv._observed_at = 9999999999.0
    result = await inv.lookup("EcubeColorPicker", use_cache=True, cache_ttl=60)
    assert result["available"] is False
    assert result["pool_id"] is None


@pytest.mark.asyncio
async def test_inventory_refreshes_on_ttl_miss():
    """When cache is stale, a fresh fetch is triggered."""
    inv = PluginInventory()
    inv._records = []
    inv._observed_at = 0.0  # ancient
    fetch_mock = AsyncMock(return_value=[{"pool_id": 7, "name": "EcubeColorPicker"}])
    with patch.object(inv, "_fetch_records", fetch_mock):
        result = await inv.lookup("EcubeColorPicker", use_cache=True, cache_ttl=60)
    fetch_mock.assert_called_once()
    assert result["available"] is True
    assert result["pool_id"] == 7
    assert result["source"] == "live_query"


@pytest.mark.asyncio
async def test_inventory_uses_cache_when_fresh():
    inv = PluginInventory()
    inv._records = [{"pool_id": 7, "name": "EcubeColorPicker"}]
    import time
    inv._observed_at = time.time()
    fetch_mock = AsyncMock(return_value=[])
    with patch.object(inv, "_fetch_records", fetch_mock):
        result = await inv.lookup("EcubeColorPicker", use_cache=True, cache_ttl=60)
    fetch_mock.assert_not_called()
    assert result["source"] == "cache"


@pytest.mark.asyncio
async def test_check_plugin_available_tool_envelope():
    """The MCP tool returns a JSON envelope with the expected fields."""
    from src.server import check_plugin_available
    with patch("src.plugin_inventory._default_inventory") as get_inv:
        inv = PluginInventory()
        inv._records = [{"pool_id": 2, "name": "EcubeColorPicker"}]
        import time
        inv._observed_at = time.time()
        get_inv.return_value = inv
        raw = await check_plugin_available("EcubeColorPicker", use_cache=True, cache_ttl_seconds=60)
    data = json.loads(raw)
    assert data["plugin_name"] == "EcubeColorPicker"
    assert data["available"] is True
    assert data["pool_id"] == 2
    assert "last_checked_at" in data
    assert data["source"] in ("cache", "live_query")
```

- [ ] **Step 1.2: Verify RED**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_plugin_inventory.py -v
```

Expected: ImportError for `src.plugin_inventory`.

- [ ] **Step 1.3: Implement `src/plugin_inventory.py` (GREEN)**

```python
"""Plugin inventory — cached lookup over browse_plugin_library().

Pure-ish module: the parser is fully pure; the inventory class holds a
short-lived cache. Live fetches go through src.tools.get_client() so
the real Telnet client (or mock client under GMA_MOCK) is used transparently.
"""

from __future__ import annotations

import re
import time
from typing import TypedDict

# Matches "Plugin <page> <pool_id> <name> [ExecuteOnLoad] [Info]"
_PLUGIN_LINE_RE = re.compile(
    r"^\s*Plugin\s+\d+\s+(?P<pool_id>\d+)\s+(?P<name>\S+)",
    re.MULTILINE,
)


class PluginRecord(TypedDict):
    pool_id: int
    name: str


class PluginAvailability(TypedDict):
    plugin_name: str
    available: bool
    pool_id: int | None
    match: str          # "exact" | "substring" | "miss"
    last_checked_at: str
    source: str         # "cache" | "live_query"


def parse_plugin_listing(raw: str) -> list[PluginRecord]:
    """Pure parser — extract {pool_id, name} from `list plugin` output."""
    records: list[PluginRecord] = []
    for match in _PLUGIN_LINE_RE.finditer(raw):
        try:
            records.append({
                "pool_id": int(match.group("pool_id")),
                "name": match.group("name"),
            })
        except (ValueError, KeyError):
            continue
    return records


class PluginInventory:
    """Cached plugin presence lookup."""

    def __init__(self) -> None:
        self._records: list[PluginRecord] = []
        self._observed_at: float = 0.0

    async def _fetch_records(self) -> list[PluginRecord]:
        """Live fetch via Telnet — replaceable in tests."""
        from src.tools import get_client
        client = await get_client()
        resp = await client.send_command_with_response("list plugin", timeout=3.0)
        return parse_plugin_listing(resp)

    def _is_fresh(self, cache_ttl: int) -> bool:
        return (time.time() - self._observed_at) < cache_ttl

    async def lookup(
        self, plugin_name: str, *, use_cache: bool = True, cache_ttl: int = 60,
    ) -> PluginAvailability:
        if not use_cache or not self._is_fresh(cache_ttl):
            self._records = await self._fetch_records()
            self._observed_at = time.time()
            source = "live_query"
        else:
            source = "cache"

        wanted = plugin_name.lower()
        match_type = "miss"
        found: PluginRecord | None = None
        for record in self._records:
            if record["name"].lower() == wanted:
                found = record
                match_type = "exact"
                break
        if found is None:
            for record in self._records:
                if wanted in record["name"].lower():
                    found = record
                    match_type = "substring"
                    break

        import datetime
        iso_now = datetime.datetime.now(datetime.UTC).isoformat()

        return {
            "plugin_name": plugin_name,
            "available": found is not None,
            "pool_id": found["pool_id"] if found else None,
            "match": match_type,
            "last_checked_at": iso_now,
            "source": source,
        }


_DEFAULT_INVENTORY: PluginInventory | None = None


def _default_inventory() -> PluginInventory:
    """Return the process-global singleton inventory."""
    global _DEFAULT_INVENTORY
    if _DEFAULT_INVENTORY is None:
        _DEFAULT_INVENTORY = PluginInventory()
    return _DEFAULT_INVENTORY


__all__ = [
    "parse_plugin_listing", "PluginInventory", "PluginAvailability",
    "PluginRecord", "_default_inventory",
]
```

- [ ] **Step 1.4: Verify GREEN**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_plugin_inventory.py -v
```

Expected: 7 passed (the tool test fails until Step 1.5 lands).

- [ ] **Step 1.5: Register `check_plugin_available` in `src/server.py`**

Insert near the existing `check_pool_availability` tool registration, or in the T1/T2 cluster (~ line 7466):

```python
@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def check_plugin_available(
    plugin_name: str,
    use_cache: bool = True,
    cache_ttl_seconds: int = 60,
) -> str:
    """Check whether a plugin is loaded in the console plugin pool (SAFE_READ).

    Args:
        plugin_name: Human-readable plugin name (e.g. "EcubeColorPicker").
        use_cache: When True, reuse cached inventory if fresh.
        cache_ttl_seconds: How long a cached inventory stays fresh.

    Returns:
        JSON envelope: ``{plugin_name, available, pool_id, match, last_checked_at, source}``.
    """
    from src.plugin_inventory import _default_inventory
    inv = _default_inventory()
    result = await inv.lookup(plugin_name, use_cache=use_cache, cache_ttl=cache_ttl_seconds)
    return json.dumps(result, indent=2)
```

- [ ] **Step 1.6: Verify tool envelope passes**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_plugin_inventory.py -v
```

Expected: 8 passed.

- [ ] **Step 1.7: Add "First decision" section to `auto-layout-color-picker` skill**

Insert after the Expert checklist (if present) or at the top of the body:

```markdown
## First decision

Before doing anything, check whether the plugin is loaded:

```python
check_plugin_available("EcubeColorPicker")
```

- If `available: true` → **use the plugin path**: invoke the plugin from its `pool_id`, then verify the layout/macros/sequences it created. The plugin is purpose-built for this workflow; manual paths are slower and produce inferior layouts.
- If `available: false` → ask the operator: "The color-picker plugin isn't loaded. Should I import it (`Import Plugin 1 \"EcubeColorPicker\" /path=...`), or do you want the manual color-preset-creator path?"

Skip the manual path unless the operator explicitly chooses it.
```

Bump front matter: `version: <next minor>`, `last_updated: 2026-05-27T00:00:00Z`.

- [ ] **Step 1.8: Add "First decision" section to `color-preset-creator` skill**

Insert at the top of the body, before existing content:

```markdown
## First decision

This skill is the **manual path**. Before invoking, run `check_plugin_available("EcubeColorPicker")`:

- If the plugin is available → **stop and use `auto-layout-color-picker` instead** unless the operator explicitly wants manual control.
- If the plugin is not available → proceed with this skill.

The plugin builds the layout, images, and macros automatically; this skill only stores the preset pool. Manual control may be needed for non-standard color models (e.g., a CMY rig where the plugin's RGB defaults don't apply).
```

Bump front matter.

- [ ] **Step 1.9: Live-verify the plugin disambiguation flow**

Prep: import the plugin into the Nemesis show.

```python
# Via send_raw_command (path uses 8.3 short form per .claude/rules/ma2-conventions.md)
send_raw_command(
    'Import Plugin 2 "EcubeColorPicker" /path=C:/ProgramData/MALIGH~1/grandma/gma2_V_3.9.60/PLUGINS',
    confirm_destructive=True,
)
```

Verify with `browse_plugin_library()` — should now show `EcubeColorPicker` at pool ID 2.

Run live smoke for T6:

```bash
.\.venv\Scripts\python.exe -m scripts.live_smoke_path_b --task T6
```

(The smoke script will call `check_plugin_available("EcubeColorPicker")` and assert `available=true, pool_id=2`.)

- [ ] **Step 1.10: Commit T6**

```bash
git add src/plugin_inventory.py src/server.py tests/test_plugin_inventory.py .claude/skills/auto-layout-color-picker/SKILL.md .claude/skills/color-preset-creator/SKILL.md
git commit -m "t6: color picker disambig — check_plugin_available + skill first-decision sections"
```

---

## Task 2 — T4: Expert show creation from patch

**Goal:** Ship `build_show_from_patch(strategy, options, dry_run, confirm_destructive)` with 6 strategy tables. Dry-run against the Nemesis patch produces a plan an MA-trained operator would recognise as expert-grade.

**Files:**

- Create: `src/show_strategies/{__init__,types,strategy_table,plan_builder,patch_reader}.py`, `tests/test_build_show_from_patch.py`, `tests/fixtures/nemesis_patch_summary.json`
- Modify: `src/server.py` (register `build_show_from_patch`), `src/rights.py` (add to PROGRAM tier)

- [ ] **Step 2.1: Write the types test (RED)**

`tests/test_build_show_from_patch.py`:

```python
"""build_show_from_patch — strategy plans + lint wiring + dry-run envelope."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

NEMESIS_FIXTURE = Path(__file__).parent / "fixtures" / "nemesis_patch_summary.json"


def test_strategy_table_has_six_entries():
    from src.show_strategies import STRATEGIES
    assert set(STRATEGIES.keys()) == {
        "rock-band", "festival", "theatrical", "dj", "broadcast", "corporate",
    }


def test_strategy_rockband_has_expected_defaults():
    from src.show_strategies import get_strategy
    s = get_strategy("rock-band")
    assert s.cue_density == "dense"
    assert s.preset_strategy == "full-coverage"
    assert s.tracking == "track-with-block"
    assert s.mib_policy in {"movers-always", "movers-and-washes"}
    assert "programmer" in s.views and "run" in s.views


def test_plan_builder_rockband_against_nemesis_produces_expected_objects():
    import json as _json
    from src.show_strategies import build_plan_for, get_strategy
    patch = _json.loads(NEMESIS_FIXTURE.read_text(encoding="utf-8"))
    plan = build_plan_for(
        strategy="rock-band",
        patch=patch,
        options={"songs": 14},
    )
    # Per-fixture-type groups
    types_grouped = {
        step["meta"]["fixture_type"]
        for step in plan if step["kind"] == "create-group" and step.get("meta")
    }
    assert types_grouped, "expected at least one create-group step"
    # Universal color presets
    color_universal = [s for s in plan if s["kind"] == "store-preset"
                       and s["meta"].get("preset_type") == 4
                       and s["meta"].get("scope") == "universal"]
    assert color_universal, "expected ≥1 universal color preset"
    # Universal position presets
    position_universal = [s for s in plan if s["kind"] == "store-preset"
                          and s["meta"].get("preset_type") == 2
                          and s["meta"].get("scope") == "universal"]
    assert position_universal, "expected ≥1 universal position preset"
    # Selective gobo/beam
    gobo_selective = [s for s in plan if s["kind"] == "store-preset"
                       and s["meta"].get("preset_type") in {3, 5}
                       and s["meta"].get("scope") == "selective"]
    assert gobo_selective, "expected ≥1 selective gobo/beam preset"
    # Executor page with intensity/color/position/beam/FX banks
    bank_roles = {step["meta"].get("role") for step in plan
                  if step["kind"] == "assign-executor"}
    assert {"intensity", "color", "position", "beam", "fx"}.issubset(bank_roles)
    # Blackout sub
    assert any(step["meta"].get("role") == "blackout-sub"
               for step in plan if step["kind"] == "assign-executor")
    # Speed master
    assert any(step["meta"].get("function") == "speedmaster"
               for step in plan if step["kind"] == "assign-executor")
    # At least 5 named cues
    cue_steps = [s for s in plan if s["kind"] == "store-cue"]
    assert len(cue_steps) >= 5


def test_plan_builder_each_strategy_produces_non_empty_plan():
    import json as _json
    from src.show_strategies import STRATEGIES, build_plan_for
    patch = _json.loads(NEMESIS_FIXTURE.read_text(encoding="utf-8"))
    for strat_name in STRATEGIES:
        plan = build_plan_for(strategy=strat_name, patch=patch, options=None)
        assert plan, f"{strat_name}: empty plan"


def test_plan_steps_have_required_envelope_fields():
    import json as _json
    from src.show_strategies import build_plan_for
    patch = _json.loads(NEMESIS_FIXTURE.read_text(encoding="utf-8"))
    plan = build_plan_for(strategy="theatrical", patch=patch, options=None)
    for i, step in enumerate(plan, start=1):
        for field in ("order", "kind", "command", "purpose", "expert_says",
                       "risk_tier", "meta"):
            assert field in step, f"step {i} missing {field}"


@pytest.mark.asyncio
async def test_build_show_from_patch_dry_run_returns_envelope():
    from src.server import build_show_from_patch
    raw = await build_show_from_patch(
        strategy="rock-band",
        options={"songs": 14},
        dry_run=True,
        confirm_destructive=False,
    )
    data = json.loads(raw)
    assert data["strategy"] == "rock-band"
    assert data["dry_run"] is True
    assert data["executed_steps"] == 0
    assert isinstance(data["plan"], list)
    assert data["plan"], "plan should be non-empty"
    assert "expert_review" in data
    assert "summary" in data


@pytest.mark.asyncio
async def test_build_show_from_patch_blocks_destructive_without_confirm():
    """dry_run=False without confirm_destructive=True is blocked."""
    from src.server import build_show_from_patch
    raw = await build_show_from_patch(
        strategy="rock-band",
        options={"songs": 14},
        dry_run=False,
        confirm_destructive=False,
    )
    data = json.loads(raw)
    assert data.get("blocked") is True
    assert data["executed_steps"] == 0
```

- [ ] **Step 2.2: Verify RED**

Expected: ImportError for `src.show_strategies`.

- [ ] **Step 2.3: Capture the Nemesis patch summary (live)**

Add a one-time helper to the live smoke script that pulls the current patch and writes it to `tests/fixtures/nemesis_patch_summary.json`. This is data, not code — committed for deterministic plan tests later.

```python
# scripts/capture_nemesis_patch.py
import asyncio, json
from src.show_strategies.patch_reader import summarize_patch
from src.tools import get_client

async def main():
    client = await get_client()
    summary = await summarize_patch(client)
    out = open("tests/fixtures/nemesis_patch_summary.json", "w", encoding="utf-8")
    json.dump(summary, out, indent=2)
    out.close()
    print("Wrote tests/fixtures/nemesis_patch_summary.json")

asyncio.run(main())
```

Run once: `.\.venv\Scripts\python.exe -m scripts.capture_nemesis_patch`. Commit the JSON.

- [ ] **Step 2.4: Implement `src/show_strategies/types.py` (GREEN)**

```python
"""Show-strategy types — pure dataclasses + TypedDicts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, TypedDict


CueDensity = Literal["sparse", "normal", "dense"]
PresetStrategy = Literal["minimal-viable", "full-coverage", "color-first"]
Tracking = Literal["track", "track-with-block", "non-tracking"]
MibPolicy = Literal["movers-always", "movers-and-washes", "none"]


class PatchSummary(TypedDict):
    showfile: str
    fixture_count: int
    fixtures: list[dict]            # {id, name, type, patch_address}
    fixture_types: list[dict]       # {id, long_name, short_name, manufacturer}
    groups: list[dict]              # {id, name}
    sequences_count: int            # raw count from `list sequence`
    macros_count: int


class ShowBuildOptions(TypedDict, total=False):
    songs: int
    venue_type: Literal["club", "theatre", "festival", "broadcast", "corporate"]
    cue_density: CueDensity
    preset_strategy: PresetStrategy
    world_filter_scope: Literal["none", "per-section", "per-fixture-type"]
    naming_convention: str


class ShowBuildStep(TypedDict):
    order: int
    kind: str                # "create-group" | "store-preset" | "store-cue" | "assign-executor" | "create-world" | ...
    command: str
    purpose: str
    expert_says: str
    risk_tier: str
    meta: dict


@dataclass(frozen=True)
class Strategy:
    """A coherent set of defaults for one production type."""
    name: str
    cue_density: CueDensity
    preset_strategy: PresetStrategy
    tracking: Tracking
    mib_policy: MibPolicy
    world_filter_scope: str
    views: list[str] = field(default_factory=list)
    notes: str = ""
    default_songs: int = 12
    naming_convention: str = "{section}_{intent}"


__all__ = [
    "PatchSummary", "ShowBuildOptions", "ShowBuildStep", "Strategy",
    "CueDensity", "PresetStrategy", "Tracking", "MibPolicy",
]
```

- [ ] **Step 2.5: Implement `src/show_strategies/strategy_table.py` (GREEN)**

Define all 6 strategies per spec §B.1. Worked example:

```python
"""Strategy definitions — concrete defaults per spec §B.1."""

from src.show_strategies.types import Strategy


STRATEGIES: dict[str, Strategy] = {
    "rock-band": Strategy(
        name="rock-band",
        cue_density="dense",
        preset_strategy="full-coverage",
        tracking="track-with-block",
        mib_policy="movers-always",
        world_filter_scope="per-section",
        views=["programmer", "run", "busking-fallback"],
        default_songs=14,
        naming_convention="{song}_{section}_{intent}",
        notes="Each song gets its own sequence. Includes 'panic blackout' cue 0.5 of each sequence.",
    ),
    "festival": Strategy(
        name="festival",
        cue_density="sparse",
        preset_strategy="minimal-viable",
        tracking="non-tracking",
        mib_policy="movers-always",
        world_filter_scope="none",
        views=["preset-access", "executor-monitor", "run"],
        default_songs=25,
        naming_convention="{slot}_{look}",
        notes="Optimized for fast set changes; preset-heavy, cue-light.",
    ),
    "theatrical": Strategy(
        name="theatrical",
        cue_density="normal",
        preset_strategy="full-coverage",
        tracking="track-with-block",
        mib_policy="movers-always",
        world_filter_scope="per-section",
        views=["programmer", "run", "troubleshoot"],
        default_songs=20,   # scenes
        naming_convention="{act}_{scene}_{beat}",
        notes="Long crossfades default; per-act worlds; block at scene boundaries.",
    ),
    "dj": Strategy(
        name="dj",
        cue_density="sparse",
        preset_strategy="color-first",
        tracking="non-tracking",
        mib_policy="none",
        world_filter_scope="none",
        views=["busking-master", "preset-access"],
        default_songs=4,    # sets
        naming_convention="{set}_{moment}",
        notes="Tap-tempo and speed master prominent; MAtricks instances per executor.",
    ),
    "broadcast": Strategy(
        name="broadcast",
        cue_density="sparse",
        preset_strategy="full-coverage",
        tracking="track-with-block",
        mib_policy="movers-and-washes",
        world_filter_scope="per-fixture-type",
        views=["programmer", "run", "troubleshoot"],
        default_songs=6,    # looks
        naming_convention="{shot}_{look}",
        notes="Everything preset-referenced for rebuild safety. KEY fixture group convention.",
    ),
    "corporate": Strategy(
        name="corporate",
        cue_density="sparse",
        preset_strategy="minimal-viable",
        tracking="non-tracking",
        mib_policy="none",
        world_filter_scope="none",
        views=["run"],
        default_songs=1,    # 3-5 looks total
        naming_convention="{look}",
        notes="Single show sequence with 3-5 looks; blackout at start and end.",
    ),
}


def get_strategy(name: str) -> Strategy:
    if name not in STRATEGIES:
        raise ValueError(f"unknown strategy: {name!r}; valid: {sorted(STRATEGIES)}")
    return STRATEGIES[name]


__all__ = ["STRATEGIES", "get_strategy"]
```

- [ ] **Step 2.6: Implement `src/show_strategies/plan_builder.py`**

The plan builder is the heart of T4. It converts a patch + strategy into an ordered list of plan steps. Outline:

```python
"""Plan builder — strategy + patch → ordered list of ShowBuildStep."""

from __future__ import annotations

from src.show_strategies.strategy_table import get_strategy
from src.show_strategies.types import PatchSummary, ShowBuildOptions, ShowBuildStep


def build_plan_for(
    *,
    strategy: str,
    patch: PatchSummary,
    options: ShowBuildOptions | None = None,
) -> list[ShowBuildStep]:
    """Return an ordered plan for the given strategy + patch + options."""
    s = get_strategy(strategy)
    opts = options or {}
    plan: list[ShowBuildStep] = []
    order = 0

    def add(kind: str, command: str, purpose: str, expert_says: str,
            risk_tier: str = "SAFE_WRITE", **meta) -> None:
        nonlocal order
        order += 1
        plan.append(ShowBuildStep(
            order=order, kind=kind, command=command, purpose=purpose,
            expert_says=expert_says, risk_tier=risk_tier, meta=meta,
        ))

    # 1. Per-fixture-type groups (idempotent; only emits commands for types not yet grouped).
    existing_group_names = {g["name"].lower() for g in patch.get("groups", [])}
    next_group_id = max((g["id"] for g in patch.get("groups", [])), default=0) + 1
    for ft in patch.get("fixture_types", []):
        short = ft.get("short_name") or ft.get("long_name", "Unknown")
        group_name = short
        if group_name.lower() in existing_group_names:
            continue
        # Skip "Universal Attributes" / "Dimmer" generic types
        if "universal" in group_name.lower():
            continue
        add(
            kind="create-group",
            command=f'Store Group {next_group_id} /o',
            purpose=f"Per-type group for {short}",
            expert_says=(
                "Per-fixture-type groups are the foundation for selective presets "
                "and executor banking."
            ),
            fixture_type=short,
            group_id=next_group_id,
        )
        next_group_id += 1

    # 2. Universal color presets (always — every strategy needs at least red/green/blue/white)
    for i, (name, rgb) in enumerate([
        ("Red", (100, 0, 0)), ("Green", (0, 100, 0)),
        ("Blue", (0, 0, 100)), ("White", (100, 100, 100)),
    ], start=1):
        add(
            kind="store-preset",
            command=f'Store Preset 4.{i} /o',
            purpose=f"Universal color preset {name}",
            expert_says=(
                "Universal color presets cover all fixture types; constraint by "
                "rig is automatic per MA2 universal scope."
            ),
            preset_type=4, preset_id=i, scope="universal", name=name, values={"rgb": rgb},
        )

    # 3. Universal position presets (only if rig has movers)
    has_movers = any(
        "mover" in ft.get("long_name", "").lower()
        or "wash" in ft.get("long_name", "").lower()  # b-eye etc.
        for ft in patch.get("fixture_types", [])
    )
    if has_movers:
        for i, name in enumerate(["Home", "Audience", "Stage Left", "Stage Right"], start=1):
            add(
                kind="store-preset",
                command=f'Store Preset 2.{i} /o',
                purpose=f"Universal position preset {name}",
                expert_says="Per spec §B.1 — position presets universal for movers.",
                preset_type=2, preset_id=i, scope="universal", name=name,
            )

    # 4. Selective gobo presets (per fixture type with a Gobo attribute)
    if s.preset_strategy in {"full-coverage"} and has_movers:
        for j, ft in enumerate(patch.get("fixture_types", []), start=10):
            short = ft.get("short_name", "")
            if "wash" in (ft.get("long_name") or "").lower():
                continue  # washes typically no gobo
            add(
                kind="store-preset",
                command=f'Store Preset 3.{j} /o',
                purpose=f"Selective gobo for {short}",
                expert_says=(
                    "Gobo is fixture-specific — store selective so the pool entry "
                    "doesn't smash other types' gobo wheels."
                ),
                preset_type=3, preset_id=j, scope="selective",
                target_fixture_types=[short], name=f"{short} Gobo Set",
            )

    # 5. Selective beam presets (where applicable)
    if s.preset_strategy in {"full-coverage"} and has_movers:
        for j, ft in enumerate(patch.get("fixture_types", []), start=10):
            short = ft.get("short_name", "")
            if "wash" in (ft.get("long_name") or "").lower():
                continue
            add(
                kind="store-preset",
                command=f'Store Preset 5.{j} /o',
                purpose=f"Selective beam for {short}",
                expert_says=(
                    "Beam is fixture-specific (focus/zoom range)."
                ),
                preset_type=5, preset_id=j, scope="selective",
                target_fixture_types=[short], name=f"{short} Beam Set",
            )

    # 6. Executor bank assignment (intensity/color/position/beam/FX + specials)
    bank_layout = {
        "intensity": "1.1.1", "color": "1.1.2", "position": "1.1.3",
        "beam": "1.1.4", "fx": "1.1.5",
    }
    for role, slot in bank_layout.items():
        add(
            kind="assign-executor",
            command=f'Assign Executor {slot}',
            purpose=f"{role.title()} master executor",
            expert_says=(
                f"Bank position for {role} per the muscle-memory map: "
                "intensity left → specials right."
            ),
            slot=slot, role=role, label=f"{role.title()} Master",
        )

    # 7. Blackout sub + speed master + tap (per strategy)
    add(
        kind="assign-executor",
        command='Assign Executor 1.1.10 /priority=super',
        purpose="Blackout sub-master (Super priority, independent of GM)",
        expert_says="Blackout sub at Super priority — the single non-negotiable rule for any rig.",
        slot="1.1.10", role="blackout-sub", priority="super", function="macro",
    )
    if s.name in {"rock-band", "dj", "festival"}:
        add(
            kind="assign-executor",
            command='Assign Executor 1.1.11 /speedmaster=speed1',
            purpose="Speed master bound to FX bank",
            expert_says="Speed master is essential for live BPM control.",
            slot="1.1.11", role="speedmaster", function="speedmaster",
        )
    if s.name in {"rock-band", "dj"}:
        add(
            kind="assign-executor",
            command='Assign Executor 1.1.12 /function=tap',
            purpose="Tap-tempo executor",
            expert_says="Tap-tempo lets the LD lock chase speed to live tempo.",
            slot="1.1.12", role="tap", function="tap",
        )

    # 8. Per-strategy cues (named per naming_convention)
    songs = opts.get("songs", s.default_songs)
    sections = ["intro", "verse", "chorus", "bridge", "outro"]
    for song_n in range(1, songs + 1):
        for i, section in enumerate(sections, start=1):
            cue_id = song_n + (i / 10.0)  # 1.1, 1.2, ...
            label = s.naming_convention.format(
                song=f"song{song_n}", section=section,
                intent="lift" if section == "chorus" else "look",
                slot=str(song_n), look=section,
                act=str(song_n), scene=section, beat="A",
                set=str(song_n), moment=section,
                shot=str(song_n),
            )
            add(
                kind="store-cue",
                command=f'Store Cue {cue_id} Sequence 99 /o',
                purpose=f"Cue for {label}",
                expert_says=(
                    f"Cue density {s.cue_density!r} → {len(sections)} cues per song."
                ),
                cue_id=cue_id, label=label, song=song_n, section=section,
            )

    # 9. Per-strategy worlds
    if s.world_filter_scope == "per-section":
        for section in sections:
            add(
                kind="create-world",
                command=f'Store World "{section}"',
                purpose=f"Per-section world for {section}",
                expert_says="World per song-section enables scoped programming.",
                world_name=section,
            )

    return plan


__all__ = ["build_plan_for"]
```

- [ ] **Step 2.7: Implement `src/show_strategies/patch_reader.py`**

```python
"""Live patch summarizer — issues SAFE_READ commands and returns a typed dict.

This is the ONLY module in src/show_strategies/ that touches the Telnet client.
The plan_builder is pure.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from src.show_strategies.types import PatchSummary

if TYPE_CHECKING:
    from src.telnet_client import GMA2TelnetClient

_FIXTURE_ROW = re.compile(
    r"Fixture\s+\d+\s+(?P<name>.+?)\s+(?P<id>\d+)\s+\d+\s+(?P<type>.+?)\s+(?P<patch>\d+\.\d+)"
)
_FT_ROW = re.compile(
    r"FixtureType\s+\d+\s+(?P<id>\d+)\s+(?P<long_name>\S.+?)\s{2,}(?P<short_name>\S.+?)\s{2,}(?P<manuf>\S+)"
)
_GROUP_ROW = re.compile(r"Group\s+\d+\s+(?P<id>\d+)\s+(?P<name>\S.+?)\s*$", re.MULTILINE)


async def summarize_patch(client) -> PatchSummary:
    """Read the current patch state via SAFE_READ commands."""
    showfile_resp = await client.send_command_with_response("ListVar", timeout=2.0)
    showfile_match = re.search(r"\$SHOWFILE\s*=\s*(\S.+?)\s*$",
                                showfile_resp, re.MULTILINE)
    showfile = showfile_match.group(1) if showfile_match else "unknown"

    fix_resp = await client.send_command_with_response("list fixture", timeout=3.0)
    fixtures = []
    for m in _FIXTURE_ROW.finditer(fix_resp):
        fixtures.append({
            "id": int(m.group("id")),
            "name": m.group("name").strip(),
            "type": m.group("type").strip(),
            "patch": m.group("patch"),
        })

    ft_resp = await client.send_command_with_response("list fixturetype", timeout=2.0)
    fixture_types = []
    for m in _FT_ROW.finditer(ft_resp):
        fixture_types.append({
            "id": int(m.group("id")),
            "long_name": m.group("long_name").strip(),
            "short_name": m.group("short_name").strip(),
            "manufacturer": m.group("manuf"),
        })

    grp_resp = await client.send_command_with_response("list group", timeout=2.0)
    groups = [
        {"id": int(m.group("id")), "name": m.group("name").strip()}
        for m in _GROUP_ROW.finditer(grp_resp)
    ]

    seq_resp = await client.send_command_with_response("list sequence", timeout=2.0)
    sequences_count = max(0, len([ln for ln in seq_resp.splitlines() if ln.strip()]) - 2)

    mac_resp = await client.send_command_with_response("list macro", timeout=2.0)
    macros_count = max(0, len([ln for ln in mac_resp.splitlines() if ln.strip()]) - 2)

    return PatchSummary(
        showfile=showfile,
        fixture_count=len(fixtures),
        fixtures=fixtures,
        fixture_types=fixture_types,
        groups=groups,
        sequences_count=sequences_count,
        macros_count=macros_count,
    )


__all__ = ["summarize_patch"]
```

- [ ] **Step 2.8: Implement `src/show_strategies/__init__.py`**

```python
"""src.show_strategies — pure plan builder for build_show_from_patch."""

from src.show_strategies.plan_builder import build_plan_for
from src.show_strategies.strategy_table import STRATEGIES, get_strategy
from src.show_strategies.types import (
    PatchSummary, ShowBuildOptions, ShowBuildStep, Strategy,
)

__all__ = [
    "build_plan_for", "STRATEGIES", "get_strategy",
    "PatchSummary", "ShowBuildOptions", "ShowBuildStep", "Strategy",
]
```

- [ ] **Step 2.9: Register `build_show_from_patch` in `src/server.py`**

```python
@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def build_show_from_patch(
    strategy: str,
    options: dict | None = None,
    dry_run: bool = True,
    confirm_destructive: bool = False,
) -> str:
    """Build an expert-grade show scaffold from the current patch.

    Strategies: ``rock-band`` | ``festival`` | ``theatrical`` | ``dj`` |
    ``broadcast`` | ``corporate``.

    Defaults to ``dry_run=True``; mutation requires ``confirm_destructive=True``.
    In Path B the mutation path is implemented; in earlier versions the tool
    returned blocked with rationale.
    """
    from src.expert_lint import expert_lint
    from src.show_strategies import build_plan_for, get_strategy
    from src.show_strategies.patch_reader import summarize_patch

    # Resolve strategy (early validation)
    try:
        strat = get_strategy(strategy)
    except ValueError as e:
        return json.dumps({"error": str(e), "blocked": True}, indent=2)

    # Read current patch
    client = await get_client()
    patch = await summarize_patch(client)

    # Build plan
    plan = build_plan_for(strategy=strategy, patch=patch, options=options or {})

    # Run lint
    lint_plan = {"kind": "show", "strategy": strategy,
                 "preset_strategy": strat.preset_strategy,
                 "cuelists": [], "fixtures": [], "worlds": [], "views": strat.views,
                 "steps": [{"order": s["order"], "command": s["command"],
                             "purpose": s["purpose"]} for s in plan]}
    findings = expert_lint(lint_plan, domain="show", context=None)

    if not dry_run and not confirm_destructive:
        return json.dumps({
            "strategy": strategy, "blocked": True,
            "error": "dry_run=False requires confirm_destructive=True",
            "plan": plan, "expert_review": [v.__dict__ for v in findings],
            "summary": {"plan_steps": len(plan)},
            "executed_steps": 0, "dry_run": dry_run,
        }, indent=2)

    executed = 0
    if not dry_run:
        # Execute each step — confirm_destructive=True already enforced above
        for step in plan:
            await client.send_command(step["command"])
            executed += 1

    return json.dumps({
        "strategy": strategy,
        "plan": plan,
        "rationale": [strat.notes],
        "expert_review": [v.__dict__ for v in findings],
        "summary": {
            "plan_steps": len(plan),
            "groups": sum(1 for s in plan if s["kind"] == "create-group"),
            "presets": sum(1 for s in plan if s["kind"] == "store-preset"),
            "cues": sum(1 for s in plan if s["kind"] == "store-cue"),
            "executors": sum(1 for s in plan if s["kind"] == "assign-executor"),
            "worlds": sum(1 for s in plan if s["kind"] == "create-world"),
        },
        "dry_run": dry_run,
        "executed_steps": executed,
    }, indent=2)
```

- [ ] **Step 2.10: Add `build_show_from_patch` to rights mapping**

`src/rights.py`:

```python
"build_show_from_patch":      MA2Right.PROGRAM,  # T4 — adds groups/presets/cues to show
```

- [ ] **Step 2.11: Verify all T4 tests pass**

Expected: 6 passed (test_build_show_from_patch.py).

- [ ] **Step 2.12: Live verify against Nemesis**

```bash
.\.venv\Scripts\python.exe -m scripts.live_smoke_path_b --task T4
```

The smoke runs `build_show_from_patch(strategy="rock-band", dry_run=True)` against the live console. Verify the plan contains: per-fixture-type groups, 4 cardinal-hue universal color presets, ≥4 universal position presets, ≥5 selective gobo/beam presets (depending on fixture count), a 5-bank executor layout, a Super-priority blackout sub, a speed master, a tap-tempo executor, and ≥5 named cues per song × 14 songs.

**Operator review checkpoint:** Show the plan summary to the operator. Do not run with `dry_run=False` until operator approves.

- [ ] **Step 2.13: Commit T4**

```bash
git add src/show_strategies/ src/server.py src/rights.py tests/test_build_show_from_patch.py tests/fixtures/nemesis_patch_summary.json
git commit -m "t4: expert show creation from patch — 6 strategies, lint-wired"
```

---

## Task 3 — T5: MA2 screen layout builder

**Goal:** Ship `build_layout_for_screen(screen, content, template, dry_run)` with 6 templates. Each template is a pure data structure describing the cells to emit; the plan builder maps template + screen size + existing-content context to an ordered list of `LayoutElement` commands.

**Files:**

- Create: `src/layout_templates/{__init__,types,templates,plan_builder}.py`, `tests/test_build_layout.py`
- Modify: `src/server.py` (register `build_layout_for_screen`), `src/rights.py`

- [ ] **Step 3.1: Write tests (RED)**

`tests/test_build_layout.py`:

```python
"""build_layout_for_screen — template population + collision detection."""

from __future__ import annotations

import json

import pytest


def test_template_table_has_six_entries():
    from src.layout_templates import TEMPLATES
    assert set(TEMPLATES.keys()) == {
        "busking-master", "preset-access", "executor-monitor",
        "macro-page", "programmer-view", "troubleshoot-view",
    }


def test_busking_master_template_populates_expected_roles():
    from src.layout_templates import build_layout_for
    plan = build_layout_for(template="busking-master", screen=1, options=None)
    roles = {step["meta"]["role"] for step in plan if step.get("meta")}
    assert {"intensity", "color", "fx", "specials"}.issubset(roles)


def test_each_template_produces_non_empty_plan():
    from src.layout_templates import TEMPLATES, build_layout_for
    for tmpl in TEMPLATES:
        plan = build_layout_for(template=tmpl, screen=1, options=None)
        assert plan, f"{tmpl}: empty plan"


def test_layout_steps_have_purpose():
    from src.layout_templates import build_layout_for
    plan = build_layout_for(template="busking-master", screen=1, options=None)
    for s in plan:
        assert s["purpose"], f"step {s['order']} missing purpose"


@pytest.mark.asyncio
async def test_build_layout_for_screen_dry_run():
    from src.server import build_layout_for_screen
    raw = await build_layout_for_screen(
        screen=1, template="busking-master", dry_run=True,
    )
    data = json.loads(raw)
    assert data["screen"] == 1
    assert data["template"] == "busking-master"
    assert data["dry_run"] is True
    assert data["plan"]
    assert "preview_ascii" in data
    assert "expert_review" in data


@pytest.mark.asyncio
async def test_build_layout_for_screen_requires_template_or_content():
    """Both None is an error; both set is also an error."""
    from src.server import build_layout_for_screen
    raw = await build_layout_for_screen(screen=1, dry_run=True)
    data = json.loads(raw)
    assert data.get("blocked") is True or data.get("error")


@pytest.mark.asyncio
async def test_build_layout_collision_detected_by_lint():
    """Layout with overlapping cells surfaces LAYOUT-COLLIDE-001."""
    from src.server import build_layout_for_screen
    content = [
        {"kind": "executor", "target": "1.1.1", "grid_x": 0, "grid_y": 0, "width": 2, "height": 1},
        {"kind": "executor", "target": "1.1.2", "grid_x": 1, "grid_y": 0, "width": 1, "height": 1},
    ]
    raw = await build_layout_for_screen(screen=1, content=content, dry_run=True)
    data = json.loads(raw)
    lint = data.get("expert_review", [])
    assert any(v["rule_id"] == "LAYOUT-COLLIDE-001" for v in lint)
```

- [ ] **Step 3.2-3.5: Implement layout templates (mechanical from spec)**

`src/layout_templates/types.py`, `templates.py`, `plan_builder.py`, `__init__.py` — same shape as the show-strategies module. Each template's content list comes from the spec's strategy table §B.2 and the `view-and-layout-designer` skill.

Template contents per spec:

| Template | Required content (roles) |
|---------|---------------------------|
| busking-master | intensity, color, position, beam, fx, specials |
| preset-access | color-preset-bank, position-preset-bank |
| executor-monitor | executor-row (every active executor) |
| macro-page | macro-grid (~16-32 macro cells) |
| programmer-view | selection-row, attribute-grid |
| troubleshoot-view | diagnostic-readouts (DMX universe status, output values, RDM device list) |

- [ ] **Step 3.6: Register `build_layout_for_screen` in `src/server.py`**

Mirrors `build_show_from_patch`'s pattern. Returns the standard envelope with `preview_ascii` (a textual rendering of the grid for the operator to eyeball before executing).

- [ ] **Step 3.7: Live verify**

Run `build_layout_for_screen(screen=1, template="busking-master", dry_run=True)` against Nemesis. Inspect the preview_ascii; if reasonable, optionally execute (operator-approved) and visually inspect on the onPC screen.

- [ ] **Step 3.8: Commit T5**

```bash
git add src/layout_templates/ src/server.py src/rights.py tests/test_build_layout.py
git commit -m "t5: MA2 screen layout builder — 6 templates, collision-aware"
```

---

## Task 4 — T8: Expert preset library architect

**Goal:** Ship `architect_preset_library(patch_filter, strategy, dry_run, confirm_destructive)` with 3 strategies. Reuses `src/show_strategies/patch_reader.py` for live patch inspection. Output is a complete preset library plan (reference fixtures, universal vs. selective scope, naming convention, MIB-aware presets, coverage report).

**Files:**

- Create: `src/preset_strategies/{__init__,types,strategy_table,plan_builder}.py`, `tests/test_architect_preset_library.py`
- Modify: `src/server.py` (register `architect_preset_library`), `src/rights.py`

- [ ] **Step 4.1-4.7: TDD same pattern as T4**

Strategies per spec §C.4:

| Strategy | Reference fixture | Universal types | Selective types | MIB-aware |
|----------|-------------------|-----------------|-----------------|-----------|
| full-coverage | lowest-ID per type | color, position | gobo, beam | yes |
| minimal-viable | lowest-ID per type | color (4 hues) | none | no |
| color-first | lowest-ID per type | color (full library), position (4) | none | no |

Acceptance per spec §T8 against Nemesis: plan includes reference fixture identified per type (32 entries), ≥4 universal color presets, ≥4 universal position presets, ≥5 per-type gobo/beam selective presets, MIB presets for movers, complete attribute-coverage map, naming convention applied consistently.

- [ ] **Step 4.8: Live verify**

Run `architect_preset_library(strategy="full-coverage", dry_run=True)` against Nemesis. Inspect the coverage_report.

- [ ] **Step 4.9: Commit T8**

```bash
git add src/preset_strategies/ src/server.py src/rights.py tests/test_architect_preset_library.py
git commit -m "t8: expert preset library architect — 3 strategies, coverage-aware"
```

---

## Task 5 — Final hygiene + plan archive

- [ ] **Step 5.1: Update tool count in CLAUDE.md**

`222 tools` → `226 tools`. `src/server.py` count: `188 tools` → `192 tools`. Skill count remains `46` (we edit existing skills in T6; no new skills added in Path B).

- [ ] **Step 5.2: Add Path-B hygiene invariants**

Extend `tests/test_architecture_hygiene.py::TestPathATools`:

```python
PATH_B_TOOLS = {
    "check_plugin_available": "test_plugin_inventory.py",
    "build_show_from_patch": "test_build_show_from_patch.py",
    "build_layout_for_screen": "test_build_layout.py",
    "architect_preset_library": "test_architect_preset_library.py",
}
```

Extend `TestExpertLintWiringInGenerators` to include `build_show_from_patch`, `architect_preset_library`, `build_layout_for_screen`.

- [ ] **Step 5.3: New invariant — strategy modules stay pure**

Add `TestStrategyModulePurity` (mirrors `TestExpertLintPurity`) for `src/show_strategies/`, `src/preset_strategies/`, `src/layout_templates/`. The `patch_reader.py` modules are exempt (they're the I/O boundary).

- [ ] **Step 5.4: Full test suite green**

```bash
.\.venv\Scripts\python.exe -m pytest -q --ignore=tests/test_live_integration.py
```

Expected: ~3000 passed (Path A's 2870 + ~130 new Path B tests).

- [ ] **Step 5.5: Archive Path B plan**

Already in `docs/superpowers/plans/2026-05-27-path-b-implementation.md`. The final commit includes it.

- [ ] **Step 5.6: Final commit**

```bash
git add CLAUDE.md tests/test_architecture_hygiene.py docs/superpowers/plans/2026-05-27-path-b-implementation.md scripts/live_smoke_path_b.py scripts/capture_nemesis_patch.py scripts/probe_onpc_state.py
git commit -m "path-b: final hygiene — tool count, architecture invariants, plan archive"
```

- [ ] **Step 5.7: Push when operator approves**

CLAUDE.md says do NOT push without explicit operator confirmation. Path A's 6 commits + Path B's commits should all push together once the operator says go.

---

## Self-Review

**1. Spec coverage:**

| Spec section | Covered by | Notes |
|--------------|------------|-------|
| §T6 (color picker disambig) | Task 1 | Plugin import as prep step; live verification depends on `EcubeColorPicker.xml` being available locally (confirmed). |
| §T4 (expert show creation) | Task 2 | 6 strategies, plan builder is pure, patch_reader is the lone I/O boundary. Live-verified against Nemesis. |
| §T5 (screen layout builder) | Task 3 | 6 templates, collision detection via LAYOUT-COLLIDE-001 from XC2. |
| §T8 (preset library architect) | Task 4 | 3 strategies, reuses patch_reader, lint-wired via PRESET-* rules. |
| §T7 (busking template) | **DEFERRED** | Per operator decision — Companion testing in a separate later phase. |
| Appendix E.3 sequencing | Tasks 1-4 follow E.3's order (T6 → T4 → T5 → T8). T7 is removed from this plan. | |
| Appendix F test strategy | Each task ships Unit + Mock + Live | Live tests run against Nemesis in steps 1.9 / 2.12 / 3.7 / 4.8. |

**Gaps acknowledged:**

- T7 (busking template) is fully out of scope here. The Companion golden fixture export, the MA2-side template, and the `companion_config` JSON emission all wait for the follow-on phase. The operator chose this explicitly.
- T6's live verification depends on importing `EcubeColorPicker.xml` into Nemesis's plugin pool. The import command is `Import Plugin 2 "EcubeColorPicker" /path=...`. If the import fails (8.3 path quirk, missing file, etc.), T6 falls back to verifying with a synthetic plugin inventory (the unit tests already cover this path).
- The Nemesis-patch-summary JSON fixture is captured during Task 2 (Step 2.3). Until then, the plan tests use a small synthetic patch baked into the test file. The final committed JSON makes future test runs deterministic against the same patch.
- Strategy table content for T4/T5/T8 is taken directly from spec §B.1, §B.2, §C.4. Where the spec is silent (e.g., exact group numbering convention for festival vs. broadcast), this plan picks a reasonable default and documents it in the strategy's `notes` field.

**2. Placeholder scan:** No "TBD" / "implement later" / "fill in" left. Each strategy in Tables 2.5, 3.x, 4.x is fully specified with concrete defaults.

**3. Type consistency:** `Strategy`, `PatchSummary`, `ShowBuildStep` are the same TypedDicts used by builder, lint, and tool envelope. `LayoutElement` shape matches the existing `LAYOUT-*` lint rules' assumptions. `PluginAvailability` matches the spec's Appendix A.4 shape.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-27-path-b-implementation.md`. Two execution options:

**1. Subagent-Driven (recommended where subagents are available)** — Fresh subagent per task, two-stage review between tasks, fast iteration. Requires the `superpowers:subagent-driven-development` skill — currently unavailable in this Claude Code build (plugin install path not yet resolved).

**2. Inline Execution (this session)** — Execute Tasks 1-5 sequentially in this conversation, following `superpowers:executing-plans` discipline (manually applied — same as for Path A): one task at a time, TDD per step, run full test suite at task boundaries, stop on blockers rather than guessing.

**Recommendation: Inline Execution for Path B.** Path B is shorter than Path A (4 work items vs 5), tightly sequenced (T6's plugin import is prep for T6's live test; T8 reuses T4's patch_reader), and each task ends with a live verification step against Nemesis — those checkpoints want operator review per task, which fits inline execution well.

**Operator review checkpoints during execution:**

- Before each Step `*.9 / *.12 / *.7 / *.8` live verification — confirm the plan summary before running against Nemesis.
- Before any `dry_run=False, confirm_destructive=True` call — even though operator authorized free use of Nemesis as a sandbox, mutations stay operator-approved per CLAUDE.md safety rules.

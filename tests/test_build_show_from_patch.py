"""build_show_from_patch — strategy plans + lint wiring + dry-run envelope."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

NEMESIS_FIXTURE = Path(__file__).parent / "fixtures" / "nemesis_patch_summary.json"
_HAVE_FIXTURE = NEMESIS_FIXTURE.exists()


# ---------------------------------------------------------------------------
# Strategy table
# ---------------------------------------------------------------------------

def test_strategy_table_has_six_entries():
    from src.show_strategies import STRATEGIES
    assert set(STRATEGIES.keys()) == {
        "rock-band", "festival", "theatrical", "dj", "broadcast", "corporate",
    }


def test_strategy_rockband_defaults():
    from src.show_strategies import get_strategy
    s = get_strategy("rock-band")
    assert s.cue_density == "dense"
    assert s.preset_strategy == "full-coverage"
    assert s.tracking == "track-with-block"
    assert s.mib_policy == "movers-always"
    assert "programmer" in s.views and "run" in s.views


def test_strategy_corporate_defaults():
    from src.show_strategies import get_strategy
    s = get_strategy("corporate")
    assert s.cue_density == "sparse"
    assert s.preset_strategy == "minimal-viable"
    assert s.tracking == "non-tracking"
    assert s.views == ["run"]


def test_strategy_unknown_raises():
    from src.show_strategies import get_strategy
    with pytest.raises(ValueError, match="unknown strategy"):
        get_strategy("space-opera")


# ---------------------------------------------------------------------------
# Plan builder — synthetic fixture (always available)
# ---------------------------------------------------------------------------

_SYNTHETIC_PATCH = {
    "showfile": "test",
    "fixture_count": 4,
    "fixtures": [
        {"id": 1, "name": "Wash 1", "type": "LED Wash", "patch": "1.001"},
        {"id": 2, "name": "Wash 2", "type": "LED Wash", "patch": "1.020"},
        {"id": 3, "name": "Mover 1", "type": "Spot Mover", "patch": "2.001"},
        {"id": 4, "name": "Bar 1", "type": "LED Bar", "patch": "3.001"},
    ],
    "fixture_types": [
        {"id": 1, "long_name": "Universal Attributes", "short_name": "Universal Attributes", "manufacturer": "AutoMA"},
        {"id": 2, "long_name": "LED Wash 1500", "short_name": "WashLED", "manufacturer": "Chauvet"},
        {"id": 3, "long_name": "Spot Mover 700", "short_name": "Mover", "manufacturer": "Clay Paky"},
        {"id": 4, "long_name": "LED Bar Pixel", "short_name": "Bar", "manufacturer": "Generic"},
    ],
    "groups": [],
    "sequences_count": 0,
    "macros_count": 0,
}


def test_plan_builder_rockband_against_synthetic():
    from src.show_strategies import build_plan_for
    plan = build_plan_for(strategy="rock-band", patch=_SYNTHETIC_PATCH, options={"songs": 2})
    assert plan, "plan should not be empty"
    # Per-fixture-type groups (skips Universal Attributes)
    groups = [s for s in plan if s["kind"] == "create-group"]
    assert len(groups) == 3, f"expected 3 groups (skipping Universal); got {len(groups)}"
    # Universal color presets
    color = [s for s in plan if s["kind"] == "store-preset"
             and s["meta"]["preset_type"] == 4]
    assert len(color) == 4
    # Position presets (has movers → yes)
    position = [s for s in plan if s["kind"] == "store-preset"
                and s["meta"]["preset_type"] == 2]
    assert len(position) == 4
    # Executor bank
    banks = {s["meta"]["role"] for s in plan if s["kind"] == "assign-executor"}
    assert {"intensity", "color", "position", "beam", "fx",
             "blackout-sub", "speedmaster", "tap"}.issubset(banks)


def test_plan_builder_each_strategy_produces_non_empty_plan():
    from src.show_strategies import STRATEGIES, build_plan_for
    for name in STRATEGIES:
        plan = build_plan_for(strategy=name, patch=_SYNTHETIC_PATCH, options=None)
        assert plan, f"{name}: empty plan"


def test_plan_steps_have_required_envelope_fields():
    from src.show_strategies import build_plan_for
    plan = build_plan_for(strategy="theatrical", patch=_SYNTHETIC_PATCH, options=None)
    for step in plan:
        for field in ("order", "kind", "command", "purpose", "expert_says",
                       "risk_tier", "meta"):
            assert field in step, f"step {step.get('order')} missing {field}"


def test_plan_corporate_no_position_presets_when_no_movers():
    minimal_patch = {
        "showfile": "test",
        "fixture_count": 1,
        "fixtures": [{"id": 1, "name": "LED Bar", "type": "Bar", "patch": "1.001"}],
        "fixture_types": [
            {"id": 1, "long_name": "LED Bar", "short_name": "Bar", "manufacturer": "X"}
        ],
        "groups": [], "sequences_count": 0, "macros_count": 0,
    }
    from src.show_strategies import build_plan_for
    plan = build_plan_for(strategy="corporate", patch=minimal_patch, options=None)
    position_presets = [s for s in plan if s["kind"] == "store-preset"
                        and s["meta"]["preset_type"] == 2]
    assert position_presets == []


# ---------------------------------------------------------------------------
# Plan builder — Nemesis fixture (when captured)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _HAVE_FIXTURE, reason="run scripts.capture_nemesis_patch first")
def test_plan_builder_rockband_against_nemesis_meets_acceptance():
    """Spec §T4 acceptance: against Nemesis-25 (76 fixtures), rock-band plan
    has per-fixture-type groups, universal color/position presets, selective
    gobo/beam, 5-bank executor layout, blackout sub, speed master, tap-tempo,
    ≥5 named cues."""
    patch = json.loads(NEMESIS_FIXTURE.read_text(encoding="utf-8"))
    from src.show_strategies import build_plan_for
    plan = build_plan_for(strategy="rock-band", patch=patch, options={"songs": 14})

    # Per-fixture-type groups (>= 5 because Nemesis has many fixture types)
    groups = [s for s in plan if s["kind"] == "create-group"]
    assert len(groups) >= 5, (
        f"expected ≥5 type-groups for Nemesis (32 types); got {len(groups)}"
    )

    # Universal color presets — exactly 4 cardinal hues
    color_universal = [
        s for s in plan if s["kind"] == "store-preset"
        and s["meta"]["preset_type"] == 4 and s["meta"]["scope"] == "universal"
    ]
    assert len(color_universal) == 4

    # Universal position presets — exactly 4 (movers present in Nemesis)
    position_universal = [
        s for s in plan if s["kind"] == "store-preset"
        and s["meta"]["preset_type"] == 2 and s["meta"]["scope"] == "universal"
    ]
    assert len(position_universal) == 4

    # Selective gobo/beam presets — at least 1 of each
    gobo_selective = [
        s for s in plan if s["kind"] == "store-preset"
        and s["meta"]["preset_type"] == 3 and s["meta"]["scope"] == "selective"
    ]
    beam_selective = [
        s for s in plan if s["kind"] == "store-preset"
        and s["meta"]["preset_type"] == 5 and s["meta"]["scope"] == "selective"
    ]
    assert gobo_selective, "expected ≥1 selective gobo preset"
    assert beam_selective, "expected ≥1 selective beam preset"

    # 5-bank executor layout + specials
    bank_roles = {s["meta"]["role"] for s in plan if s["kind"] == "assign-executor"}
    assert {"intensity", "color", "position", "beam", "fx"}.issubset(bank_roles)
    assert "blackout-sub" in bank_roles
    assert "speedmaster" in bank_roles
    assert "tap" in bank_roles

    # ≥5 named cues × 14 songs × 5 sections = 70 cues expected
    cues = [s for s in plan if s["kind"] == "store-cue"]
    assert len(cues) >= 70


# ---------------------------------------------------------------------------
# Tool envelope
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_build_show_from_patch_dry_run_returns_envelope(monkeypatch):
    """Dry-run returns a populated envelope without executing anything.

    Uses GMA_MOCK so we don't need a live console."""
    monkeypatch.setenv("GMA_MOCK", "schema")
    monkeypatch.setattr("src.server._session_manager", None)
    from src.server import build_show_from_patch
    raw = await build_show_from_patch(
        strategy="rock-band", options={"songs": 2}, dry_run=True,
        confirm_destructive=False,
    )
    data = json.loads(raw)
    assert data["strategy"] == "rock-band"
    assert data["dry_run"] is True
    assert data["executed_steps"] == 0
    assert isinstance(data["plan"], list)
    # Mock fixture has 12 groups but minimal fixture types → plan may be lean
    assert data["plan"]
    assert "expert_review" in data
    assert "summary" in data


@pytest.mark.asyncio
async def test_build_show_from_patch_blocks_destructive_without_confirm(monkeypatch):
    monkeypatch.setenv("GMA_MOCK", "schema")
    monkeypatch.setattr("src.server._session_manager", None)
    from src.server import build_show_from_patch
    raw = await build_show_from_patch(
        strategy="rock-band", options={"songs": 2}, dry_run=False,
        confirm_destructive=False,
    )
    data = json.loads(raw)
    assert data.get("blocked") is True
    assert data["executed_steps"] == 0


@pytest.mark.asyncio
async def test_build_show_from_patch_unknown_strategy_blocks(monkeypatch):
    monkeypatch.setenv("GMA_MOCK", "schema")
    monkeypatch.setattr("src.server._session_manager", None)
    from src.server import build_show_from_patch
    raw = await build_show_from_patch(strategy="space-opera", dry_run=True)
    data = json.loads(raw)
    assert data.get("blocked") is True or "error" in data

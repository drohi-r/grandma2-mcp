"""architect_preset_library — coverage report + strategy plans + lint wiring."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

NEMESIS_FIXTURE = Path(__file__).parent / "fixtures" / "nemesis_patch_summary.json"
_HAVE_FIXTURE = NEMESIS_FIXTURE.exists()


_SYNTHETIC_PATCH = {
    "showfile": "test",
    "fixture_count": 4,
    "fixtures": [
        {"id": 1, "name": "Wash 1", "type": "Wash", "patch": "1.001"},
        {"id": 2, "name": "Wash 2", "type": "Wash", "patch": "1.020"},
        {"id": 11, "name": "Mover 1", "type": "Spot Mover", "patch": "2.001"},
        {"id": 21, "name": "Bar 1", "type": "Bar", "patch": "3.001"},
    ],
    "fixture_types": [
        {"id": 1, "long_name": "Universal Attributes", "short_name": "Universal Attributes", "manufacturer": "AutoMA"},
        {"id": 2, "long_name": "LED Wash 1500", "short_name": "WashLED", "manufacturer": "Chauvet"},
        {"id": 3, "long_name": "Spot Mover 700", "short_name": "Mover", "manufacturer": "Clay Paky"},
        {"id": 4, "long_name": "LED Bar Pixel", "short_name": "Bar", "manufacturer": "Generic"},
    ],
    "groups": [], "sequences_count": 0, "macros_count": 0,
}


# ---------------------------------------------------------------------------
# Strategy table
# ---------------------------------------------------------------------------

def test_preset_strategy_table_has_three_entries():
    from src.preset_strategies import PRESET_STRATEGIES
    assert set(PRESET_STRATEGIES.keys()) == {
        "full-coverage", "minimal-viable", "color-first",
    }


def test_full_coverage_strategy_defaults():
    from src.preset_strategies import get_preset_strategy
    s = get_preset_strategy("full-coverage")
    assert 4 in s.universal_types and 2 in s.universal_types
    assert s.cardinal_color_count == 8
    assert s.include_mib is True


def test_minimal_viable_strategy_defaults():
    from src.preset_strategies import get_preset_strategy
    s = get_preset_strategy("minimal-viable")
    assert s.universal_types == [4]
    assert s.selective_types == []
    assert s.cardinal_color_count == 4
    assert s.include_mib is False


def test_color_first_strategy_defaults():
    from src.preset_strategies import get_preset_strategy
    s = get_preset_strategy("color-first")
    assert s.cardinal_color_count == 12
    assert s.include_warm_cool_wash is True


def test_preset_strategy_unknown_raises():
    from src.preset_strategies import get_preset_strategy
    with pytest.raises(ValueError, match="unknown preset strategy"):
        get_preset_strategy("rainbow-overdrive")


# ---------------------------------------------------------------------------
# Plan builder
# ---------------------------------------------------------------------------

def test_full_coverage_against_synthetic_produces_color_position_and_selective():
    from src.preset_strategies import architect_preset_library_for
    result = architect_preset_library_for(
        strategy="full-coverage", patch=_SYNTHETIC_PATCH, options=None,
    )
    plan = result["plan"]
    # 8 cardinal hues + 2 warm/cool = 10 universal color presets
    universal_color = [p for p in plan if p["preset_type"] == 4 and p["scope"] == "universal"]
    assert len(universal_color) == 10
    # 4 universal position presets (rig has movers)
    universal_pos = [p for p in plan if p["preset_type"] == 2 and p["scope"] == "universal"]
    assert len(universal_pos) == 4
    # Selective gobo + beam for the Mover type
    selective_gobo = [p for p in plan if p["preset_type"] == 3 and p["scope"] == "selective"]
    selective_beam = [p for p in plan if p["preset_type"] == 5 and p["scope"] == "selective"]
    assert selective_gobo, "expected ≥1 selective gobo preset"
    assert selective_beam, "expected ≥1 selective beam preset"
    # MIB presets (full-coverage with movers)
    mib = [p for p in plan if p.get("mib_aware")]
    assert mib, "expected MIB presets for movers"


def test_minimal_viable_skips_position_and_selective():
    from src.preset_strategies import architect_preset_library_for
    result = architect_preset_library_for(
        strategy="minimal-viable", patch=_SYNTHETIC_PATCH, options=None,
    )
    plan = result["plan"]
    pos_presets = [p for p in plan if p["preset_type"] == 2]
    selective = [p for p in plan if p["scope"] == "selective"]
    assert pos_presets == []
    assert selective == []
    # Just 4 cardinal color presets
    color = [p for p in plan if p["preset_type"] == 4]
    assert len(color) == 4


def test_color_first_has_twelve_hues_plus_warm_cool():
    from src.preset_strategies import architect_preset_library_for
    result = architect_preset_library_for(
        strategy="color-first", patch=_SYNTHETIC_PATCH, options=None,
    )
    plan = result["plan"]
    color_universal = [p for p in plan if p["preset_type"] == 4 and p["scope"] == "universal"]
    assert len(color_universal) == 14  # 12 hues + warm + cool


def test_reference_fixtures_pick_lowest_id_per_type():
    from src.preset_strategies import architect_preset_library_for
    result = architect_preset_library_for(
        strategy="full-coverage", patch=_SYNTHETIC_PATCH, options=None,
    )
    refs = result["reference_fixtures"]
    # Two wash fixtures (id 1, 2) → reference is 1
    assert refs.get("Wash") == 1


def test_coverage_report_populated():
    from src.preset_strategies import architect_preset_library_for
    result = architect_preset_library_for(
        strategy="full-coverage", patch=_SYNTHETIC_PATCH, options=None,
    )
    cov = result["coverage_report"]
    assert cov, "coverage report should not be empty"
    # Wash should have R/G/B covered by universal color presets
    wash_rgb = [c for c in cov if c["fixture_type"] == "WashLED"
                and c["attribute"] in ("R", "G", "B")]
    assert wash_rgb, "expected RGB coverage entries for wash"
    assert all(c["has_preset"] for c in wash_rgb), (
        f"expected RGB to be covered for wash; got {wash_rgb}"
    )


def test_summary_counts_match_plan_lengths():
    from src.preset_strategies import architect_preset_library_for
    result = architect_preset_library_for(
        strategy="full-coverage", patch=_SYNTHETIC_PATCH, options=None,
    )
    s = result["summary"]
    plan = result["plan"]
    assert s["total_presets"] == len(plan)
    assert s["universal"] + s["selective"] == len(plan)


# ---------------------------------------------------------------------------
# Nemesis acceptance test
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _HAVE_FIXTURE, reason="run scripts.capture_nemesis_patch first")
def test_full_coverage_against_nemesis_meets_acceptance():
    """Spec §T8 acceptance: against Nemesis-25, full-coverage plan has
    reference fixture per type, ≥4 universal color presets, ≥4 universal
    position presets, per-type gobo/beam, MIB presets for movers."""
    patch = json.loads(NEMESIS_FIXTURE.read_text(encoding="utf-8"))
    from src.preset_strategies import architect_preset_library_for
    result = architect_preset_library_for(
        strategy="full-coverage", patch=patch, options=None,
    )
    # Reference fixtures per type (lowest ID picked)
    assert result["reference_fixtures"], "expected references"
    # ≥4 universal color presets
    color_univ = [p for p in result["plan"]
                   if p["preset_type"] == 4 and p["scope"] == "universal"]
    assert len(color_univ) >= 4
    # ≥4 universal position presets
    pos_univ = [p for p in result["plan"]
                 if p["preset_type"] == 2 and p["scope"] == "universal"]
    assert len(pos_univ) >= 4
    # ≥1 selective gobo/beam
    sel_gobo = [p for p in result["plan"]
                 if p["preset_type"] == 3 and p["scope"] == "selective"]
    sel_beam = [p for p in result["plan"]
                 if p["preset_type"] == 5 and p["scope"] == "selective"]
    assert sel_gobo and sel_beam
    # ≥1 MIB preset
    mib = [p for p in result["plan"] if p.get("mib_aware")]
    assert mib


# ---------------------------------------------------------------------------
# Tool envelope
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_architect_preset_library_dry_run(monkeypatch):
    monkeypatch.setenv("GMA_MOCK", "schema")
    monkeypatch.setattr("src.server._session_manager", None)
    from src.server import architect_preset_library
    raw = await architect_preset_library(
        strategy="full-coverage", dry_run=True, confirm_destructive=False,
    )
    data = json.loads(raw)
    assert data["strategy"] == "full-coverage"
    assert data["dry_run"] is True
    assert data["executed_steps"] == 0
    assert "plan" in data
    assert "coverage_report" in data
    assert "summary" in data
    assert "expert_review" in data


@pytest.mark.asyncio
async def test_architect_preset_library_blocks_destructive_without_confirm(monkeypatch):
    monkeypatch.setenv("GMA_MOCK", "schema")
    monkeypatch.setattr("src.server._session_manager", None)
    from src.server import architect_preset_library
    raw = await architect_preset_library(
        strategy="full-coverage", dry_run=False, confirm_destructive=False,
    )
    data = json.loads(raw)
    assert data.get("blocked") is True
    assert data["executed_steps"] == 0


@pytest.mark.asyncio
async def test_architect_preset_library_unknown_strategy_blocks(monkeypatch):
    monkeypatch.setenv("GMA_MOCK", "schema")
    monkeypatch.setattr("src.server._session_manager", None)
    from src.server import architect_preset_library
    raw = await architect_preset_library(
        strategy="rainbow-overdrive", dry_run=True,
    )
    data = json.loads(raw)
    assert data.get("blocked") is True or "error" in data

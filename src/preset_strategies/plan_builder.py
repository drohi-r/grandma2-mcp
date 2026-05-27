"""Preset-library plan builder — strategy + patch summary → PresetEntry list + coverage.

Pure function. Reuses :class:`src.show_strategies.types.PatchSummary`
shape (same `fixtures` + `fixture_types` fields).

Output:
    {
      "strategy": str,
      "reference_fixtures": {fixture_type_short: fixture_id},
      "plan": list[PresetEntry],
      "coverage_report": list[CoverageReport],
      "naming_convention": str,
      "summary": {universal: int, selective: int, mib: int, by_type: dict},
    }
"""

from __future__ import annotations

from src.preset_strategies.strategy_table import get_preset_strategy
from src.preset_strategies.types import (
    ArchitectOptions,
    CoverageReport,
    PresetEntry,
    PresetStrategy,
)
from src.show_strategies.types import PatchSummary


# Cardinal hues used in spec §C.4 — 4 / 8 / 12 progressions:
_CARDINAL_HUES_4 = [
    ("Red",   (100, 0,   0)),
    ("Green", (0,   100, 0)),
    ("Blue",  (0,   0,   100)),
    ("White", (100, 100, 100)),
]
_CARDINAL_HUES_8 = _CARDINAL_HUES_4 + [
    ("Orange",  (100, 40,  0)),
    ("Yellow",  (100, 100, 0)),
    ("Cyan",    (0,   100, 100)),
    ("Magenta", (100, 0,   100)),
]
_CARDINAL_HUES_12 = _CARDINAL_HUES_8 + [
    ("Pink",     (100, 60, 80)),
    ("Lavender", (60,  60, 100)),
    ("Lime",     (60, 100, 0)),
    ("Teal",     (0,  80, 80)),
]
_CARDINAL_LOOKUP = {4: _CARDINAL_HUES_4, 8: _CARDINAL_HUES_8, 12: _CARDINAL_HUES_12}

# Common attribute coverage expectations per fixture-type category
_TYPE_ATTRS = {
    "wash":   ["Pan", "Tilt", "Dim", "R", "G", "B"],
    "mover":  ["Pan", "Tilt", "Dim", "R", "G", "B", "Gobo1", "Zoom", "Focus"],
    "spot":   ["Pan", "Tilt", "Dim", "Gobo1", "Zoom", "Focus", "Color1"],
    "beam":   ["Pan", "Tilt", "Dim", "Gobo1", "Zoom"],
    "bar":    ["Dim", "R", "G", "B"],
    "strobe": ["Dim", "Shutter"],
    "blinder":["Dim"],
    "dimmer": ["Dim"],
    "default":["Dim"],
}

_GENERIC_TYPE_NAMES = ("universal attributes", "automa")


def _categorise_type(long_name: str) -> str:
    """Bucket a fixture type into a coarse category for attribute coverage."""
    ln = long_name.lower()
    if any(kw in ln for kw in ("b-eye", "wash")):
        return "wash"
    if "spot" in ln or "mover" in ln:
        return "spot"
    if "beam" in ln:
        return "beam"
    if "bar" in ln:
        return "bar"
    if "strobe" in ln:
        return "strobe"
    if "blinder" in ln:
        return "blinder"
    if "dim" in ln:
        return "dimmer"
    return "default"


def _pick_reference_fixtures(patch: PatchSummary) -> dict[str, int]:
    """Lowest-ID fixture per type."""
    refs: dict[str, int] = {}
    for f in patch.get("fixtures", []):
        t = f.get("type", "")
        fid = f.get("id", 0)
        if t not in refs or fid < refs[t]:
            refs[t] = fid
    return refs


def architect_preset_library_for(
    *,
    strategy: str,
    patch: PatchSummary,
    options: ArchitectOptions | None = None,
) -> dict:
    """Build a preset-library plan for the given strategy + patch."""
    s: PresetStrategy = get_preset_strategy(strategy)
    opts = dict(options or {})
    naming = opts.get("naming_convention", s.naming_convention)
    color_model = opts.get("color_model", "RGB")

    plan: list[PresetEntry] = []
    refs = _pick_reference_fixtures(patch)

    # 1. Universal color presets (cardinal hues)
    if 4 in s.universal_types:
        hues = _CARDINAL_LOOKUP.get(s.cardinal_color_count, _CARDINAL_HUES_4)
        for i, (name, rgb) in enumerate(hues, start=1):
            plan.append(PresetEntry(
                preset_type=4,
                preset_id=i,
                name=name,
                scope="universal",
                target_fixture_types=[],
                values={"rgb": rgb},
                mib_aware=False,
                color_model=color_model,
            ))
        if s.include_warm_cool_wash:
            warm_id = len(hues) + 1
            cool_id = warm_id + 1
            plan.append(PresetEntry(
                preset_type=4, preset_id=warm_id, name="Warm Wash",
                scope="universal", target_fixture_types=[],
                values={"rgb": (100, 70, 30)},
                mib_aware=False, color_model=color_model,
            ))
            plan.append(PresetEntry(
                preset_type=4, preset_id=cool_id, name="Cool Wash",
                scope="universal", target_fixture_types=[],
                values={"rgb": (40, 70, 100)},
                mib_aware=False, color_model=color_model,
            ))

    # 2. Universal position presets (4 default positions, only when movers present)
    has_movers = any(
        _categorise_type(ft.get("long_name", "")) in {"wash", "spot", "mover", "beam"}
        for ft in patch.get("fixture_types", [])
    )
    if 2 in s.universal_types and has_movers:
        for i, name in enumerate(["Home", "Audience", "Stage Left", "Stage Right"], start=1):
            plan.append(PresetEntry(
                preset_type=2, preset_id=i, name=name,
                scope="universal", target_fixture_types=[],
                values={}, mib_aware=False, color_model=None,
            ))

    # 3. Selective gobo/beam/focus/control per fixture type
    next_selective_id = 10
    for ft in patch.get("fixture_types", []):
        long_name = (ft.get("long_name") or "").lower()
        if any(g in long_name for g in _GENERIC_TYPE_NAMES):
            continue
        short = ft.get("short_name") or ft.get("long_name", "Unknown")
        category = _categorise_type(long_name)
        for ptype in s.selective_types:
            # Match preset_type to fixture capability
            if ptype == 3 and category not in {"spot", "mover", "beam"}:
                continue
            if ptype == 5 and category not in {"spot", "mover", "beam"}:
                continue
            if ptype == 6 and category not in {"spot", "mover"}:
                continue
            type_names = {1: "Dimmer", 2: "Position", 3: "Gobo",
                           4: "Color", 5: "Beam", 6: "Focus", 7: "Control"}
            plan.append(PresetEntry(
                preset_type=ptype,
                preset_id=next_selective_id,
                name=f"{short} {type_names[ptype]} Set",
                scope="selective",
                target_fixture_types=[short],
                values={}, mib_aware=False, color_model=None,
            ))
            next_selective_id += 1

    # 4. MIB presets for movers (full-coverage with movers)
    if s.include_mib and has_movers:
        mib_start = max((p.get("preset_id", 0) for p in plan if p.get("preset_type") == 2), default=0) + 100
        mover_types = [
            ft for ft in patch.get("fixture_types", [])
            if _categorise_type(ft.get("long_name", "")) in {"spot", "mover", "beam", "wash"}
            and not any(g in (ft.get("long_name") or "").lower() for g in _GENERIC_TYPE_NAMES)
        ]
        for i, ft in enumerate(mover_types, start=0):
            short = ft.get("short_name", "")
            plan.append(PresetEntry(
                preset_type=2,
                preset_id=mib_start + i,
                name=f"MIB {short}",
                scope="selective",
                target_fixture_types=[short],
                values={"mib": True},
                mib_aware=True,
                color_model=None,
            ))

    # 5. Coverage report — per-attribute presence across types
    coverage: list[CoverageReport] = []
    for ft in patch.get("fixture_types", []):
        long_name = (ft.get("long_name") or "").lower()
        if any(g in long_name for g in _GENERIC_TYPE_NAMES):
            continue
        category = _categorise_type(long_name)
        short = ft.get("short_name", "Unknown")
        expected = _TYPE_ATTRS.get(category, _TYPE_ATTRS["default"])
        for attr in expected:
            # An attr is "covered" if any preset's covers_attributes / values mentions it,
            # or if its preset_type semantically covers it.
            attr_lower = attr.lower()
            covered_by: list[str] = []
            for p in plan:
                if p.get("scope") == "universal" and p.get("preset_type") == 4 and attr in ("R", "G", "B"):
                    covered_by.append(f"{p['preset_type']}.{p['preset_id']}")
                elif p.get("scope") == "universal" and p.get("preset_type") == 2 and attr in ("Pan", "Tilt"):
                    covered_by.append(f"{p['preset_type']}.{p['preset_id']}")
                elif p.get("scope") == "selective" and short in p.get("target_fixture_types", []):
                    pt = p.get("preset_type")
                    if pt == 3 and attr_lower.startswith("gobo"):
                        covered_by.append(f"{pt}.{p['preset_id']}")
                    elif pt == 5 and attr_lower in {"zoom", "iris"}:
                        covered_by.append(f"{pt}.{p['preset_id']}")
                    elif pt == 6 and attr_lower == "focus":
                        covered_by.append(f"{pt}.{p['preset_id']}")
            coverage.append({
                "fixture_type": short,
                "attribute": attr,
                "has_preset": bool(covered_by),
                "preset_ids": covered_by[:3],
            })

    universal_count = sum(1 for p in plan if p.get("scope") == "universal")
    selective_count = sum(1 for p in plan if p.get("scope") == "selective")
    mib_count = sum(1 for p in plan if p.get("mib_aware"))

    return {
        "strategy": strategy,
        "reference_fixtures": refs,
        "plan": plan,
        "coverage_report": coverage,
        "naming_convention": naming,
        "summary": {
            "universal": universal_count,
            "selective": selective_count,
            "mib": mib_count,
            "total_presets": len(plan),
        },
    }


__all__ = ["architect_preset_library_for"]

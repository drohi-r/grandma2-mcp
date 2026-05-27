"""Preset-library expert-lint rules (PRESET-*).

Plan shape:

    {"kind": "preset",
     "strategy": "full-coverage" | "minimal-viable" | "color-first" | ...,
     "reference_fixtures": {fixture_type: fixture_id},
     "plan": [{"preset_type": int, "preset_id": int, "name": str,
               "scope": "universal" | "selective",
               "target_fixture_types": list[str],
               "values": dict, "mib_aware": bool,
               "color_model": "HSB" | "RGB" (optional),
               "covers_attributes": list[str] (optional)}, ...],
     "fixture_types": list[str],
     "naming_convention": str}
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict

from src.expert_lint.types import Violation

_VALID_PRESET_TYPES = {1: "Dimmer", 2: "Position", 3: "Gobo", 4: "Color",
                       5: "Beam", 6: "Focus", 7: "Control"}
_CARDINAL_HUES = {"red", "green", "blue", "white"}
_WARM_KEYWORDS = ("warm",)
_COOL_KEYWORDS = ("cool",)


def _presets(plan: dict) -> list[dict]:
    return plan.get("plan", [])


# REF-001
def check_ref_001_no_reference_fixture(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """PRESET-REF-001 (warning): reference fixture not chosen for a type that has multiples."""
    fixtures = (context or {}).get("fixtures", [])
    by_type: dict[str, list[int]] = defaultdict(list)
    for f in fixtures:
        by_type[f.get("type", "")].append(f.get("id", 0))
    refs = plan.get("reference_fixtures", {})
    out: list[Violation] = []
    for ftype, ids in by_type.items():
        if len(ids) > 1 and ftype not in refs:
            out.append(Violation(
                rule_id="PRESET-REF-001",
                severity="warning",
                domain="preset",
                target=f"fixture_type:{ftype}",
                expert_says=(
                    f"Reference fixture not chosen for type {ftype!r} "
                    f"(patch has {len(ids)} of this type)"
                ),
                fix_suggestion="Pick the lowest-ID fixture of each type as the reference",
            ))
    return out


# COVER-001
def check_cover_001_attribute_uncovered(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """PRESET-COVER-001 (warning): full-coverage strategy but an attribute has no preset."""
    if plan.get("strategy") != "full-coverage":
        return []
    required = (context or {}).get("required_attributes", {})
    if not required:
        return []
    covered: set[str] = set()
    for p in _presets(plan):
        for attr in p.get("covers_attributes", []):
            covered.add(attr)
    out: list[Violation] = []
    for ftype, attrs in required.items():
        for attr in attrs:
            if attr not in covered:
                out.append(Violation(
                    rule_id="PRESET-COVER-001",
                    severity="warning",
                    domain="preset",
                    target=f"fixture_type:{ftype}:attr:{attr}",
                    expert_says=(
                        f"Attribute {attr!r} on type {ftype!r} has no preset (full-coverage)"
                    ),
                    fix_suggestion=f"Add a default/home preset for {attr}",
                ))
    return out


# COVER-002
def check_cover_002_no_cardinal_hues(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """PRESET-COVER-002 (warning): missing one of red/green/blue/white color presets."""
    color_names = {
        (p.get("name") or "").lower()
        for p in _presets(plan) if p.get("preset_type") == 4
    }
    have = {h for h in _CARDINAL_HUES if any(h in n for n in color_names)}
    missing = _CARDINAL_HUES - have
    if not missing:
        return []
    return [Violation(
        rule_id="PRESET-COVER-002",
        severity="warning",
        domain="preset",
        target="color_presets",
        expert_says=f"Missing cardinal hue preset(s): {sorted(missing)}",
        fix_suggestion=(
            "Add the 4 cardinal hues per "
            ".claude/skills/constrained-color-design/SKILL.md"
        ),
    )]


# COVER-003
def check_cover_003_no_warm_cool_wash(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """PRESET-COVER-003 (advice): no warm or cool wash preset."""
    names = " ".join(((p.get("name") or "").lower())
                     for p in _presets(plan) if p.get("preset_type") == 4)
    has_warm = any(kw in names for kw in _WARM_KEYWORDS)
    has_cool = any(kw in names for kw in _COOL_KEYWORDS)
    if has_warm and has_cool:
        return []
    return [Violation(
        rule_id="PRESET-COVER-003",
        severity="advice",
        domain="preset",
        target="color_presets",
        expert_says=(
            "No warm and/or cool wash preset (operator convenience)"
        ),
        fix_suggestion="Add at least one of each (warm wash, cool wash)",
    )]


# SCOPE-001
def check_scope_001_color_selective_when_universal(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """PRESET-SCOPE-001 (warning): color preset is selective when strategy says universal."""
    out: list[Violation] = []
    for p in _presets(plan):
        if p.get("preset_type") == 4 and p.get("scope") == "selective":
            out.append(Violation(
                rule_id="PRESET-SCOPE-001",
                severity="warning",
                domain="preset",
                target=f"preset:4.{p.get('preset_id')}",
                expert_says=(
                    f"Color preset {p.get('name')!r} is selective; convention is universal"
                ),
                fix_suggestion="Convert to universal — values clamp to per-fixture-type capability",
            ))
    return out


# SCOPE-002
def check_scope_002_gobo_universal(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """PRESET-SCOPE-002 (warning): gobo preset is universal — gobos are fixture-specific."""
    out: list[Violation] = []
    for p in _presets(plan):
        if p.get("preset_type") == 3 and p.get("scope") == "universal":
            out.append(Violation(
                rule_id="PRESET-SCOPE-002",
                severity="warning",
                domain="preset",
                target=f"preset:3.{p.get('preset_id')}",
                expert_says=(
                    f"Gobo preset {p.get('name')!r} is universal — gobos are fixture-specific"
                ),
                fix_suggestion="Convert to selective per fixture type",
            ))
    return out


# NAME-001
def check_name_001_naming_convention_inconsistent(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """PRESET-NAME-001 (warning): naming convention not applied consistently.

    Convention `{type}_{name}` requires snake_case-like names (lowercase + underscores).
    """
    convention = plan.get("naming_convention", "")
    if not convention:
        return []
    out: list[Violation] = []
    snake_case_re = re.compile(r"^[a-z]+(_[a-z0-9]+)+$")
    if convention.startswith("{type}_"):
        for p in _presets(plan):
            name = p.get("name", "")
            if not snake_case_re.match(name):
                out.append(Violation(
                    rule_id="PRESET-NAME-001",
                    severity="warning",
                    domain="preset",
                    target=f"preset:{p.get('preset_type')}.{p.get('preset_id')}",
                    expert_says=f"Preset name {name!r} does not follow convention {convention!r}",
                    fix_suggestion="Run rename per convention from strategy options",
                ))
    return out


# NUM-001
def check_num_001_duplicate_preset_number(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """PRESET-NUM-001 (error): duplicate preset numbers within a type."""
    counts: Counter[tuple[int, int]] = Counter()
    for p in _presets(plan):
        counts[(p.get("preset_type", -1), p.get("preset_id", -1))] += 1
    out: list[Violation] = []
    for (ptype, pid), n in counts.items():
        if n > 1:
            out.append(Violation(
                rule_id="PRESET-NUM-001",
                severity="error",
                domain="preset",
                target=f"preset:{ptype}.{pid}",
                expert_says=f"Preset {ptype}.{pid} declared {n} times",
                fix_suggestion="Renumber; never reuse a slot within a type",
            ))
    return out


# NUM-002
def check_num_002_numbering_not_type_convention(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """PRESET-NUM-002 (warning): preset_type doesn't match MA2 convention (1-7)."""
    out: list[Violation] = []
    for p in _presets(plan):
        ptype = p.get("preset_type")
        if ptype not in _VALID_PRESET_TYPES:
            out.append(Violation(
                rule_id="PRESET-NUM-002",
                severity="warning",
                domain="preset",
                target=f"preset:{ptype}.{p.get('preset_id')}",
                expert_says=(
                    f"Preset type {ptype} not in MA2 convention (1=Dimmer..7=Control)"
                ),
                fix_suggestion="Renumber per type convention",
            ))
    return out


# MIB-001 (preset)
def check_mib_001_movers_without_mib_preset(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """PRESET-MIB-001 (warning): movers in patch but no MIB-aware presets."""
    fixture_types = (context or {}).get("fixture_types_in_patch", [])
    has_movers = any("mover" in (ft or "").lower() for ft in fixture_types)
    if not has_movers:
        return []
    has_mib_preset = any(p.get("mib_aware") for p in _presets(plan))
    if has_mib_preset:
        return []
    return [Violation(
        rule_id="PRESET-MIB-001",
        severity="warning",
        domain="preset",
        target="preset_plan",
        expert_says="Movers in patch but no MIB presets defined",
        fix_suggestion="Add MIB presets per mover type",
    )]


# EMPTY-001
def check_empty_001_empty_preset_slot(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """PRESET-EMPTY-001 (error): preset slot is stored as empty.

    Convention:
        ``values=None``  — declared by the architect; will be populated by a
                            follow-up store-against-reference-fixture pass.
                            **Not flagged** — empty here is expected.
        ``values={}``    — populated and broken (store emitted nothing).
                            Flagged as error.
        ``values={...}`` — populated and valid. Not flagged.

    The distinction lets ``architect_preset_library`` emit selective / MIB
    presets without flooding the lint output with false positives.
    """
    out: list[Violation] = []
    for p in _presets(plan):
        values = p.get("values")
        if values is None:
            continue  # declared but not yet stored — expected
        if not values:
            out.append(Violation(
                rule_id="PRESET-EMPTY-001",
                severity="error",
                domain="preset",
                target=f"preset:{p.get('preset_type')}.{p.get('preset_id')}",
                expert_says=f"Preset {p.get('name')!r} is stored but has no values",
                fix_suggestion="Either populate the preset or remove the empty slot",
            ))
    return out


# CLONE-001
def check_clone_001_could_clone(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """PRESET-CLONE-001 (advice): selective preset on type A could be cloned to similar type B."""
    similar = (context or {}).get("similar_types", {})
    if not similar:
        return []
    covered_by_type: dict[str, set[tuple[int, int]]] = defaultdict(set)
    for p in _presets(plan):
        if p.get("scope") != "selective":
            continue
        for ft in p.get("target_fixture_types", []):
            covered_by_type[ft].add((p.get("preset_type"), p.get("preset_id")))
    out: list[Violation] = []
    for src_type, similars in similar.items():
        for sim in similars:
            missing = covered_by_type.get(src_type, set()) - covered_by_type.get(sim, set())
            for ptype, pid in missing:
                out.append(Violation(
                    rule_id="PRESET-CLONE-001",
                    severity="advice",
                    domain="preset",
                    target=f"preset:{ptype}.{pid}",
                    expert_says=(
                        f"Preset {ptype}.{pid} on type {src_type!r} could be cloned to {sim!r}"
                    ),
                    fix_suggestion=(
                        "Use Clone workflow per .claude/skills/clone-and-data-transfer/SKILL.md"
                    ),
                ))
    return out


# HSB-001
def check_hsb_001_rgb_when_hsb_expected(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """PRESET-HSB-001 (advice): RGB used when constrained-color strategy expects HSB."""
    if plan.get("strategy") not in {"constrained-color", "color-first"}:
        return []
    out: list[Violation] = []
    for p in _presets(plan):
        if p.get("preset_type") == 4 and p.get("color_model") == "RGB":
            out.append(Violation(
                rule_id="PRESET-HSB-001",
                severity="advice",
                domain="preset",
                target=f"preset:4.{p.get('preset_id')}",
                expert_says=(
                    f"Color preset {p.get('name')!r} stored as RGB; constrained-color expects HSB"
                ),
                fix_suggestion="Re-store using HSB color model",
            ))
    return out


__all__ = [
    "check_ref_001_no_reference_fixture",
    "check_cover_001_attribute_uncovered",
    "check_cover_002_no_cardinal_hues",
    "check_cover_003_no_warm_cool_wash",
    "check_scope_001_color_selective_when_universal",
    "check_scope_002_gobo_universal",
    "check_name_001_naming_convention_inconsistent",
    "check_num_001_duplicate_preset_number",
    "check_num_002_numbering_not_type_convention",
    "check_mib_001_movers_without_mib_preset",
    "check_empty_001_empty_preset_slot",
    "check_clone_001_could_clone",
    "check_hsb_001_rgb_when_hsb_expected",
]

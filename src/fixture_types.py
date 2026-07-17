"""fixture_types.py — FixtureTypeModel: fixture-type intelligence over the patch.

Pure module (no I/O): builds a typed model of the patch — fixture types, their
attribute capabilities, category classification, and member fixtures — and
derives from it:

  - ID-block verification against the operator's 100-block numbering scheme
    (1-99 wash, 100s movers, 200s bars, 300s strobes, 400s blinders)
  - a renumbering plan for out-of-block fixtures
  - type-ordered selection command sequences (what preset/color-picker
    plugins require at runtime)

Console I/O stays in the callers (src/server.py tools) which feed this module
``PatchSummary`` (from src.show_strategies.patch_reader.summarize_patch) and
optional per-type attribute sets (from discover_fixture_type_attributes).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.show_strategies.types import PatchSummary

# ---------------------------------------------------------------------------
# Categories and ID blocks
# ---------------------------------------------------------------------------

# Canonical category order — also the canonical plugin selection order.
CATEGORY_ORDER: list[str] = [
    "wash", "mover", "bar", "strobe", "blinder", "conventional", "other",
]

# Operator's 100-block numbering scheme. Categories without a block are
# unconstrained (verification skips them).
DEFAULT_CATEGORY_BLOCKS: dict[str, tuple[int, int]] = {
    "wash":    (1, 99),
    "mover":   (100, 199),
    "bar":     (200, 299),
    "strobe":  (300, 399),
    "blinder": (400, 499),
}

# Capability flag names, in preset-type order (1=Dimmer .. 7=Control).
CAPABILITY_FLAGS = (
    "dimmer", "position", "gobo", "color_mix", "beam", "focus", "control",
)

# preset_type id → capability flag required for that preset to apply
PRESET_TYPE_CAPABILITY: dict[int, str] = {
    1: "dimmer",
    2: "position",
    3: "gobo",
    4: "color_mix",
    5: "beam",
    6: "focus",
    7: "control",
}


# ---------------------------------------------------------------------------
# Attribute → capability mapping
# ---------------------------------------------------------------------------

# Attribute-library name prefixes (as returned by the EditSetup ChannelType
# rows, e.g. PAN, TILT, COLORRGB1, GOBO1, ZOOM) → capability flag.
_ATTRIBUTE_CAPABILITY_PREFIXES: list[tuple[str, str]] = [
    ("DIM", "dimmer"),
    ("PAN", "position"),
    ("TILT", "position"),
    ("GOBO", "gobo"),
    ("COLORRGB", "color_mix"),
    ("COLORMIX", "color_mix"),
    ("CTC", "color_mix"),
    ("MIXCOLOR", "color_mix"),
    ("COLOR", "color_mix"),     # COLOR1 wheels count as color capability
    ("ZOOM", "beam"),
    ("IRIS", "beam"),
    ("PRISM", "beam"),
    ("SHUTTER", "beam"),
    ("STROBE", "beam"),
    ("FROST", "beam"),
    ("FOCUS", "focus"),
    ("CONTROL", "control"),
    ("CTRL", "control"),
    ("FIXTUREGLOBAL", "control"),
]


def capabilities_from_attributes(attribute_names: set[str]) -> dict[str, bool]:
    """Map a set of attribute-library names to capability flags."""
    caps = {flag: False for flag in CAPABILITY_FLAGS}
    for raw in attribute_names:
        token = raw.strip().upper()
        for prefix, flag in _ATTRIBUTE_CAPABILITY_PREFIXES:
            if token.startswith(prefix):
                caps[flag] = True
                break
    return caps


# Console output may embed ANSI color escapes; attribute rows on 3.9.60 are
# "ChannelType <no> <no> NAME (Shortname) ..." (live-verified 2026-07-17).
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_CHANNEL_TYPE_ROW_RE = re.compile(r"ChannelType\s+\d+\s+\d+\s+([A-Z][A-Z0-9_]+)\s*\(")


def parse_channel_type_rows(raw: str) -> set[str]:
    """Extract attribute names from discover_fixture_type_attributes output.

    The EditSetup subfixture ``list`` emits ChannelType rows whose attribute
    column is an attribute-library name (PAN, TILT, COLORRGB1, ...). We accept
    any row containing 'ChannelType' and take the first ALL-CAPS token after
    it; rows without one are skipped.
    """
    names: set[str] = set()
    raw = _ANSI_RE.sub("", raw)
    for line in raw.splitlines():
        if "ChannelType" not in line:
            continue
        match = _CHANNEL_TYPE_ROW_RE.search(line)
        if match:
            names.add(match.group(1))
            continue
        _, _, rest = line.partition("ChannelType")
        for token in rest.replace('"', " ").split():
            cleaned = token.strip().rstrip(",;")
            if (
                len(cleaned) >= 2
                and cleaned.upper() == cleaned
                and any(c.isalpha() for c in cleaned)
            ):
                names.add(cleaned)
                break
    return names


# ---------------------------------------------------------------------------
# Curated capability fallback (by type-name keyword)
# ---------------------------------------------------------------------------

# Used when console attribute readback is unavailable/incomplete. Keyed by
# keyword found in the fixture type long name (lowercased).
_FALLBACK_CAPS: list[tuple[tuple[str, ...], dict[str, bool]]] = [
    (("b-eye", "wash", "aura"), {
        "dimmer": True, "position": True, "gobo": False, "color_mix": True,
        "beam": True, "focus": False, "control": True,
    }),
    (("spot", "profile", "viper", "beam"), {
        "dimmer": True, "position": True, "gobo": True, "color_mix": True,
        "beam": True, "focus": True, "control": True,
    }),
    (("bar", "batten", "pixel", "led", "rgb"), {
        "dimmer": True, "position": False, "gobo": False, "color_mix": True,
        "beam": False, "focus": False, "control": True,
    }),
    (("strobe", "atomic"), {
        "dimmer": True, "position": False, "gobo": False, "color_mix": False,
        "beam": True, "focus": False, "control": True,
    }),
    (("blinder", "molefay", "sunstrip"), {
        "dimmer": True, "position": False, "gobo": False, "color_mix": False,
        "beam": False, "focus": False, "control": False,
    }),
    (("dimmer", "conventional", "par", "fresnel"), {
        "dimmer": True, "position": False, "gobo": False, "color_mix": False,
        "beam": False, "focus": False, "control": False,
    }),
]


def fallback_capabilities(type_name: str) -> dict[str, bool] | None:
    """Curated capability flags for common type names; None if unknown."""
    lowered = type_name.lower()
    for keywords, caps in _FALLBACK_CAPS:
        if any(kw in lowered for kw in keywords):
            return dict(caps)
    return None


# ---------------------------------------------------------------------------
# Category classification
# ---------------------------------------------------------------------------

_CATEGORY_KEYWORDS: list[tuple[tuple[str, ...], str]] = [
    (("blinder", "molefay", "sunstrip"), "blinder"),
    (("strobe", "atomic"), "strobe"),
    (("bar", "batten", "pixel", "led", "rgb"), "bar"),
    (("wash", "b-eye", "aura"), "wash"),
    (("spot", "profile", "beam", "viper", "mover", "hybrid"), "mover"),
    (("dimmer", "par", "fresnel", "conventional", "generic"), "conventional"),
]


def classify_category(type_name: str, capabilities: dict[str, bool]) -> str:
    """Classify a fixture type into a category (name keywords, then caps)."""
    lowered = type_name.lower()
    for keywords, category in _CATEGORY_KEYWORDS:
        if any(kw in lowered for kw in keywords):
            return category
    # Capability heuristics when the name tells us nothing
    if capabilities.get("position"):
        return "mover" if capabilities.get("gobo") else "wash"
    if capabilities.get("color_mix"):
        return "bar"
    if capabilities.get("dimmer") and not any(
        capabilities.get(f) for f in ("position", "gobo", "color_mix", "beam")
    ):
        return "conventional"
    return "other"


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

@dataclass
class FixtureTypeRecord:
    """One fixture type with capabilities, category, and member fixtures."""

    type_id: int | None
    name: str
    short_name: str = ""
    category: str = "other"
    capabilities: dict[str, bool] = field(default_factory=dict)
    capability_source: str = "unknown"   # "console" | "fallback" | "unknown"
    member_ids: list[int] = field(default_factory=list)
    member_names: dict[int, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "type_id": self.type_id,
            "name": self.name,
            "short_name": self.short_name,
            "category": self.category,
            "capabilities": self.capabilities,
            "capability_source": self.capability_source,
            "member_ids": self.member_ids,
            "member_count": len(self.member_ids),
        }


@dataclass
class FixtureTypeModel:
    """Typed model of the whole patch, keyed by fixture type name."""

    types: dict[str, FixtureTypeRecord] = field(default_factory=dict)
    unmatched_fixtures: list[dict] = field(default_factory=list)

    def by_category(self) -> dict[str, list[FixtureTypeRecord]]:
        out: dict[str, list[FixtureTypeRecord]] = {}
        for rec in self.types.values():
            out.setdefault(rec.category, []).append(rec)
        for recs in out.values():
            recs.sort(key=lambda r: r.name)
        return out

    def types_with_capability(self, flag: str) -> list[FixtureTypeRecord]:
        return [r for r in self.types.values() if r.capabilities.get(flag)]

    def all_member_ids(self) -> list[int]:
        ids: list[int] = []
        for rec in self.types.values():
            ids.extend(rec.member_ids)
        return sorted(ids)

    def to_dict(self) -> dict:
        return {
            "types": {name: rec.to_dict() for name, rec in self.types.items()},
            "categories": {
                cat: [r.name for r in recs]
                for cat, recs in self.by_category().items()
            },
            "unmatched_fixtures": self.unmatched_fixtures,
            "fixture_count": len(self.all_member_ids()),
        }


def build_fixture_type_model(
    patch: PatchSummary,
    attributes_by_type: dict[str, set[str]] | None = None,
) -> FixtureTypeModel:
    """Build the FixtureTypeModel from a PatchSummary.

    Args:
        patch: Output of summarize_patch — fixtures carry a ``type`` string
            matching a fixture_types ``long_name`` (or close to it).
        attributes_by_type: Optional map of fixture type name → attribute
            names read from the console (discover_fixture_type_attributes).
            When absent for a type, the curated fallback table is used.
    """
    attributes_by_type = attributes_by_type or {}
    model = FixtureTypeModel()

    # Index declared fixture types by long name for id/short_name lookup
    declared: dict[str, dict] = {}
    for ft in patch.get("fixture_types", []):
        declared[ft.get("long_name", "").strip().lower()] = ft

    def resolve_declared(type_name: str) -> dict:
        """Match a fixture's type string to a declared fixture type.

        Live patch rows carry composite strings "{type_id} {long_name} {mode}"
        (e.g. "4 VL3500 Spot 00") while `list fixturetype` declares the bare
        long_name — fall back to containment when the exact key misses.
        """
        key = type_name.strip().lower()
        exact = declared.get(key)
        if exact is not None:
            return exact
        for long_name, ft in declared.items():
            if long_name and long_name in key:
                return ft
        return {}

    for fx in patch.get("fixtures", []):
        type_name = (fx.get("type") or "").strip()
        if not type_name:
            model.unmatched_fixtures.append(fx)
            continue
        rec = model.types.get(type_name)
        if rec is None:
            decl = resolve_declared(type_name)
            attrs = attributes_by_type.get(type_name) or attributes_by_type.get(
                decl.get("long_name", "")
            )
            if attrs:
                caps = capabilities_from_attributes(attrs)
                source = "console"
            else:
                caps = fallback_capabilities(type_name)
                source = "fallback" if caps is not None else "unknown"
                if caps is None:
                    caps = {flag: False for flag in CAPABILITY_FLAGS}
            rec = FixtureTypeRecord(
                type_id=decl.get("id"),
                name=type_name,
                short_name=decl.get("short_name", ""),
                capabilities=caps,
                capability_source=source,
            )
            rec.category = classify_category(type_name, caps)
            model.types[type_name] = rec
        fx_id = fx.get("id")
        if isinstance(fx_id, int):
            rec.member_ids.append(fx_id)
            rec.member_names[fx_id] = fx.get("name", "")

    for rec in model.types.values():
        rec.member_ids.sort()
    return model


# ---------------------------------------------------------------------------
# ID-block verification & renumbering plan
# ---------------------------------------------------------------------------

def verify_id_blocks(
    model: FixtureTypeModel,
    blocks: dict[str, tuple[int, int]] | None = None,
) -> dict:
    """Verify fixture IDs against the category block scheme.

    Returns a report dict:
      - per-category: block, member counts, in/out of block, free slots left
      - out_of_block: [{fixture_id, name, type, category, expected_block}]
      - collisions: fixture IDs used by more than one fixture
      - renumber_plan: [{old_id, new_id, name, type, category}] moving each
        out-of-block fixture to the lowest free slot inside its block
      - compliant: True when out_of_block and collisions are empty
    """
    blocks = blocks or DEFAULT_CATEGORY_BLOCKS
    by_cat = model.by_category()

    # Collision detection across the whole patch
    seen: dict[int, int] = {}
    for rec in model.types.values():
        for fid in rec.member_ids:
            seen[fid] = seen.get(fid, 0) + 1
    collisions = sorted(fid for fid, n in seen.items() if n > 1)

    used_ids = set(seen)
    categories: dict[str, dict] = {}
    out_of_block: list[dict] = []
    renumber_plan: list[dict] = []

    for cat in CATEGORY_ORDER:
        recs = by_cat.get(cat, [])
        if not recs:
            continue
        block = blocks.get(cat)
        member_ids = sorted(i for r in recs for i in r.member_ids)
        entry: dict = {
            "category": cat,
            "block": list(block) if block else None,
            "member_count": len(member_ids),
        }
        if block:
            lo, hi = block
            inside = [i for i in member_ids if lo <= i <= hi]
            outside = [i for i in member_ids if not (lo <= i <= hi)]
            entry["in_block"] = len(inside)
            entry["out_of_block"] = outside
            free = [i for i in range(lo, hi + 1) if i not in used_ids]
            entry["free_slots"] = len(free)
            for fid in outside:
                rec = next(r for r in recs if fid in r.member_ids)
                out_of_block.append({
                    "fixture_id": fid,
                    "name": rec.member_names.get(fid, ""),
                    "type": rec.name,
                    "category": cat,
                    "expected_block": [lo, hi],
                })
                if free:
                    new_id = free.pop(0)
                    used_ids.add(new_id)
                    renumber_plan.append({
                        "old_id": fid,
                        "new_id": new_id,
                        "name": rec.member_names.get(fid, ""),
                        "type": rec.name,
                        "category": cat,
                    })
                else:
                    renumber_plan.append({
                        "old_id": fid,
                        "new_id": None,
                        "name": rec.member_names.get(fid, ""),
                        "type": rec.name,
                        "category": cat,
                        "error": f"no free slot left in block {lo}-{hi}",
                    })
        categories[cat] = entry

    return {
        "categories": categories,
        "out_of_block": out_of_block,
        "collisions": collisions,
        "renumber_plan": renumber_plan,
        "compliant": not out_of_block and not collisions,
    }


def renumber_commands(renumber_plan: list[dict]) -> list[str]:
    """Build MA2 commands for a renumber plan (skips unplannable entries).

    Uses ``Assign Fixture <old> /fixid=<new>``. Renumbering changes the
    fixture's ID, which groups/presets reference — callers must warn before
    executing.
    """
    return [
        f"Assign Fixture {e['old_id']} /fixid={e['new_id']}"
        for e in renumber_plan
        if e.get("new_id") is not None
    ]


# ---------------------------------------------------------------------------
# Type-ordered selection
# ---------------------------------------------------------------------------

def _compress_ranges(ids: list[int]) -> str:
    """[1,2,3,7,9,10] → '1 Thru 3 + 7 + 9 Thru 10'"""
    if not ids:
        return ""
    parts: list[str] = []
    start = prev = ids[0]
    for i in ids[1:]:
        if i == prev + 1:
            prev = i
            continue
        parts.append(str(start) if start == prev else f"{start} Thru {prev}")
        start = prev = i
    parts.append(str(start) if start == prev else f"{start} Thru {prev}")
    return " + ".join(parts)


def build_type_ordered_selection(
    model: FixtureTypeModel,
    order: list[str] | None = None,
    clear_first: bool = True,
) -> list[str]:
    """Build a selection command sequence in category order.

    Selection order is what type-order-sensitive plugins consume: categories
    in ``order`` (default CATEGORY_ORDER), types alphabetically inside each
    category, each emitted as an additive ``Fixture <ranges>`` command so the
    console's selection order matches the emission order.
    """
    order = order or CATEGORY_ORDER
    commands: list[str] = ["ClearAll"] if clear_first else []
    by_cat = model.by_category()
    for cat in order:
        for rec in by_cat.get(cat, []):
            spec = _compress_ranges(rec.member_ids)
            if spec:
                commands.append(f"Fixture {spec}")
    return commands


__all__ = [
    "CATEGORY_ORDER",
    "DEFAULT_CATEGORY_BLOCKS",
    "CAPABILITY_FLAGS",
    "PRESET_TYPE_CAPABILITY",
    "FixtureTypeRecord",
    "FixtureTypeModel",
    "capabilities_from_attributes",
    "parse_channel_type_rows",
    "fallback_capabilities",
    "classify_category",
    "build_fixture_type_model",
    "verify_id_blocks",
    "renumber_commands",
    "build_type_ordered_selection",
]

"""Preset-library types — pure dataclasses + TypedDicts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, TypedDict


PresetStrategyName = Literal["full-coverage", "minimal-viable", "color-first"]


class PresetEntry(TypedDict, total=False):
    """One preset entry in the architect's plan."""

    preset_type: int               # 1=Dimmer, 2=Position, 3=Gobo, 4=Color, 5=Beam, 6=Focus, 7=Control
    preset_id: int
    name: str
    scope: Literal["universal", "selective"]
    target_fixture_types: list[str]
    values: dict
    mib_aware: bool
    color_model: str | None


class CoverageReport(TypedDict):
    fixture_type: str
    attribute: str
    has_preset: bool
    preset_ids: list[str]   # ["4.1", "2.3"]


class ArchitectOptions(TypedDict, total=False):
    naming_convention: str
    include_mib_for_movers: bool
    color_model: Literal["RGB", "HSB"]


@dataclass(frozen=True)
class PresetStrategy:
    """A coherent set of defaults for one preset-library architecture style."""

    name: str
    universal_types: list[int] = field(default_factory=list)    # preset_type ids that go universal
    selective_types: list[int] = field(default_factory=list)    # selective per fixture type
    cardinal_color_count: int = 4
    include_warm_cool_wash: bool = False
    include_mib: bool = False
    naming_convention: str = "{type}_{name}"
    notes: str = ""


__all__ = [
    "PresetEntry", "CoverageReport", "ArchitectOptions",
    "PresetStrategy", "PresetStrategyName",
]

"""Show-strategy types — pure dataclasses + TypedDicts.

Pure module; no I/O, no project-internal imports beyond stdlib. The
``src/show_strategies/`` purity invariant (added in Path B hygiene pass)
enforces this. The patch_reader module is the lone I/O boundary in this
package.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, TypedDict


CueDensity = Literal["sparse", "normal", "dense"]
PresetStrategy = Literal["minimal-viable", "full-coverage", "color-first"]
Tracking = Literal["track", "track-with-block", "non-tracking"]
MibPolicy = Literal["movers-always", "movers-and-washes", "none"]


class PatchSummary(TypedDict):
    """Minimal typed view of the patch state used by the plan builder."""

    showfile: str
    fixture_count: int
    fixtures: list[dict]            # {id, name, type, patch}
    fixture_types: list[dict]       # {id, long_name, short_name, manufacturer}
    groups: list[dict]              # {id, name}
    sequences_count: int
    macros_count: int


class ShowBuildOptions(TypedDict, total=False):
    songs: int
    venue_type: Literal["club", "theatre", "festival", "broadcast", "corporate"]
    cue_density: CueDensity
    preset_strategy: PresetStrategy
    world_filter_scope: Literal["none", "per-section", "per-fixture-type"]
    naming_convention: str


class ShowBuildStep(TypedDict):
    """One ordered step in a show-build plan."""

    order: int
    kind: str           # "create-group" | "store-preset" | "store-cue" | "assign-executor" | "create-world"
    command: str
    purpose: str
    expert_says: str
    risk_tier: str
    meta: dict


@dataclass(frozen=True)
class Strategy:
    """A coherent set of defaults for one production type.

    Strategies are the operator-facing knob for ``build_show_from_patch``.
    Each strategy defines: cue density, preset coverage, tracking discipline,
    MIB policy, world/filter scope, default views, default song count, and
    a naming convention template.
    """

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
    "PatchSummary",
    "ShowBuildOptions",
    "ShowBuildStep",
    "Strategy",
    "CueDensity",
    "PresetStrategy",
    "Tracking",
    "MibPolicy",
]

"""Three preset-library strategies per spec §C.4."""

from __future__ import annotations

from src.preset_strategies.types import PresetStrategy


PRESET_STRATEGIES: dict[str, PresetStrategy] = {
    "full-coverage": PresetStrategy(
        name="full-coverage",
        universal_types=[2, 4],            # position, color universal
        selective_types=[3, 5, 6, 7],      # gobo, beam, focus, control selective
        cardinal_color_count=8,            # red, green, blue, white, orange, yellow, cyan, magenta
        include_warm_cool_wash=True,
        include_mib=True,
        naming_convention="{type}_{name}",
        notes=(
            "Every attribute on every fixture type has at least one expert-graded "
            "preset. Movers get MIB presets. Selective per-type for gobo/beam/focus/control."
        ),
    ),
    "minimal-viable": PresetStrategy(
        name="minimal-viable",
        universal_types=[4],               # color only
        selective_types=[],
        cardinal_color_count=4,            # red, green, blue, white only
        include_warm_cool_wash=False,
        include_mib=False,
        naming_convention="{name}",
        notes=(
            "Lean preset library — 4 cardinal hues only. No position, gobo, or beam "
            "presets. Use only when rig is so small that selective presets are overkill."
        ),
    ),
    "color-first": PresetStrategy(
        name="color-first",
        universal_types=[2, 4],
        selective_types=[],
        cardinal_color_count=12,           # full hue wheel
        include_warm_cool_wash=True,
        include_mib=False,
        naming_convention="{type}_{name}",
        notes=(
            "Color-heavy library — full 12-hue wheel plus warm/cool wash variants. "
            "Position universal but minimal (4 cardinal). No gobo/beam/focus/control."
        ),
    ),
}


def get_preset_strategy(name: str) -> PresetStrategy:
    if name not in PRESET_STRATEGIES:
        raise ValueError(
            f"unknown preset strategy: {name!r}; valid: {sorted(PRESET_STRATEGIES)}"
        )
    return PRESET_STRATEGIES[name]


__all__ = ["PRESET_STRATEGIES", "get_preset_strategy"]

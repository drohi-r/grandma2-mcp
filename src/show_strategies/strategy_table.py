"""Strategy definitions — concrete defaults per spec §B.1.

Six strategies, each a frozen :class:`Strategy` instance. Pure data;
no I/O, no project imports beyond ``.types``.
"""

from __future__ import annotations

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
        notes=(
            "Each song gets its own sequence. Includes panic-blackout cue 0.5 "
            "as the first cue of every sequence."
        ),
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
        notes=(
            "Optimized for fast set changes between bands; preset-heavy, "
            "cue-light. Heavy reliance on instant-recall executor buttons."
        ),
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
        notes=(
            "Long crossfades default; per-act worlds; block cues at scene "
            "boundaries. Includes an emergency cue list at Super priority."
        ),
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
        notes=(
            "Tap-tempo and speed master prominent; MAtricks instances per "
            "executor for variation. Includes drop sequences (build/bang/release)."
        ),
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
        notes=(
            "Everything preset-referenced for rebuild safety. KEY fixture "
            "group convention applied; no bare numeric values in cues."
        ),
    ),
    "corporate": Strategy(
        name="corporate",
        cue_density="sparse",
        preset_strategy="minimal-viable",
        tracking="non-tracking",
        mib_policy="none",
        world_filter_scope="none",
        views=["run"],
        default_songs=1,    # 3-5 looks total in one sequence
        naming_convention="{look}",
        notes=(
            "Single show sequence with 3-5 looks; blackout cue at start and "
            "end. No worlds, minimal preset library."
        ),
    ),
}


def get_strategy(name: str) -> Strategy:
    """Return the named strategy, or raise ``ValueError``."""
    if name not in STRATEGIES:
        raise ValueError(
            f"unknown strategy: {name!r}; valid: {sorted(STRATEGIES)}"
        )
    return STRATEGIES[name]


__all__ = ["STRATEGIES", "get_strategy"]

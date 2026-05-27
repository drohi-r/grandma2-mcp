"""src.show_strategies — pure plan builder for ``build_show_from_patch``.

Public API:
    ``build_plan_for(strategy, patch, options)`` — pure plan builder.
    ``STRATEGIES`` / ``get_strategy(name)`` — six strategy tables (rock-band,
        festival, theatrical, dj, broadcast, corporate).
    ``PatchSummary``, ``ShowBuildOptions``, ``ShowBuildStep``, ``Strategy``
        — typed shapes for callers.

The ``patch_reader`` submodule provides the I/O boundary (live patch read
via Telnet) and is exempt from the package's purity invariant.
"""

from src.show_strategies.plan_builder import build_plan_for
from src.show_strategies.strategy_table import STRATEGIES, get_strategy
from src.show_strategies.types import (
    PatchSummary,
    ShowBuildOptions,
    ShowBuildStep,
    Strategy,
)

__all__ = [
    "build_plan_for",
    "STRATEGIES",
    "get_strategy",
    "PatchSummary",
    "ShowBuildOptions",
    "ShowBuildStep",
    "Strategy",
]

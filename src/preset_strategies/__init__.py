"""src.preset_strategies — pure plan builder for ``architect_preset_library``.

Public API:
    ``architect_preset_library_for(strategy, patch, options)`` — pure builder
    ``PRESET_STRATEGIES`` / ``get_preset_strategy(name)`` — 3 strategies
    ``PresetStrategy``, ``PresetEntry``, ``CoverageReport``, ``ArchitectOptions``
        — typed shapes

Reuses ``src.show_strategies.types.PatchSummary`` for the patch input shape.
Pure module — no I/O, no telnet client.
"""

from src.preset_strategies.plan_builder import architect_preset_library_for
from src.preset_strategies.strategy_table import (
    PRESET_STRATEGIES,
    get_preset_strategy,
)
from src.preset_strategies.types import (
    ArchitectOptions,
    CoverageReport,
    PresetEntry,
    PresetStrategy,
)

__all__ = [
    "architect_preset_library_for",
    "PRESET_STRATEGIES",
    "get_preset_strategy",
    "ArchitectOptions",
    "CoverageReport",
    "PresetEntry",
    "PresetStrategy",
]

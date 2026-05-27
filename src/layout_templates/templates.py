"""Six template definitions — required roles per spec §B.2 and view-and-layout-designer."""

from __future__ import annotations

from src.layout_templates.types import Template


TEMPLATES: dict[str, Template] = {
    "busking-master": Template(
        name="busking-master",
        required_roles=["intensity", "color", "fx", "specials"],
        default_grid_cols=8,
        default_grid_rows=5,
        description=(
            "Live-performance master view — intensity row, color row, "
            "position/beam row, FX row, specials (kill / blackout / tap)."
        ),
    ),
    "preset-access": Template(
        name="preset-access",
        required_roles=["color-preset-bank", "position-preset-bank"],
        default_grid_cols=8,
        default_grid_rows=4,
        description=(
            "Preset-recall page — quick-fire color/position presets organised by hue."
        ),
    ),
    "executor-monitor": Template(
        name="executor-monitor",
        required_roles=["executor-row"],
        default_grid_cols=10,
        default_grid_rows=5,
        description=(
            "Read-only monitor of all active executors with running-cue indicator."
        ),
    ),
    "macro-page": Template(
        name="macro-page",
        required_roles=["macro-grid"],
        default_grid_cols=8,
        default_grid_rows=4,
        description=(
            "Macro grid — 32 macro slots arranged for quick recall during a show."
        ),
    ),
    "programmer-view": Template(
        name="programmer-view",
        required_roles=["selection-row", "attribute-grid"],
        default_grid_cols=8,
        default_grid_rows=6,
        description=(
            "Programmer working surface — current selection + attribute editing grid."
        ),
    ),
    "troubleshoot-view": Template(
        name="troubleshoot-view",
        required_roles=["diagnostic-readouts"],
        default_grid_cols=8,
        default_grid_rows=4,
        description=(
            "Diagnostic readouts: DMX universe status, output values, RDM device list."
        ),
    ),
}


def get_template(name: str) -> Template:
    if name not in TEMPLATES:
        raise ValueError(f"unknown template: {name!r}; valid: {sorted(TEMPLATES)}")
    return TEMPLATES[name]


__all__ = ["TEMPLATES", "get_template"]

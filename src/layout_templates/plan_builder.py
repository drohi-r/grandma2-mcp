"""Layout plan builder — template → ordered list of LayoutPlanStep + content cells.

Pure function. Two public entry points:

    build_layout_for(template, screen, options) → (plan_steps, content)
    render_ascii_preview(content, grid_cols, grid_rows) → str

The content emitted by ``build_layout_for`` is shaped for the
``src.expert_lint.layout_rules`` module: each cell has kind/target/label/
grid_x/grid_y/width/height/role.
"""

from __future__ import annotations

from src.layout_templates.templates import get_template
from src.layout_templates.types import ContentSpec, LayoutPlanStep


# Default cell content per template — concrete cells that fulfil the required
# roles. Pure data tables; callers pass these to MA2 unchanged.
_TEMPLATE_CONTENT: dict[str, list[ContentSpec]] = {
    "busking-master": [
        # Row 0 — intensity sub-masters (4 slots)
        {"kind": "executor", "target": "1.1.1", "label": "Wash Int", "grid_x": 0, "grid_y": 0, "width": 1, "height": 1, "role": "intensity"},
        {"kind": "executor", "target": "1.1.2", "label": "Mover Int", "grid_x": 1, "grid_y": 0, "width": 1, "height": 1, "role": "intensity"},
        {"kind": "executor", "target": "1.1.3", "label": "Bar Int", "grid_x": 2, "grid_y": 0, "width": 1, "height": 1, "role": "intensity"},
        {"kind": "executor", "target": "1.1.4", "label": "Blinder Int", "grid_x": 3, "grid_y": 0, "width": 1, "height": 1, "role": "intensity"},
        # Row 1 — color chases (4 slots)
        {"kind": "executor", "target": "1.1.5", "label": "Color A", "grid_x": 0, "grid_y": 1, "width": 1, "height": 1, "role": "color"},
        {"kind": "executor", "target": "1.1.6", "label": "Color B", "grid_x": 1, "grid_y": 1, "width": 1, "height": 1, "role": "color"},
        {"kind": "executor", "target": "1.1.7", "label": "Color C", "grid_x": 2, "grid_y": 1, "width": 1, "height": 1, "role": "color"},
        {"kind": "executor", "target": "1.1.8", "label": "Color D", "grid_x": 3, "grid_y": 1, "width": 1, "height": 1, "role": "color"},
        # Row 2 — FX
        {"kind": "executor", "target": "1.1.21", "label": "FX A", "grid_x": 0, "grid_y": 2, "width": 1, "height": 1, "role": "fx"},
        {"kind": "executor", "target": "1.1.22", "label": "FX B", "grid_x": 1, "grid_y": 2, "width": 1, "height": 1, "role": "fx"},
        {"kind": "executor", "target": "1.1.23", "label": "FX C", "grid_x": 2, "grid_y": 2, "width": 1, "height": 1, "role": "fx"},
        # Row 3 — specials
        {"kind": "executor", "target": "1.1.10", "label": "Blackout", "grid_x": 0, "grid_y": 3, "width": 1, "height": 1, "role": "specials"},
        {"kind": "executor", "target": "1.1.11", "label": "Speed M", "grid_x": 1, "grid_y": 3, "width": 1, "height": 1, "role": "specials"},
        {"kind": "executor", "target": "1.1.12", "label": "Tap", "grid_x": 2, "grid_y": 3, "width": 1, "height": 1, "role": "specials"},
    ],
    "preset-access": [
        # Color preset grid (8x2)
        *[
            {"kind": "preset", "target": f"4.{i+1}",
             "label": ["Red", "Orange", "Yellow", "Green", "Cyan", "Blue", "Magenta", "White"][i],
             "grid_x": i, "grid_y": 0, "width": 1, "height": 1,
             "role": "color-preset-bank"}
            for i in range(8)
        ],
        # Position preset row
        *[
            {"kind": "preset", "target": f"2.{i+1}",
             "label": ["Home", "Audience", "Stage L", "Stage R"][i],
             "grid_x": i, "grid_y": 2, "width": 1, "height": 1,
             "role": "position-preset-bank"}
            for i in range(4)
        ],
    ],
    "executor-monitor": [
        # Generic executor cells — operators fill in their active executors
        *[
            {"kind": "executor", "target": f"1.1.{i+1}",
             "label": f"Exec {i+1}",
             "grid_x": i % 10, "grid_y": i // 10,
             "width": 1, "height": 1, "role": "executor-row"}
            for i in range(20)
        ],
    ],
    "macro-page": [
        *[
            {"kind": "macro", "target": str(i+1),
             "label": f"Macro {i+1}",
             "grid_x": i % 8, "grid_y": i // 8,
             "width": 1, "height": 1, "role": "macro-grid"}
            for i in range(32)
        ],
    ],
    "programmer-view": [
        # Selection row at top — labels only; operator pins their current selection here
        {"kind": "label", "target": "selection", "label": "Selection",
         "grid_x": 0, "grid_y": 0, "width": 8, "height": 1, "role": "selection-row"},
        # Attribute grid (6 rows × 4 cols of attribute readouts)
        *[
            {"kind": "label", "target": f"attr_{i}",
             "label": f"Attr {i+1}",
             "grid_x": i % 4, "grid_y": 1 + (i // 4),
             "width": 1, "height": 1, "role": "attribute-grid"}
            for i in range(20)
        ],
    ],
    "troubleshoot-view": [
        # DMX universe status, output values, RDM device list — readouts only
        {"kind": "label", "target": "dmx_status", "label": "DMX Universe Status",
         "grid_x": 0, "grid_y": 0, "width": 8, "height": 1, "role": "diagnostic-readouts"},
        {"kind": "label", "target": "output_values", "label": "Live Output Values",
         "grid_x": 0, "grid_y": 1, "width": 8, "height": 2, "role": "diagnostic-readouts"},
        {"kind": "label", "target": "rdm_devices", "label": "RDM Device List",
         "grid_x": 0, "grid_y": 3, "width": 8, "height": 1, "role": "diagnostic-readouts"},
    ],
}


def build_layout_for(
    *,
    template: str,
    screen: int,
    options: dict | None = None,
) -> tuple[list[LayoutPlanStep], list[ContentSpec]]:
    """Build a layout plan + content list for a named template."""
    tmpl = get_template(template)
    content = list(_TEMPLATE_CONTENT.get(template, []))
    order = 0
    plan: list[LayoutPlanStep] = []

    plan.append(LayoutPlanStep(
        order=(order := order + 1),
        kind="set-screen",
        command=f'Screen {screen}',
        purpose=f"Switch to screen {screen} before placing cells",
        meta={"screen": screen, "template": template},
    ))

    for cell in content:
        target = cell.get("target", "")
        label = cell.get("label") or ""
        x = cell.get("grid_x", 0)
        y = cell.get("grid_y", 0)
        # MA2 layout-element command shape varies by content kind; we emit a
        # canonical 'LayoutElement' line per cell. The actual command string
        # is illustrative — execution paths land in Path B follow-on work.
        cmd = (
            f'LayoutElement {x},{y} {cell.get("kind", "label")} "{label}" '
            f'@ {target}'
        )
        plan.append(LayoutPlanStep(
            order=(order := order + 1),
            kind="place-cell",
            command=cmd,
            purpose=f"Place {cell.get('kind', 'label')} at ({x},{y}): {label or target}",
            meta=dict(cell),
        ))

    return plan, content


def render_ascii_preview(
    content: list[ContentSpec],
    grid_cols: int = 8,
    grid_rows: int = 5,
) -> str:
    """Render an ASCII preview of the layout grid for operator review."""
    grid: list[list[str]] = [["." for _ in range(grid_cols)] for _ in range(grid_rows)]
    for cell in content:
        x = cell.get("grid_x", 0)
        y = cell.get("grid_y", 0)
        w = max(1, cell.get("width", 1))
        h = max(1, cell.get("height", 1))
        glyph = (cell.get("kind") or "x")[0].upper()
        for dy in range(h):
            for dx in range(w):
                gy, gx = y + dy, x + dx
                if 0 <= gy < grid_rows and 0 <= gx < grid_cols:
                    grid[gy][gx] = glyph
    lines = ["".join(row) for row in grid]
    return "\n".join(lines)


__all__ = ["build_layout_for", "render_ascii_preview"]

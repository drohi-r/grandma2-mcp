"""src.layout_templates — pure layout plan builder for ``build_layout_for_screen``.

Public API:
    ``build_layout_for(template, screen, options)`` → (plan_steps, content)
    ``render_ascii_preview(content, grid_cols, grid_rows)`` → ASCII grid string
    ``TEMPLATES`` / ``get_template(name)`` — six named templates
    ``Template``, ``ContentSpec``, ``LayoutPlanStep`` — typed shapes

Pure module — no I/O, no telnet client. Layouts are static templates +
content lists; execution is handled by the calling tool.
"""

from src.layout_templates.plan_builder import (
    build_layout_for,
    render_ascii_preview,
)
from src.layout_templates.templates import TEMPLATES, get_template
from src.layout_templates.types import (
    ContentSpec,
    LayoutPlanStep,
    Template,
)

__all__ = [
    "build_layout_for", "render_ascii_preview",
    "TEMPLATES", "get_template",
    "ContentSpec", "LayoutPlanStep", "Template",
]

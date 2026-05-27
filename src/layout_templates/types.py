"""Layout-template types — pure dataclasses + TypedDicts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, TypedDict


TemplateName = Literal[
    "busking-master",
    "preset-access",
    "executor-monitor",
    "macro-page",
    "programmer-view",
    "troubleshoot-view",
]

CellKind = Literal[
    "group", "preset", "executor", "macro", "label", "image", "fader"
]


class ContentSpec(TypedDict, total=False):
    """One cell to place on the layout."""

    kind: CellKind
    target: str | int
    label: str | None
    grid_x: int
    grid_y: int
    width: int
    height: int
    role: str   # for template-requirement matching


class LayoutPlanStep(TypedDict):
    order: int
    kind: str           # "place-cell" | "set-screen" | ...
    command: str
    purpose: str
    meta: dict


@dataclass(frozen=True)
class Template:
    """A named layout template with default content roles + slot hints."""

    name: str
    required_roles: list[str] = field(default_factory=list)
    default_grid_cols: int = 8
    default_grid_rows: int = 5
    description: str = ""


__all__ = [
    "TemplateName", "CellKind", "ContentSpec",
    "LayoutPlanStep", "Template",
]

"""Workflow templates for the agent harness.

Each template defines the canonical step ordering for a domain workflow.
Templates are pure functions that return lists of PlanSteps — no I/O.
"""

from src.agent.workflows.common import (
    build_discover_names_steps,
    build_label_step,
    build_verify_step,
)
from src.agent.workflows.patch import build_patch_workflow
from src.agent.workflows.playback import build_playback_workflow
from src.agent.workflows.preset import build_preset_workflow

__all__ = [
    "build_discover_names_steps",
    "build_label_step",
    "build_patch_workflow",
    "build_playback_workflow",
    "build_preset_workflow",
    "build_verify_step",
]

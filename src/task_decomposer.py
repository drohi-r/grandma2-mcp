"""
task_decomposer.py — Break high-level show intent into ordered sub-agent steps.

Jensen: "In the future, we're going to write ideas, architectures, specifications.
We're going to organize teams... define how to evaluate the definition of good vs bad."

A TaskDecomposer takes a natural-language lighting goal and produces an ordered
plan of SubTask objects, each scoped to one agent and one risk tier — so no single
agent ever holds all three capabilities (read + write + destructive) at once.

Jensen: "we have policies that give these agents two of the three things
but not all three things at the same time."
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

from .vocab import RiskTier  # single source of truth — do not redefine

# ---------------------------------------------------------------------------
# Sub-task definition
# ---------------------------------------------------------------------------

@dataclass
class SubTask:
    """
    One atomic unit of work assigned to a specialized sub-agent.

    Jensen's agent model: each agent has a clear scope, memory access,
    allowed tools, and a definition of success.
    """

    name: str                           # e.g. "select_wash_fixtures"
    agent_role: str                     # e.g. "SelectionAgent"
    description: str                    # natural-language intent
    allowed_risk: RiskTier              # max risk level this agent may exercise
    mcp_tools: list[str]                # which of the 90 tools it may call
    inputs: dict = field(default_factory=dict)   # params passed in
    outputs: dict = field(default_factory=dict)  # results written back
    depends_on: list[str] = field(default_factory=list)  # step names
    eval_criteria: str = ""             # Jensen: "definition of good vs bad"
    retryable: bool = True
    confirmed: bool = False             # must be True for DESTRUCTIVE steps
    workflow: Literal["inspect", "plan", "execute"] = "inspect"  # standard workflow tier


@dataclass
class TaskPlan:
    """Ordered sequence of SubTasks for one high-level goal."""

    goal: str
    steps: list[SubTask] = field(default_factory=list)
    session_id: str = ""

    def ordered_steps(self) -> list[SubTask]:
        """Topological sort respecting depends_on."""
        completed: set[str] = set()
        ordered: list[SubTask] = []
        remaining = list(self.steps)
        max_passes = len(remaining) + 1
        passes = 0
        while remaining and passes < max_passes:
            passes += 1
            for step in list(remaining):
                if all(d in completed for d in step.depends_on):
                    ordered.append(step)
                    completed.add(step.name)
                    remaining.remove(step)
        ordered.extend(remaining)  # append any cycles unresolved
        return ordered

    def summary(self) -> str:
        lines = [f"Goal: {self.goal}", f"Steps ({len(self.steps)}):"]
        for i, s in enumerate(self.ordered_steps(), 1):
            deps = f" [after: {', '.join(s.depends_on)}]" if s.depends_on else ""
            lines.append(f"  {i}. [{s.agent_role}] {s.name}{deps}")
            lines.append(f"     risk={s.allowed_risk.value} tools={s.mcp_tools}")
            lines.append(f"     eval: {s.eval_criteria}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Built-in decomposition rules
# ---------------------------------------------------------------------------

# Each rule: (pattern, plan_builder_fn)
# pattern matches against the lowercased goal string.

Rule = tuple[str, Callable[[str, dict], TaskPlan]]

def _build_wash_look(goal: str, params: dict) -> TaskPlan:
    """Decompose a 'wash look' lighting goal."""
    color   = params.get("color", "")
    group   = params.get("group", "wash")
    preset  = params.get("preset", "")
    seq     = params.get("sequence", 1)
    cue     = params.get("cue", 1.0)

    return TaskPlan(goal=goal, steps=[
        SubTask(
            name="select_wash_group",
            agent_role="SelectionAgent",
            description=f"Select all fixtures in group '{group}'",
            allowed_risk=RiskTier.SAFE_WRITE,
            mcp_tools=["select_fixtures_by_group", "modify_selection"],
            inputs={"group": group},
            eval_criteria="Programmer selection is non-empty and matches group",
            workflow="execute",
        ),
        SubTask(
            name="apply_wash_color",
            agent_role="ColorAgent",
            description=f"Apply {color} color preset to selection",
            allowed_risk=RiskTier.SAFE_WRITE,
            mcp_tools=["apply_preset", "set_attribute"],
            inputs={"color": color, "preset": preset},
            depends_on=["select_wash_group"],
            eval_criteria="Color attribute matches target in programmer",
            workflow="execute",
        ),
        SubTask(
            name="set_wash_intensity",
            agent_role="IntensityAgent",
            description="Set wash intensity to full",
            allowed_risk=RiskTier.SAFE_WRITE,
            mcp_tools=["set_intensity"],
            inputs={"level": 100},
            depends_on=["select_wash_group"],
            eval_criteria="Intensity channel is at 100% in programmer",
            workflow="execute",
        ),
        SubTask(
            name="store_wash_cue",
            agent_role="CueAgent",
            description=f"Store programmer state into sequence {seq} cue {cue}",
            allowed_risk=RiskTier.DESTRUCTIVE,
            mcp_tools=["store_current_cue", "store_cue_with_timing"],
            inputs={"sequence": seq, "cue": cue, "label": f"{color} wash"},
            depends_on=["apply_wash_color", "set_wash_intensity"],
            eval_criteria="Cue exists in sequence with correct label",
            confirmed=False,  # orchestrator must set True after human approval
            workflow="execute",
        ),
        SubTask(
            name="verify_wash_cue",
            agent_role="ValidationAgent",
            description="Confirm cue is stored and playback-ready",
            allowed_risk=RiskTier.SAFE_READ,
            mcp_tools=["list_sequence_cues", "get_executor_status"],
            inputs={"sequence": seq, "cue": cue},
            depends_on=["store_wash_cue"],
            eval_criteria="Cue appears in sequence list with matching label",
            workflow="inspect",
        ),
    ])


def _build_blackout_sequence(goal: str, params: dict) -> TaskPlan:
    seq = params.get("sequence", 1)
    return TaskPlan(goal=goal, steps=[
        SubTask(
            name="read_current_cues",
            agent_role="InspectionAgent",
            description="List existing cues so we don't overwrite",
            allowed_risk=RiskTier.SAFE_READ,
            mcp_tools=["list_sequence_cues", "navigate_console"],
            inputs={"sequence": seq},
            eval_criteria="Cue list returned without error",
            workflow="inspect",
        ),
        SubTask(
            name="store_blackout_cue",
            agent_role="CueAgent",
            description="Store a blackout cue at end of sequence",
            allowed_risk=RiskTier.DESTRUCTIVE,
            mcp_tools=["store_current_cue"],
            inputs={"sequence": seq, "label": "BLK"},
            depends_on=["read_current_cues"],
            eval_criteria="Blackout cue appended to sequence",
            confirmed=False,
            workflow="execute",
        ),
    ])


def _build_group_preset_library(goal: str, params: dict) -> TaskPlan:
    """Decompose building a fixture group + preset library."""
    return TaskPlan(goal=goal, steps=[
        SubTask(
            name="discover_fixtures",
            agent_role="InspectionAgent",
            description="List all patched fixtures to understand the rig",
            allowed_risk=RiskTier.SAFE_READ,
            mcp_tools=["list_fixtures", "list_fixture_types", "list_universes"],
            eval_criteria="Fixture list non-empty",
            workflow="inspect",
        ),
        SubTask(
            name="create_groups",
            agent_role="GroupAgent",
            description="Create fixture groups from discovered rig layout",
            allowed_risk=RiskTier.DESTRUCTIVE,
            mcp_tools=["create_fixture_group"],
            depends_on=["discover_fixtures"],
            eval_criteria="Groups created for each zone",
            confirmed=False,
            workflow="execute",
        ),
        SubTask(
            name="build_color_presets",
            agent_role="PresetAgent",
            description="Store color presets for common looks",
            allowed_risk=RiskTier.DESTRUCTIVE,
            mcp_tools=["store_new_preset"],
            depends_on=["create_groups"],
            eval_criteria="Preset pool contains target colors",
            confirmed=False,
            workflow="execute",
        ),
        SubTask(
            name="verify_library",
            agent_role="ValidationAgent",
            description="Confirm all groups and presets are accessible",
            allowed_risk=RiskTier.SAFE_READ,
            mcp_tools=["list_preset_pool", "query_object_list"],
            depends_on=["build_color_presets"],
            eval_criteria="Groups and presets queryable from pool",
            workflow="inspect",
        ),
    ])


def _build_inspect_only(goal: str, params: dict) -> TaskPlan:
    """Inspect-only plan: read system state then summarize findings."""
    return TaskPlan(goal=goal, steps=[
        SubTask(
            name="read_system_state",
            agent_role="InspectionAgent",
            description="Read system variables and console destination list",
            allowed_risk=RiskTier.SAFE_READ,
            mcp_tools=["list_system_variables", "list_console_destination"],
            eval_criteria="System state returned without error",
            workflow="inspect",
        ),
        SubTask(
            name="summarize_findings",
            agent_role="InspectionAgent",
            description="Query objects and summarize console state",
            allowed_risk=RiskTier.SAFE_READ,
            mcp_tools=["get_object_info", "query_object_list"],
            depends_on=["read_system_state"],
            eval_criteria="Findings returned in structured form",
            workflow="inspect",
        ),
    ])


def _build_plan_only(goal: str, params: dict) -> TaskPlan:
    """Plan-only workflow: inspect + preflight + propose (no mutations)."""
    return TaskPlan(goal=goal, steps=[
        SubTask(
            name="inspect_current_state",
            agent_role="InspectionAgent",
            description="Read current console state using SAFE_READ tools",
            allowed_risk=RiskTier.SAFE_READ,
            mcp_tools=["list_console_destination", "get_object_info", "query_object_list"],
            eval_criteria="Current state captured",
            workflow="inspect",
        ),
        SubTask(
            name="preflight_rights_check",
            agent_role="InspectionAgent",
            description="Verify user rights before proposing any change",
            allowed_risk=RiskTier.SAFE_READ,
            mcp_tools=["list_system_variables"],
            depends_on=["inspect_current_state"],
            eval_criteria="$USERRIGHTS read and sufficient for planned operation",
            workflow="inspect",
        ),
        SubTask(
            name="propose_change_plan",
            agent_role="PlannerAgent",
            description="Propose the sequence of commands to achieve the goal (no execution)",
            allowed_risk=RiskTier.SAFE_READ,
            mcp_tools=[],
            depends_on=["preflight_rights_check"],
            eval_criteria="Proposed plan lists specific MA2 commands with risk tier",
            workflow="plan",
        ),
    ])


def _build_color_sequence_workflow(goal: str, params: dict) -> TaskPlan:
    """Decompose a color palette or hue sequence build workflow."""
    sequence_id = params.get("sequence_id", 99)
    executor_id = params.get("executor_id", 201)
    hue_pair    = params.get("hue_pair", None)

    return TaskPlan(goal=goal, steps=[
        SubTask(
            name="audit_color_presets",
            agent_role="InspectionAgent",
            description="List color preset pool to discover available presets",
            allowed_risk=RiskTier.SAFE_READ,
            mcp_tools=["list_preset_pool", "query_object_list"],
            inputs={"preset_type": "color"},
            eval_criteria="Preset pool returned non-empty color preset list",
            workflow="inspect",
        ),
        SubTask(
            name="validate_target_sequence",
            agent_role="InspectionAgent",
            description=f"Check sequence {sequence_id} for existing cues",
            allowed_risk=RiskTier.SAFE_READ,
            mcp_tools=["query_object_list", "list_system_variables"],
            inputs={"sequence_id": sequence_id},
            depends_on=["audit_color_presets"],
            eval_criteria="Cue count reported (zero or existing)",
            workflow="inspect",
        ),
        SubTask(
            name="build_color_cues",
            agent_role="SequenceAgent",
            description="SelFix → apply preset → store cue → appearance → ClearAll for each color",
            allowed_risk=RiskTier.DESTRUCTIVE,
            mcp_tools=["store_current_cue", "label_or_appearance", "apply_preset"],
            inputs={"sequence_id": sequence_id, "hue_pair": hue_pair, "overwrite": True},
            depends_on=["validate_target_sequence"],
            eval_criteria="Cue count matches preset count",
            confirmed=False,
            workflow="execute",
        ),
        SubTask(
            name="assign_to_executor",
            agent_role="ExecutorAgent",
            description=f"Assign sequence {sequence_id} to executor {executor_id}",
            allowed_risk=RiskTier.DESTRUCTIVE,
            mcp_tools=["assign_object", "get_executor_status"],
            inputs={"sequence_id": sequence_id, "executor_id": executor_id},
            depends_on=["build_color_cues"],
            eval_criteria="Executor status confirms sequence assignment",
            confirmed=False,
            workflow="execute",
        ),
        SubTask(
            name="verify_color_sequence",
            agent_role="ValidationAgent",
            description="Count cues in sequence and confirm executor assignment",
            allowed_risk=RiskTier.SAFE_READ,
            mcp_tools=["query_object_list", "get_executor_status"],
            inputs={"sequence_id": sequence_id, "executor_id": executor_id},
            depends_on=["assign_to_executor"],
            eval_criteria="Cue count == preset count AND executor shows sequence",
            workflow="inspect",
        ),
    ])


def _build_preset_library_workflow(goal: str, params: dict) -> TaskPlan:
    """Decompose a full preset library build across all preset types."""
    return TaskPlan(goal=goal, steps=[
        SubTask(
            name="audit_existing_presets",
            agent_role="InspectionAgent",
            description="List all preset pools to find occupied slots",
            allowed_risk=RiskTier.SAFE_READ,
            mcp_tools=["list_preset_pool", "query_object_list"],
            eval_criteria="All preset type pools queried",
            workflow="inspect",
        ),
        SubTask(
            name="store_dimmer_presets",
            agent_role="PresetAgent",
            description="Store 5 dimmer presets (Full, 75%, Half, 25%, Off) — universal",
            allowed_risk=RiskTier.DESTRUCTIVE,
            mcp_tools=["store_new_preset", "label_or_appearance"],
            depends_on=["audit_existing_presets"],
            eval_criteria="5 dimmer presets in pool",
            confirmed=False,
            workflow="execute",
        ),
        SubTask(
            name="store_color_presets",
            agent_role="PresetAgent",
            description="Store 8 color presets (White–Yellow spectrum) — universal",
            allowed_risk=RiskTier.DESTRUCTIVE,
            mcp_tools=["store_new_preset", "label_or_appearance"],
            depends_on=["audit_existing_presets"],
            eval_criteria="8 color presets in pool",
            confirmed=False,
            workflow="execute",
        ),
        SubTask(
            name="store_position_presets",
            agent_role="PresetAgent",
            description="Store 5+ position presets per moving head group — selective",
            allowed_risk=RiskTier.DESTRUCTIVE,
            mcp_tools=["store_new_preset", "label_or_appearance", "list_groups"],
            depends_on=["audit_existing_presets"],
            eval_criteria="At least 5 position presets in pool",
            confirmed=False,
            workflow="execute",
        ),
        SubTask(
            name="verify_preset_library",
            agent_role="ValidationAgent",
            description="Confirm counts: ≥5 dimmer, ≥8 color, ≥5 position presets",
            allowed_risk=RiskTier.SAFE_READ,
            mcp_tools=["list_preset_pool", "query_object_list"],
            depends_on=["store_dimmer_presets", "store_color_presets", "store_position_presets"],
            eval_criteria="All counts meet targets",
            workflow="inspect",
        ),
    ])


def _build_patch_fixtures_workflow(goal: str, params: dict) -> TaskPlan:
    """Decompose a fixture patching and group creation workflow."""
    return TaskPlan(goal=goal, steps=[
        SubTask(
            name="discover_fixture_types",
            agent_role="InspectionAgent",
            description="List existing fixture types to avoid re-importing",
            allowed_risk=RiskTier.SAFE_READ,
            mcp_tools=["list_console_destination", "list_fixture_types"],
            eval_criteria="Fixture type pool listed without error",
            workflow="inspect",
        ),
        SubTask(
            name="discover_patch",
            agent_role="InspectionAgent",
            description="List current DMX patch to find free addresses",
            allowed_risk=RiskTier.SAFE_READ,
            mcp_tools=["list_universes", "query_object_list"],
            depends_on=["discover_fixture_types"],
            eval_criteria="DMX address map returned",
            workflow="inspect",
        ),
        SubTask(
            name="import_fixture_types",
            agent_role="PatchAgent",
            description="Import new fixture type XML files (skip if already present)",
            allowed_risk=RiskTier.DESTRUCTIVE,
            mcp_tools=["import_fixture_type"],
            depends_on=["discover_fixture_types"],
            eval_criteria="Fixture type appears in pool after import",
            confirmed=False,
            workflow="execute",
        ),
        SubTask(
            name="patch_fixtures",
            agent_role="PatchAgent",
            description="Patch each fixture to a DMX address using verified free slots",
            allowed_risk=RiskTier.DESTRUCTIVE,
            mcp_tools=["patch_fixture"],
            depends_on=["import_fixture_types", "discover_patch"],
            eval_criteria="All fixtures appear in fixture list",
            confirmed=False,
            workflow="execute",
        ),
        SubTask(
            name="create_fixture_groups",
            agent_role="GroupAgent",
            description="Create one group per fixture type via macro (reliable store pattern)",
            allowed_risk=RiskTier.DESTRUCTIVE,
            mcp_tools=["store_object", "label_or_appearance"],
            depends_on=["patch_fixtures"],
            eval_criteria="Groups queryable via list_groups",
            confirmed=False,
            workflow="execute",
        ),
        SubTask(
            name="verify_patch",
            agent_role="ValidationAgent",
            description="Confirm fixture count and group membership",
            allowed_risk=RiskTier.SAFE_READ,
            mcp_tools=["list_console_destination", "query_object_list", "get_object_info"],
            depends_on=["create_fixture_groups"],
            eval_criteria="Fixture and group counts match expected values",
            workflow="inspect",
        ),
    ])


_RULES: list[Rule] = [
    (r"color palette|hue sequence|hue pair|palette sequence|color cue list",
                                                                   _build_color_sequence_workflow),
    (r"wash|color look|stage wash",                                    _build_wash_look),
    (r"blackout|blk|fade to black",                                    _build_blackout_sequence),
    (r"preset library|build presets|store presets|preset layout",      _build_preset_library_workflow),
    (r"patch fixture|repatch|fixture type|dmx address|new fixture",    _build_patch_fixtures_workflow),
    (r"group.*preset|library|rig setup",                               _build_group_preset_library),
    (r"inspect|check|show state|what is|status|list|query|how many",   _build_inspect_only),
    (r"plan|draft|propose|what would|what should|design",              _build_plan_only),
]


# ---------------------------------------------------------------------------
# Worker catalog — maps worker name → allowed tools (used by Orchestrator)
# ---------------------------------------------------------------------------

WORKER_CATALOG: dict[str, list[str]] = {
    "show-file-analyzer":       ["list_console_destination", "get_object_info",
                                 "query_object_list", "scan_console_indexes"],
    "cue-list-auditor":         ["query_object_list", "get_object_info",
                                 "list_system_variables"],
    "feedback-investigator":    ["send_raw_command", "get_variable",
                                 "list_system_variables"],
    "console-state-hydrator":   ["hydrate_console_state", "list_system_variables"],
    "object-resolution-worker": ["discover_object_names", "query_object_list",
                                 "get_object_info"],
    "safety-preflight-checker": ["list_system_variables", "get_variable"],
    "preset-library-builder":   ["list_preset_pool", "store_new_preset",
                                 "label_or_appearance", "query_object_list"],
    "patch-and-group-builder":  ["list_console_destination", "import_fixture_type",
                                 "patch_fixture", "store_object", "label_or_appearance",
                                 "get_object_info"],
}


# ---------------------------------------------------------------------------
# Decomposer
# ---------------------------------------------------------------------------

class TaskDecomposer:
    """
    Converts a natural-language lighting goal into a TaskPlan.

    Jensen: "You're going to write ideas, architectures, specifications...
    help them define how to evaluate the definition of good versus bad."
    """

    def __init__(self, custom_rules: list[Rule] | None = None) -> None:
        self._rules: list[Rule] = list(_RULES)
        if custom_rules:
            self._rules = custom_rules + self._rules

    def decompose(self, goal: str, params: dict | None = None) -> TaskPlan:
        """
        Match goal against rules and return a TaskPlan.
        Falls back to a safe read-only inspection plan if no rule matches.
        """
        params = params or {}
        lower = goal.lower()

        for pattern, builder in self._rules:
            if re.search(pattern, lower):
                plan = builder(goal, params)
                return plan

        # Fallback: read-only discovery plan
        return TaskPlan(
            goal=goal,
            steps=[
                SubTask(
                    name="inspect_console",
                    agent_role="InspectionAgent",
                    description=f"No template matched '{goal}'. Gather console state to plan next steps.",
                    allowed_risk=RiskTier.SAFE_READ,
                    mcp_tools=[
                        "navigate_console", "list_console_destination",
                        "get_object_info", "query_object_list",
                    ],
                    eval_criteria="Console state returned without error",
                )
            ],
        )

    def register_rule(self, pattern: str, builder: Callable[[str, dict], TaskPlan]) -> None:
        """Add a domain-specific decomposition rule at the front of the chain."""
        self._rules.insert(0, (pattern, builder))

"""Tests for src/agent/workflows/ — workflow template step generation."""

from src.agent.state import GoalIntent, ParsedGoal
from src.agent.workflows.common import (
    build_discover_names_steps,
    build_label_step,
    build_verify_step,
)
from src.agent.workflows.patch import build_patch_workflow
from src.agent.workflows.playback import build_playback_workflow
from src.agent.workflows.preset import build_preset_workflow
from src.vocab import RiskTier


class TestCommonWorkflows:
    def test_build_label_step(self):
        step = build_label_step("group", 1, "Front Wash")
        assert step.tool_name == "label_or_appearance"
        assert step.risk_tier == RiskTier.DESTRUCTIVE
        assert step.tool_args["name"] == "Front Wash"
        assert step.tool_args["action"] == "label"

    def test_build_label_step_with_dependency(self):
        step = build_label_step("group", 1, "name", depends_on=["dep1"])
        assert step.depends_on == ["dep1"]

    def test_build_verify_step(self):
        step = build_verify_step(
            "query_object_list",
            "group exists",
            tool_args={"object_type": "group"},
        )
        assert step.risk_tier == RiskTier.SAFE_READ
        assert "Verify" in step.description
        assert step.tool_args["object_type"] == "group"

    def test_build_discover_names_steps(self):
        steps = build_discover_names_steps("Group")
        assert len(steps) == 1
        assert steps[0].tool_name == "discover_object_names"
        assert steps[0].risk_tier == RiskTier.SAFE_READ


class TestPatchWorkflow:
    def test_basic_patch(self):
        goal = ParsedGoal(
            raw="Patch 2 fixtures",
            intent=GoalIntent.PATCH,
            count=2,
            fixture_type="Generic Dimmer",
        )
        steps = build_patch_workflow(goal)
        # discover + import + 2 patch + verify = 5
        assert len(steps) == 5
        assert steps[0].tool_name == "list_fixture_types"
        assert steps[1].tool_name == "import_fixture_type"
        assert steps[2].tool_name == "patch_fixture"
        assert steps[3].tool_name == "patch_fixture"
        assert "Verify" in steps[4].description

    def test_patch_with_names(self):
        goal = ParsedGoal(
            raw="Patch fixtures",
            intent=GoalIntent.PATCH,
            count=2,
            names=["Wash L", "Wash R"],
        )
        steps = build_patch_workflow(goal)
        label_steps = [s for s in steps if s.tool_name == "label_or_appearance"]
        assert len(label_steps) == 2

    def test_patch_dependencies(self):
        goal = ParsedGoal(
            raw="Patch 1 fixture",
            intent=GoalIntent.PATCH,
            count=1,
        )
        steps = build_patch_workflow(goal)
        discover = steps[0]
        import_step = steps[1]
        patch = steps[2]
        # Import depends on discover
        assert discover.id in import_step.depends_on
        # Patch depends on import
        assert import_step.id in patch.depends_on

    def test_patch_custom_address(self):
        goal = ParsedGoal(
            raw="Patch at 2.100",
            intent=GoalIntent.PATCH,
            count=1,
            options={"universe": 2, "start_address": 100},
        )
        steps = build_patch_workflow(goal)
        patch = [s for s in steps if s.tool_name == "patch_fixture"][0]
        assert patch.tool_args["universe"] == 2
        assert patch.tool_args["address"] == 100


class TestPresetWorkflow:
    def test_basic_preset(self):
        goal = ParsedGoal(
            raw="Create color preset",
            intent=GoalIntent.PRESET,
            options={"preset_type": "color", "preset_id": 1, "group_id": 1},
        )
        steps = build_preset_workflow(goal)
        assert len(steps) >= 3  # select + store + verify
        assert steps[0].tool_name == "select_fixtures_by_group"

    def test_preset_with_values(self):
        goal = ParsedGoal(
            raw="Create color preset",
            intent=GoalIntent.PRESET,
            options={
                "preset_type": "color",
                "preset_id": 1,
                "group_id": 1,
                "values": {"COLORRGB1": 100, "COLORRGB2": 0},
            },
        )
        steps = build_preset_workflow(goal)
        attr_steps = [s for s in steps if s.tool_name == "set_attribute"]
        assert len(attr_steps) == 2

    def test_preset_with_label(self):
        goal = ParsedGoal(
            raw="Create preset",
            intent=GoalIntent.PRESET,
            names=["Red"],
            options={"preset_type": "color", "preset_id": 1},
        )
        steps = build_preset_workflow(goal)
        label_steps = [s for s in steps if s.tool_name == "label_or_appearance"]
        assert len(label_steps) == 1


class TestPlaybackWorkflow:
    def test_basic_playback(self):
        goal = ParsedGoal(
            raw="Assign executor",
            intent=GoalIntent.PLAYBACK,
            options={"sequence_id": 1, "executor_id": 201, "cue_count": 2},
        )
        steps = build_playback_workflow(goal)
        # discover + 2 store_cue + assign + verify = 5
        assert len(steps) == 5
        tool_names = [s.tool_name for s in steps]
        assert "query_object_list" in tool_names
        assert "store_current_cue" in tool_names
        assert "assign_object" in tool_names

    def test_playback_with_auto_go(self):
        goal = ParsedGoal(
            raw="Create and play",
            intent=GoalIntent.PLAYBACK,
            options={"sequence_id": 1, "executor_id": 1, "auto_go": True},
        )
        steps = build_playback_workflow(goal)
        go_steps = [s for s in steps if s.tool_name == "execute_sequence"]
        assert len(go_steps) == 1

    def test_playback_with_label(self):
        goal = ParsedGoal(
            raw="Assign executor",
            intent=GoalIntent.PLAYBACK,
            names=["Main Cue"],
            options={"sequence_id": 1, "executor_id": 1},
        )
        steps = build_playback_workflow(goal)
        label_steps = [s for s in steps if s.tool_name == "label_or_appearance"]
        assert len(label_steps) == 1

    def test_playback_dependencies(self):
        goal = ParsedGoal(
            raw="Assign executor",
            intent=GoalIntent.PLAYBACK,
            options={"sequence_id": 1, "executor_id": 1, "cue_count": 1},
        )
        steps = build_playback_workflow(goal)
        discover = steps[0]
        store_cue = steps[1]
        assign = steps[2]
        # Store cue depends on discover
        assert discover.id in store_cue.depends_on
        # Assign depends on store cue
        assert store_cue.id in assign.depends_on

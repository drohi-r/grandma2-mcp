"""Planner tests for the fixture-type intelligence intents and the
fixture-range extraction fix."""

from __future__ import annotations

from src.agent.planner import DomainPlanner
from src.agent.state import GoalIntent
from src.vocab import RiskTier


planner = DomainPlanner()


class TestIntentClassification:
    def test_preset_from_patch(self):
        for goal in (
            "create presets from my fixtures",
            "make presets for the patch",
            "build a preset library",
        ):
            parsed = planner.classify_goal(goal)
            assert parsed.intent == GoalIntent.PRESET_FROM_PATCH, goal

    def test_plugin_setup(self):
        for goal in (
            "set up the color picker",
            "run my preset plugin",
            "setup the colour picker layout",
        ):
            parsed = planner.classify_goal(goal)
            assert parsed.intent == GoalIntent.PLUGIN_SETUP, goal

    def test_id_hygiene(self):
        for goal in (
            "check my fixture numbering",
            "fix the fixture ids",
            "renumber the rig into blocks",
        ):
            parsed = planner.classify_goal(goal)
            assert parsed.intent == GoalIntent.ID_HYGIENE, goal

    def test_plain_preset_still_routes_to_preset(self):
        parsed = planner.classify_goal('store a color preset called "Deep Red"')
        assert parsed.intent == GoalIntent.PRESET

    def test_confidence_high_for_new_intents(self):
        assert planner.classify_goal("set up the color picker").confidence >= 0.9


class TestWorkflows:
    def test_preset_from_patch_plan_shape(self):
        parsed, steps = planner.plan_from_text("create presets from my fixtures")
        tools = [s.tool_name for s in steps]
        assert tools == [
            "analyze_patch_types",
            "verify_fixture_id_blocks",
            "create_presets_for_patch",
            "query_object_list",
        ]
        create = steps[2]
        assert create.risk_tier == RiskTier.DESTRUCTIVE
        assert create.tool_args["confirm_destructive"] is False
        assert create.tool_args["strategy"] == "full-coverage"

    def test_preset_strategy_extraction(self):
        _, steps = planner.plan_from_text("create a minimal preset library from the patch")
        assert steps[2].tool_args["strategy"] == "minimal-viable"

    def test_plugin_setup_plan(self):
        _, steps = planner.plan_from_text("set up the color picker")
        assert [s.tool_name for s in steps] == ["run_preset_plugin", "run_preset_plugin"]
        assert steps[0].tool_args["dry_run"] is True
        assert steps[0].risk_tier == RiskTier.SAFE_READ
        assert steps[1].tool_args["dry_run"] is False
        assert steps[1].risk_tier == RiskTier.DESTRUCTIVE
        assert steps[1].tool_args["plugin_name"] == "auto-layout-color-picker"

    def test_plugin_setup_named_plugin(self):
        _, steps = planner.plan_from_text('run the "MyPresetGen" plugin')
        assert steps[0].tool_args["plugin_name"] == "MyPresetGen"

    def test_id_hygiene_check_only(self):
        _, steps = planner.plan_from_text("check my fixture numbering")
        assert [s.tool_name for s in steps] == ["verify_fixture_id_blocks"]

    def test_id_hygiene_with_repair(self):
        _, steps = planner.plan_from_text("fix my fixture numbering")
        tools = [s.tool_name for s in steps]
        assert tools == ["verify_fixture_id_blocks", "renumber_fixtures"]
        # renumber_fixtures is plan-only (fixture IDs not assignable via
        # telnet, live-verified 2026-07-17) — the step must be SAFE_READ
        # and must not pass dry_run=False, which the tool now blocks.
        assert steps[1].risk_tier == RiskTier.SAFE_READ
        assert steps[1].tool_args == {}


class TestGroupRangeFix:
    def test_group_workflow_uses_fixture_range(self):
        _, steps = planner.plan_from_text('create group 5 from fixtures 20-30 called "Bars"')
        create = next(s for s in steps if s.tool_name == "create_fixture_group")
        assert create.tool_args["start"] == 20
        assert create.tool_args["end"] == 30

    def test_group_workflow_thru_syntax(self):
        parsed = planner.classify_goal("group fixtures 101 thru 112")
        assert parsed.options["fixture_start"] == 101
        assert parsed.options["fixture_end"] == 112

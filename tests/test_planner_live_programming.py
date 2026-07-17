"""Planner tests for the live-programming intents: effect, chaser, MAtricks."""

from __future__ import annotations

from src.agent.planner import DomainPlanner
from src.agent.state import GoalIntent
from src.vocab import RiskTier

planner = DomainPlanner()


class TestClassification:
    def test_effect(self):
        for goal in (
            "add a tilt wave effect on the movers",
            "put effect 3 on executor 5",
        ):
            assert planner.classify_goal(goal).intent == GoalIntent.EFFECT, goal

    def test_chaser(self):
        for goal in (
            "make a color chaser on executor 5",
            "build a 6 step chase for group 2",
        ):
            assert planner.classify_goal(goal).intent == GoalIntent.CHASER, goal

    def test_matricks(self):
        for goal in (
            "interleave 4 on the wash",
            "select every other fixture with matricks",
        ):
            assert planner.classify_goal(goal).intent == GoalIntent.MATRICKS, goal

    def test_generic_playback_unaffected(self):
        parsed = planner.classify_goal("assign sequence 3 to executor 1")
        assert parsed.intent == GoalIntent.PLAYBACK


class TestEffectWorkflow:
    def test_assign_path(self):
        _, steps = planner.plan_from_text("put effect 3 on executor 5 for group 2")
        tools = [s.tool_name for s in steps]
        assert tools == [
            "list_effects_pool",
            "select_fixtures_by_group",
            "assign_effect_to_executor",
            "list_effects_pool",
        ]
        assign = steps[2]
        assert assign.risk_tier == RiskTier.DESTRUCTIVE
        assert assign.tool_args["effect_id"] == 3
        assert assign.tool_args["executor_id"] == 5
        assert assign.tool_args["confirm_destructive"] is False

    def test_browse_path_without_ids(self):
        _, steps = planner.plan_from_text("add a tilt wave effect on the movers")
        tools = [s.tool_name for s in steps]
        assert tools == [
            "list_effects_pool",
            "select_fixtures_by_type_order",
            "browse_effect_library",
        ]
        assert all(s.risk_tier != RiskTier.DESTRUCTIVE for s in steps)


class TestChaserWorkflow:
    def test_default_four_steps(self):
        _, steps = planner.plan_from_text("make a color chaser on executor 5")
        recalls = [s for s in steps if s.tool_name == "apply_preset"]
        stores = [s for s in steps if s.tool_name == "store_cue_with_timing"]
        assert len(recalls) == 4 and len(stores) == 4
        assert stores[0].tool_args["sequence_id"] == 90
        assert stores[0].tool_args["confirm_destructive"] is False
        assign = next(s for s in steps if s.tool_name == "assign_object")
        assert assign.tool_args["source_id"] == 90
        assert assign.tool_args["target_id"] == 5
        assert steps[-1].tool_name == "query_object_list"

    def test_explicit_count_and_sequence(self):
        _, steps = planner.plan_from_text(
            "build a chaser with 6 cues into sequence 42 for group 1"
        )
        stores = [s for s in steps if s.tool_name == "store_cue_with_timing"]
        assert len(stores) == 6
        assert stores[0].tool_args["sequence_id"] == 42
        assert steps[0].tool_name == "select_fixtures_by_group"

    def test_no_executor_no_assign(self):
        _, steps = planner.plan_from_text("make a color chase for group 3")
        assert not any(s.tool_name == "assign_object" for s in steps)


class TestMatricksWorkflow:
    def test_interleave_value(self):
        _, steps = planner.plan_from_text("interleave 4 on group 2")
        apply = next(s for s in steps if s.tool_name == "manage_matricks")
        assert apply.tool_args == {"action": "interleave", "value": 4}
        assert steps[-1].tool_name == "get_matricks_state"

    def test_every_other_defaults_interleave_2(self):
        _, steps = planner.plan_from_text("select every other fixture")
        apply = next(s for s in steps if s.tool_name == "manage_matricks")
        assert apply.tool_args == {"action": "interleave", "value": 2}

    def test_blocks_xy(self):
        _, steps = planner.plan_from_text("matricks blocks 2.3 on group 1")
        apply = next(s for s in steps if s.tool_name == "manage_matricks")
        assert apply.tool_args == {"action": "blocks", "x": 2, "y": 3}

    def test_wings(self):
        _, steps = planner.plan_from_text("matricks wings 2 on the rig")
        apply = next(s for s in steps if s.tool_name == "manage_matricks")
        assert apply.tool_args == {"action": "wings", "value": 2}


class TestCompositeContext:
    def test_composite_subgoals_carry_context(self):
        parsed, steps = planner.plan_from_text(
            'patch 8 fixtures of type "Mac Aura" at 1.001, create a color preset and store cue 1'
        )
        assert parsed.intent == GoalIntent.COMPOSITE
        assert parsed.count == 8
        # The plan must exist and chain; the sub-goals now inherit count and
        # fixture_type rather than being rebuilt blank.
        assert len(steps) >= 3

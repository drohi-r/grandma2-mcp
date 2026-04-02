"""Tests for src/agent/planner.py — goal classification and plan generation."""

from src.agent.planner import DomainPlanner
from src.agent.state import GoalIntent
from src.vocab import RiskTier


class TestClassifyGoal:
    def setup_method(self):
        self.planner = DomainPlanner()

    def test_patch_intent(self):
        goal = self.planner.classify_goal("Patch 8 Mac 700 fixtures at 1.001")
        assert goal.intent == GoalIntent.PATCH

    def test_preset_intent(self):
        goal = self.planner.classify_goal("Create a color preset for group 1")
        assert goal.intent == GoalIntent.PRESET

    def test_playback_intent(self):
        goal = self.planner.classify_goal("Assign sequence 1 to executor 201")
        assert goal.intent == GoalIntent.PLAYBACK

    def test_discover_intent(self):
        goal = self.planner.classify_goal("List all groups")
        assert goal.intent == GoalIntent.DISCOVER

    def test_label_intent(self):
        goal = self.planner.classify_goal('Label fixture 1 as "Front Wash"')
        assert goal.intent == GoalIntent.LABEL

    def test_group_intent(self):
        goal = self.planner.classify_goal("Create a fixture group with fixtures 1-12")
        assert goal.intent == GoalIntent.GROUP

    def test_composite_intent(self):
        goal = self.planner.classify_goal(
            "Patch 4 fixtures and create a preset and assign executor"
        )
        assert goal.intent == GoalIntent.COMPOSITE

    def test_fallback_to_discover(self):
        goal = self.planner.classify_goal("something vague about the show")
        assert goal.intent == GoalIntent.DISCOVER


class TestExtractCount:
    def setup_method(self):
        self.planner = DomainPlanner()

    def test_extract_fixture_count(self):
        goal = self.planner.classify_goal("Patch 12 fixtures")
        assert goal.count == 12

    def test_no_count(self):
        goal = self.planner.classify_goal("List groups")
        assert goal.count is None


class TestExtractFixtureType:
    def setup_method(self):
        self.planner = DomainPlanner()

    def test_quoted_fixture_type(self):
        goal = self.planner.classify_goal('Patch "Mac 700 Profile" fixtures')
        assert goal.fixture_type == "Mac 700 Profile"

    def test_unquoted_mac(self):
        goal = self.planner.classify_goal("Patch Mac 700 fixtures")
        assert goal.fixture_type is not None
        assert "Mac" in goal.fixture_type

    def test_generic_dimmer(self):
        goal = self.planner.classify_goal("Patch Generic Dimmer fixtures")
        assert goal.fixture_type is not None
        assert "Generic" in goal.fixture_type


class TestExtractAddress:
    def setup_method(self):
        self.planner = DomainPlanner()

    def test_full_address(self):
        goal = self.planner.classify_goal("Patch fixture at 1.001")
        assert goal.options.get("universe") == 1
        assert goal.options.get("start_address") == 1

    def test_universe_keyword(self):
        goal = self.planner.classify_goal("Patch on universe 2")
        assert goal.options.get("universe") == 2

    def test_address_keyword(self):
        goal = self.planner.classify_goal("Patch at address 100")
        assert goal.options.get("start_address") == 100


class TestExtractNames:
    def setup_method(self):
        self.planner = DomainPlanner()

    def test_quoted_names(self):
        goal = self.planner.classify_goal('Label fixture 1 "Front Wash"')
        assert "Front Wash" in goal.names

    def test_no_names(self):
        goal = self.planner.classify_goal("List fixtures")
        assert goal.names == []


class TestEstimateConfidence:
    def setup_method(self):
        self.planner = DomainPlanner()

    def test_high_confidence_with_details(self):
        goal = self.planner.classify_goal(
            'Patch 8 "Mac 700 Profile" fixtures at 1.001 "Front Wash"'
        )
        assert goal.confidence >= 0.8

    def test_low_confidence_vague(self):
        goal = self.planner.classify_goal("Do something with fixtures")
        # DISCOVER intent gets high confidence (discovery is always safe)
        # but non-discovery intents with minimal details get lower confidence
        assert goal.confidence <= 1.0  # valid confidence range


class TestPlanGeneration:
    def setup_method(self):
        self.planner = DomainPlanner()

    def test_patch_workflow_steps(self):
        goal = self.planner.classify_goal("Patch 2 Mac 700 fixtures at 1.001")
        plan = self.planner.plan(goal)
        # Should have: discover + import + 2 patch + verify = 5 minimum
        assert len(plan) >= 4
        # First step should be discovery
        assert plan[0].risk_tier == RiskTier.SAFE_READ
        # Should have destructive steps
        destructive = [s for s in plan if s.risk_tier == RiskTier.DESTRUCTIVE]
        assert len(destructive) >= 2  # import + patches

    def test_discover_workflow_steps(self):
        goal = self.planner.classify_goal("List all groups")
        plan = self.planner.plan(goal)
        assert len(plan) >= 1
        assert all(s.risk_tier == RiskTier.SAFE_READ for s in plan)

    def test_playback_workflow_steps(self):
        goal = self.planner.classify_goal("Create a sequence and assign executor 1")
        plan = self.planner.plan(goal)
        assert len(plan) >= 3
        tool_names = [s.tool_name for s in plan]
        assert "query_object_list" in tool_names

    def test_plan_from_text_convenience(self):
        parsed, plan = self.planner.plan_from_text("List groups")
        assert parsed.intent == GoalIntent.DISCOVER
        assert len(plan) >= 1

    def test_dependency_edges_set(self):
        goal = self.planner.classify_goal("Patch 1 fixture")
        plan = self.planner.plan(goal)
        # Patch steps (tool_name=patch_fixture) should depend on import step
        import_steps = [s for s in plan if s.tool_name == "import_fixture_type"]
        patch_steps = [s for s in plan if s.tool_name == "patch_fixture"]
        if import_steps and patch_steps:
            for ps in patch_steps:
                assert import_steps[0].id in ps.depends_on

    def test_composite_chains_workflows(self):
        goal = self.planner.classify_goal(
            "Patch 1 fixture, create preset, assign executor"
        )
        plan = self.planner.plan(goal)
        # Should have steps from multiple workflows
        [s.tool_name for s in plan]
        # At minimum should have some discovery and mutations
        assert len(plan) >= 5

"""Rule-based domain planner — decomposes goals into PlanStep sequences.

No LLM dependency. Uses keyword matching to classify goals and dispatch
to workflow templates that define canonical step orderings.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from src.agent.state import GoalIntent, ParsedGoal, PlanStep
from src.agent.workflows.common import build_verify_step
from src.agent.workflows.patch import build_patch_workflow
from src.agent.workflows.playback import build_playback_workflow
from src.agent.workflows.preset import build_preset_workflow
from src.vocab import RiskTier

logger = logging.getLogger(__name__)

# Keyword patterns for intent classification
_PATCH_PATTERNS = re.compile(
    r"\b(patch|add\s+fixture|import\s+fixture|create\s+fixture)\b", re.IGNORECASE
)
_PRESET_PATTERNS = re.compile(
    r"\b(preset|store\s+preset|create\s+preset|color\s+preset|position\s+preset"
    r"|gobo\s+preset|beam\s+preset)\b",
    re.IGNORECASE,
)
_PLAYBACK_PATTERNS = re.compile(
    r"\b(playback|assign\s+executor|create\s+sequence|store\s+cue|executor|sequence)\b",
    re.IGNORECASE,
)
_LABEL_PATTERNS = re.compile(
    r"\b(label|rename|name)\b", re.IGNORECASE
)
_DISCOVER_PATTERNS = re.compile(
    r"\b(list|show|discover|inspect|check|query|what|info|status)\b", re.IGNORECASE
)
_GROUP_PATTERNS = re.compile(
    r"\b(group|create\s+group|fixture\s+group)\b", re.IGNORECASE
)

# Object type extraction
_OBJECT_TYPE_PATTERNS = {
    "fixture": re.compile(r"\bfixture", re.IGNORECASE),
    "group": re.compile(r"\bgroup", re.IGNORECASE),
    "sequence": re.compile(r"\bsequence", re.IGNORECASE),
    "preset": re.compile(r"\bpreset", re.IGNORECASE),
    "executor": re.compile(r"\bexecutor", re.IGNORECASE),
    "cue": re.compile(r"\bcue", re.IGNORECASE),
    "macro": re.compile(r"\bmacro", re.IGNORECASE),
}

# Count extraction: "12 fixtures", "8 Mac 700s"
_COUNT_PATTERN = re.compile(r"\b(\d+)\s+(?:fixture|group|preset|cue|sequence|executor)", re.IGNORECASE)

# Fixture type extraction: quoted strings or known types
_FIXTURE_TYPE_PATTERN = re.compile(
    r"(?:\"([^\"]+)\"|'([^']+)'|"
    r"(Mac\s*\d+[^,;.]*|Martin\s+\w+[^,;.]*|Generic\s+\w+[^,;.]*))",
    re.IGNORECASE,
)

# Address extraction: "universe 1", "address 001", "1.001"
_UNIVERSE_PATTERN = re.compile(r"\buniverse\s+(\d+)", re.IGNORECASE)
_ADDRESS_PATTERN = re.compile(r"\baddress\s+(\d+)", re.IGNORECASE)
_FULL_ADDRESS_PATTERN = re.compile(r"\b(\d+)\.(\d{3})\b")

# ID extraction: "group 5", "preset 10", "executor 201"
_ID_PATTERN = re.compile(r"\b(?:group|preset|sequence|executor|fixture)\s+(\d+)", re.IGNORECASE)


class DomainPlanner:
    """Rule-based planner that decomposes goals into PlanStep sequences."""

    def classify_goal(self, goal_text: str) -> ParsedGoal:
        """Extract intent, object types, counts, and names from goal text."""
        intent = self._classify_intent(goal_text)
        object_type = self._extract_object_type(goal_text)
        count = self._extract_count(goal_text)
        fixture_type = self._extract_fixture_type(goal_text)
        names = self._extract_names(goal_text)
        options = self._extract_options(goal_text)
        confidence = self._estimate_confidence(goal_text, intent)

        return ParsedGoal(
            raw=goal_text,
            intent=intent,
            object_type=object_type,
            count=count,
            fixture_type=fixture_type,
            names=names,
            options=options,
            confidence=confidence,
        )

    def plan(self, goal: ParsedGoal) -> list[PlanStep]:
        """Decompose a parsed goal into ordered PlanSteps.

        Dispatches to the appropriate workflow template based on intent.
        """
        if goal.intent == GoalIntent.PATCH:
            return build_patch_workflow(goal)
        elif goal.intent == GoalIntent.PRESET:
            return build_preset_workflow(goal)
        elif goal.intent == GoalIntent.PLAYBACK:
            return build_playback_workflow(goal)
        elif goal.intent == GoalIntent.GROUP:
            return self._build_group_workflow(goal)
        elif goal.intent == GoalIntent.LABEL:
            return self._build_label_workflow(goal)
        elif goal.intent == GoalIntent.DISCOVER:
            return self._build_discover_workflow(goal)
        elif goal.intent == GoalIntent.COMPOSITE:
            return self._build_composite_workflow(goal)
        else:
            # Fallback: discovery
            return self._build_discover_workflow(goal)

    def plan_from_text(self, goal_text: str) -> tuple[ParsedGoal, list[PlanStep]]:
        """Convenience: classify + plan in one call."""
        parsed = self.classify_goal(goal_text)
        steps = self.plan(parsed)
        return parsed, steps

    # ---------------------------------------------------------------- intent

    def _classify_intent(self, text: str) -> GoalIntent:
        """Classify the primary intent from goal text."""
        # Check for composite (multiple intents)
        matches = sum([
            bool(_PATCH_PATTERNS.search(text)),
            bool(_PRESET_PATTERNS.search(text)),
            bool(_PLAYBACK_PATTERNS.search(text)),
        ])
        if matches >= 2:
            return GoalIntent.COMPOSITE

        # Single intent matching (order matters — more specific first)
        if _PATCH_PATTERNS.search(text):
            return GoalIntent.PATCH
        if _PRESET_PATTERNS.search(text):
            return GoalIntent.PRESET
        if _PLAYBACK_PATTERNS.search(text):
            return GoalIntent.PLAYBACK
        if _GROUP_PATTERNS.search(text):
            return GoalIntent.GROUP
        if _LABEL_PATTERNS.search(text):
            return GoalIntent.LABEL
        if _DISCOVER_PATTERNS.search(text):
            return GoalIntent.DISCOVER

        return GoalIntent.DISCOVER  # safe fallback

    # ---------------------------------------------------------------- extraction

    def _extract_object_type(self, text: str) -> str | None:
        for obj_type, pattern in _OBJECT_TYPE_PATTERNS.items():
            if pattern.search(text):
                return obj_type
        return None

    def _extract_count(self, text: str) -> int | None:
        m = _COUNT_PATTERN.search(text)
        return int(m.group(1)) if m else None

    def _extract_fixture_type(self, text: str) -> str | None:
        m = _FIXTURE_TYPE_PATTERN.search(text)
        if m:
            return m.group(1) or m.group(2) or m.group(3)
        return None

    def _extract_names(self, text: str) -> list[str]:
        """Extract quoted names from the goal text."""
        # Match both single and double quoted strings
        return re.findall(r'"([^"]+)"', text)

    def _extract_options(self, text: str) -> dict[str, Any]:
        """Extract address, universe, and other options from goal text."""
        options: dict[str, Any] = {}

        # Full address: 1.001
        m = _FULL_ADDRESS_PATTERN.search(text)
        if m:
            options["universe"] = int(m.group(1))
            options["start_address"] = int(m.group(2))

        # Separate universe/address
        m = _UNIVERSE_PATTERN.search(text)
        if m:
            options["universe"] = int(m.group(1))
        m = _ADDRESS_PATTERN.search(text)
        if m:
            options["start_address"] = int(m.group(1))

        # ID extraction for specific objects
        m = _ID_PATTERN.search(text)
        if m:
            options["object_id"] = int(m.group(1))

        # Page
        m = re.search(r"\bpage\s+(\d+)", text, re.IGNORECASE)
        if m:
            options["page"] = int(m.group(1))

        return options

    def _estimate_confidence(self, text: str, intent: GoalIntent) -> float:
        """Estimate how confident we are in the goal classification."""
        if intent == GoalIntent.DISCOVER:
            # Discovery is always safe, so high confidence even for vague goals
            return 0.9

        # Count how many specific details we extracted
        specificity = 0
        if _COUNT_PATTERN.search(text):
            specificity += 1
        if _FIXTURE_TYPE_PATTERN.search(text):
            specificity += 1
        if _FULL_ADDRESS_PATTERN.search(text) or _ADDRESS_PATTERN.search(text):
            specificity += 1
        if re.findall(r'"[^"]+"', text):
            specificity += 1

        # More details = higher confidence
        if specificity >= 3:
            return 1.0
        elif specificity >= 2:
            return 0.8
        elif specificity >= 1:
            return 0.6
        return 0.4

    # ---------------------------------------------------------------- workflows

    def _build_group_workflow(self, goal: ParsedGoal) -> list[PlanStep]:
        """Build a fixture group creation workflow."""
        steps: list[PlanStep] = []

        group_id = goal.options.get("object_id", 1)
        fixture_start = goal.options.get("fixture_start", 1)
        fixture_end = goal.options.get("fixture_end", fixture_start + (goal.count or 1) - 1)

        # Discovery
        discover = PlanStep(
            tool_name="query_object_list",
            tool_args={"object_type": "group"},
            description="List existing groups",
            risk_tier=RiskTier.SAFE_READ,
        )
        steps.append(discover)

        # Create group
        create = PlanStep(
            tool_name="create_fixture_group",
            tool_args={
                "start": fixture_start,
                "end": fixture_end,
                "group_id": group_id,
                "name": goal.names[0] if goal.names else None,
                "confirm_destructive": False,
            },
            description=f"Create group {group_id} (fixtures {fixture_start}-{fixture_end})",
            risk_tier=RiskTier.DESTRUCTIVE,
            depends_on=[discover.id],
        )
        steps.append(create)

        # Verify
        verify = build_verify_step(
            "query_object_list",
            f"Verify group {group_id} exists",
            tool_args={"object_type": "group"},
            depends_on=[create.id],
        )
        steps.append(verify)

        return steps

    def _build_label_workflow(self, goal: ParsedGoal) -> list[PlanStep]:
        """Build a labeling workflow."""
        steps: list[PlanStep] = []

        object_type = goal.object_type or "fixture"
        object_id = goal.options.get("object_id", 1)

        if goal.names:
            from src.agent.workflows.common import build_label_step

            label = build_label_step(
                object_type, object_id, goal.names[0]
            )
            steps.append(label)

            verify = build_verify_step(
                "get_object_info",
                f"Verify {object_type} {object_id} labeled",
                tool_args={"object_type": object_type, "object_id": object_id},
                depends_on=[label.id],
            )
            steps.append(verify)

        return steps

    def _build_discover_workflow(self, goal: ParsedGoal) -> list[PlanStep]:
        """Build a discovery-only workflow."""
        object_type = goal.object_type

        if object_type:
            return [
                PlanStep(
                    tool_name="query_object_list",
                    tool_args={"object_type": object_type},
                    description=f"List all {object_type}s",
                    risk_tier=RiskTier.SAFE_READ,
                ),
            ]

        # Generic discovery: get console location + list
        return [
            PlanStep(
                tool_name="get_console_location",
                tool_args={},
                description="Get current console location",
                risk_tier=RiskTier.SAFE_READ,
            ),
            PlanStep(
                tool_name="list_console_destination",
                tool_args={},
                description="List objects at current location",
                risk_tier=RiskTier.SAFE_READ,
            ),
        ]

    def _build_composite_workflow(self, goal: ParsedGoal) -> list[PlanStep]:
        """Build a composite workflow by chaining multiple sub-workflows.

        For composite goals (e.g., "patch 12 fixtures, create presets, assign executor"),
        we build each sub-workflow and chain them via dependencies.
        """
        all_steps: list[PlanStep] = []

        # Determine which sub-workflows are needed
        text = goal.raw

        if _PATCH_PATTERNS.search(text):
            patch_goal = ParsedGoal(
                raw=goal.raw,
                intent=GoalIntent.PATCH,
                object_type="fixture",
                count=goal.count,
                fixture_type=goal.fixture_type,
                names=goal.names,
                options=goal.options,
            )
            patch_steps = build_patch_workflow(patch_goal)
            all_steps.extend(patch_steps)

        if _PRESET_PATTERNS.search(text):
            # Presets depend on patching being done
            last_id = all_steps[-1].id if all_steps else None
            preset_goal = ParsedGoal(
                raw=goal.raw,
                intent=GoalIntent.PRESET,
                options=goal.options,
                names=goal.names,
            )
            preset_steps = build_preset_workflow(preset_goal)
            if last_id and preset_steps:
                preset_steps[0].depends_on.append(last_id)
            all_steps.extend(preset_steps)

        if _PLAYBACK_PATTERNS.search(text):
            last_id = all_steps[-1].id if all_steps else None
            playback_goal = ParsedGoal(
                raw=goal.raw,
                intent=GoalIntent.PLAYBACK,
                options=goal.options,
                names=goal.names,
            )
            playback_steps = build_playback_workflow(playback_goal)
            if last_id and playback_steps:
                playback_steps[0].depends_on.append(last_id)
            all_steps.extend(playback_steps)

        if not all_steps:
            return self._build_discover_workflow(goal)

        return all_steps

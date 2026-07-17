"""Agent runtime — top-level orchestrator wiring planner, executor, policy, and memory.

This is the entry point for the agent harness. It accepts a high-level goal,
generates a plan, validates it, executes steps, and produces a trace.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from src.agent.executor import ConfirmCallback, PreflightCallback, StepExecutor
from src.agent.memory import WorkflowMemory
from src.agent.planner import DomainPlanner
from src.agent.policy import PolicyEngine
from src.agent.state import ParsedGoal, PlanStep, RunContext, RunStatus
from src.agent.trace import ExecutionTrace, build_trace
from src.agent.verification import Verifier
from src.vocab import RiskTier

logger = logging.getLogger(__name__)


def _recipe_key(goal: str) -> str:
    """Normalize a goal string into a recipe lookup key."""
    return " ".join(goal.lower().split())


class AgentRuntime:
    """Top-level agent harness that turns goals into executed plans."""

    def __init__(
        self,
        tool_registry: dict[str, Callable[..., Awaitable[str]]],
        *,
        memory_db_path: str | None = None,
        batch_limit: int = 10,
        max_retries: int = 2,
        preflight: PreflightCallback | None = None,
    ):
        self.planner = DomainPlanner()
        self.policy = PolicyEngine(batch_limit=batch_limit)
        self.verifier = Verifier(tool_dispatch=tool_registry)
        self._tool_registry = tool_registry
        self._baseline_showfile: str | None = None
        self.executor = StepExecutor(
            tool_registry=tool_registry,
            policy=self.policy,
            verifier=self.verifier,
            max_retries=max_retries,
            preflight=preflight or self._showfile_preflight,
        )
        if memory_db_path:
            self.memory = WorkflowMemory(db_path=memory_db_path)
        else:
            self.memory = WorkflowMemory()

    async def run(
        self,
        goal: str,
        on_confirm: ConfirmCallback | None = None,
    ) -> ExecutionTrace:
        """Full agent loop: goal -> plan -> validate -> execute -> trace.

        Args:
            goal: High-level natural language goal.
            on_confirm: Async callback for destructive step confirmation.
                Receives a PlanStep, returns True to proceed or False to abort.

        Returns:
            ExecutionTrace with the complete run record.
        """
        started_at = datetime.now(UTC)

        # 1. Parse goal
        parsed_goal = self.planner.classify_goal(goal)
        logger.info(
            "Goal classified: intent=%s, object_type=%s, confidence=%.2f",
            parsed_goal.intent.value,
            parsed_goal.object_type,
            parsed_goal.confidence,
        )

        # 2. Recipe reuse: an identical goal that previously completed replays
        #    its proven plan (statuses reset, destructive confirms re-gated)
        #    instead of being re-planned from scratch.
        plan: list[PlanStep] | None = None
        recipe_used = False
        recipe_key = _recipe_key(goal)
        try:
            recipes = self.memory.recall_recipe(name=recipe_key)
            if recipes:
                plan = self._rebuild_plan_from_recipe(recipes[0])
                if plan:
                    recipe_used = True
                    self.memory.increment_recipe_usage(recipe_key)
                    logger.info(
                        "Reusing recipe %r (%d steps, use_count=%s)",
                        recipe_key, len(plan), recipes[0].get("use_count"),
                    )
        except Exception as e:
            logger.debug("Recipe lookup failed: %s", e)

        # 3. Generate plan (fresh, unless a recipe was replayed)
        if plan is None:
            plan = self.planner.plan(parsed_goal)
        logger.info("Plan generated: %d steps", len(plan))

        # 4. Validate plan via policy engine
        policy_result = self.policy.validate_plan(plan, confidence=parsed_goal.confidence)
        policy_warnings = policy_result.warnings

        if not policy_result.approved:
            # Plan rejected by policy
            context = RunContext(goal=goal, plan=plan, status=RunStatus.ABORTED)
            violation_msgs = [v.message for v in policy_result.violations]
            logger.warning("Plan rejected by policy: %s", violation_msgs)
            trace = build_trace(context, started_at, policy_warnings=violation_msgs)
            return trace

        # Inject any policy-added steps (verification, discovery)
        if policy_result.injected_steps:
            plan = policy_result.injected_steps + plan

        # 5. Create run context; baseline the showfile for the divergence guard
        context = RunContext(goal=goal, plan=plan)
        self._baseline_showfile = await self._read_showfile()
        logger.info("Run %s started: %s", context.run_id, goal)

        # 6. Execute
        context = await self.executor.execute_plan(context, on_confirm=on_confirm)

        # 7. Build trace
        trace = build_trace(context, started_at, policy_warnings=policy_warnings)

        # 8. Recipe capture: a fully successful fresh plan becomes the recipe
        #    for this exact goal (destructive confirms sanitized back to False)
        if not recipe_used and trace.result == "success":
            try:
                self.memory.store_recipe(
                    name=recipe_key,
                    steps=self._sanitize_plan_for_recipe(context.plan),
                    tags=[parsed_goal.intent.value]
                    + ([parsed_goal.object_type] if parsed_goal.object_type else []),
                )
                logger.info("Stored recipe %r from successful run", recipe_key)
            except Exception as e:
                logger.warning("Failed to store recipe: %s", e)

        # 8b. Store run summary in memory
        try:
            self.memory.record_run_summary(
                run_id=trace.run_id,
                goal=trace.goal,
                result=trace.result,
                trace_json=trace.to_json(),
            )
        except Exception as e:
            logger.warning("Failed to store run in memory: %s", e)

        # 9. Save trace to file
        try:
            trace.to_file()
        except Exception as e:
            logger.warning("Failed to write trace file: %s", e)

        logger.info(
            "Run %s completed: result=%s, steps=%d, duration=%dms",
            trace.run_id,
            trace.result,
            len(trace.steps),
            trace.total_duration_ms,
        )

        return trace

    async def plan_only(self, goal: str) -> tuple[ParsedGoal, list[PlanStep], list[str]]:
        """Generate and validate a plan without executing it.

        Returns:
            (parsed_goal, plan_steps, policy_warnings)
        """
        parsed_goal = self.planner.classify_goal(goal)
        plan = self.planner.plan(parsed_goal)
        policy_result = self.policy.validate_plan(plan, confidence=parsed_goal.confidence)
        return parsed_goal, plan, policy_result.warnings

    # ── Console divergence guard ─────────────────────────────────────

    async def _read_showfile(self) -> str | None:
        """Read $SHOWFILE via the tool registry; None when unavailable."""
        fn = self._tool_registry.get("list_system_variables")
        if fn is None:
            return None
        try:
            data = json.loads(await fn(filter_prefix="SHOWFILE"))
            return data.get("variables", {}).get("$SHOWFILE")
        except Exception as e:  # noqa: BLE001 — guard must not crash the run
            logger.debug("Showfile read failed: %s", e)
            return None

    async def _showfile_preflight(self, step: PlanStep) -> str | None:
        """Default pre-destructive guard: abort when the showfile changed
        since the run started (operator loaded another show mid-run)."""
        if self._baseline_showfile is None:
            return None
        current = await self._read_showfile()
        if current is not None and current != self._baseline_showfile:
            return (
                f"showfile changed since run start "
                f"({self._baseline_showfile!r} -> {current!r}) — console state "
                f"diverged; re-run the goal against the new show"
            )
        return None

    # ── Recipe replay helpers ────────────────────────────────────────

    def _rebuild_plan_from_recipe(self, recipe: dict[str, Any]) -> list[PlanStep] | None:
        """Rebuild executable PlanSteps from stored recipe step dicts."""
        steps: list[PlanStep] = []
        try:
            for d in recipe["steps"]:
                steps.append(PlanStep(
                    tool_name=d["tool_name"],
                    tool_args=dict(d["tool_args"]),
                    description=d.get("description", ""),
                    risk_tier=RiskTier(d["risk_tier"]),
                    id=d["id"],
                    depends_on=list(d.get("depends_on", [])),
                ))
        except (KeyError, TypeError, ValueError) as e:
            logger.warning("Recipe %r not replayable: %s", recipe.get("name"), e)
            return None
        return steps or None

    @staticmethod
    def _sanitize_plan_for_recipe(plan: list[PlanStep]) -> list[dict[str, Any]]:
        """Serialize a plan for recipe storage: strip run-state, re-gate
        destructive confirms (execution injects confirm_destructive=True —
        a stored recipe must never replay that automatically)."""
        out: list[dict[str, Any]] = []
        for step in plan:
            d = step.to_dict()
            for volatile in ("status", "result", "error", "started_at",
                             "completed_at", "verification", "retry_count"):
                d.pop(volatile, None)
            if "confirm_destructive" in d["tool_args"]:
                d["tool_args"] = {**d["tool_args"], "confirm_destructive": False}
            out.append(d)
        return out

    def _find_matching_recipe(self, goal: ParsedGoal) -> dict[str, Any] | None:
        """Check workflow memory for a matching recipe."""
        try:
            # Search by intent tag
            recipes = self.memory.recall_recipe(tags=[goal.intent.value])
            if recipes:
                return recipes[0]

            # Search by object type tag
            if goal.object_type:
                recipes = self.memory.recall_recipe(tags=[goal.object_type])
                if recipes:
                    return recipes[0]
        except Exception as e:
            logger.debug("Recipe search failed: %s", e)

        return None

"""
orchestrator.py — Multi-agent orchestrator for MA2 MCP.

Jensen: "Agents working with other agents. Some of the agents are very large models.
Some of them are smaller models... we have policies that give these agents
two of the three things but not all three things at the same time."

v2: Hydrates ConsoleStateSnapshot before the first sub-agent runs,
closing all 19 show-memory gaps identified from the cd-tree analysis.
Every sub-agent now starts with ground truth — no mid-task blind spots.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from src.context import _current_session_id

from .agent_memory import LongTermMemory, WorkingMemory
from .console_state import ConsoleStateHydrator, ConsoleStateSnapshot, parse_showfile_from_listvar
from .rights import (
    FeedbackClass,
    MA2Right,
    RightsContext,
    is_permitted,
    min_right_for_tool,
    parse_telnet_feedback,
)
from .task_decomposer import RiskTier, SubTask, TaskDecomposer, TaskPlan

logger = logging.getLogger(__name__)

ToolCaller = Callable[[str, dict], Awaitable[Any]]
TelnetSend = Callable[[str], Awaitable[str]]

# Tools that write to the programmer — Blind mode warning applies to these
_STORE_TOOLS: frozenset[str] = frozenset({
    "store_current_cue", "store_new_preset",
    "store_cue_with_timing", "update_cue_data",
})


# ---------------------------------------------------------------------------
# Step result
# ---------------------------------------------------------------------------

@dataclass
class StepResult:
    step_name: str
    success: bool
    output: Any = None
    error: str = ""
    tokens_used: int = 0
    eval_passed: bool | None = None
    eval_notes: str = ""
    # Rights / feedback classification — from validation patch
    feedback_class: FeedbackClass = FeedbackClass.INCONCLUSIVE
    rights_level: str = ""


# ---------------------------------------------------------------------------
# Pre-flight guard — checks snapshot before DESTRUCTIVE steps
# ---------------------------------------------------------------------------

def _preflight_guard(step: SubTask, wm: WorkingMemory) -> str | None:
    """
    Returns an error string if the step should be blocked, else None.

    Checks in order:
      1. MA2 native rights level — FAILED_CLOSED prevention
         Does the active user's rights permit this tool at all?
         Blocks before even reaching the MCP safety gate.

      2. DESTRUCTIVE gate — requires confirmed=True
         Second gate: explicit human approval for data-mutating ops.

      3. Snapshot staleness — DESTRUCTIVE ops need fresh state
         If snapshot is >60s old before a destructive step, block.

      4. Blind mode guard — store ops in blind go to blind programmer
         Warning only (logged), not a hard block.

      5. Park state — at commands against parked fixtures silently no-op
         Warning only (logged), not a hard block.
    """
    rc = wm.rights_context
    tool = step.mcp_tools[0] if step.mcp_tools else None

    # ── Check 1: MA2 rights level ────────────────────────────────────
    # This is the new layer from the rights patch.
    # Prevents FAILED_CLOSED: user lacks rights, MCP gate would pass it,
    # console rejects silently with Error #72.
    # Only enforce when we have a real rights level (not default NONE
    # which means "not yet hydrated" — don't block on unknown state)
    if tool and rc.user_right != MA2Right.NONE and not is_permitted(tool, rc.user_right):
        min_r = min_right_for_tool(tool)
        return (
            f"[FAILED_CLOSED] Rights check failed for step '{step.name}': "
            f"user '{rc.username}' has rights={rc.user_right.value}, "
            f"tool '{tool}' requires {min_r.value} or above. "
            f"Aborting before console would reject with Error #72."
        )

    # ── Check 2: DESTRUCTIVE gate ────────────────────────────────────
    if step.allowed_risk == RiskTier.DESTRUCTIVE and not step.confirmed:
        return (
            f"Step '{step.name}' is DESTRUCTIVE and confirm=False. "
            f"Set step.confirmed=True after human approval."
        )

    # ── Check 3: Snapshot staleness ──────────────────────────────────
    warn = wm.staleness_warning(max_age=60.0)
    if warn and step.allowed_risk == RiskTier.DESTRUCTIVE:
        return f"Snapshot stale before DESTRUCTIVE step: {warn}"

    # ── Check 4: Blind mode warning ──────────────────────────────────
    if wm.is_blind() and tool in _STORE_TOOLS:
        logger.warning(
            "Step '%s' stores while BLIND mode is active — "
            "output will go to blind programmer, not live show",
            step.name,
        )

    # ── Check 5: Park state warning ──────────────────────────────────
    parked = [fid for fid in wm.park_ledger if str(fid) in str(step.inputs)]
    if parked:
        logger.warning(
            "Step '%s' references parked fixture(s) %s — "
            "at commands will be silently ignored by console",
            step.name, parked,
        )

    return None  # all checks passed


# ---------------------------------------------------------------------------
# Default sub-agent executor
# ---------------------------------------------------------------------------

async def _default_sub_agent(
    step: SubTask,
    memory: WorkingMemory,
    tool_caller: ToolCaller,
) -> StepResult:
    """
    Rights-aware sub-agent with structured FeedbackClass classification.
    Replaces heuristic 'error not in str(result)' with:
      PASS_ALLOWED  — permitted and succeeded
      PASS_DENIED   — correctly blocked at rights level
      FAILED_OPEN   — slipped past MCP gate, console rejected (dangerous)
      FAILED_CLOSED — blocked by MCP gate, should have been allowed
    """
    tool = step.mcp_tools[0] if step.mcp_tools else None
    rc   = memory.rights_context

    if not tool:
        return StepResult(
            step_name=step.name, success=False,
            error="No tools assigned",
            feedback_class=FeedbackClass.INCONCLUSIVE,
            rights_level=rc.user_right.value,
        )

    block = _preflight_guard(step, memory)
    if block:
        fc = (
            FeedbackClass.FAILED_CLOSED if "FAILED_CLOSED" in block
            else FeedbackClass.PASS_DENIED
        )
        return StepResult(
            step_name=step.name, success=False,
            error=block, feedback_class=fc,
            rights_level=rc.user_right.value,
        )

    try:
        result = await tool_caller(tool, step.inputs)
        memory.mark_done(step.name)

        fb = parse_telnet_feedback(
            str(result), tool_name=tool, user_right=rc.user_right,
        )

        if fb.feedback_class == FeedbackClass.FAILED_OPEN:
            logger.error(
                "[FAILED_OPEN] step='%s' tool='%s' error_code=%s "
                "user_rights=%s — review _OPERATION_MIN_RIGHT in rights.py",
                step.name, tool, fb.error_code, rc.user_right.value,
            )

        return StepResult(
            step_name=step.name,
            success=fb.feedback_class == FeedbackClass.PASS_ALLOWED,
            output=result,
            tokens_used=_estimate_tokens(step.inputs, result),
            eval_passed=fb.accepted and not fb.is_rights_denial,
            eval_notes=step.eval_criteria,
            feedback_class=fb.feedback_class,
            rights_level=rc.user_right.value,
        )
    except Exception as exc:
        memory.mark_failed(step.name, str(exc))
        return StepResult(
            step_name=step.name, success=False,
            error=str(exc),
            feedback_class=FeedbackClass.INCONCLUSIVE,
            rights_level=rc.user_right.value,
        )


def _estimate_tokens(inputs: dict, output: Any) -> int:
    import json
    try:
        return max(1, (len(json.dumps(inputs)) + len(json.dumps(str(output)))) // 4)
    except Exception:
        return 10


# ---------------------------------------------------------------------------
# Orchestration result
# ---------------------------------------------------------------------------

@dataclass
class OrchestrationResult:
    session_id: str
    goal: str
    outcome: str
    steps_done: int
    steps_failed: int
    total_tokens: int
    elapsed_s: float
    step_results: list[StepResult] = field(default_factory=list)
    memory_snapshot: dict = field(default_factory=dict)
    console_state_summary: str = ""

    def report(self) -> str:
        lines = [
            f"╔══ Orchestration Report [{self.session_id}] ══",
            f"║ Goal      : {self.goal}",
            f"║ Outcome   : {self.outcome.upper()}",
            f"║ Steps     : {self.steps_done} done / {self.steps_failed} failed",
            f"║ Tokens    : {self.total_tokens}",
            f"║ Elapsed   : {self.elapsed_s}s",
        ]
        if self.console_state_summary:
            lines.append("╠── Console State at Start ──")
            for ln in self.console_state_summary.splitlines():
                lines.append(f"║ {ln}")
        lines.append("╠── Step Results ──")
        for r in self.step_results:
            icon = "✅" if r.success else "❌"
            eval_icon = ("🟢" if r.eval_passed else "🔴") if r.eval_passed is not None else "⬜"
            fc = r.feedback_class.value if hasattr(r, "feedback_class") else ""
            rights = f" [{r.rights_level}]" if getattr(r, "rights_level", "") else ""
            lines.append(f"║ {icon} {eval_icon} [{r.step_name}] {fc}{rights} tokens={r.tokens_used}")
            if r.error:
                lines.append(f"║    ⚠ {r.error}")
        lines.append("╚══")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class Orchestrator:
    """
    Multi-agent orchestrator with full console state hydration.

    Jensen's agentic model — now gap-free:
      1. Hydrate ConsoleStateSnapshot (all 19 cd-tree gaps)
      2. Task decomposition
      3. Pre-flight guard (park state, blind mode, staleness)
      4. Agent spawning with risk-tier isolation
      5. Working memory + long-term memory
      6. Evaluation loop per step
      7. Token tracking
    """

    def __init__(
        self,
        tool_caller: ToolCaller,
        telnet_send: TelnetSend | None = None,
        *,
        ltm: LongTermMemory | None = None,
        decomposer: TaskDecomposer | None = None,
        sub_agent_fn: Callable | None = None,
        parallel: bool = False,
        auto_hydrate: bool = True,
    ) -> None:
        self._call = tool_caller
        self._send = telnet_send
        self._ltm = ltm or LongTermMemory()
        self._decomposer = decomposer or TaskDecomposer()
        self._sub_agent = sub_agent_fn or _default_sub_agent
        self._parallel = parallel
        self._auto_hydrate = auto_hydrate and telnet_send is not None
        self._last_snapshot: ConsoleStateSnapshot | None = None

    # ── Public properties ─────────────────────────────────────────────

    @property
    def last_snapshot(self) -> ConsoleStateSnapshot | None:
        """The most recently hydrated ConsoleStateSnapshot, or None."""
        return self._last_snapshot

    @last_snapshot.setter
    def last_snapshot(self, snap: ConsoleStateSnapshot) -> None:
        self._last_snapshot = snap

    def register_decomposition_rule(
        self,
        pattern: str,
        builder,
    ) -> None:
        """Register a new task decomposition rule at the front of the chain."""
        self._decomposer.register_rule(pattern, builder)

    # ── Public API ───────────────────────────────────────────────────

    async def run(
        self,
        goal: str,
        params: dict | None = None,
        *,
        auto_confirm_destructive: bool = False,
        sequence_ids: list[int] | None = None,
    ) -> OrchestrationResult:
        """
        Execute a full multi-agent task for the given goal.

        Args:
            goal: Natural-language show intent
            params: Optional structured params for the decomposer
            auto_confirm_destructive: Skip human-approval gate on DESTRUCTIVE steps
            sequence_ids: Sequence IDs to deep-hydrate (cues + parts) before running
        """
        t0 = time.time()
        session_id = str(uuid.uuid4())[:8]
        wm = WorkingMemory(session_id=session_id, task_description=goal)

        # ── Step 0: Hydrate console state (closes all 19 gaps) ──────
        console_state_summary = ""
        if self._auto_hydrate and self._send is not None:
            try:
                hydrator = ConsoleStateHydrator(self._send)
                snapshot = await hydrator.hydrate(sequence_ids=sequence_ids)
                wm.console_state = snapshot
                wm.baseline_showfile = snapshot.showfile  # showfile change detection
                self._last_snapshot = snapshot          # cache for tool access
                wm.rights_context = RightsContext.from_snapshot(snapshot)
                console_state_summary = snapshot.summary()
                logger.info("Console state hydrated:\n%s", console_state_summary)
                if snapshot.hydration_errors:
                    logger.warning("Partial hydration — errors: %s", snapshot.hydration_errors)
            except Exception as exc:
                logger.warning("ConsoleState hydration failed: %s — continuing without snapshot", exc)

        # ── Step 1: Decompose goal into plan ─────────────────────────
        plan: TaskPlan = self._decomposer.decompose(goal, params or {})
        plan.session_id = session_id
        logger.info("Orchestrator [%s] plan:\n%s", session_id, plan.summary())

        if auto_confirm_destructive:
            for step in plan.steps:
                if step.allowed_risk == RiskTier.DESTRUCTIVE:
                    step.confirmed = True

        # ── Step 2: Execute ──────────────────────────────────────────
        if self._parallel:
            step_results = await self._run_parallel(plan, wm)
        else:
            step_results = await self._run_sequential(plan, wm)

        # ── Step 3: Accounting ───────────────────────────────────────
        total_tokens = sum(r.tokens_used for r in step_results)
        wm.charge_tokens(total_tokens)

        failed = [r for r in step_results if not r.success]
        done   = [r for r in step_results if r.success]
        outcome = "success" if not failed else ("partial" if done else "failed")

        self._ltm.save_session(wm, outcome)

        return OrchestrationResult(
            session_id=session_id,
            goal=goal,
            outcome=outcome,
            steps_done=len(done),
            steps_failed=len(failed),
            total_tokens=total_tokens,
            elapsed_s=round(time.time() - t0, 2),
            step_results=step_results,
            memory_snapshot=wm.to_dict(),
            console_state_summary=console_state_summary,
        )

    async def check_showfile(self) -> tuple[str, str]:
        """Return (baseline_showfile, live_showfile) for comparison.

        ``baseline_showfile`` comes from the last hydrated snapshot.
        ``live_showfile`` is read live from the console via ListVar.
        Both are empty strings when no telnet or no snapshot is available.
        """
        baseline = self._last_snapshot.showfile if self._last_snapshot else ""
        if not self._send:
            return baseline, ""
        try:
            raw = await self._send("ListVar")
            live = parse_showfile_from_listvar(raw)
        except Exception:
            live = ""
        return baseline, live

    async def hydrate_snapshot(
        self, sequence_ids: list[int] | None = None
    ) -> ConsoleStateSnapshot | None:
        """Manually hydrate and return a snapshot without running a task."""
        if not self._send:
            return None
        hydrator = ConsoleStateHydrator(self._send)
        return await hydrator.hydrate(sequence_ids=sequence_ids)

    async def _showfile_guard(self, step: SubTask, wm: WorkingMemory) -> StepResult | None:
        """Check that the open show has not changed since hydration.

        Only runs for DESTRUCTIVE steps when a baseline exists and telnet is wired.
        Returns a failed StepResult if the show changed, otherwise None (pass).
        """
        if step.allowed_risk != RiskTier.DESTRUCTIVE:
            return None
        if not wm.baseline_showfile or not self._send:
            return None
        try:
            raw = await self._send("ListVar")
            live = parse_showfile_from_listvar(raw)
        except Exception as exc:
            logger.warning("Showfile guard ListVar failed: %s — skipping check", exc)
            return None
        if not wm.showfile_changed(live):
            return None
        wm.console_state = None  # invalidate stale snapshot
        msg = (
            f"[FAILED_CLOSED] Show changed mid-session: "
            f"expected '{wm.baseline_showfile}', got '{live}'. "
            f"Re-run hydrate_console_state before proceeding."
        )
        logger.error(msg)
        return StepResult(
            step_name=step.name,
            success=False,
            error=msg,
            feedback_class=FeedbackClass.FAILED_CLOSED,
            rights_level=wm.rights_context.user_right.value,
        )

    # ── Execution strategies ─────────────────────────────────────────

    async def _run_sequential(self, plan: TaskPlan, wm: WorkingMemory) -> list[StepResult]:
        results: list[StepResult] = []
        completed: set[str] = set()

        for step in plan.ordered_steps():
            dep_failures = [d for d in step.depends_on if d not in completed]
            if dep_failures:
                results.append(StepResult(
                    step_name=step.name, success=False,
                    error=f"Skipped — dependencies not met: {dep_failures}",
                ))
                wm.mark_failed(step.name, "dependency not met")
                continue

            showfile_block = await self._showfile_guard(step, wm)
            if showfile_block:
                results.append(showfile_block)
                wm.mark_failed(step.name, showfile_block.error)
                break  # show has changed — abort remaining steps

            _tok = _current_session_id.set(wm.session_id)
            try:
                result = await self._sub_agent(step, wm, self._call)
            finally:
                _current_session_id.reset(_tok)
            results.append(result)
            if result.success:
                completed.add(step.name)
            elif not step.retryable:
                logger.warning("Non-retryable step '%s' failed — aborting", step.name)
                break

        return results

    async def _run_parallel(self, plan: TaskPlan, wm: WorkingMemory) -> list[StepResult]:
        results: list[StepResult] = []
        completed: set[str] = set()
        remaining = list(plan.ordered_steps())

        while remaining:
            ready = [s for s in remaining if all(d in completed for d in s.depends_on)]
            if not ready:
                ready = [remaining[0]]

            _tok = _current_session_id.set(wm.session_id)
            try:
                batch = await asyncio.gather(
                    *[self._sub_agent(s, wm, self._call) for s in ready],
                    return_exceptions=True,
                )
            finally:
                _current_session_id.reset(_tok)
            interrupted = False
            for step, res in zip(ready, batch, strict=False):
                if isinstance(res, (KeyboardInterrupt, SystemExit)):
                    logger.warning("Interrupted during step %r — stopping orchestrator", step.name)
                    interrupted = True
                    step_res: StepResult = StepResult(step_name=step.name, success=False, error=f"Interrupted: {res!r}")
                elif isinstance(res, BaseException):
                    step_res = StepResult(step_name=step.name, success=False, error=str(res))
                else:
                    step_res = res  # type: ignore[assignment]
                results.append(step_res)
                if step_res.success:
                    completed.add(step.name)
                remaining.remove(step)
            if interrupted:
                break

        return results

    # ── Convenience helpers ──────────────────────────────────────────

    async def quick_run(self, goal: str, **params) -> str:
        result = await self.run(goal, params)
        return result.report()

    def recent_sessions(self, limit: int = 5) -> list[dict]:
        return self._ltm.recent_sessions(limit)

    def recall(self, session_id: str) -> dict | None:
        return self._ltm.recall_session(session_id)

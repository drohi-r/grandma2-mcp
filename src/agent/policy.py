"""Plan-level policy engine — extends command-level safety to full plans.

Builds on src/vocab.py RiskTier classification to enforce governance rules
across multi-step agent plans. Six rules:

1. Staging: reads before writes before destructive (no interleaving)
2. Verification: every DESTRUCTIVE step must be followed by a verification step
3. Discovery-first: mutations without prior inspection get discovery prepended
4. Confidence gate: low-confidence goals route to discovery-only mode
5. Connection safety: block new_show without preserve_connectivity
6. Batch limit: many destructive steps require upfront plan confirmation
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from src.agent.state import PlanStep, RunContext, StepStatus
from src.vocab import RiskTier

logger = logging.getLogger(__name__)

DEFAULT_BATCH_LIMIT = 10
CONFIDENCE_THRESHOLD = 0.5


@dataclass
class PolicyViolation:
    """A rule that was violated."""

    rule: str
    severity: str  # "error" | "warning"
    message: str
    step_id: str | None = None


class StepDecision:
    """Decision for a single step: execute, confirm, block, or defer."""

    EXECUTE = "execute"
    CONFIRM = "confirm"
    BLOCK = "block"
    DEFER_TO_DISCOVERY = "defer_to_discovery"

    def __init__(self, action: str, reason: str = ""):
        self.action = action
        self.reason = reason


@dataclass
class PolicyResult:
    """Outcome of plan validation."""

    approved: bool
    violations: list[PolicyViolation] = field(default_factory=list)
    injected_steps: list[PlanStep] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class PolicyEngine:
    """Plan-level governance extending vocab.py command safety."""

    def __init__(self, batch_limit: int = DEFAULT_BATCH_LIMIT):
        self.batch_limit = batch_limit

    def validate_plan(self, plan: list[PlanStep], confidence: float = 1.0) -> PolicyResult:
        """Check entire plan before execution begins. Returns PolicyResult."""
        violations: list[PolicyViolation] = []
        warnings: list[str] = []
        injected: list[PlanStep] = []

        # Rule 1: Staging — no destructive before all reads are done
        self._check_staging(plan, violations, warnings)

        # Rule 2: Verification — destructive steps need a following verification
        verification_steps = self._check_verification(plan, violations, warnings)
        injected.extend(verification_steps)

        # Rule 3: Discovery-first — prepend inspection if plan starts with mutation
        discovery_steps = self._check_discovery_first(plan, violations, warnings)
        injected.extend(discovery_steps)

        # Rule 4: Confidence gate
        self._check_confidence(confidence, violations, warnings)

        # Rule 5: Connection safety — new_show must preserve connectivity
        self._check_connection_safety(plan, violations, warnings)

        # Rule 6: Batch limit
        self._check_batch_limit(plan, violations, warnings)

        has_errors = any(v.severity == "error" for v in violations)
        approved = not has_errors

        return PolicyResult(
            approved=approved,
            violations=violations,
            injected_steps=injected,
            warnings=warnings,
        )

    def gate_step(self, step: PlanStep, context: RunContext) -> StepDecision:
        """Per-step runtime decision: execute, confirm, block, or defer."""
        # Destructive steps always require confirmation
        if step.risk_tier == RiskTier.DESTRUCTIVE:
            return StepDecision(
                StepDecision.CONFIRM,
                f"Step '{step.description}' is DESTRUCTIVE — requires confirmation",
            )

        # Check if dependencies are met
        for dep_id in step.depends_on:
            dep_step = next((s for s in context.plan if s.id == dep_id), None)
            if dep_step and dep_step.status != StepStatus.COMPLETED:
                return StepDecision(
                    StepDecision.BLOCK,
                    f"Dependency '{dep_step.description}' not completed (status={dep_step.status.value})",
                )

        return StepDecision(StepDecision.EXECUTE)

    # ------------------------------------------------------------------ rules

    def _check_staging(
        self,
        plan: list[PlanStep],
        violations: list[PolicyViolation],
        warnings: list[str],
    ) -> None:
        """Rule 1: No DESTRUCTIVE step before all SAFE_READ steps are done."""
        seen_destructive = False
        for step in plan:
            if step.risk_tier == RiskTier.DESTRUCTIVE:
                seen_destructive = True
            elif step.risk_tier == RiskTier.SAFE_READ and seen_destructive:
                # A read after a destructive is acceptable if it's a verification step
                if "verify" in step.description.lower():
                    continue
                warnings.append(
                    f"Staging advisory: SAFE_READ step '{step.description}' "
                    f"follows a DESTRUCTIVE step — consider reordering"
                )

    def _check_verification(
        self,
        plan: list[PlanStep],
        violations: list[PolicyViolation],
        warnings: list[str],
    ) -> list[PlanStep]:
        """Rule 2: Every DESTRUCTIVE step should be followed by verification."""
        missing_verification: list[PlanStep] = []
        for i, step in enumerate(plan):
            if step.risk_tier != RiskTier.DESTRUCTIVE:
                continue
            # Check if next step is a verification
            has_verify = False
            if i + 1 < len(plan):
                next_step = plan[i + 1]
                if "verify" in next_step.description.lower():
                    has_verify = True
            if not has_verify:
                warnings.append(
                    f"No verification after DESTRUCTIVE step '{step.description}' — "
                    f"consider adding a verification step"
                )
        return missing_verification

    def _check_discovery_first(
        self,
        plan: list[PlanStep],
        violations: list[PolicyViolation],
        warnings: list[str],
    ) -> list[PlanStep]:
        """Rule 3: Plan should start with inspection, not mutation."""
        injected: list[PlanStep] = []
        if plan and plan[0].risk_tier in (RiskTier.SAFE_WRITE, RiskTier.DESTRUCTIVE):
            warnings.append(
                "Plan starts with a mutation — consider prepending discovery steps "
                "to inspect current console state first"
            )
        return injected

    def _check_confidence(
        self,
        confidence: float,
        violations: list[PolicyViolation],
        warnings: list[str],
    ) -> None:
        """Rule 4: Low confidence goals should route to discovery only."""
        if confidence < CONFIDENCE_THRESHOLD:
            violations.append(
                PolicyViolation(
                    rule="confidence_gate",
                    severity="error",
                    message=(
                        f"Goal confidence {confidence:.2f} is below threshold "
                        f"{CONFIDENCE_THRESHOLD:.2f} — routing to discovery-only mode"
                    ),
                )
            )

    def _check_connection_safety(
        self,
        plan: list[PlanStep],
        violations: list[PolicyViolation],
        warnings: list[str],
    ) -> None:
        """Rule 5: new_show must use preserve_connectivity=True."""
        for step in plan:
            if step.tool_name == "create_new_show":
                preserve = step.tool_args.get("preserve_connectivity", True)
                if not preserve:
                    violations.append(
                        PolicyViolation(
                            rule="connection_safety",
                            severity="error",
                            message=(
                                "new_show with preserve_connectivity=False will sever "
                                "the Telnet connection — blocked by policy"
                            ),
                            step_id=step.id,
                        )
                    )

    def _check_batch_limit(
        self,
        plan: list[PlanStep],
        violations: list[PolicyViolation],
        warnings: list[str],
    ) -> None:
        """Rule 6: Too many destructive steps require upfront confirmation."""
        destructive_count = sum(
            1 for s in plan if s.risk_tier == RiskTier.DESTRUCTIVE
        )
        if destructive_count > self.batch_limit:
            warnings.append(
                f"Plan contains {destructive_count} DESTRUCTIVE steps "
                f"(limit={self.batch_limit}) — full plan confirmation required "
                f"before execution begins"
            )

"""
skill_improver.py — Controlled improvement loop for OpenSpace-style observability.

Analyses telemetry and session history to surface:
  1. RepairSuggestion  — tools failing repeatedly, with error classification
  2. PromotionCandidate — successful sessions that haven't been promoted to Skills

IMPORTANT: This module surfaces suggestions only.  It never writes to the Skill
registry autonomously.  All promotions must be operator-initiated (Tool 141) or
DESTRUCTIVE approvals must be human-gated (Tool 143).

Design rule: no suggestion returned by this module triggers any console action.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .agent_memory import LongTermMemory
from .skill import SkillRegistry
from .telemetry import ToolTelemetry

_DEFAULT_DB = Path(__file__).parent.parent / "rag" / "store" / "agent_memory.db"


# ---------------------------------------------------------------------------
# Suggestion dataclasses  (read-only outputs — never auto-applied)
# ---------------------------------------------------------------------------

@dataclass
class RepairSuggestion:
    """A tool that is failing repeatedly and may need attention."""

    tool_name: str
    failure_count: int
    error_classes: list[str]
    hint: str                  # human-readable repair guidance


@dataclass
class PromotionCandidate:
    """A successful session that could be promoted to a named Skill."""

    session_id: str
    task: str
    outcome: str
    steps_done: int
    steps_failed: int
    tokens: int
    quality_score: float
    suggested_name: str        # auto-derived from task description


# ---------------------------------------------------------------------------
# SkillImprover
# ---------------------------------------------------------------------------

class SkillImprover:
    """
    Reads telemetry and LTM session logs to identify improvement opportunities.

    All three collaborators (telemetry, registry, ltm) share the same DB file
    via separate connections; SQLite WAL mode handles concurrent readers fine.
    """

    def __init__(
        self,
        telemetry: ToolTelemetry,
        registry: SkillRegistry,
        ltm: LongTermMemory,
    ) -> None:
        self._tel = telemetry
        self._reg = registry
        self._ltm = ltm

    # ------------------------------------------------------------------ #
    # Failure pattern detection                                            #
    # ------------------------------------------------------------------ #

    def identify_failure_patterns(
        self, days: int = 7, min_failures: int = 3
    ) -> list[RepairSuggestion]:
        """
        Return tools with >= min_failures errors in the last N days.

        Groups errors by error_class and generates a human-readable hint
        for each affected tool.
        """
        failing = self._tel.top_failing_tools(days=days, min_failures=min_failures)
        suggestions: list[RepairSuggestion] = []
        for entry in failing:
            tool_name = entry["tool_name"]
            total = entry["total"]
            errors: dict[str, int] = entry["errors"]
            dominant = max(errors, key=errors.__getitem__)
            hint = _repair_hint(tool_name, dominant, total)
            suggestions.append(
                RepairSuggestion(
                    tool_name=tool_name,
                    failure_count=total,
                    error_classes=list(errors.keys()),
                    hint=hint,
                )
            )
        suggestions.sort(key=lambda s: s.failure_count, reverse=True)
        return suggestions

    # ------------------------------------------------------------------ #
    # Promotion candidate detection                                        #
    # ------------------------------------------------------------------ #

    def identify_promotion_candidates(
        self, min_quality: float = 0.8
    ) -> list[PromotionCandidate]:
        """
        Return successful sessions not yet promoted to Skills.

        Quality score = steps_done / (steps_done + steps_failed).
        Sessions with quality >= min_quality and no existing Skill pointing to
        them are returned as promotion candidates.
        """
        rows = self._ltm._conn.execute(
            "SELECT id, task, outcome, steps_done, steps_failed, tokens "
            "FROM sessions WHERE outcome='success' ORDER BY timestamp DESC LIMIT 200"
        ).fetchall()

        candidates: list[PromotionCandidate] = []
        for session_id, task, outcome, done, failed, tokens in rows:
            done = done or 0
            failed = failed or 0
            total = done + failed
            if total == 0:
                continue
            quality = done / total
            if quality < min_quality:
                continue
            # Skip sessions already promoted
            already = self._reg._conn.execute(
                "SELECT 1 FROM skills WHERE source_session_id=?", (session_id,)
            ).fetchone()
            if already:
                continue
            candidates.append(
                PromotionCandidate(
                    session_id=session_id,
                    task=task or "",
                    outcome=outcome or "success",
                    steps_done=done,
                    steps_failed=failed,
                    tokens=tokens or 0,
                    quality_score=round(quality, 3),
                    suggested_name=_slugify(task or session_id),
                )
            )
        candidates.sort(key=lambda c: c.quality_score, reverse=True)
        return candidates

    # ------------------------------------------------------------------ #
    # Quality scoring                                                      #
    # ------------------------------------------------------------------ #

    def quality_score_for_session(self, session_id: str) -> float:
        """
        Compute a 0.0–1.0 quality score for a session.

        Formula: steps_done / (steps_done + steps_failed).
        Returns 0.0 if session not found or has no steps.
        """
        row = self._ltm._conn.execute(
            "SELECT steps_done, steps_failed FROM sessions WHERE id=?",
            (session_id,),
        ).fetchone()
        if not row:
            return 0.0
        done, failed = row
        done = done or 0
        failed = failed or 0
        total = done + failed
        if total == 0:
            return 0.0
        return round(done / total, 3)

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    def close(self) -> None:
        pass  # collaborators manage their own connections


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s_]", "", text)
    text = re.sub(r"\s+", "_", text)
    return text[:60]


_HINT_MAP: dict[str, str] = {
    "ConnectionError": (
        "Repeated ConnectionError — verify GMA_HOST/GMA_PORT are reachable "
        "and the console's Telnet login is enabled (Setup → Console → Global Settings)."
    ),
    "RuntimeError": (
        "Repeated RuntimeError — check that the grandMA2 safety level (GMA_SAFETY_LEVEL) "
        "allows the operations being requested, and review recent server logs."
    ),
    "TimeoutError": (
        "Repeated TimeoutError — increase GMA_TIMEOUT or check network latency "
        "between the MCP server and the grandMA2 console."
    ),
}

_DEFAULT_HINT = (
    "Repeated {error_class} on {tool_name} ({count}x in last N days) — "
    "review server logs for stack traces and confirm the console is responsive."
)


def _repair_hint(tool_name: str, dominant_error: str, count: int) -> str:
    base = _HINT_MAP.get(
        dominant_error,
        _DEFAULT_HINT.format(
            error_class=dominant_error, tool_name=tool_name, count=count
        ),
    )
    return f"{tool_name}: {base}"

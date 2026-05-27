"""Busking-domain expert-lint rules (BUSK-*).

Plan shape:

    {"kind": "busking",
     "strategy": "rock-band" | "dj" | "festival" | "theatrical",
     "executors": [{"slot", "label", "priority", "function", "role"}, ...],
     "companion_grid": [{"row": int, "cells": [...]}],   # optional
     "companion_config": dict,                            # optional
     "fader_bank_layout": "muscle-memory" | "sequential" | "category-grouped"}
"""

from __future__ import annotations

import re
from typing import Callable

from src.expert_lint.types import Violation

_GENERIC_LABEL_RE = re.compile(r"^(Exec|Executor)\s+\d+$", re.IGNORECASE)


def _execs(plan: dict) -> list[dict]:
    return plan.get("executors", [])


# ---------------------------------------------------------------------------
# SUB-001 — blackout sub-master independent of Grand Master
# ---------------------------------------------------------------------------

def check_sub_001_blackout_independent(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """BUSK-SUB-001 (error): No executor with role == 'blackout-sub'."""
    if any(e.get("role") == "blackout-sub" for e in _execs(plan)):
        return []
    return [Violation(
        rule_id="BUSK-SUB-001",
        severity="error",
        domain="busking",
        target="page",
        expert_says="No blackout sub-master independent of the Grand Master",
        fix_suggestion=(
            "Add a dedicated executor with BlackScreen or DMX off macro, priority Super"
        ),
    )]


# ---------------------------------------------------------------------------
# SUB-002 — speed master missing for FX bank
# ---------------------------------------------------------------------------

def check_sub_002_speed_master_missing(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """BUSK-SUB-002 (warning): No executor with function == 'speedmaster'
    in rock-band/dj/festival strategies."""
    if plan.get("strategy") not in {"rock-band", "dj", "festival"}:
        return []
    if any(e.get("function") == "speedmaster" for e in _execs(plan)):
        return []
    return [Violation(
        rule_id="BUSK-SUB-002",
        severity="warning",
        domain="busking",
        target="page",
        expert_says="Speed master not assigned for FX bank",
        fix_suggestion="Add a speed master executor and bind to all chasers' SpeedMaster property",
    )]


# ---------------------------------------------------------------------------
# PRIO-001 — blackout sub priority is not Super
# ---------------------------------------------------------------------------

def check_prio_001_blackout_sub_priority(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """BUSK-PRIO-001 (error): blackout-sub executor exists but priority != 'super'."""
    out: list[Violation] = []
    for e in _execs(plan):
        if e.get("role") == "blackout-sub" and e.get("priority") != "super":
            out.append(Violation(
                rule_id="BUSK-PRIO-001",
                severity="error",
                domain="busking",
                target=f"executor:{e.get('slot')}",
                expert_says=(
                    f"Blackout sub priority is {e.get('priority')!r}, not 'super'"
                ),
                fix_suggestion="Set executor priority to `super` per functional-domains.md",
            ))
    return out


# ---------------------------------------------------------------------------
# PRIO-002 — all executors set to Normal (no priority discrimination)
# ---------------------------------------------------------------------------

def check_prio_002_all_executors_normal(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """BUSK-PRIO-002 (warning): every executor has priority 'normal'."""
    execs = _execs(plan)
    if not execs:
        return []
    if all(e.get("priority") == "normal" for e in execs):
        return [Violation(
            rule_id="BUSK-PRIO-002",
            severity="warning",
            domain="busking",
            target="page",
            expert_says="All executors set to Normal priority — no discrimination",
            fix_suggestion=(
                "Assign Super/High/Swap per the strategy table in scope spec Appendix B.2"
            ),
        )]
    return []


# ---------------------------------------------------------------------------
# PRIO-003 — blinder priority too low (rock-band/dj)
# ---------------------------------------------------------------------------

def check_prio_003_blinder_priority(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """BUSK-PRIO-003 (warning): blinder executor not High/Swap in rock-band/dj."""
    if plan.get("strategy") not in {"rock-band", "dj"}:
        return []
    out: list[Violation] = []
    for e in _execs(plan):
        if e.get("role") == "blinder" and e.get("priority") not in {"high", "swap"}:
            out.append(Violation(
                rule_id="BUSK-PRIO-003",
                severity="warning",
                domain="busking",
                target=f"executor:{e.get('slot')}",
                expert_says=(
                    f"Blinder priority is {e.get('priority')!r} — flash will be overridden"
                ),
                fix_suggestion="Set blinders to High priority",
            ))
    return out


# ---------------------------------------------------------------------------
# KILL-001 — no kill-color (rock-band/dj)
# ---------------------------------------------------------------------------

def check_kill_001_no_kill_color(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """BUSK-KILL-001 (warning): no kill-color executor in rock-band/dj."""
    if plan.get("strategy") not in {"rock-band", "dj"}:
        return []
    if any(e.get("role") == "kill-color" for e in _execs(plan)):
        return []
    return [Violation(
        rule_id="BUSK-KILL-001",
        severity="warning",
        domain="busking",
        target="page",
        expert_says="No kill button for color bank",
        fix_suggestion="Add a `Kill /color` macro on a dedicated executor in the specials bank",
    )]


# ---------------------------------------------------------------------------
# KILL-002 — no kill-fx (rock-band/dj)
# ---------------------------------------------------------------------------

def check_kill_002_no_kill_fx(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """BUSK-KILL-002 (warning): no kill-fx executor in rock-band/dj."""
    if plan.get("strategy") not in {"rock-band", "dj"}:
        return []
    if any(e.get("role") == "kill-fx" for e in _execs(plan)):
        return []
    return [Violation(
        rule_id="BUSK-KILL-002",
        severity="warning",
        domain="busking",
        target="page",
        expert_says="No kill button for FX bank",
        fix_suggestion="Add a `Kill /effect` macro on a dedicated executor in the specials bank",
    )]


# ---------------------------------------------------------------------------
# TAP-001 — tap-tempo missing (rock-band/dj)
# ---------------------------------------------------------------------------

def check_tap_001_tap_tempo_missing(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """BUSK-TAP-001 (warning): no tap-tempo executor in rock-band/dj."""
    if plan.get("strategy") not in {"rock-band", "dj"}:
        return []
    for e in _execs(plan):
        if e.get("function") == "tap" or e.get("role") == "tap":
            return []
    return [Violation(
        rule_id="BUSK-TAP-001",
        severity="warning",
        domain="busking",
        target="page",
        expert_says="Tap-tempo executor missing",
        fix_suggestion="Add `Tap` executor bound to a speed master",
    )]


# ---------------------------------------------------------------------------
# LAYOUT-001 — fader bank layout not muscle-memory
# ---------------------------------------------------------------------------

def check_layout_001_layout_not_muscle_memory(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """BUSK-LAYOUT-001 (advice): fader_bank_layout deviates from muscle-memory
    without explicit override."""
    if plan.get("fader_bank_layout") == "muscle-memory":
        return []
    if (context or {}).get("fader_layout_overridden"):
        return []
    return [Violation(
        rule_id="BUSK-LAYOUT-001",
        severity="advice",
        domain="busking",
        target="page",
        expert_says=(
            f"Fader bank layout is {plan.get('fader_bank_layout')!r} — "
            "deviates from muscle-memory map"
        ),
        fix_suggestion=(
            "Confirm the deviation is intentional; otherwise use the muscle-memory default"
        ),
    )]


# ---------------------------------------------------------------------------
# CONF-001 — two executors share the same slot
# ---------------------------------------------------------------------------

def check_conf_001_executor_slot_collision(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """BUSK-CONF-001 (error): duplicate executor slot."""
    seen: dict[str, dict] = {}
    out: list[Violation] = []
    for e in _execs(plan):
        slot = e.get("slot", "")
        if slot in seen:
            out.append(Violation(
                rule_id="BUSK-CONF-001",
                severity="error",
                domain="busking",
                target=f"executor:{slot}",
                expert_says=f"Executor slot {slot!r} assigned twice",
                fix_suggestion="Re-allocate so each executor lives in a distinct slot",
            ))
        else:
            seen[slot] = e
    return out


# ---------------------------------------------------------------------------
# LABEL-001 — executor has no label or generic one
# ---------------------------------------------------------------------------

def check_label_001_executor_label_missing(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """BUSK-LABEL-001 (warning): executor label empty or generic."""
    out: list[Violation] = []
    for e in _execs(plan):
        label = (e.get("label") or "").strip()
        if not label or _GENERIC_LABEL_RE.match(label):
            out.append(Violation(
                rule_id="BUSK-LABEL-001",
                severity="warning",
                domain="busking",
                target=f"executor:{e.get('slot')}",
                expert_says=f"Executor {e.get('slot')!r} has empty or generic label {label!r}",
                fix_suggestion='Label every executor with intent (e.g., "Wash Blue", "Strobe All")',
            ))
    return out


# ---------------------------------------------------------------------------
# HTP-001 — intensity submaster is not HTP
# ---------------------------------------------------------------------------

def check_htp_001_intensity_not_htp(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """BUSK-HTP-001 (warning): intensity-submaster executor priority != 'htp'."""
    out: list[Violation] = []
    for e in _execs(plan):
        if e.get("role") == "intensity-submaster" and e.get("priority") != "htp":
            out.append(Violation(
                rule_id="BUSK-HTP-001",
                severity="warning",
                domain="busking",
                target=f"executor:{e.get('slot')}",
                expert_says=(
                    f"Intensity sub-master at {e.get('slot')!r} configured as "
                    f"{e.get('priority')!r}, not HTP"
                ),
                fix_suggestion="Change priority to HTP for intensity-only executors",
            ))
    return out


# ---------------------------------------------------------------------------
# LTP-001 — color executor configured as HTP
# ---------------------------------------------------------------------------

def check_ltp_001_color_executor_is_htp(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """BUSK-LTP-001 (warning): color executor priority == 'htp' — should be LTP."""
    out: list[Violation] = []
    for e in _execs(plan):
        if e.get("role") == "color" and e.get("priority") == "htp":
            out.append(Violation(
                rule_id="BUSK-LTP-001",
                severity="warning",
                domain="busking",
                target=f"executor:{e.get('slot')}",
                expert_says=(
                    f"Color executor at {e.get('slot')!r} is HTP — should be LTP "
                    "so the last fired wins"
                ),
                fix_suggestion="Change priority to LTP/Normal",
            ))
    return out


# ---------------------------------------------------------------------------
# COMP-001 — Companion config fails schema validation
# ---------------------------------------------------------------------------

def check_comp_001_companion_schema_invalid(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """BUSK-COMP-001 (error): companion_config present but fails schema check.

    Context may supply a validator callable as `validate_companion_schema`.
    Default: always returns True (no validator wired — Path A stub)."""
    if "companion_config" not in plan:
        return []
    validator: Callable[[dict], bool] = (
        (context or {}).get("validate_companion_schema") or (lambda _: True)
    )
    if validator(plan["companion_config"]):
        return []
    return [Violation(
        rule_id="BUSK-COMP-001",
        severity="error",
        domain="busking",
        target="companion_config",
        expert_says="Generated Companion config fails schema validation",
        fix_suggestion="Regenerate using the golden-fixture-derived template",
    )]


# ---------------------------------------------------------------------------
# COMP-002 — companion_grid has non-contiguous rows
# ---------------------------------------------------------------------------

def check_comp_002_companion_grid_noncontiguous(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """BUSK-COMP-002 (warning): companion_grid rows are non-contiguous."""
    grid = plan.get("companion_grid", [])
    if len(grid) < 2:
        return []
    rows = sorted(r.get("row", 0) for r in grid)
    expected = list(range(rows[0], rows[0] + len(rows)))
    if rows == expected:
        return []
    return [Violation(
        rule_id="BUSK-COMP-002",
        severity="warning",
        domain="busking",
        target="companion_grid",
        expert_says=(
            f"Companion grid layout has non-contiguous rows: {rows} (expected {expected})"
        ),
        fix_suggestion="Compact the layout so used rows are contiguous",
    )]


# ---------------------------------------------------------------------------
# KEY-001 — KEY fixture group missing (rock-band/broadcast/theatrical)
# ---------------------------------------------------------------------------

def check_key_001_missing_key_fixture(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """BUSK-KEY-001 (advice): no executor with role 'key-fixture' for
    rock-band / broadcast / theatrical strategies."""
    if plan.get("strategy") not in {"rock-band", "broadcast", "theatrical"}:
        return []
    if any(e.get("role") == "key-fixture" for e in _execs(plan)):
        return []
    return [Violation(
        rule_id="BUSK-KEY-001",
        severity="advice",
        domain="busking",
        target="page",
        expert_says="KEY fixture group not defined",
        fix_suggestion="Add a KEY group containing the front-key fixture for that production",
    )]


__all__ = [
    "check_sub_001_blackout_independent",
    "check_sub_002_speed_master_missing",
    "check_prio_001_blackout_sub_priority",
    "check_prio_002_all_executors_normal",
    "check_prio_003_blinder_priority",
    "check_kill_001_no_kill_color",
    "check_kill_002_no_kill_fx",
    "check_tap_001_tap_tempo_missing",
    "check_layout_001_layout_not_muscle_memory",
    "check_conf_001_executor_slot_collision",
    "check_label_001_executor_label_missing",
    "check_htp_001_intensity_not_htp",
    "check_ltp_001_color_executor_is_htp",
    "check_comp_001_companion_schema_invalid",
    "check_comp_002_companion_grid_noncontiguous",
    "check_key_001_missing_key_fixture",
]

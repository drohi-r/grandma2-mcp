"""Show-creation expert-lint rules (SHOW-*).

Plan shape:

    {"kind": "show",
     "strategy": str,
     "preset_strategy": str,
     "cuelists": [{
         "id": int, "label": str, "tracking": "track" | "non-tracking",
         "priority": str, "off_time_ms": int | None, "section": str | None,
         "options": {"wrap": bool, "softltp": bool, ...},
         "cues": [{
             "id": float, "label": str, "block": bool,
             "uses_preset": bool, "is_mib": bool,
         }, ...]
     }, ...],
     "fixtures": [{"id": int, "type": str, "covered_by_any_cue": bool,
                   "mib_enabled": bool}, ...],
     "worlds": [{"name": str, "section": str | None}, ...],
     "views": [str, ...]}
"""

from __future__ import annotations

import re

from src.expert_lint.types import Violation

_GENERIC_CUE_NOTE_RE = re.compile(r"^Cue\s+\d+(\.\d+)?$", re.IGNORECASE)
_GENERIC_SEQ_LABEL_RE = re.compile(r"^Seq\s+\d+$", re.IGNORECASE)
_PER_SECTION_STRATEGIES = {"rock-band", "theatrical", "broadcast"}
_PER_SECTION_MIN_WORLDS = 3   # any per-section strategy needs at least a few worlds


def _cuelists(plan: dict) -> list[dict]:
    return plan.get("cuelists", [])


def _fixtures(plan: dict) -> list[dict]:
    return plan.get("fixtures", [])


# TRACK-001
def check_track_001_block_at_song_boundary(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """SHOW-TRACK-001 (warning): strategy expects block at song/scene boundary
    but no block cue found at the cuelist's last cue."""
    if plan.get("strategy") not in {"rock-band", "theatrical"}:
        return []
    out: list[Violation] = []
    for cl in _cuelists(plan):
        if cl.get("tracking") != "track" or not cl.get("cues"):
            continue
        # Boundary = last cue in the cuelist
        last = cl["cues"][-1]
        if not last.get("block"):
            out.append(Violation(
                rule_id="SHOW-TRACK-001",
                severity="warning",
                domain="show",
                target=f"cuelist:{cl.get('id')}",
                expert_says=(
                    f"Tracking cuelist {cl.get('label')!r} has no block cue at boundary"
                ),
                fix_suggestion="Insert a block cue at each cuelist's last cue",
            ))
    return out


# TRACK-002
def check_track_002_nontracking_with_wrap_no_softltp(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """SHOW-TRACK-002 (warning): non-tracking cuelist with Wrap set but no SoftLTP."""
    out: list[Violation] = []
    for cl in _cuelists(plan):
        if cl.get("tracking") != "non-tracking":
            continue
        opts = cl.get("options", {})
        if opts.get("wrap") and not opts.get("softltp"):
            out.append(Violation(
                rule_id="SHOW-TRACK-002",
                severity="warning",
                domain="show",
                target=f"cuelist:{cl.get('id')}",
                expert_says=(
                    "Non-tracking cuelist has Wrap enabled without SoftLTP"
                ),
                fix_suggestion="Set softltp=true OR switch to a tracking strategy",
            ))
    return out


# MIB-001
def check_mib_001_movers_have_mib(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """SHOW-MIB-001 (warning): movers present but no MIB cues exist."""
    has_movers = any(f.get("type") == "mover" for f in _fixtures(plan))
    if not has_movers:
        return []
    any_mib = any(
        cue.get("is_mib")
        for cl in _cuelists(plan)
        for cue in cl.get("cues", [])
    )
    if any_mib:
        return []
    return [Violation(
        rule_id="SHOW-MIB-001",
        severity="warning",
        domain="show",
        target="plan",
        expert_says='Movers present but no MIB ("Move In Black") cues defined',
        fix_suggestion="Add MIB cues for each mover type at scene boundaries",
    )]


# MIB-002
def check_mib_002_mib_on_dimmer_only(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """SHOW-MIB-002 (error): MIB enabled on dimmer-only fixtures (no movement)."""
    out: list[Violation] = []
    for f in _fixtures(plan):
        if f.get("type") == "dimmer" and f.get("mib_enabled"):
            out.append(Violation(
                rule_id="SHOW-MIB-002",
                severity="error",
                domain="show",
                target=f"fixture:{f.get('id')}",
                expert_says=(
                    f"Fixture {f.get('id')} (type=dimmer) has MIB enabled — "
                    "dimmers have no movement attribute"
                ),
                fix_suggestion="Disable MIB for dimmer-only fixtures",
            ))
    return out


# REF-001
def check_ref_001_hard_values_when_preset_expected(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """SHOW-REF-001 (warning): full-coverage strategy but cue stores hard values."""
    if plan.get("preset_strategy") not in {"full-coverage", "color-first"}:
        return []
    out: list[Violation] = []
    for cl in _cuelists(plan):
        for cue in cl.get("cues", []):
            if "uses_preset" in cue and not cue["uses_preset"]:
                out.append(Violation(
                    rule_id="SHOW-REF-001",
                    severity="warning",
                    domain="show",
                    target=f"cue:{cl.get('id')}.{cue.get('id')}",
                    expert_says=(
                        f"Cue {cue.get('label')!r} stores hard values where strategy expects presets"
                    ),
                    fix_suggestion="Replace numeric values with preset references",
                ))
    return out


# OFF-001
def check_off_001_off_time_missing(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """SHOW-OFF-001 (warning): cuelist has no off-time configured."""
    out: list[Violation] = []
    for cl in _cuelists(plan):
        if cl.get("off_time_ms") is None:
            out.append(Violation(
                rule_id="SHOW-OFF-001",
                severity="warning",
                domain="show",
                target=f"cuelist:{cl.get('id')}",
                expert_says=f"Cuelist {cl.get('label')!r} has no off-time configured",
                fix_suggestion="Set off-time per .claude/skills/cue-tracking-and-timing/SKILL.md defaults",
            ))
    return out


# PRIO-001
def check_prio_001_all_cuelists_normal(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """SHOW-PRIO-001 (warning): every cuelist has priority 'normal'."""
    cl = _cuelists(plan)
    if not cl:
        return []
    if all(c.get("priority") == "normal" for c in cl):
        return [Violation(
            rule_id="SHOW-PRIO-001",
            severity="warning",
            domain="show",
            target="plan",
            expert_says="All cuelists set to Normal priority — no discrimination",
            fix_suggestion="Assign Super to emergency/blackout, Normal default, document any High/Swap",
        )]
    return []


# WORLD-001
def check_world_001_missing_per_section_worlds(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """SHOW-WORLD-001 (warning): per-section strategy but too few worlds."""
    if plan.get("strategy") not in _PER_SECTION_STRATEGIES:
        return []
    worlds = plan.get("worlds", [])
    if len(worlds) >= _PER_SECTION_MIN_WORLDS:
        return []
    return [Violation(
        rule_id="SHOW-WORLD-001",
        severity="warning",
        domain="show",
        target="plan",
        expert_says=(
            f"Per-section strategy {plan.get('strategy')!r} has only {len(worlds)} world(s)"
        ),
        fix_suggestion="Generate worlds matching the strategy's section count",
    )]


# NOTE-001
def check_note_001_generic_cue_note(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """SHOW-NOTE-001 (advice): generic cue label like 'Cue 5'."""
    out: list[Violation] = []
    for cl in _cuelists(plan):
        for cue in cl.get("cues", []):
            label = (cue.get("label") or "").strip()
            if not label or _GENERIC_CUE_NOTE_RE.match(label):
                out.append(Violation(
                    rule_id="SHOW-NOTE-001",
                    severity="advice",
                    domain="show",
                    target=f"cue:{cl.get('id')}.{cue.get('id')}",
                    expert_says=f"Cue label {label!r} is generic",
                    fix_suggestion="Apply naming convention: {song}_{section}_{intent}",
                ))
    return out


# EMERG-001
def check_emerg_001_no_emergency_cuelist(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """SHOW-EMERG-001 (warning): theatrical/broadcast strategy with no Super-priority cuelist."""
    if plan.get("strategy") not in {"theatrical", "broadcast"}:
        return []
    if any(c.get("priority") == "super" for c in _cuelists(plan)):
        return []
    return [Violation(
        rule_id="SHOW-EMERG-001",
        severity="warning",
        domain="show",
        target="plan",
        expert_says="Theatrical/broadcast strategy but no emergency cuelist found",
        fix_suggestion="Add an emergency cuelist at Super priority",
    )]


# VIEW-001
def check_view_001_missing_required_view(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """SHOW-VIEW-001 (warning): required view template missing per strategy."""
    required_by_strategy = {
        "rock-band": {"programmer", "run", "busking-fallback"},
        "festival": {"preset-access", "executor-monitor", "run"},
        "theatrical": {"programmer", "run", "troubleshoot"},
        "dj": {"busking-master", "preset-access"},
        "broadcast": {"programmer", "run", "troubleshoot"},
        "corporate": {"run"},
    }
    needed = required_by_strategy.get(plan.get("strategy", ""), set())
    if not needed:
        return []
    have = set(plan.get("views", []))
    missing = needed - have
    if not missing:
        return []
    return [Violation(
        rule_id="SHOW-VIEW-001",
        severity="warning",
        domain="show",
        target="views",
        expert_says=(
            f"Strategy {plan.get('strategy')!r} requires views {sorted(needed)} "
            f"but missing {sorted(missing)}"
        ),
        fix_suggestion="Add the missing views per strategy table (Appendix B.1)",
    )]


# BLACK-001
def check_black_001_no_panic_blackout_cue(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """SHOW-BLACK-001 (warning): rock-band strategy needs panic blackout cue per sequence."""
    if plan.get("strategy") != "rock-band":
        return []
    out: list[Violation] = []
    for cl in _cuelists(plan):
        if not cl.get("cues"):
            continue
        first_cue = cl["cues"][0]
        label = (first_cue.get("label") or "").lower()
        if "blackout" not in label and "panic" not in label:
            out.append(Violation(
                rule_id="SHOW-BLACK-001",
                severity="warning",
                domain="show",
                target=f"cuelist:{cl.get('id')}",
                expert_says=(
                    f'No "panic blackout" cue at start of cuelist {cl.get("label")!r}'
                ),
                fix_suggestion="Insert blackout cue as cue 0.5 of each sequence",
            ))
    return out


# SEQ-001
def check_seq_001_generic_sequence_label(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """SHOW-SEQ-001 (advice): generic sequence label like 'Seq 12'."""
    out: list[Violation] = []
    for cl in _cuelists(plan):
        label = (cl.get("label") or "").strip()
        if not label or _GENERIC_SEQ_LABEL_RE.match(label):
            out.append(Violation(
                rule_id="SHOW-SEQ-001",
                severity="advice",
                domain="show",
                target=f"cuelist:{cl.get('id')}",
                expert_says=f"Sequence label {label!r} is generic",
                fix_suggestion="Label sequence with song name + section",
            ))
    return out


# COVER-001
def check_cover_001_uncovered_fixtures(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """SHOW-COVER-001 (advice): fixtures present but never targeted by any cue/executor."""
    uncovered = [f for f in _fixtures(plan) if not f.get("covered_by_any_cue", False)]
    if not uncovered:
        return []
    return [Violation(
        rule_id="SHOW-COVER-001",
        severity="advice",
        domain="show",
        target="fixtures",
        expert_says=(
            f"{len(uncovered)} fixture(s) in patch never targeted by any cue or executor"
        ),
        fix_suggestion="Either include them in a cue/executor or document why they're parked",
    )]


__all__ = [
    "check_track_001_block_at_song_boundary",
    "check_track_002_nontracking_with_wrap_no_softltp",
    "check_mib_001_movers_have_mib",
    "check_mib_002_mib_on_dimmer_only",
    "check_ref_001_hard_values_when_preset_expected",
    "check_off_001_off_time_missing",
    "check_prio_001_all_cuelists_normal",
    "check_world_001_missing_per_section_worlds",
    "check_note_001_generic_cue_note",
    "check_emerg_001_no_emergency_cuelist",
    "check_view_001_missing_required_view",
    "check_black_001_no_panic_blackout_cue",
    "check_seq_001_generic_sequence_label",
    "check_cover_001_uncovered_fixtures",
]

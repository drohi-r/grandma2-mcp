"""Macro-domain expert-lint rules (MACRO-*).

Each rule is a pure function:

    def check_<id>_<short_name>(plan: dict, context: dict | None) -> list[Violation]

Plan shape:

    {"kind": "macro", "label": str, "lines": [{"index": int, "command": str}, ...],
     "body_xml": str (optional)}

Context (optional) carries cross-rule state — existing_macros, user_rights_level,
required_rights, session_vars, etc. Rules that ignore the context accept None.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from src.expert_lint.types import Violation

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

_MACRO_CALL_RE = re.compile(
    r'Go\s+Macro\s+(?:\d+\.)?"(?P<name>[^"]+)"\s*\.\s*(?P<line>\d+)',
    re.IGNORECASE,
)
_DESTRUCTIVE_KEYWORDS = ("delete", "new_show", "store /merge")
_SYSTEM_VARS = frozenset({
    "$VERSION", "$SHOWFILE", "$USER", "$USERRIGHTS", "$SELECTEDEXEC",
    "$SELECTEDEXECCUE", "$SELECTEDFIXTURESCOUNT", "$FADERPAGE", "$PRESET",
    "$FEATURE", "$ATTRIBUTE", "$DATE", "$TIME", "$IP", "$RUNNING",
    "$MASTERVALUE", "$EXECVALUE", "$EXECPAUSED", "$PAGENAME",
    "$SHOWTIME", "$EDITTIME", "$SAVETIME", "$CMDDELAY", "$LASTCOMMAND",
    "$CLOCKTIME", "$BPM",
})
_EXEC_REF_RE = re.compile(r"\b\d+\.\d+\.\d+\b")
_GETVAR_RE = re.compile(r"GetVar\s+(\$\w+)", re.IGNORECASE)
_SETVAR_RE = re.compile(r"SetVar\s+(\$\w+)", re.IGNORECASE)
_SETUSERVAR_RE = re.compile(r"SetUserVar\s+(\$\w+)", re.IGNORECASE)


def _commands(plan: dict) -> list[tuple[int, str]]:
    return [(ln.get("index", 0), ln.get("command", "")) for ln in plan.get("lines", [])]


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

def check_jt_001_jump_target_exists(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """MACRO-JT-001 (error): Jump target line number does not exist in the macro."""
    valid_indices = {idx for idx, _ in _commands(plan)}
    out: list[Violation] = []
    for idx, cmd in _commands(plan):
        for match in _MACRO_CALL_RE.finditer(cmd):
            target = int(match.group("line"))
            target_name = match.group("name")
            # Only flag self-targeting calls (same macro). If target_name doesn't
            # match the plan's label, it's a cross-macro link (covered by LINK-001).
            if plan.get("label") and target_name != plan["label"]:
                continue
            if target not in valid_indices:
                out.append(Violation(
                    rule_id="MACRO-JT-001",
                    severity="error",
                    domain="macro",
                    target=f"step:{idx}",
                    expert_says=(
                        f"Jump target line {target} does not exist in this macro "
                        f"(valid: {sorted(valid_indices)})"
                    ),
                    fix_suggestion=(
                        "Recompute target after insertion; use the index-shift "
                        "table in .claude/rules/ma2-conventions.md"
                    ),
                ))
    return out


def check_jt_002_jump_target_is_store(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """MACRO-JT-002 (warning): Jump target points to a Store line — fragile."""
    by_index = {idx: cmd for idx, cmd in _commands(plan)}
    out: list[Violation] = []
    for idx, cmd in _commands(plan):
        for match in _MACRO_CALL_RE.finditer(cmd):
            target = int(match.group("line"))
            target_cmd = by_index.get(target, "")
            if re.match(r"^\s*Store\b", target_cmd, re.IGNORECASE):
                out.append(Violation(
                    rule_id="MACRO-JT-002",
                    severity="warning",
                    domain="macro",
                    target=f"step:{idx}",
                    expert_says=(
                        f"Jump target line {target} contains a Store — fragile "
                        "under future edits"
                    ),
                    fix_suggestion=(
                        "Use a labelled marker comment or split into two macros"
                    ),
                ))
    return out


def check_safety_001_destructive_without_noconfirm(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """MACRO-SAFETY-001 (error): Destructive command without /noconfirm."""
    out: list[Violation] = []
    for idx, cmd in _commands(plan):
        low = cmd.lower()
        if any(kw in low for kw in _DESTRUCTIVE_KEYWORDS) and "/noconfirm" not in low:
            out.append(Violation(
                rule_id="MACRO-SAFETY-001",
                severity="error",
                domain="macro",
                target=f"step:{idx}",
                expert_says="Destructive command without /noconfirm will hang the macro",
                fix_suggestion="Append /noconfirm or precede with explicit confirmation logic",
            ))
    return out


def check_safety_002_new_show_without_globalsettings(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """MACRO-SAFETY-002 (error): new_show without /globalsettings disables Telnet."""
    out: list[Violation] = []
    for idx, cmd in _commands(plan):
        low = cmd.lower()
        if "new_show" in low and "/globalsettings" not in low:
            out.append(Violation(
                rule_id="MACRO-SAFETY-002",
                severity="error",
                domain="macro",
                target=f"step:{idx}",
                expert_says="new_show without /globalsettings will disable Telnet",
                fix_suggestion="Append /globalsettings (always)",
            ))
    return out


def check_time_001_wait_instead_of_cmddelay(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """MACRO-TIME-001 (warning): 2+ consecutive Wait lines instead of CmdDelay."""
    out: list[Violation] = []
    prev_was_wait = False
    for idx, cmd in _commands(plan):
        is_wait = bool(re.match(r"^\s*Wait\b", cmd, re.IGNORECASE))
        if is_wait and prev_was_wait:
            out.append(Violation(
                rule_id="MACRO-TIME-001",
                severity="warning",
                domain="macro",
                target=f"step:{idx}",
                expert_says=(
                    "Consecutive Wait lines — busy-wait pattern instead of CmdDelay"
                ),
                fix_suggestion="Use CmdDelay <ms> (project convention)",
            ))
        prev_was_wait = is_wait
    return out


def check_var_001_getvar_without_setvar(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """MACRO-VAR-001 (error): GetVar reads a variable not previously SetVar-ed
    and not listed in context["session_vars"]."""
    session_vars = set((context or {}).get("session_vars", []))
    out: list[Violation] = []
    set_so_far: set[str] = set()
    for idx, cmd in _commands(plan):
        for setv in _SETVAR_RE.findall(cmd):
            set_so_far.add(setv)
        for setuv in _SETUSERVAR_RE.findall(cmd):
            set_so_far.add(setuv)
        for getv in _GETVAR_RE.findall(cmd):
            if getv not in set_so_far and getv not in session_vars:
                out.append(Violation(
                    rule_id="MACRO-VAR-001",
                    severity="error",
                    domain="macro",
                    target=f"step:{idx}",
                    expert_says=f"GetVar {getv} reads an uninitialised variable",
                    fix_suggestion="Add SetVar earlier or document the dependency",
                ))
    return out


def check_var_002_setvar_to_system_var(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """MACRO-VAR-002 (warning): SetVar targets a read-only system variable."""
    out: list[Violation] = []
    for idx, cmd in _commands(plan):
        for setv in _SETVAR_RE.findall(cmd):
            if setv.upper() in _SYSTEM_VARS:
                out.append(Violation(
                    rule_id="MACRO-VAR-002",
                    severity="warning",
                    domain="macro",
                    target=f"step:{idx}",
                    expert_says=f"SetVar targets read-only system variable {setv}",
                    fix_suggestion="Rename the variable with a user prefix (my_)",
                ))
    return out


def check_select_001_store_without_clearall(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """MACRO-SELECT-001 (error): Store without preceding ClearAll/Select."""
    out: list[Violation] = []
    cleared = False
    for idx, cmd in _commands(plan):
        low = cmd.lower()
        if "clearall" in low or re.search(r"\bselect\b", low):
            cleared = True
        if re.match(r"^\s*store\b", low) and not cleared:
            out.append(Violation(
                rule_id="MACRO-SELECT-001",
                severity="error",
                domain="macro",
                target=f"step:{idx}",
                expert_says="Store of selection-dependent target without preceding ClearAll/Select",
                fix_suggestion="Add ClearAll then explicit selection on the same line as Store",
            ))
    return out


def check_select_002_selection_after_fixturetype(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """MACRO-SELECT-002 (warning): Selection right after FixtureType ... Thru
    is a known timing race per .claude/rules/ma2-conventions.md."""
    out: list[Violation] = []
    prev_was_fixturetype_thru = False
    for idx, cmd in _commands(plan):
        if re.match(r"^\s*Selection\b", cmd, re.IGNORECASE) and prev_was_fixturetype_thru:
            out.append(Violation(
                rule_id="MACRO-SELECT-002",
                severity="warning",
                domain="macro",
                target=f"step:{idx}",
                expert_says=(
                    "Selection keyword after FixtureType X.M.1 Thru — known timing race"
                ),
                fix_suggestion=(
                    "Insert new lines around existing Store logic; do not modify "
                    "existing Store lines"
                ),
            ))
        prev_was_fixturetype_thru = bool(
            re.search(r"FixtureType\b.*\bThru\b", cmd, re.IGNORECASE)
        )
    return out


def check_link_001_macro_call_target_exists(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """MACRO-LINK-001 (warning): Macro calls another macro not in current show.

    Skipped when context lacks "existing_macros" (cannot evaluate)."""
    if context is None or "existing_macros" not in context:
        return []
    existing = set(context["existing_macros"])
    self_label = plan.get("label", "")
    out: list[Violation] = []
    for idx, cmd in _commands(plan):
        for match in _MACRO_CALL_RE.finditer(cmd):
            name = match.group("name")
            if name != self_label and name not in existing:
                out.append(Violation(
                    rule_id="MACRO-LINK-001",
                    severity="warning",
                    domain="macro",
                    target=f"step:{idx}",
                    expert_says=f"Macro call to {name!r} — not present in current show",
                    fix_suggestion=(
                        "Verify target macro is part of the same show or "
                        "document the cross-show dependency"
                    ),
                ))
    return out


def check_perm_001_rights_required(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """MACRO-PERM-001 (error): Macro requires rights operator lacks.

    Context shape:
        {"required_rights": {"Keyword": min_level, ...}, "user_rights_level": int}
    """
    if context is None:
        return []
    required = context.get("required_rights", {})
    user_level = context.get("user_rights_level", 5)  # default: assume admin
    if not required:
        return []
    out: list[Violation] = []
    for idx, cmd in _commands(plan):
        for keyword, min_level in required.items():
            if re.search(rf"\b{re.escape(keyword)}\b", cmd, re.IGNORECASE) \
                    and user_level < min_level:
                out.append(Violation(
                    rule_id="MACRO-PERM-001",
                    severity="error",
                    domain="macro",
                    target=f"step:{idx}",
                    expert_says=(
                        f"Macro uses {keyword!r} which requires rights level "
                        f">= {min_level}; current user has {user_level}"
                    ),
                    fix_suggestion="Reduce macro scope or document required rights",
                ))
    return out


def check_name_001_generic_label(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """MACRO-NAME-001 (advice): Generic or missing label."""
    label = plan.get("label", "").strip()
    if not label or re.match(r"^Macro\s+\d+$", label, re.IGNORECASE):
        return [Violation(
            rule_id="MACRO-NAME-001",
            severity="advice",
            domain="macro",
            target="macro:label",
            expert_says="Macro has no label or generic label like 'Macro 17'",
            fix_suggestion="Label the macro with intent (e.g. 'Verse to Chorus Lift')",
        )]
    return []


def check_park_001_park_without_unpark(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """MACRO-PARK-001 (warning): Park used without a paired Unpark macro elsewhere."""
    has_park = any(re.search(r"\bPark\b", cmd, re.IGNORECASE)
                   for _, cmd in _commands(plan))
    if not has_park:
        return []
    existing = (context or {}).get("existing_macros", [])
    has_unpark_companion = any(
        re.search(r"\bUnpark\b", name, re.IGNORECASE) for name in existing
    )
    if has_unpark_companion:
        return []
    return [Violation(
        rule_id="MACRO-PARK-001",
        severity="warning",
        domain="macro",
        target="macro:label",
        expert_says="Macro parks fixtures but no paired Unpark macro found",
        fix_suggestion="Add the paired unpark macro and reference it in this macro's notes",
    )]


def check_scope_001_hardcoded_exec_ref(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """MACRO-SCOPE-001 (advice): Hardcoded executor reference without prior
    SetUserVar to parameterize it."""
    out: list[Violation] = []
    has_setuservar = False
    for idx, cmd in _commands(plan):
        if _SETUSERVAR_RE.search(cmd):
            has_setuservar = True
        if _EXEC_REF_RE.search(cmd) and not has_setuservar:
            out.append(Violation(
                rule_id="MACRO-SCOPE-001",
                severity="advice",
                domain="macro",
                target=f"step:{idx}",
                expert_says=(
                    "Hardcoded executor reference (e.g. 1.1.1) — risky on operator's main page"
                ),
                fix_suggestion=(
                    "Make the executor target a SetUserVar parameter, or guard with "
                    "a current-page check"
                ),
            ))
    return out


def check_xml_001_xml_body_invalid(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """MACRO-XML-001 (error): body_xml fails XML schema validation."""
    body = plan.get("body_xml")
    if not body:
        return []
    try:
        ET.fromstring(body)
        return []
    except ET.ParseError as e:
        return [Violation(
            rule_id="MACRO-XML-001",
            severity="error",
            domain="macro",
            target="macro:body_xml",
            expert_says=f"Macro XML body fails schema validation: {e}",
            fix_suggestion=(
                "Regenerate with schema-aware emitter; check for unescaped quotes"
            ),
        )]


__all__ = [
    "check_jt_001_jump_target_exists",
    "check_jt_002_jump_target_is_store",
    "check_safety_001_destructive_without_noconfirm",
    "check_safety_002_new_show_without_globalsettings",
    "check_time_001_wait_instead_of_cmddelay",
    "check_var_001_getvar_without_setvar",
    "check_var_002_setvar_to_system_var",
    "check_select_001_store_without_clearall",
    "check_select_002_selection_after_fixturetype",
    "check_link_001_macro_call_target_exists",
    "check_perm_001_rights_required",
    "check_name_001_generic_label",
    "check_park_001_park_without_unpark",
    "check_scope_001_hardcoded_exec_ref",
    "check_xml_001_xml_body_invalid",
]

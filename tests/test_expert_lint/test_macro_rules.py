"""Macro-domain expert-lint rules.

Each rule has one passing-case and one failing-case test.
"""

import pytest

from src.expert_lint.macro_rules import (
    check_jt_001_jump_target_exists,
    check_jt_002_jump_target_is_store,
    check_link_001_macro_call_target_exists,
    check_name_001_generic_label,
    check_park_001_park_without_unpark,
    check_perm_001_rights_required,
    check_safety_001_destructive_without_noconfirm,
    check_safety_002_new_show_without_globalsettings,
    check_scope_001_hardcoded_exec_ref,
    check_select_001_store_without_clearall,
    check_select_002_selection_after_fixturetype,
    check_time_001_wait_instead_of_cmddelay,
    check_var_001_getvar_without_setvar,
    check_var_002_setvar_to_system_var,
    check_xml_001_xml_body_invalid,
)
from src.expert_lint.types import Violation


# ---------------------------------------------------------------------------
# JT-001 — jump target line number exists
# ---------------------------------------------------------------------------

def test_jt_001_no_violation_when_jump_target_valid():
    plan = {
        "kind": "macro",
        "lines": [
            {"index": 1, "command": "Go Sequence 5"},
            {"index": 2, "command": 'Go Macro 1."Loop".1'},
        ],
    }
    assert check_jt_001_jump_target_exists(plan, context=None) == []


def test_jt_001_flags_jump_to_nonexistent_line():
    plan = {
        "kind": "macro",
        "lines": [
            {"index": 1, "command": 'Go Macro 1."Loop".99'},
        ],
    }
    findings = check_jt_001_jump_target_exists(plan, context=None)
    assert len(findings) == 1
    v = findings[0]
    assert isinstance(v, Violation)
    assert v.rule_id == "MACRO-JT-001"
    assert v.severity == "error"
    assert v.target == "step:1"


# ---------------------------------------------------------------------------
# JT-002 — jump target points to a Store line
# ---------------------------------------------------------------------------

def test_jt_002_clean_when_target_is_not_store():
    plan = {"kind": "macro", "lines": [
        {"index": 1, "command": 'Go Macro 1."L".2'},
        {"index": 2, "command": "ClearAll"},
    ]}
    assert check_jt_002_jump_target_is_store(plan, context=None) == []


def test_jt_002_flags_when_target_is_store():
    plan = {"kind": "macro", "lines": [
        {"index": 1, "command": 'Go Macro 1."L".2'},
        {"index": 2, "command": "Store Cue 1 Sequence 99 /merge"},
    ]}
    findings = check_jt_002_jump_target_is_store(plan, context=None)
    assert any(v.rule_id == "MACRO-JT-002" for v in findings)


# ---------------------------------------------------------------------------
# SAFETY-001 — destructive without /noconfirm
# ---------------------------------------------------------------------------

def test_safety_001_clean_when_destructive_has_noconfirm():
    plan = {"kind": "macro", "lines": [
        {"index": 1, "command": "Delete Macro 99 /noconfirm"},
    ]}
    assert check_safety_001_destructive_without_noconfirm(plan, context=None) == []


def test_safety_001_flags_destructive_without_noconfirm():
    plan = {"kind": "macro", "lines": [
        {"index": 1, "command": "Delete Macro 99"},
    ]}
    findings = check_safety_001_destructive_without_noconfirm(plan, context=None)
    assert any(v.rule_id == "MACRO-SAFETY-001" and v.severity == "error" for v in findings)


# ---------------------------------------------------------------------------
# SAFETY-002 — new_show without /globalsettings
# ---------------------------------------------------------------------------

def test_safety_002_clean_when_new_show_has_globalsettings():
    plan = {"kind": "macro", "lines": [
        {"index": 1, "command": "new_show /globalsettings /noconfirm"},
    ]}
    assert check_safety_002_new_show_without_globalsettings(plan, context=None) == []


def test_safety_002_flags_missing_globalsettings():
    plan = {"kind": "macro", "lines": [
        {"index": 1, "command": "new_show /noconfirm"},
    ]}
    findings = check_safety_002_new_show_without_globalsettings(plan, context=None)
    assert any(v.rule_id == "MACRO-SAFETY-002" for v in findings)


# ---------------------------------------------------------------------------
# TIME-001 — consecutive Wait instead of CmdDelay
# ---------------------------------------------------------------------------

def test_time_001_clean_when_cmddelay_used():
    plan = {"kind": "macro", "lines": [
        {"index": 1, "command": "CmdDelay 500"},
        {"index": 2, "command": "Go Sequence 1"},
    ]}
    assert check_time_001_wait_instead_of_cmddelay(plan, context=None) == []


def test_time_001_flags_consecutive_wait():
    plan = {"kind": "macro", "lines": [
        {"index": 1, "command": "Wait 1"},
        {"index": 2, "command": "Wait 1"},
    ]}
    findings = check_time_001_wait_instead_of_cmddelay(plan, context=None)
    assert any(v.rule_id == "MACRO-TIME-001" for v in findings)


# ---------------------------------------------------------------------------
# VAR-001 — GetVar without prior SetVar (and not in context session_vars)
# ---------------------------------------------------------------------------

def test_var_001_clean_when_setvar_precedes():
    plan = {"kind": "macro", "lines": [
        {"index": 1, "command": "SetVar $foo 1"},
        {"index": 2, "command": "GetVar $foo"},
    ]}
    assert check_var_001_getvar_without_setvar(plan, context=None) == []


def test_var_001_flags_getvar_without_setvar():
    plan = {"kind": "macro", "lines": [
        {"index": 1, "command": "GetVar $foo"},
    ]}
    findings = check_var_001_getvar_without_setvar(plan, context=None)
    assert any(v.rule_id == "MACRO-VAR-001" for v in findings)


# ---------------------------------------------------------------------------
# VAR-002 — SetVar targets a system variable
# ---------------------------------------------------------------------------

def test_var_002_clean_when_user_variable():
    plan = {"kind": "macro", "lines": [
        {"index": 1, "command": "SetVar $my_count 1"},
    ]}
    assert check_var_002_setvar_to_system_var(plan, context=None) == []


def test_var_002_flags_setvar_to_system_var():
    plan = {"kind": "macro", "lines": [
        {"index": 1, "command": "SetVar $SHOWFILE foo"},
    ]}
    findings = check_var_002_setvar_to_system_var(plan, context=None)
    assert any(v.rule_id == "MACRO-VAR-002" for v in findings)


# ---------------------------------------------------------------------------
# SELECT-001 — Store without preceding ClearAll/Select
# ---------------------------------------------------------------------------

def test_select_001_clean_with_clearall_then_select_then_store():
    plan = {"kind": "macro", "lines": [
        {"index": 1, "command": "ClearAll"},
        {"index": 2, "command": "Select Fixture 1 Thru 10"},
        {"index": 3, "command": "Store Group 5 /o"},
    ]}
    assert check_select_001_store_without_clearall(plan, context=None) == []


def test_select_001_flags_store_without_clearall():
    plan = {"kind": "macro", "lines": [
        {"index": 1, "command": "Store Group 5 /o"},
    ]}
    findings = check_select_001_store_without_clearall(plan, context=None)
    assert any(v.rule_id == "MACRO-SELECT-001" for v in findings)


# ---------------------------------------------------------------------------
# SELECT-002 — Selection after FixtureType ... Thru
# ---------------------------------------------------------------------------

def test_select_002_clean_when_no_selection_after_fixturetype_thru():
    plan = {"kind": "macro", "lines": [
        {"index": 1, "command": "FixtureType 1.1 Thru"},
        {"index": 2, "command": "Store Group 5 /o"},
    ]}
    assert check_select_002_selection_after_fixturetype(plan, context=None) == []


def test_select_002_flags_selection_after_fixturetype():
    plan = {"kind": "macro", "lines": [
        {"index": 1, "command": "FixtureType 1.1 Thru"},
        {"index": 2, "command": "Selection"},
    ]}
    findings = check_select_002_selection_after_fixturetype(plan, context=None)
    assert any(v.rule_id == "MACRO-SELECT-002" for v in findings)


# ---------------------------------------------------------------------------
# LINK-001 — macro call to non-existent macro
# ---------------------------------------------------------------------------

def test_link_001_clean_when_target_exists():
    plan = {"kind": "macro", "lines": [
        {"index": 1, "command": 'Go Macro 1."Existing".1'},
    ]}
    ctx = {"existing_macros": ["Existing"]}
    assert check_link_001_macro_call_target_exists(plan, context=ctx) == []


def test_link_001_flags_missing_target():
    plan = {"kind": "macro", "lines": [
        {"index": 1, "command": 'Go Macro 1."MissingMacro".1'},
    ]}
    ctx = {"existing_macros": ["OtherMacro"]}
    findings = check_link_001_macro_call_target_exists(plan, context=ctx)
    assert any(v.rule_id == "MACRO-LINK-001" for v in findings)


# ---------------------------------------------------------------------------
# PERM-001 — requires rights operator lacks
# ---------------------------------------------------------------------------

def test_perm_001_clean_when_rights_sufficient():
    plan = {"kind": "macro", "lines": [
        {"index": 1, "command": "Patch Fixture 1 At 1.1"},
    ]}
    ctx = {"required_rights": {"Patch": 4}, "user_rights_level": 4}
    assert check_perm_001_rights_required(plan, context=ctx) == []


def test_perm_001_flags_when_rights_insufficient():
    plan = {"kind": "macro", "lines": [
        {"index": 1, "command": "Patch Fixture 1 At 1.1"},
    ]}
    ctx = {"required_rights": {"Patch": 4}, "user_rights_level": 2}
    findings = check_perm_001_rights_required(plan, context=ctx)
    assert any(v.rule_id == "MACRO-PERM-001" for v in findings)


# ---------------------------------------------------------------------------
# NAME-001 — generic or missing label
# ---------------------------------------------------------------------------

def test_name_001_clean_when_label_is_descriptive():
    plan = {"kind": "macro", "label": "Verse to Chorus Lift", "lines": []}
    assert check_name_001_generic_label(plan, context=None) == []


def test_name_001_flags_generic_label():
    plan = {"kind": "macro", "label": "Macro 17", "lines": []}
    findings = check_name_001_generic_label(plan, context=None)
    assert any(v.rule_id == "MACRO-NAME-001" for v in findings)


# ---------------------------------------------------------------------------
# PARK-001 — Park without matching Unpark
# ---------------------------------------------------------------------------

def test_park_001_clean_when_unpark_exists_elsewhere():
    plan = {"kind": "macro", "label": "Park Movers", "lines": [
        {"index": 1, "command": "Park Group 2"},
    ]}
    ctx = {"existing_macros": ["Unpark Movers"]}
    assert check_park_001_park_without_unpark(plan, context=ctx) == []


def test_park_001_flags_park_without_unpark_companion():
    plan = {"kind": "macro", "label": "Park Movers", "lines": [
        {"index": 1, "command": "Park Group 2"},
    ]}
    ctx = {"existing_macros": ["Some Other Macro"]}
    findings = check_park_001_park_without_unpark(plan, context=ctx)
    assert any(v.rule_id == "MACRO-PARK-001" for v in findings)


# ---------------------------------------------------------------------------
# SCOPE-001 — hardcoded executor reference without SetUserVar
# ---------------------------------------------------------------------------

def test_scope_001_clean_when_setuservar_precedes():
    plan = {"kind": "macro", "lines": [
        {"index": 1, "command": "SetUserVar $exec '1.1.1'"},
        {"index": 2, "command": "Go Executor 1.1.1"},
    ]}
    assert check_scope_001_hardcoded_exec_ref(plan, context=None) == []


def test_scope_001_flags_hardcoded_executor():
    plan = {"kind": "macro", "lines": [
        {"index": 1, "command": "Go Executor 1.1.1"},
    ]}
    findings = check_scope_001_hardcoded_exec_ref(plan, context=None)
    assert any(v.rule_id == "MACRO-SCOPE-001" for v in findings)


# ---------------------------------------------------------------------------
# XML-001 — body_xml fails XML schema validation
# ---------------------------------------------------------------------------

def test_xml_001_clean_when_xml_valid():
    plan = {"kind": "macro", "body_xml": "<Macro><Line nr=\"1\">ClearAll</Line></Macro>", "lines": []}
    assert check_xml_001_xml_body_invalid(plan, context=None) == []


def test_xml_001_flags_invalid_xml():
    plan = {"kind": "macro", "body_xml": "<Macro><Line>unclosed", "lines": []}
    findings = check_xml_001_xml_body_invalid(plan, context=None)
    assert any(v.rule_id == "MACRO-XML-001" for v in findings)

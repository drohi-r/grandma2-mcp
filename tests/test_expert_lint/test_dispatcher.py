"""Dispatcher routes plan + domain to the right rule list and applies cross-cutting rules."""

import pytest

from src.expert_lint import expert_lint


def test_dispatcher_macro_returns_list():
    plan = {"kind": "macro", "lines": []}
    findings = expert_lint(plan, domain="macro", context=None)
    assert isinstance(findings, list)


def test_dispatcher_surfaces_specific_violation():
    plan = {
        "kind": "macro",
        "lines": [{"index": 1, "command": 'Go Macro 1."Self".99'}],
        "label": "Self",
    }
    findings = expert_lint(plan, domain="macro", context=None)
    assert any(v.rule_id == "MACRO-JT-001" for v in findings)


def test_dispatcher_unknown_domain_raises():
    with pytest.raises(ValueError, match="unknown domain"):
        expert_lint({}, domain="bogus", context=None)  # type: ignore[arg-type]


def test_dispatcher_runs_busking_rules():
    plan = {"kind": "busking", "strategy": "rock-band", "executors": [],
            "fader_bank_layout": "muscle-memory"}
    findings = expert_lint(plan, domain="busking", context=None)
    assert any(v.rule_id == "BUSK-SUB-001" for v in findings)


def test_dispatcher_runs_show_rules():
    plan = {"kind": "show", "strategy": "rock-band", "preset_strategy": "full-coverage",
            "cuelists": [], "fixtures": [], "worlds": [], "views": []}
    findings = expert_lint(plan, domain="show", context=None)
    # Multiple rules will fire on an empty rock-band show; verify we get a list
    assert isinstance(findings, list)


def test_dispatcher_runs_preset_rules():
    plan = {"kind": "preset", "strategy": "full-coverage",
            "reference_fixtures": {}, "plan": [], "fixture_types": []}
    findings = expert_lint(plan, domain="preset", context=None)
    assert any(v.rule_id == "PRESET-COVER-002" for v in findings)


def test_dispatcher_runs_layout_rules():
    plan = {"kind": "layout", "screen": 1, "template": "busking-master",
            "content": [], "screen_native_resolution": (1920, 1080),
            "cell_size": (100, 50)}
    findings = expert_lint(plan, domain="layout", context=None)
    assert any(v.rule_id == "LAYOUT-REQ-001" for v in findings)


def test_cross_cutting_purpose_field_advice():
    """§C.6 — every plan step has a `purpose` field; empty triggers advice."""
    plan = {
        "kind": "show", "strategy": "corporate", "preset_strategy": "minimal-viable",
        "cuelists": [{"id": 1, "label": "Main", "tracking": "non-tracking",
                      "priority": "normal", "off_time_ms": 500, "cues": []}],
        "fixtures": [], "worlds": [], "views": ["run"],
        "steps": [{"order": 1, "command": "Store Cue 1 Sequence 1", "purpose": ""}],
    }
    findings = expert_lint(plan, domain="show", context=None)
    assert any(v.rule_id == "CROSSCUT-PURPOSE-001" for v in findings)


def test_cross_cutting_no_purpose_violation_when_filled():
    plan = {
        "kind": "show", "strategy": "corporate", "preset_strategy": "minimal-viable",
        "cuelists": [], "fixtures": [], "worlds": [], "views": [],
        "steps": [{"order": 1, "command": "x", "purpose": "store opening cue"}],
    }
    findings = expert_lint(plan, domain="show", context=None)
    assert not any(v.rule_id == "CROSSCUT-PURPOSE-001" for v in findings)

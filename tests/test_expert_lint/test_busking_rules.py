"""Busking-domain expert-lint rules (BUSK-*)."""

from src.expert_lint.busking_rules import (
    check_comp_001_companion_schema_invalid,
    check_comp_002_companion_grid_noncontiguous,
    check_conf_001_executor_slot_collision,
    check_htp_001_intensity_not_htp,
    check_key_001_missing_key_fixture,
    check_kill_001_no_kill_color,
    check_kill_002_no_kill_fx,
    check_label_001_executor_label_missing,
    check_layout_001_layout_not_muscle_memory,
    check_ltp_001_color_executor_is_htp,
    check_prio_001_blackout_sub_priority,
    check_prio_002_all_executors_normal,
    check_prio_003_blinder_priority,
    check_sub_001_blackout_independent,
    check_sub_002_speed_master_missing,
    check_tap_001_tap_tempo_missing,
)


def _plan(strategy: str = "rock-band", **overrides) -> dict:
    base = {
        "kind": "busking",
        "strategy": strategy,
        "executors": [],
        "companion_grid": [],
        "fader_bank_layout": "muscle-memory",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# SUB-001 — blackout sub independent of Grand Master
# ---------------------------------------------------------------------------

def test_sub_001_clean_when_blackout_sub_present():
    plan = _plan(executors=[
        {"slot": "1.1.1", "role": "blackout-sub", "priority": "super", "label": "BO", "function": "macro"},
    ])
    assert check_sub_001_blackout_independent(plan, None) == []


def test_sub_001_flags_missing_blackout_sub():
    plan = _plan(executors=[
        {"slot": "1.1.1", "role": "intensity", "priority": "normal", "label": "Wash", "function": "fader"},
    ])
    findings = check_sub_001_blackout_independent(plan, None)
    assert any(v.rule_id == "BUSK-SUB-001" and v.severity == "error" for v in findings)


# ---------------------------------------------------------------------------
# SUB-002 — speed master not assigned
# ---------------------------------------------------------------------------

def test_sub_002_clean_when_speed_master_present():
    plan = _plan(executors=[
        {"slot": "1.1.1", "role": "fx", "priority": "normal", "label": "FX1", "function": "speedmaster"},
    ])
    assert check_sub_002_speed_master_missing(plan, None) == []


def test_sub_002_flags_no_speed_master():
    plan = _plan(strategy="rock-band", executors=[])
    findings = check_sub_002_speed_master_missing(plan, None)
    assert any(v.rule_id == "BUSK-SUB-002" for v in findings)


# ---------------------------------------------------------------------------
# PRIO-001 — blackout sub priority is Super
# ---------------------------------------------------------------------------

def test_prio_001_clean_when_blackout_is_super():
    plan = _plan(executors=[
        {"slot": "1.1.1", "role": "blackout-sub", "priority": "super", "label": "BO", "function": "macro"},
    ])
    assert check_prio_001_blackout_sub_priority(plan, None) == []


def test_prio_001_flags_blackout_not_super():
    plan = _plan(executors=[
        {"slot": "1.1.1", "role": "blackout-sub", "priority": "normal", "label": "BO", "function": "macro"},
    ])
    findings = check_prio_001_blackout_sub_priority(plan, None)
    assert any(v.rule_id == "BUSK-PRIO-001" for v in findings)


# ---------------------------------------------------------------------------
# PRIO-002 — all executors are Normal (no discrimination)
# ---------------------------------------------------------------------------

def test_prio_002_clean_when_priority_mixed():
    plan = _plan(executors=[
        {"slot": "1.1.1", "role": "intensity", "priority": "high", "label": "x", "function": "fader"},
        {"slot": "1.1.2", "role": "fx", "priority": "normal", "label": "y", "function": "fader"},
    ])
    assert check_prio_002_all_executors_normal(plan, None) == []


def test_prio_002_flags_all_normal():
    plan = _plan(executors=[
        {"slot": "1.1.1", "role": "intensity", "priority": "normal", "label": "x", "function": "fader"},
        {"slot": "1.1.2", "role": "fx", "priority": "normal", "label": "y", "function": "fader"},
    ])
    findings = check_prio_002_all_executors_normal(plan, None)
    assert any(v.rule_id == "BUSK-PRIO-002" for v in findings)


# ---------------------------------------------------------------------------
# PRIO-003 — blinders not High in rock-band/dj
# ---------------------------------------------------------------------------

def test_prio_003_clean_when_blinder_high():
    plan = _plan(strategy="rock-band", executors=[
        {"slot": "1.1.1", "role": "blinder", "priority": "high", "label": "Blind", "function": "fader"},
    ])
    assert check_prio_003_blinder_priority(plan, None) == []


def test_prio_003_flags_blinder_normal():
    plan = _plan(strategy="rock-band", executors=[
        {"slot": "1.1.1", "role": "blinder", "priority": "normal", "label": "Blind", "function": "fader"},
    ])
    findings = check_prio_003_blinder_priority(plan, None)
    assert any(v.rule_id == "BUSK-PRIO-003" for v in findings)


# ---------------------------------------------------------------------------
# KILL-001 — no kill-color (rock-band/dj)
# ---------------------------------------------------------------------------

def test_kill_001_clean_when_kill_color_present():
    plan = _plan(strategy="dj", executors=[
        {"slot": "1.1.1", "role": "kill-color", "priority": "high", "label": "Kill Color", "function": "macro"},
    ])
    assert check_kill_001_no_kill_color(plan, None) == []


def test_kill_001_flags_missing_kill_color():
    plan = _plan(strategy="dj", executors=[])
    findings = check_kill_001_no_kill_color(plan, None)
    assert any(v.rule_id == "BUSK-KILL-001" for v in findings)


# ---------------------------------------------------------------------------
# KILL-002 — no kill-fx (rock-band/dj)
# ---------------------------------------------------------------------------

def test_kill_002_clean_when_kill_fx_present():
    plan = _plan(strategy="rock-band", executors=[
        {"slot": "1.1.1", "role": "kill-fx", "priority": "high", "label": "Kill FX", "function": "macro"},
    ])
    assert check_kill_002_no_kill_fx(plan, None) == []


def test_kill_002_flags_missing_kill_fx():
    plan = _plan(strategy="rock-band", executors=[])
    findings = check_kill_002_no_kill_fx(plan, None)
    assert any(v.rule_id == "BUSK-KILL-002" for v in findings)


# ---------------------------------------------------------------------------
# TAP-001 — tap-tempo missing
# ---------------------------------------------------------------------------

def test_tap_001_clean_when_tap_executor_present():
    plan = _plan(strategy="dj", executors=[
        {"slot": "1.1.1", "role": "tap", "priority": "normal", "label": "Tap", "function": "tap"},
    ])
    assert check_tap_001_tap_tempo_missing(plan, None) == []


def test_tap_001_flags_missing_tap_executor():
    plan = _plan(strategy="dj", executors=[])
    findings = check_tap_001_tap_tempo_missing(plan, None)
    assert any(v.rule_id == "BUSK-TAP-001" for v in findings)


# ---------------------------------------------------------------------------
# LAYOUT-001 — fader bank layout deviates from muscle-memory
# ---------------------------------------------------------------------------

def test_layout_001_clean_when_muscle_memory():
    plan = _plan(fader_bank_layout="muscle-memory")
    assert check_layout_001_layout_not_muscle_memory(plan, None) == []


def test_layout_001_flags_sequential_layout():
    plan = _plan(fader_bank_layout="sequential")
    findings = check_layout_001_layout_not_muscle_memory(plan, None)
    assert any(v.rule_id == "BUSK-LAYOUT-001" for v in findings)


# ---------------------------------------------------------------------------
# CONF-001 — two executors share the same slot
# ---------------------------------------------------------------------------

def test_conf_001_clean_when_slots_unique():
    plan = _plan(executors=[
        {"slot": "1.1.1", "role": "x", "priority": "normal", "label": "a", "function": "f"},
        {"slot": "1.1.2", "role": "y", "priority": "normal", "label": "b", "function": "f"},
    ])
    assert check_conf_001_executor_slot_collision(plan, None) == []


def test_conf_001_flags_slot_collision():
    plan = _plan(executors=[
        {"slot": "1.1.1", "role": "x", "priority": "normal", "label": "a", "function": "f"},
        {"slot": "1.1.1", "role": "y", "priority": "normal", "label": "b", "function": "f"},
    ])
    findings = check_conf_001_executor_slot_collision(plan, None)
    assert any(v.rule_id == "BUSK-CONF-001" and v.severity == "error" for v in findings)


# ---------------------------------------------------------------------------
# LABEL-001 — empty / generic label
# ---------------------------------------------------------------------------

def test_label_001_clean_when_labels_descriptive():
    plan = _plan(executors=[
        {"slot": "1.1.1", "role": "x", "priority": "normal", "label": "Wash Blue", "function": "f"},
    ])
    assert check_label_001_executor_label_missing(plan, None) == []


def test_label_001_flags_generic_label():
    plan = _plan(executors=[
        {"slot": "1.1.1", "role": "x", "priority": "normal", "label": "Exec 5", "function": "f"},
    ])
    findings = check_label_001_executor_label_missing(plan, None)
    assert any(v.rule_id == "BUSK-LABEL-001" for v in findings)


# ---------------------------------------------------------------------------
# HTP-001 — intensity submaster not HTP
# ---------------------------------------------------------------------------

def test_htp_001_clean_when_intensity_is_htp():
    plan = _plan(executors=[
        {"slot": "1.1.1", "role": "intensity-submaster", "priority": "htp", "label": "Wash", "function": "f"},
    ])
    assert check_htp_001_intensity_not_htp(plan, None) == []


def test_htp_001_flags_intensity_not_htp():
    plan = _plan(executors=[
        {"slot": "1.1.1", "role": "intensity-submaster", "priority": "normal", "label": "Wash", "function": "f"},
    ])
    findings = check_htp_001_intensity_not_htp(plan, None)
    assert any(v.rule_id == "BUSK-HTP-001" for v in findings)


# ---------------------------------------------------------------------------
# LTP-001 — color executor is HTP (should be LTP)
# ---------------------------------------------------------------------------

def test_ltp_001_clean_when_color_is_ltp():
    plan = _plan(executors=[
        {"slot": "1.1.1", "role": "color", "priority": "normal", "label": "Color", "function": "f"},
    ])
    assert check_ltp_001_color_executor_is_htp(plan, None) == []


def test_ltp_001_flags_color_set_to_htp():
    plan = _plan(executors=[
        {"slot": "1.1.1", "role": "color", "priority": "htp", "label": "Color", "function": "f"},
    ])
    findings = check_ltp_001_color_executor_is_htp(plan, None)
    assert any(v.rule_id == "BUSK-LTP-001" for v in findings)


# ---------------------------------------------------------------------------
# COMP-001 — Companion config fails schema validation
# ---------------------------------------------------------------------------

def test_comp_001_clean_when_companion_config_absent():
    plan = _plan()  # no companion_config field
    assert check_comp_001_companion_schema_invalid(plan, None) == []


def test_comp_001_flags_invalid_companion_config():
    plan = _plan(companion_config={"version": "wrong-shape"})
    ctx = {"validate_companion_schema": lambda c: False}
    findings = check_comp_001_companion_schema_invalid(plan, ctx)
    assert any(v.rule_id == "BUSK-COMP-001" for v in findings)


# ---------------------------------------------------------------------------
# COMP-002 — companion_grid has non-contiguous rows
# ---------------------------------------------------------------------------

def test_comp_002_clean_when_grid_contiguous():
    plan = _plan(companion_grid=[
        {"row": 0, "cells": [{"label": "a"}]},
        {"row": 1, "cells": [{"label": "b"}]},
    ])
    assert check_comp_002_companion_grid_noncontiguous(plan, None) == []


def test_comp_002_flags_non_contiguous_grid():
    plan = _plan(companion_grid=[
        {"row": 0, "cells": [{"label": "a"}]},
        {"row": 2, "cells": [{"label": "b"}]},  # row 1 is missing
    ])
    findings = check_comp_002_companion_grid_noncontiguous(plan, None)
    assert any(v.rule_id == "BUSK-COMP-002" for v in findings)


# ---------------------------------------------------------------------------
# KEY-001 — no KEY fixture (rock-band/broadcast/theatrical)
# ---------------------------------------------------------------------------

def test_key_001_clean_when_key_fixture_present():
    plan = _plan(strategy="rock-band", executors=[
        {"slot": "1.1.1", "role": "key-fixture", "priority": "high", "label": "KEY", "function": "f"},
    ])
    assert check_key_001_missing_key_fixture(plan, None) == []


def test_key_001_flags_missing_key_fixture():
    plan = _plan(strategy="rock-band", executors=[])
    findings = check_key_001_missing_key_fixture(plan, None)
    assert any(v.rule_id == "BUSK-KEY-001" for v in findings)

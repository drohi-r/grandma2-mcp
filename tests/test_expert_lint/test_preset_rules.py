"""Preset-library expert-lint rules (PRESET-*)."""

from src.expert_lint.preset_rules import (
    check_clone_001_could_clone,
    check_cover_001_attribute_uncovered,
    check_cover_002_no_cardinal_hues,
    check_cover_003_no_warm_cool_wash,
    check_empty_001_empty_preset_slot,
    check_hsb_001_rgb_when_hsb_expected,
    check_mib_001_movers_without_mib_preset,
    check_name_001_naming_convention_inconsistent,
    check_num_001_duplicate_preset_number,
    check_num_002_numbering_not_type_convention,
    check_ref_001_no_reference_fixture,
    check_scope_001_color_selective_when_universal,
    check_scope_002_gobo_universal,
)


def _plan(**overrides) -> dict:
    base = {
        "kind": "preset",
        "strategy": "full-coverage",
        "reference_fixtures": {"wash": 1, "mover": 11},
        "plan": [],
        "fixture_types": ["wash", "mover"],
        "naming_convention": "{type}_{name}",
    }
    base.update(overrides)
    return base


# REF-001
def test_ref_001_clean_when_reference_chosen():
    plan = _plan(reference_fixtures={"wash": 1, "mover": 11})
    ctx = {"fixtures": [{"id": 1, "type": "wash"}, {"id": 2, "type": "wash"}]}
    assert check_ref_001_no_reference_fixture(plan, ctx) == []


def test_ref_001_flags_missing_reference_when_multiple_of_type():
    plan = _plan(reference_fixtures={})
    ctx = {"fixtures": [{"id": 1, "type": "wash"}, {"id": 2, "type": "wash"}]}
    findings = check_ref_001_no_reference_fixture(plan, ctx)
    assert any(v.rule_id == "PRESET-REF-001" for v in findings)


# COVER-001
def test_cover_001_clean_when_attribute_covered():
    plan = _plan(plan=[
        {"preset_type": 4, "preset_id": 1, "name": "Red", "scope": "universal",
         "target_fixture_types": [], "values": {"R": 100}, "covers_attributes": ["R", "G", "B"]},
    ])
    ctx = {"required_attributes": {"wash": ["R", "G", "B"]}}
    assert check_cover_001_attribute_uncovered(plan, ctx) == []


def test_cover_001_flags_uncovered_attribute():
    plan = _plan(plan=[
        {"preset_type": 4, "preset_id": 1, "name": "Red", "scope": "universal",
         "target_fixture_types": [], "values": {"R": 100}, "covers_attributes": ["R"]},
    ])
    ctx = {"required_attributes": {"wash": ["R", "G", "B"]}}
    findings = check_cover_001_attribute_uncovered(plan, ctx)
    assert any(v.rule_id == "PRESET-COVER-001" for v in findings)


# COVER-002
def test_cover_002_clean_when_cardinal_hues_present():
    plan = _plan(plan=[
        {"preset_type": 4, "preset_id": 1, "name": "Red"},
        {"preset_type": 4, "preset_id": 2, "name": "Green"},
        {"preset_type": 4, "preset_id": 3, "name": "Blue"},
        {"preset_type": 4, "preset_id": 4, "name": "White"},
    ])
    assert check_cover_002_no_cardinal_hues(plan, None) == []


def test_cover_002_flags_missing_cardinal_hues():
    plan = _plan(plan=[
        {"preset_type": 4, "preset_id": 1, "name": "Magenta"},
    ])
    findings = check_cover_002_no_cardinal_hues(plan, None)
    assert any(v.rule_id == "PRESET-COVER-002" for v in findings)


# COVER-003
def test_cover_003_clean_when_warm_cool_present():
    plan = _plan(plan=[
        {"preset_type": 4, "preset_id": 10, "name": "Warm Wash"},
        {"preset_type": 4, "preset_id": 11, "name": "Cool Wash"},
    ])
    assert check_cover_003_no_warm_cool_wash(plan, None) == []


def test_cover_003_flags_missing_warm_cool():
    plan = _plan(plan=[
        {"preset_type": 4, "preset_id": 1, "name": "Red"},
    ])
    findings = check_cover_003_no_warm_cool_wash(plan, None)
    assert any(v.rule_id == "PRESET-COVER-003" for v in findings)


# SCOPE-001
def test_scope_001_clean_when_color_universal():
    plan = _plan(plan=[
        {"preset_type": 4, "preset_id": 1, "name": "Red", "scope": "universal"},
    ])
    assert check_scope_001_color_selective_when_universal(plan, None) == []


def test_scope_001_flags_color_selective():
    plan = _plan(plan=[
        {"preset_type": 4, "preset_id": 1, "name": "Red", "scope": "selective",
         "target_fixture_types": ["wash"]},
    ])
    findings = check_scope_001_color_selective_when_universal(plan, None)
    assert any(v.rule_id == "PRESET-SCOPE-001" for v in findings)


# SCOPE-002
def test_scope_002_clean_when_gobo_selective():
    plan = _plan(plan=[
        {"preset_type": 3, "preset_id": 1, "name": "Dots", "scope": "selective",
         "target_fixture_types": ["mover"]},
    ])
    assert check_scope_002_gobo_universal(plan, None) == []


def test_scope_002_flags_gobo_universal():
    plan = _plan(plan=[
        {"preset_type": 3, "preset_id": 1, "name": "Dots", "scope": "universal",
         "target_fixture_types": []},
    ])
    findings = check_scope_002_gobo_universal(plan, None)
    assert any(v.rule_id == "PRESET-SCOPE-002" for v in findings)


# NAME-001
def test_preset_name_001_clean_when_naming_consistent():
    plan = _plan(plan=[
        {"preset_type": 4, "preset_id": 1, "name": "color_red"},
        {"preset_type": 4, "preset_id": 2, "name": "color_green"},
    ], naming_convention="{type}_{name}")
    assert check_name_001_naming_convention_inconsistent(plan, None) == []


def test_preset_name_001_flags_inconsistent_naming():
    plan = _plan(plan=[
        {"preset_type": 4, "preset_id": 1, "name": "color_red"},
        {"preset_type": 4, "preset_id": 2, "name": "Green Color"},  # breaks convention
    ], naming_convention="{type}_{name}")
    findings = check_name_001_naming_convention_inconsistent(plan, None)
    assert any(v.rule_id == "PRESET-NAME-001" for v in findings)


# NUM-001
def test_num_001_clean_when_unique_numbers():
    plan = _plan(plan=[
        {"preset_type": 4, "preset_id": 1, "name": "Red"},
        {"preset_type": 4, "preset_id": 2, "name": "Green"},
    ])
    assert check_num_001_duplicate_preset_number(plan, None) == []


def test_num_001_flags_duplicate_within_type():
    plan = _plan(plan=[
        {"preset_type": 4, "preset_id": 1, "name": "Red"},
        {"preset_type": 4, "preset_id": 1, "name": "Crimson"},
    ])
    findings = check_num_001_duplicate_preset_number(plan, None)
    assert any(v.rule_id == "PRESET-NUM-001" and v.severity == "error" for v in findings)


# NUM-002
def test_num_002_clean_when_type_convention_followed():
    plan = _plan(plan=[
        {"preset_type": 4, "preset_id": 1, "name": "Red"},  # color is type 4
    ])
    assert check_num_002_numbering_not_type_convention(plan, None) == []


def test_num_002_flags_wrong_type_convention():
    plan = _plan(plan=[
        {"preset_type": 99, "preset_id": 1, "name": "Red"},  # invalid type
    ])
    findings = check_num_002_numbering_not_type_convention(plan, None)
    assert any(v.rule_id == "PRESET-NUM-002" for v in findings)


# MIB-001 (preset domain)
def test_preset_mib_001_clean_when_mib_presets_for_movers():
    plan = _plan(plan=[
        {"preset_type": 2, "preset_id": 1, "name": "MIB Home", "mib_aware": True,
         "target_fixture_types": ["mover"]},
    ])
    ctx = {"fixture_types_in_patch": ["mover"]}
    assert check_mib_001_movers_without_mib_preset(plan, ctx) == []


def test_preset_mib_001_flags_movers_without_mib():
    plan = _plan(plan=[])
    ctx = {"fixture_types_in_patch": ["mover"]}
    findings = check_mib_001_movers_without_mib_preset(plan, ctx)
    assert any(v.rule_id == "PRESET-MIB-001" for v in findings)


# EMPTY-001
def test_empty_001_clean_when_all_slots_populated():
    plan = _plan(plan=[
        {"preset_type": 4, "preset_id": 1, "name": "Red", "values": {"R": 100}},
    ])
    assert check_empty_001_empty_preset_slot(plan, None) == []


def test_empty_001_flags_empty_slot():
    plan = _plan(plan=[
        {"preset_type": 4, "preset_id": 1, "name": "Red", "values": {}},
    ])
    findings = check_empty_001_empty_preset_slot(plan, None)
    assert any(v.rule_id == "PRESET-EMPTY-001" and v.severity == "error" for v in findings)


def test_empty_001_skips_declared_values_none():
    """values=None signals 'declared by architect; will be populated later' —
    PRESET-EMPTY-001 must not flag it."""
    plan = _plan(plan=[
        {"preset_type": 3, "preset_id": 10, "name": "Mover Gobo",
         "scope": "selective", "target_fixture_types": ["Mover"], "values": None},
    ])
    findings = check_empty_001_empty_preset_slot(plan, None)
    assert not any(v.rule_id == "PRESET-EMPTY-001" for v in findings)


# CLONE-001
def test_clone_001_clean_when_no_clone_opportunity():
    plan = _plan(plan=[
        {"preset_type": 3, "preset_id": 1, "name": "Dots", "scope": "selective",
         "target_fixture_types": ["mover"]},
    ])
    assert check_clone_001_could_clone(plan, None) == []


def test_clone_001_flags_similar_types_could_clone():
    plan = _plan(plan=[
        {"preset_type": 3, "preset_id": 1, "name": "Dots", "scope": "selective",
         "target_fixture_types": ["mover_a"]},
    ], fixture_types=["mover_a", "mover_b"])
    ctx = {"similar_types": {"mover_a": ["mover_b"]}}
    findings = check_clone_001_could_clone(plan, ctx)
    assert any(v.rule_id == "PRESET-CLONE-001" for v in findings)


# HSB-001
def test_hsb_001_clean_when_hsb_used():
    plan = _plan(plan=[
        {"preset_type": 4, "preset_id": 1, "name": "Red", "color_model": "HSB"},
    ], strategy="constrained-color")
    assert check_hsb_001_rgb_when_hsb_expected(plan, None) == []


def test_hsb_001_flags_rgb_when_hsb_expected():
    plan = _plan(plan=[
        {"preset_type": 4, "preset_id": 1, "name": "Red", "color_model": "RGB"},
    ], strategy="constrained-color")
    findings = check_hsb_001_rgb_when_hsb_expected(plan, None)
    assert any(v.rule_id == "PRESET-HSB-001" for v in findings)

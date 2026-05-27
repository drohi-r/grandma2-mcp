"""Show-creation expert-lint rules (SHOW-*)."""

from src.expert_lint.show_rules import (
    check_black_001_no_panic_blackout_cue,
    check_cover_001_uncovered_fixtures,
    check_emerg_001_no_emergency_cuelist,
    check_mib_001_movers_have_mib,
    check_mib_002_mib_on_dimmer_only,
    check_note_001_generic_cue_note,
    check_off_001_off_time_missing,
    check_prio_001_all_cuelists_normal,
    check_ref_001_hard_values_when_preset_expected,
    check_seq_001_generic_sequence_label,
    check_track_001_block_at_song_boundary,
    check_track_002_nontracking_with_wrap_no_softltp,
    check_view_001_missing_required_view,
    check_world_001_missing_per_section_worlds,
)


def _show(strategy: str = "rock-band", **overrides) -> dict:
    base = {
        "kind": "show",
        "strategy": strategy,
        "cuelists": [],
        "fixtures": [],
        "worlds": [],
        "views": ["programmer", "run", "busking-fallback"],
        "preset_strategy": "full-coverage",
    }
    base.update(overrides)
    return base


# TRACK-001
def test_track_001_clean_when_block_at_boundary():
    cl = [{"id": 1, "label": "Song1", "tracking": "track", "priority": "normal",
           "off_time_ms": 1000, "section": "song",
           "cues": [
               {"id": 1.0, "label": "v1", "block": False},
               {"id": 2.0, "label": "v1-end", "block": True},  # block at boundary
           ]}]
    plan = _show(cuelists=cl)
    assert check_track_001_block_at_song_boundary(plan, None) == []


def test_track_001_flags_no_block_at_boundary():
    cl = [{"id": 1, "label": "Song1", "tracking": "track", "priority": "normal",
           "off_time_ms": 1000, "section": "song",
           "cues": [
               {"id": 1.0, "label": "v1", "block": False},
               {"id": 2.0, "label": "v1-end", "block": False},
           ]}]
    plan = _show(strategy="rock-band", cuelists=cl)
    findings = check_track_001_block_at_song_boundary(plan, None)
    assert any(v.rule_id == "SHOW-TRACK-001" for v in findings)


# TRACK-002
def test_track_002_clean_when_softltp_set():
    cl = [{"id": 1, "label": "X", "tracking": "non-tracking", "priority": "normal",
           "options": {"wrap": True, "softltp": True}, "cues": []}]
    plan = _show(cuelists=cl)
    assert check_track_002_nontracking_with_wrap_no_softltp(plan, None) == []


def test_track_002_flags_wrap_without_softltp_in_nontracking():
    cl = [{"id": 1, "label": "X", "tracking": "non-tracking", "priority": "normal",
           "options": {"wrap": True, "softltp": False}, "cues": []}]
    plan = _show(cuelists=cl)
    findings = check_track_002_nontracking_with_wrap_no_softltp(plan, None)
    assert any(v.rule_id == "SHOW-TRACK-002" for v in findings)


# MIB-001
def test_mib_001_clean_when_mib_cues_present_for_movers():
    plan = _show(
        fixtures=[{"id": 1, "type": "mover", "covered_by_any_cue": True}],
        cuelists=[{"id": 1, "label": "X", "tracking": "track", "priority": "normal",
                   "cues": [{"id": 1.0, "label": "x", "is_mib": True}]}],
        movers_present=True,
    )
    assert check_mib_001_movers_have_mib(plan, None) == []


def test_mib_001_flags_movers_without_mib():
    plan = _show(
        strategy="rock-band",
        fixtures=[{"id": 1, "type": "mover", "covered_by_any_cue": True}],
        cuelists=[{"id": 1, "label": "X", "tracking": "track", "priority": "normal",
                   "cues": [{"id": 1.0, "label": "x", "is_mib": False}]}],
    )
    findings = check_mib_001_movers_have_mib(plan, None)
    assert any(v.rule_id == "SHOW-MIB-001" for v in findings)


# MIB-002
def test_mib_002_clean_when_mib_only_on_movers():
    plan = _show(
        fixtures=[{"id": 1, "type": "mover", "mib_enabled": True}],
    )
    assert check_mib_002_mib_on_dimmer_only(plan, None) == []


def test_mib_002_flags_mib_on_dimmer():
    plan = _show(
        fixtures=[{"id": 1, "type": "dimmer", "mib_enabled": True}],
    )
    findings = check_mib_002_mib_on_dimmer_only(plan, None)
    assert any(v.rule_id == "SHOW-MIB-002" and v.severity == "error" for v in findings)


# REF-001
def test_ref_001_clean_when_preset_referenced():
    cl = [{"id": 1, "label": "X", "tracking": "track", "priority": "normal",
           "cues": [{"id": 1.0, "label": "x", "uses_preset": True}]}]
    plan = _show(preset_strategy="full-coverage", cuelists=cl)
    assert check_ref_001_hard_values_when_preset_expected(plan, None) == []


def test_ref_001_flags_hard_values():
    cl = [{"id": 1, "label": "X", "tracking": "track", "priority": "normal",
           "cues": [{"id": 1.0, "label": "x", "uses_preset": False}]}]
    plan = _show(preset_strategy="full-coverage", cuelists=cl)
    findings = check_ref_001_hard_values_when_preset_expected(plan, None)
    assert any(v.rule_id == "SHOW-REF-001" for v in findings)


# OFF-001
def test_off_001_clean_when_off_time_set():
    cl = [{"id": 1, "label": "X", "tracking": "track", "priority": "normal",
           "off_time_ms": 500, "cues": []}]
    plan = _show(cuelists=cl)
    assert check_off_001_off_time_missing(plan, None) == []


def test_off_001_flags_missing_off_time():
    cl = [{"id": 1, "label": "X", "tracking": "track", "priority": "normal",
           "off_time_ms": None, "cues": []}]
    plan = _show(cuelists=cl)
    findings = check_off_001_off_time_missing(plan, None)
    assert any(v.rule_id == "SHOW-OFF-001" for v in findings)


# PRIO-001
def test_show_prio_001_clean_when_priorities_mixed():
    plan = _show(cuelists=[
        {"id": 1, "label": "X", "tracking": "track", "priority": "normal", "cues": []},
        {"id": 2, "label": "Y", "tracking": "track", "priority": "super", "cues": []},
    ])
    assert check_prio_001_all_cuelists_normal(plan, None) == []


def test_show_prio_001_flags_all_normal():
    plan = _show(cuelists=[
        {"id": 1, "label": "X", "tracking": "track", "priority": "normal", "cues": []},
        {"id": 2, "label": "Y", "tracking": "track", "priority": "normal", "cues": []},
    ])
    findings = check_prio_001_all_cuelists_normal(plan, None)
    assert any(v.rule_id == "SHOW-PRIO-001" for v in findings)


# WORLD-001
def test_world_001_clean_when_worlds_match_sections():
    plan = _show(strategy="rock-band", worlds=[{"name": "intro"}, {"name": "verse"},
                                                {"name": "chorus"}, {"name": "bridge"},
                                                {"name": "outro"}])
    assert check_world_001_missing_per_section_worlds(plan, None) == []


def test_world_001_flags_few_worlds_when_per_section_expected():
    plan = _show(strategy="rock-band", worlds=[{"name": "main"}])
    findings = check_world_001_missing_per_section_worlds(plan, None)
    assert any(v.rule_id == "SHOW-WORLD-001" for v in findings)


# NOTE-001
def test_note_001_clean_when_cue_notes_descriptive():
    cl = [{"id": 1, "label": "X", "tracking": "track", "priority": "normal",
           "cues": [{"id": 1.0, "label": "verse1_lift"}]}]
    plan = _show(cuelists=cl)
    assert check_note_001_generic_cue_note(plan, None) == []


def test_note_001_flags_generic_cue_note():
    cl = [{"id": 1, "label": "X", "tracking": "track", "priority": "normal",
           "cues": [{"id": 1.0, "label": "Cue 5"}]}]
    plan = _show(cuelists=cl)
    findings = check_note_001_generic_cue_note(plan, None)
    assert any(v.rule_id == "SHOW-NOTE-001" for v in findings)


# EMERG-001
def test_emerg_001_clean_when_emergency_cuelist_present():
    cl = [{"id": 999, "label": "Emergency", "tracking": "non-tracking", "priority": "super",
           "cues": []}]
    plan = _show(strategy="theatrical", cuelists=cl)
    assert check_emerg_001_no_emergency_cuelist(plan, None) == []


def test_emerg_001_flags_missing_emergency_cuelist():
    plan = _show(strategy="theatrical", cuelists=[])
    findings = check_emerg_001_no_emergency_cuelist(plan, None)
    assert any(v.rule_id == "SHOW-EMERG-001" for v in findings)


# VIEW-001
def test_view_001_clean_when_required_views_present():
    plan = _show(strategy="rock-band", views=["programmer", "run", "busking-fallback"])
    assert check_view_001_missing_required_view(plan, None) == []


def test_view_001_flags_missing_view():
    plan = _show(strategy="rock-band", views=["programmer"])
    findings = check_view_001_missing_required_view(plan, None)
    assert any(v.rule_id == "SHOW-VIEW-001" for v in findings)


# BLACK-001
def test_black_001_clean_when_panic_blackout_present():
    cl = [{"id": 1, "label": "Song1", "tracking": "track", "priority": "normal",
           "cues": [
               {"id": 0.5, "label": "panic_blackout", "block": True},
               {"id": 1.0, "label": "verse"},
           ]}]
    plan = _show(strategy="rock-band", cuelists=cl)
    assert check_black_001_no_panic_blackout_cue(plan, None) == []


def test_black_001_flags_no_panic_blackout():
    cl = [{"id": 1, "label": "Song1", "tracking": "track", "priority": "normal",
           "cues": [
               {"id": 1.0, "label": "verse"},
           ]}]
    plan = _show(strategy="rock-band", cuelists=cl)
    findings = check_black_001_no_panic_blackout_cue(plan, None)
    assert any(v.rule_id == "SHOW-BLACK-001" for v in findings)


# SEQ-001
def test_seq_001_clean_when_sequence_label_descriptive():
    cl = [{"id": 1, "label": "Verse 1", "tracking": "track", "priority": "normal", "cues": []}]
    plan = _show(cuelists=cl)
    assert check_seq_001_generic_sequence_label(plan, None) == []


def test_seq_001_flags_generic_sequence_label():
    cl = [{"id": 12, "label": "Seq 12", "tracking": "track", "priority": "normal", "cues": []}]
    plan = _show(cuelists=cl)
    findings = check_seq_001_generic_sequence_label(plan, None)
    assert any(v.rule_id == "SHOW-SEQ-001" for v in findings)


# COVER-001
def test_cover_001_clean_when_all_fixtures_covered():
    plan = _show(fixtures=[{"id": 1, "type": "wash", "covered_by_any_cue": True}])
    assert check_cover_001_uncovered_fixtures(plan, None) == []


def test_cover_001_flags_uncovered_fixtures():
    plan = _show(fixtures=[
        {"id": 1, "type": "wash", "covered_by_any_cue": False},
        {"id": 2, "type": "wash", "covered_by_any_cue": False},
    ])
    findings = check_cover_001_uncovered_fixtures(plan, None)
    assert any(v.rule_id == "SHOW-COVER-001" for v in findings)

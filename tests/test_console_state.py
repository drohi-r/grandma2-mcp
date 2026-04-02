"""
tests/test_console_state.py — Unit tests for src/console_state.py

Covers:
  - ConsoleStateSnapshot field defaults
  - age_seconds() and staleness_warning()
  - preset_exists()
  - summary() content
  - MAtricksTracker: reset(), summary(), field updates
  - ExecutorState defaults
  - CueRecord and SequenceEntry construction
"""

import time

from src.console_state import (
    ConsoleStateSnapshot,
    CuePart,
    CueRecord,
    ExecutorState,
    MAtricksTracker,
    SequenceEntry,
)

# ── ConsoleStateSnapshot defaults ────────────────────────────────────────────

class TestConsoleStateSnapshotDefaults:

    def test_hydrated_at_is_set_on_init(self):
        before = time.time()
        snap = ConsoleStateSnapshot()
        after = time.time()
        assert before <= snap.hydrated_at <= after

    def test_partial_defaults_false(self):
        assert ConsoleStateSnapshot().partial is False

    def test_hydration_errors_empty(self):
        assert ConsoleStateSnapshot().hydration_errors == []

    def test_parked_fixtures_empty_set(self):
        snap = ConsoleStateSnapshot()
        assert isinstance(snap.parked_fixtures, set)
        assert len(snap.parked_fixtures) == 0

    def test_filter_vte_all_true(self):
        snap = ConsoleStateSnapshot()
        assert snap.filter_vte == {"value": True, "value_timing": True, "effect": True}

    def test_console_modes_all_false(self):
        snap = ConsoleStateSnapshot()
        for mode in ("blind", "highlight", "freeze", "solo", "blackout"):
            assert snap.console_modes[mode] is False

    def test_active_filter_none(self):
        assert ConsoleStateSnapshot().active_filter is None

    def test_active_world_none(self):
        assert ConsoleStateSnapshot().active_world is None

    def test_world_labels_empty(self):
        assert ConsoleStateSnapshot().world_labels == {}

    def test_selected_fixture_count_zero(self):
        assert ConsoleStateSnapshot().selected_fixture_count == 0

    def test_matricks_is_tracker_instance(self):
        snap = ConsoleStateSnapshot()
        assert isinstance(snap.matricks, MAtricksTracker)

    def test_executor_state_empty_dict(self):
        assert ConsoleStateSnapshot().executor_state == {}

    def test_sequences_empty_list(self):
        assert ConsoleStateSnapshot().sequences == []

    def test_sequence_cues_empty_list(self):
        assert ConsoleStateSnapshot().sequence_cues == []

    def test_has_unsaved_changes_false(self):
        assert ConsoleStateSnapshot().has_unsaved_changes is False

    def test_fader_page_default_1(self):
        assert ConsoleStateSnapshot().fader_page == 1

    def test_active_user_profile_default(self):
        assert ConsoleStateSnapshot().active_user_profile == "Default"


# ── age_seconds / staleness_warning ──────────────────────────────────────────

class TestAgeAndStaleness:

    def test_age_seconds_is_small_just_after_init(self):
        snap = ConsoleStateSnapshot()
        assert snap.age_seconds() < 1.0

    def test_age_seconds_grows(self):
        snap = ConsoleStateSnapshot()
        snap.hydrated_at = time.time() - 10.0
        assert snap.age_seconds() >= 10.0

    def test_staleness_warning_returns_none_when_fresh(self):
        snap = ConsoleStateSnapshot()
        assert snap.staleness_warning(max_age=30.0) is None

    def test_staleness_warning_returns_string_when_old(self):
        snap = ConsoleStateSnapshot()
        snap.hydrated_at = time.time() - 60.0
        warning = snap.staleness_warning(max_age=30.0)
        assert warning is not None
        assert "60" in warning or "s old" in warning

    def test_staleness_warning_custom_threshold(self):
        snap = ConsoleStateSnapshot()
        snap.hydrated_at = time.time() - 5.0
        assert snap.staleness_warning(max_age=3.0) is not None
        assert snap.staleness_warning(max_age=10.0) is None


# ── preset_exists ─────────────────────────────────────────────────────────────

class TestPresetExists:

    def test_returns_false_when_index_empty(self):
        snap = ConsoleStateSnapshot()
        assert snap.preset_exists(2, 1) is False

    def test_returns_true_after_adding_entry(self):
        snap = ConsoleStateSnapshot()
        snap.name_index.add_entry("preset", "My Preset", 1, preset_type=2)
        assert snap.preset_exists(2, 1) is True

    def test_wrong_preset_type_returns_false(self):
        snap = ConsoleStateSnapshot()
        snap.name_index.add_entry("preset", "My Preset", 1, preset_type=2)
        assert snap.preset_exists(3, 1) is False

    def test_wrong_id_returns_false(self):
        snap = ConsoleStateSnapshot()
        snap.name_index.add_entry("preset", "My Preset", 1, preset_type=2)
        assert snap.preset_exists(2, 99) is False


# ── summary ───────────────────────────────────────────────────────────────────

class TestSummary:

    def test_summary_returns_string(self):
        snap = ConsoleStateSnapshot()
        assert isinstance(snap.summary(), str)

    def test_summary_contains_snapshot_label(self):
        snap = ConsoleStateSnapshot()
        assert "ConsoleStateSnapshot" in snap.summary()

    def test_summary_contains_world_and_filter(self):
        snap = ConsoleStateSnapshot()
        assert "world=" in snap.summary()
        assert "filter=" in snap.summary()

    def test_summary_contains_parked_count(self):
        snap = ConsoleStateSnapshot()
        snap.parked_fixtures.add("fixture 1")
        assert "parked" in snap.summary()

    def test_summary_contains_matricks_summary(self):
        snap = ConsoleStateSnapshot()
        assert "matricks" in snap.summary()

    def test_summary_includes_errors_when_present(self):
        snap = ConsoleStateSnapshot()
        snap.hydration_errors.append("phase_world failed")
        assert "phase_world failed" in snap.summary()


# ── MAtricksTracker ───────────────────────────────────────────────────────────

class TestMAtricksTracker:

    def test_default_fields_all_none(self):
        mt = MAtricksTracker()
        assert mt.interleave is None
        assert mt.blocks_x is None
        assert mt.blocks_y is None
        assert mt.groups_x is None
        assert mt.groups_y is None
        assert mt.wings is None
        assert mt.filter_id is None
        assert mt.active is False

    def test_reset_clears_all_fields(self):
        mt = MAtricksTracker(interleave=4, wings=2, filter_id=3, active=True)
        mt.reset()
        assert mt.interleave is None
        assert mt.wings is None
        assert mt.filter_id is None
        assert mt.active is False

    def test_summary_returns_off_when_empty(self):
        assert MAtricksTracker().summary() == "off"

    def test_summary_shows_active_fields(self):
        mt = MAtricksTracker(interleave=4, wings=2)
        s = mt.summary()
        assert "interleave=4" in s
        assert "wings=2" in s

    def test_summary_blocks_xy(self):
        mt = MAtricksTracker(blocks_x=2, blocks_y=3)
        assert "blocks=2.3" in mt.summary()

    def test_summary_blocks_x_only(self):
        mt = MAtricksTracker(blocks_x=2)
        assert "blocks=2" in mt.summary()

    def test_reset_is_idempotent(self):
        mt = MAtricksTracker()
        mt.reset()
        mt.reset()
        assert mt.summary() == "off"


# ── ExecutorState ─────────────────────────────────────────────────────────────

class TestExecutorState:

    def test_defaults(self):
        es = ExecutorState(id=201)
        assert es.id == 201
        assert es.page == 1
        assert es.sequence_id is None
        assert es.label == ""
        assert es.priority == "normal"
        assert es.button_function == ""
        assert es.fader_function == ""
        assert es.ooo is False
        assert es.kill_protect is False
        assert es.auto_start is False

    def test_custom_values(self):
        es = ExecutorState(id=5, page=2, priority="high", kill_protect=True)
        assert es.page == 2
        assert es.priority == "high"
        assert es.kill_protect is True


# ── SequenceEntry and CueRecord ───────────────────────────────────────────────

class TestSequenceEntryAndCueRecord:

    def test_sequence_entry_defaults(self):
        seq = SequenceEntry(id=1)
        assert seq.id == 1
        assert seq.label == ""
        assert seq.loop is False
        assert seq.chaser is False
        assert seq.autoprepare is False
        assert seq.speed_master is None

    def test_cue_record_construction(self):
        cue = CueRecord(sequence_id=1, cue_number=2.0, label="Fade Up")
        assert cue.sequence_id == 1
        assert cue.cue_number == 2.0
        assert cue.label == "Fade Up"
        assert cue.parts == []

    def test_cue_part(self):
        part = CuePart(part=1, label="Part A")
        assert part.part == 1
        assert part.label == "Part A"

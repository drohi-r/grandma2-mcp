"""
tests/test_agent_memory.py — Unit tests for src/agent_memory.py

Covers:
  - FixtureSnapshot
  - DecisionCheckpoint: is_fresh() freshness window
  - WorkingMemory: fixture tracking, park ledger, mode overrides, step tracking
  - LongTermMemory: save/load, recent_sessions, recall
"""

import tempfile
from pathlib import Path

import pytest

from src.agent_memory import FixtureSnapshot, LongTermMemory, WorkingMemory
from src.commands.constants import MA2Right
from src.rights import RightsContext

# ── FixtureSnapshot ──────────────────────────────────────────────────────────

class TestFixtureSnapshot:
    def test_basic_fields(self):
        fs = FixtureSnapshot(fixture_id=1, group="wash", intensity=75.0)
        assert fs.fixture_id == 1
        assert fs.group == "wash"
        assert fs.intensity == 75.0
        assert fs.preset_applied is None
        assert fs.attribute == {}


# ── WorkingMemory ────────────────────────────────────────────────────────────

class TestWorkingMemory:
    def test_session_id_auto_generated(self):
        wm = WorkingMemory()
        assert len(wm.session_id) == 8

    def test_session_id_unique(self):
        wm1, wm2 = WorkingMemory(), WorkingMemory()
        assert wm1.session_id != wm2.session_id

    def test_record_fixture_creates_entry(self):
        wm = WorkingMemory()
        wm.record_fixture(1, group="wash", intensity=100.0)
        assert "1" in wm.fixtures
        assert wm.fixtures["1"].intensity == 100.0

    def test_record_fixture_updates_existing(self):
        wm = WorkingMemory()
        wm.record_fixture(1, intensity=50.0)
        wm.record_fixture(1, intensity=100.0)
        assert wm.fixtures["1"].intensity == 100.0

    def test_record_fixture_attributes(self):
        wm = WorkingMemory()
        wm.record_fixture(1, attributes={"color": "blue"})
        assert wm.fixtures["1"].attribute["color"] == "blue"

    def test_fixtures_in_group(self):
        wm = WorkingMemory()
        wm.record_fixture(1, group="wash")
        wm.record_fixture(2, group="wash")
        wm.record_fixture(3, group="spots")
        result = wm.fixtures_in_group("wash")
        assert len(result) == 2

    # Park ledger

    def test_park_adds_to_ledger(self):
        wm = WorkingMemory()
        wm.park(5)
        assert wm.is_parked(5) is True

    def test_unpark_removes_from_ledger(self):
        wm = WorkingMemory()
        wm.park(5)
        wm.unpark(5)
        assert wm.is_parked(5) is False

    def test_park_uses_string_key(self):
        wm = WorkingMemory()
        wm.park("7")
        assert wm.is_parked(7) is True  # int lookup works

    # Mode overrides

    def test_is_blind_default_false(self):
        wm = WorkingMemory()
        assert wm.is_blind() is False

    def test_set_blind_mode(self):
        wm = WorkingMemory()
        wm.set_mode("blind", True)
        assert wm.is_blind() is True

    def test_set_mode_no_console_state(self):
        wm = WorkingMemory()
        wm.set_mode("freeze", True)
        assert wm.mode_overrides["freeze"] is True

    # Step tracking

    def test_mark_done(self):
        wm = WorkingMemory()
        wm.mark_done("step_a")
        assert "step_a" in wm.completed_steps

    def test_mark_failed(self):
        wm = WorkingMemory()
        wm.mark_failed("step_b", "timeout")
        assert any("step_b" in s for s in wm.failed_steps)

    # Rights context

    def test_can_execute_with_admin_rights(self):
        wm = WorkingMemory()
        wm.rights_context = RightsContext(user_right=MA2Right.ADMIN)
        assert wm.can_execute("load_show") is True

    def test_can_execute_denied_at_low_right(self):
        wm = WorkingMemory()
        wm.rights_context = RightsContext(user_right=MA2Right.PLAYBACK)
        assert wm.can_execute("store_current_cue") is False

    def test_upr_flag(self):
        wm = WorkingMemory()
        wm.rights_context = RightsContext(user_right=MA2Right.PROGRAM)
        assert wm.upr_flag() == "/UPR=3"

    # Staleness with no snapshot

    def test_staleness_warning_no_snapshot(self):
        wm = WorkingMemory()
        warn = wm.staleness_warning()
        assert warn is not None
        assert "hydrate" in warn.lower() or "snapshot" in warn.lower()

    # Console summary with no snapshot

    def test_console_summary_no_snapshot(self):
        wm = WorkingMemory()
        summary = wm.console_summary()
        assert "not hydrated" in summary.lower()


# ── LongTermMemory ───────────────────────────────────────────────────────────

@pytest.fixture
def ltm_tmp():
    """LTM instance backed by a temp file, cleaned up after test."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    ltm = LongTermMemory(db_path=db_path)
    yield ltm
    ltm._conn.close()
    db_path.unlink(missing_ok=True)


class TestLongTermMemory:
    def test_save_and_recent_sessions(self, ltm_tmp):
        wm = WorkingMemory(task_description="test wash look")
        wm.charge_tokens(120)
        ltm_tmp.save_session(wm, outcome="success")
        sessions = ltm_tmp.recent_sessions(5)
        assert len(sessions) == 1
        assert sessions[0]["task"] == "test wash look"
        assert sessions[0]["outcome"] == "success"
        assert sessions[0]["tokens"] == 120

    def test_recent_sessions_limit(self, ltm_tmp):
        for i in range(5):
            wm = WorkingMemory(task_description=f"task {i}")
            ltm_tmp.save_session(wm, outcome="success")
        assert len(ltm_tmp.recent_sessions(3)) == 3

    def test_recall_existing_session(self, ltm_tmp):
        wm = WorkingMemory(task_description="recall test")
        ltm_tmp.save_session(wm, outcome="success")
        snap = ltm_tmp.recall_session(wm.session_id)
        assert snap is not None
        assert snap.get("task") == "recall test"  # v2 format uses "task" key

    def test_recall_nonexistent_returns_none(self, ltm_tmp):
        result = ltm_tmp.recall_session("deadbeef")
        assert result is None

    def test_recent_sessions_empty(self, ltm_tmp):
        assert ltm_tmp.recent_sessions(10) == []

    def test_session_id_stored(self, ltm_tmp):
        wm = WorkingMemory(task_description="id check")
        ltm_tmp.save_session(wm, outcome="success")
        sessions = ltm_tmp.recent_sessions(1)
        assert sessions[0]["id"] == wm.session_id

    def test_fixture_history(self, ltm_tmp):
        wm = WorkingMemory(task_description="fx history test")
        wm.record_fixture(3, group="wash", intensity=80.0, preset="blue")
        ltm_tmp.save_session(wm, outcome="success")
        hist = ltm_tmp.fixture_history("3", limit=5)
        assert len(hist) == 1
        assert hist[0]["group_name"] == "wash"

    def test_park_history(self, ltm_tmp):
        wm = WorkingMemory(task_description="park test")
        wm.park(7)
        ltm_tmp.save_session(wm, outcome="success")
        hist = ltm_tmp.park_history("7")
        assert len(hist) == 1
        assert hist[0]["action"] == "parked"


class TestCompressSessionSnapshot:
    def test_snapshot_has_v2_key(self, ltm_tmp):
        wm = WorkingMemory(task_description="compression test")
        ltm_tmp.save_session(wm, outcome="ok")
        snap = ltm_tmp.recall_session(wm.session_id)
        assert snap is not None
        assert snap.get("_v") == 2

    def test_snapshot_contains_decision_fields(self, ltm_tmp):
        wm = WorkingMemory(task_description="decision test")
        wm.completed_steps.append("step_a")
        wm.failed_steps.append("step_b")
        wm.charge_tokens(100)
        ltm_tmp.save_session(wm, outcome="partial")
        snap = ltm_tmp.recall_session(wm.session_id)
        assert "step_a" in snap["completed_steps"]
        assert "step_b" in snap["failed_steps"]
        assert snap["token_spend"] == 100

    def test_snapshot_does_not_contain_full_fixture_snapshots(self, ltm_tmp):
        wm = WorkingMemory(task_description="fixture compress test")
        wm.record_fixture(1, group="wash", intensity=75.0)
        ltm_tmp.save_session(wm, outcome="ok")
        snap = ltm_tmp.recall_session(wm.session_id)
        # v2 stores fixture_summary (names+values), not full FixtureSnapshot dicts
        assert "fixture_summary" in snap
        assert "fixtures" not in snap  # full FixtureSnapshot key absent
        summary = snap["fixture_summary"]
        assert "1" in summary
        assert "intensity" in summary["1"]

    def test_snapshot_park_ledger_is_sorted_list(self, ltm_tmp):
        wm = WorkingMemory(task_description="park ledger test")
        wm.park(5)
        wm.park(3)
        ltm_tmp.save_session(wm, outcome="ok")
        snap = ltm_tmp.recall_session(wm.session_id)
        assert snap["park_ledger"] == sorted(snap["park_ledger"])

    def test_recall_session_v1_compat(self, ltm_tmp):
        """recall_session must return v1 blobs unchanged (no _v key)."""
        import json
        import time
        # Manually insert a v1-style blob
        wm = WorkingMemory(task_description="v1 compat")
        v1_blob = wm.to_dict()  # v1 format: has 'fixtures' key, no '_v'
        ltm_tmp._conn.execute(
            "INSERT OR REPLACE INTO sessions "
            "(id,timestamp,task,outcome,steps_done,steps_failed,"
            "tokens,elapsed_s,showfile,active_user,active_world,active_filter,snapshot)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (wm.session_id, time.time(), wm.task_description, "ok",
             0, 0, 0, 0.0, "", "", None, None, json.dumps(v1_blob)),
        )
        ltm_tmp._conn.commit()
        snap = ltm_tmp.recall_session(wm.session_id)
        assert snap is not None
        # v1 blobs have 'fixtures' key and no '_v'
        assert snap.get("_v", 1) == 1


# ── DecisionCheckpoint ───────────────────────────────────────────────────────

class TestDecisionCheckpoint:
    def test_add_checkpoint_stores_entry(self):
        wm = WorkingMemory(task_description="cp test")
        cp = wm.add_checkpoint("rights_denied", "list system variables")
        assert len(wm.checkpoints) == 1
        assert cp.fault == "rights_denied"
        assert cp.query == "list system variables"
        assert cp.replay == "list system variables"
        assert cp.confidence == "medium"

    def test_checkpoint_is_fresh_within_window(self):
        wm = WorkingMemory(task_description="fresh test")
        cp = wm.add_checkpoint("cue_audit_seq_1", "query_object_list",
                               fresh_for_seconds=60)
        assert cp.is_fresh() is True

    def test_checkpoint_is_stale_after_window(self):
        import time
        wm = WorkingMemory(task_description="stale test")
        cp = wm.add_checkpoint("stale_fault", "list", fresh_for_seconds=0)
        # Give it a tiny sleep so observed_at < now
        time.sleep(0.01)
        assert cp.is_fresh() is False

    def test_fresh_checkpoint_returns_latest(self):
        wm = WorkingMemory(task_description="latest test")
        wm.add_checkpoint("same_fault", "query v1", fresh_for_seconds=60,
                          confidence="low")
        wm.add_checkpoint("same_fault", "query v2", fresh_for_seconds=60,
                          confidence="high")
        cp = wm.fresh_checkpoint("same_fault")
        assert cp is not None
        assert cp.confidence == "high"

    def test_fresh_checkpoint_returns_none_for_unknown_fault(self):
        wm = WorkingMemory(task_description="none test")
        assert wm.fresh_checkpoint("no_such_fault") is None

    def test_compress_snapshot_includes_checkpoint_count(self, ltm_tmp):
        wm = WorkingMemory(task_description="checkpoint count test")
        wm.add_checkpoint("rights_denied", "list system variables",
                          fresh_for_seconds=60, confidence="high")
        ltm_tmp.save_session(wm, outcome="ok")
        snap = ltm_tmp.recall_session(wm.session_id)
        assert snap["checkpoint_count"] == 1
        assert snap["checkpoints"][0]["fault"] == "rights_denied"
        assert snap["checkpoints"][0]["confidence"] == "high"


# ── Duplicate method guard (Bug 3 fix) ───────────────────────────────────────

class TestNoDuplicateCheckpointMethods:
    """WorkingMemory must have exactly one definition of each checkpoint helper."""

    def test_single_add_checkpoint_definition(self):
        import inspect
        src = inspect.getsource(WorkingMemory)
        assert src.count("def add_checkpoint") == 1, (
            "WorkingMemory has duplicate add_checkpoint definitions"
        )

    def test_single_fresh_checkpoint_definition(self):
        import inspect
        src = inspect.getsource(WorkingMemory)
        assert src.count("def fresh_checkpoint") == 1, (
            "WorkingMemory has duplicate fresh_checkpoint definitions"
        )


# ── Showfile tracking (dynamic show awareness) ────────────────────────────────

class TestShowfileTracking:
    """WorkingMemory must track baseline showfile and detect changes."""

    def _make_snapshot(self, showfile: str):
        """Create a minimal ConsoleStateSnapshot-like object with a showfile field."""
        from unittest.mock import MagicMock
        snap = MagicMock()
        snap.showfile = showfile
        return snap

    def test_baseline_field_exists_and_defaults_empty(self):
        wm = WorkingMemory()
        assert wm.baseline_showfile == ""

    def test_baseline_set_explicitly(self):
        # Orchestrator sets both fields after hydration
        wm = WorkingMemory()
        snap = self._make_snapshot("my_show")
        wm.console_state = snap
        wm.baseline_showfile = snap.showfile
        assert wm.baseline_showfile == "my_show"

    def test_baseline_persists_when_console_state_cleared(self):
        wm = WorkingMemory()
        snap = self._make_snapshot("my_show")
        wm.console_state = snap
        wm.baseline_showfile = snap.showfile
        wm.console_state = None  # invalidate snapshot
        assert wm.baseline_showfile == "my_show"  # baseline remains

    def test_showfile_changed_returns_false_when_same(self):
        wm = WorkingMemory()
        wm.baseline_showfile = "show_a"
        assert wm.showfile_changed("show_a") is False

    def test_showfile_changed_returns_true_when_different(self):
        wm = WorkingMemory()
        wm.baseline_showfile = "show_a"
        assert wm.showfile_changed("show_b") is True

    def test_showfile_changed_returns_false_when_no_baseline(self):
        wm = WorkingMemory()
        # No hydration — baseline is empty string → guard should not block
        assert wm.showfile_changed("any_show") is False

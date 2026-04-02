"""
tests/test_skill_improver.py — Unit tests for src/skill_improver.py

All tests use a temp SQLite DB.  No live console required.
"""

from __future__ import annotations

import time

import pytest

from src.agent_memory import LongTermMemory
from src.skill import SkillRegistry
from src.skill_improver import SkillImprover, _slugify
from src.telemetry import ToolTelemetry

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test_improver.db"


@pytest.fixture
def tel(db_path):
    t = ToolTelemetry(db_path=db_path)
    yield t
    t.close()


@pytest.fixture
def reg(db_path):
    r = SkillRegistry(db_path=db_path)
    yield r
    r.close()


@pytest.fixture
def ltm(db_path):
    mem = LongTermMemory(db_path=db_path)
    yield mem
    mem.close()


@pytest.fixture
def imp(tel, reg, ltm):
    return SkillImprover(tel, reg, ltm)


# ---------------------------------------------------------------------------
# Helper: insert raw sessions directly into the sessions table
# ---------------------------------------------------------------------------

def _insert_session(ltm, session_id, task, outcome, steps_done, steps_failed, tokens=10):
    ltm._conn.execute(
        "INSERT OR REPLACE INTO sessions "
        "(id,timestamp,task,outcome,steps_done,steps_failed,tokens,elapsed_s,"
        "showfile,active_user,active_world,active_filter,snapshot) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            session_id, time.time(), task, outcome,
            steps_done, steps_failed, tokens, 1.0,
            "test_show", "admin", None, None, "{}",
        ),
    )
    ltm._conn.commit()


# ---------------------------------------------------------------------------
# _slugify
# ---------------------------------------------------------------------------

class TestSlugify:
    def test_spaces_to_underscores(self):
        assert _slugify("store wash cue") == "store_wash_cue"

    def test_special_chars_removed(self):
        assert _slugify("store cue #1!") == "store_cue_1"

    def test_truncates_to_60(self):
        assert len(_slugify("x" * 100)) <= 60


# ---------------------------------------------------------------------------
# identify_failure_patterns
# ---------------------------------------------------------------------------

class TestIdentifyFailurePatterns:
    def _insert_errors(self, tel, tool_name, error_class, count):
        for _ in range(count):
            tel._conn.execute(
                "INSERT INTO tool_invocations "
                "(ts,tool_name,inputs_json,output_preview,error_class,latency_ms,risk_tier,operator) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (time.time(), tool_name, "{}", "", error_class, 1.0, "SAFE_WRITE", "op"),
            )
        tel._conn.commit()

    def test_returns_failing_tools(self, imp, tel):
        self._insert_errors(tel, "bad_tool", "ConnectionError", 5)
        suggestions = imp.identify_failure_patterns(days=7, min_failures=3)
        names = [s.tool_name for s in suggestions]
        assert "bad_tool" in names

    def test_below_threshold_excluded(self, imp, tel):
        self._insert_errors(tel, "rare_fail", "RuntimeError", 2)
        suggestions = imp.identify_failure_patterns(days=7, min_failures=3)
        names = [s.tool_name for s in suggestions]
        assert "rare_fail" not in names

    def test_empty_when_no_errors(self, imp):
        assert imp.identify_failure_patterns(days=7, min_failures=1) == []

    def test_suggestion_has_hint(self, imp, tel):
        self._insert_errors(tel, "conn_tool", "ConnectionError", 4)
        suggestions = imp.identify_failure_patterns(days=7, min_failures=3)
        assert len(suggestions) == 1
        assert "conn_tool" in suggestions[0].hint
        assert suggestions[0].failure_count == 4
        assert "ConnectionError" in suggestions[0].error_classes

    def test_sorted_by_failure_count_desc(self, imp, tel):
        self._insert_errors(tel, "worst_tool", "RuntimeError", 10)
        self._insert_errors(tel, "medium_tool", "RuntimeError", 5)
        suggestions = imp.identify_failure_patterns(days=7, min_failures=3)
        names = [s.tool_name for s in suggestions]
        assert names.index("worst_tool") < names.index("medium_tool")


# ---------------------------------------------------------------------------
# identify_promotion_candidates
# ---------------------------------------------------------------------------

class TestIdentifyPromotionCandidates:
    def test_successful_session_returned(self, imp, ltm):
        _insert_session(ltm, "sess_good", "store wash cue", "success", 5, 0)
        candidates = imp.identify_promotion_candidates(min_quality=0.8)
        ids = [c.session_id for c in candidates]
        assert "sess_good" in ids

    def test_failed_session_excluded(self, imp, ltm):
        _insert_session(ltm, "sess_bad", "bad task", "failed", 0, 5)
        candidates = imp.identify_promotion_candidates(min_quality=0.8)
        ids = [c.session_id for c in candidates]
        assert "sess_bad" not in ids

    def test_partial_session_low_quality_excluded(self, imp, ltm):
        # 3 done, 7 failed → quality=0.3
        _insert_session(ltm, "sess_partial", "partial task", "success", 3, 7)
        candidates = imp.identify_promotion_candidates(min_quality=0.8)
        ids = [c.session_id for c in candidates]
        assert "sess_partial" not in ids

    def test_already_promoted_excluded(self, imp, ltm, reg):
        _insert_session(ltm, "promoted_sess", "promoted task", "success", 5, 0)
        reg.promote_from_session(
            session_id="promoted_sess",
            name="existing_skill",
            description="d",
            body="b",
            safety_scope="SAFE_WRITE",
            applicable_context="c",
        )
        candidates = imp.identify_promotion_candidates(min_quality=0.8)
        ids = [c.session_id for c in candidates]
        assert "promoted_sess" not in ids

    def test_suggested_name_derived_from_task(self, imp, ltm):
        _insert_session(ltm, "sess_name", "Create Blue Wash Look", "success", 5, 0)
        candidates = imp.identify_promotion_candidates(min_quality=0.8)
        match = next((c for c in candidates if c.session_id == "sess_name"), None)
        assert match is not None
        assert "create_blue_wash_look" in match.suggested_name or "blue" in match.suggested_name

    def test_sorted_by_quality_desc(self, imp, ltm):
        _insert_session(ltm, "perfect", "task A", "success", 10, 0)   # quality=1.0
        _insert_session(ltm, "good", "task B", "success", 9, 1)        # quality=0.9
        candidates = imp.identify_promotion_candidates(min_quality=0.8)
        ids = [c.session_id for c in candidates]
        assert ids.index("perfect") < ids.index("good")

    def test_empty_when_no_sessions(self, imp):
        assert imp.identify_promotion_candidates() == []


# ---------------------------------------------------------------------------
# quality_score_for_session
# ---------------------------------------------------------------------------

class TestQualityScoreForSession:
    def test_perfect_score(self, imp, ltm):
        _insert_session(ltm, "perfect", "task", "success", 5, 0)
        assert imp.quality_score_for_session("perfect") == 1.0

    def test_half_score(self, imp, ltm):
        _insert_session(ltm, "half", "task", "success", 5, 5)
        assert abs(imp.quality_score_for_session("half") - 0.5) < 0.01

    def test_zero_score_all_failed(self, imp, ltm):
        _insert_session(ltm, "all_failed", "task", "failed", 0, 5)
        assert imp.quality_score_for_session("all_failed") == 0.0

    def test_nonexistent_session(self, imp):
        assert imp.quality_score_for_session("does-not-exist") == 0.0

    def test_zero_steps(self, imp, ltm):
        _insert_session(ltm, "no_steps", "task", "success", 0, 0)
        assert imp.quality_score_for_session("no_steps") == 0.0

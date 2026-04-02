"""
tests/test_telemetry.py — Unit tests for src/telemetry.py

All tests use an in-memory or temp-file SQLite DB (GMA_TELEMETRY=0 is NOT set
so the real recording path is exercised).  No live console required.
"""

from __future__ import annotations

import time

import pytest

from src.telemetry import ToolTelemetry, infer_risk_tier

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def tel(tmp_path):
    db = tmp_path / "test_telemetry.db"
    t = ToolTelemetry(db_path=db)
    yield t
    t.close()


# ---------------------------------------------------------------------------
# infer_risk_tier
# ---------------------------------------------------------------------------

def _make_func(name, has_confirm=False):
    if has_confirm:
        def f(confirm_destructive: bool = False):
            pass
    else:
        def f():
            pass
    f.__name__ = name
    return f


class TestInferRiskTier:
    def test_destructive_if_confirm_param(self):
        f = _make_func("store_cue", has_confirm=True)
        assert infer_risk_tier(f) == "DESTRUCTIVE"

    def test_safe_read_list_prefix(self):
        f = _make_func("list_objects")
        assert infer_risk_tier(f) == "SAFE_READ"

    def test_safe_read_get_prefix(self):
        f = _make_func("get_console_state")
        assert infer_risk_tier(f) == "SAFE_READ"

    def test_safe_read_discover_prefix(self):
        f = _make_func("discover_object_names")
        assert infer_risk_tier(f) == "SAFE_READ"

    def test_safe_read_search_prefix(self):
        f = _make_func("search_codebase")
        assert infer_risk_tier(f) == "SAFE_READ"

    def test_safe_read_info_prefix(self):
        f = _make_func("info_object")
        assert infer_risk_tier(f) == "SAFE_READ"

    def test_safe_read_suggest_prefix(self):
        f = _make_func("suggest_tool_for_task")
        assert infer_risk_tier(f) == "SAFE_READ"

    def test_safe_write_default(self):
        f = _make_func("execute_sequence")
        assert infer_risk_tier(f) == "SAFE_WRITE"

    def test_confirm_overrides_prefix(self):
        """confirm_destructive wins even if name starts with 'list_'."""
        f = _make_func("list_and_delete", has_confirm=True)
        assert infer_risk_tier(f) == "DESTRUCTIVE"


# ---------------------------------------------------------------------------
# ToolTelemetry._init_schema
# ---------------------------------------------------------------------------

class TestSchema:
    def test_tables_created(self, tel):
        rows = tel._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        names = {r[0] for r in rows}
        assert "tool_invocations" in names

    def test_indexes_created(self, tel):
        rows = tel._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
        names = {r[0] for r in rows}
        assert "idx_ti_tool" in names
        assert "idx_ti_ts" in names


# ---------------------------------------------------------------------------
# record_sync
# ---------------------------------------------------------------------------

class TestRecordSync:
    def test_basic_record(self, tel):
        tel.record_sync(
            tool_name="list_objects",
            inputs_json='{"keyword":"Group"}',
            output_preview="Group 1",
            error_class=None,
            latency_ms=12.3,
            risk_tier="SAFE_READ",
            operator="administrator",
        )
        row = tel._conn.execute(
            "SELECT tool_name, error_class, latency_ms, risk_tier, operator "
            "FROM tool_invocations"
        ).fetchone()
        assert row[0] == "list_objects"
        assert row[1] is None
        assert abs(row[2] - 12.3) < 0.01
        assert row[3] == "SAFE_READ"
        assert row[4] == "administrator"

    def test_error_record(self, tel):
        tel.record_sync(
            tool_name="create_fixture_group",
            inputs_json="{}",
            output_preview='{"error":"Connection failed"}',
            error_class="ConnectionError",
            latency_ms=5.0,
            risk_tier="DESTRUCTIVE",
            operator="admin",
        )
        row = tel._conn.execute(
            "SELECT error_class FROM tool_invocations WHERE tool_name='create_fixture_group'"
        ).fetchone()
        assert row[0] == "ConnectionError"

    def test_multiple_records(self, tel):
        for i in range(5):
            tel.record_sync(
                tool_name="go_executor",
                inputs_json="{}",
                output_preview="ok",
                error_class=None,
                latency_ms=float(i),
                risk_tier="SAFE_WRITE",
                operator="op",
            )
        count = tel._conn.execute(
            "SELECT COUNT(*) FROM tool_invocations WHERE tool_name='go_executor'"
        ).fetchone()[0]
        assert count == 5

    def test_record_never_raises(self, tel):
        """record_sync must not raise even if connection is broken."""
        tel._conn.close()  # break the connection
        # Should not raise
        tel.record_sync(
            tool_name="any",
            inputs_json="{}",
            output_preview="",
            error_class=None,
            latency_ms=1.0,
            risk_tier="SAFE_READ",
            operator="x",
        )


# ---------------------------------------------------------------------------
# metrics
# ---------------------------------------------------------------------------

class TestMetrics:
    def _insert(self, tel, tool_name, latency, error_class=None, ts_offset=0):
        tel._conn.execute(
            "INSERT INTO tool_invocations "
            "(ts,tool_name,inputs_json,output_preview,error_class,latency_ms,risk_tier,operator) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (time.time() - ts_offset, tool_name, "{}", "", error_class, latency, "SAFE_READ", "op"),
        )
        tel._conn.commit()

    def test_no_calls(self, tel):
        result = tel.metrics("nonexistent_tool", days=7)
        assert result["calls"] == 0
        assert result["tool"] == "nonexistent_tool"

    def test_basic_metrics(self, tel):
        for lat in [10.0, 20.0, 30.0, 40.0, 50.0]:
            self._insert(tel, "list_objects", lat)
        m = tel.metrics("list_objects", days=7)
        assert m["calls"] == 5
        assert m["error_count"] == 0
        assert m["error_rate"] == 0.0
        assert m["p50_ms"] == 30.0

    def test_error_rate(self, tel):
        self._insert(tel, "create_fixture_group", 10.0, error_class="ConnectionError")
        self._insert(tel, "create_fixture_group", 10.0, error_class="ConnectionError")
        self._insert(tel, "create_fixture_group", 10.0)
        m = tel.metrics("create_fixture_group", days=7)
        assert m["calls"] == 3
        assert m["error_count"] == 2
        assert abs(m["error_rate"] - 0.667) < 0.01

    def test_old_records_excluded(self, tel):
        # Insert a record 10 days ago
        self._insert(tel, "old_tool", 5.0, ts_offset=10 * 86400)
        m = tel.metrics("old_tool", days=7)
        assert m["calls"] == 0


# ---------------------------------------------------------------------------
# top_failing_tools
# ---------------------------------------------------------------------------

class TestTopFailingTools:
    def _insert_error(self, tel, tool_name, error_class, count=1):
        for _ in range(count):
            tel._conn.execute(
                "INSERT INTO tool_invocations "
                "(ts,tool_name,inputs_json,output_preview,error_class,latency_ms,risk_tier,operator) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (time.time(), tool_name, "{}", "", error_class, 1.0, "SAFE_WRITE", "op"),
            )
        tel._conn.commit()

    def test_returns_tools_above_threshold(self, tel):
        self._insert_error(tel, "bad_tool", "ConnectionError", count=5)
        failing = tel.top_failing_tools(days=7, min_failures=3)
        names = [f["tool_name"] for f in failing]
        assert "bad_tool" in names

    def test_excludes_tools_below_threshold(self, tel):
        self._insert_error(tel, "rare_fail", "RuntimeError", count=2)
        failing = tel.top_failing_tools(days=7, min_failures=3)
        names = [f["tool_name"] for f in failing]
        assert "rare_fail" not in names

    def test_empty_when_no_errors(self, tel):
        tel.record_sync(
            tool_name="good_tool", inputs_json="{}", output_preview="ok",
            error_class=None, latency_ms=1.0, risk_tier="SAFE_READ", operator="op",
        )
        assert tel.top_failing_tools(days=7, min_failures=1) == []


# ---------------------------------------------------------------------------
# recent
# ---------------------------------------------------------------------------

class TestRecent:
    def test_returns_rows_in_desc_order(self, tel):
        for i in range(3):
            tel.record_sync(
                tool_name="my_tool", inputs_json="{}", output_preview=f"result_{i}",
                error_class=None, latency_ms=float(i), risk_tier="SAFE_WRITE",
                operator="op",
            )
        rows = tel.recent("my_tool", limit=3)
        assert len(rows) == 3
        # Most recent first (highest latency was inserted last)
        assert rows[0]["latency_ms"] == 2.0

    def test_limit_respected(self, tel):
        for _ in range(10):
            tel.record_sync(
                tool_name="tool_x", inputs_json="{}", output_preview="",
                error_class=None, latency_ms=1.0, risk_tier="SAFE_READ", operator="op",
            )
        assert len(tel.recent("tool_x", limit=5)) == 5


# ---------------------------------------------------------------------------
# session_id linkage (Bug 1 fix)
# ---------------------------------------------------------------------------

class TestSessionIdLinkage:
    """Verify that session_id is stored and queryable."""

    def test_session_id_stored(self, tel):
        tel.record_sync(
            tool_name="my_tool", inputs_json="{}", output_preview="ok",
            error_class=None, latency_ms=5.0, risk_tier="SAFE_READ",
            operator="op", session_id="ses-abc123",
        )
        rows = tel.recent("my_tool", limit=1)
        assert rows[0]["session_id"] == "ses-abc123"

    def test_session_id_defaults_to_empty(self, tel):
        tel.record_sync(
            tool_name="other_tool", inputs_json="{}", output_preview="ok",
            error_class=None, latency_ms=1.0, risk_tier="SAFE_READ", operator="op",
        )
        rows = tel.recent("other_tool", limit=1)
        assert rows[0]["session_id"] == ""


# ---------------------------------------------------------------------------
# Singleton identity (Bug 2 fix)
# ---------------------------------------------------------------------------

class TestSingletonIdentity:
    """_get_telemetry() must return the same object on every call."""

    def test_singleton_is_same_object(self):
        from src.server import _get_telemetry
        t1 = _get_telemetry()
        t2 = _get_telemetry()
        assert t1 is t2, "_get_telemetry() returned two different instances"


# ---------------------------------------------------------------------------
# ContextVar session_id propagation (Bug 1 fix)
# ---------------------------------------------------------------------------

class TestContextVarPropagation:
    """_current_session_id ContextVar default is empty; can be set and read."""

    def test_default_is_empty(self):
        from src.context import _current_session_id
        assert _current_session_id.get() == ""

    def test_set_and_reset(self):
        from src.context import _current_session_id
        token = _current_session_id.set("ses-xyz")
        assert _current_session_id.get() == "ses-xyz"
        _current_session_id.reset(token)
        assert _current_session_id.get() == ""

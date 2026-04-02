"""
telemetry.py — Per-tool invocation recorder for OpenSpace-style observability.

Records every MCP tool call to the ``tool_invocations`` table in agent_memory.db.
Writes are synchronous but fast (local SQLite); they add <1 ms per call and run
inside the existing async task so no extra thread or event-loop plumbing is needed.

Controlled via the ``GMA_TELEMETRY`` env var:
    GMA_TELEMETRY=1  (default) — recording enabled
    GMA_TELEMETRY=0            — recording disabled (CI / unit tests)

Risk-tier inference heuristic (applied once at decoration time, not per call):
    1. ``confirm_destructive`` in function signature → DESTRUCTIVE
    2. Function name starts with a SAFE_READ prefix          → SAFE_READ
    3. Anything else                                         → SAFE_WRITE
"""

from __future__ import annotations

import inspect
import sqlite3
import time
from collections.abc import Callable
from pathlib import Path

# Reuse the same DB as LongTermMemory so all memory tables live together.
_DEFAULT_DB = Path(__file__).parent.parent / "rag" / "store" / "agent_memory.db"

_SAFE_READ_PREFIXES: tuple[str, ...] = (
    "list_",
    "discover_",
    "get_",
    "search_",
    "info_",
    "suggest_",
    "assert_",
    "recall_",
)


def infer_risk_tier(func: Callable) -> str:
    """Return the most likely risk tier for a tool function.

    Called once at decoration time — not on every invocation.
    """
    try:
        sig = inspect.signature(func)
    except (ValueError, TypeError):
        return "SAFE_WRITE"
    if "confirm_destructive" in sig.parameters:
        return "DESTRUCTIVE"
    name = func.__name__
    if any(name.startswith(p) for p in _SAFE_READ_PREFIXES):
        return "SAFE_READ"
    return "SAFE_WRITE"


class ToolTelemetry:
    """
    Thread-safe, per-tool invocation recorder backed by agent_memory.db.

    Exposes:
      - ``record_sync``  — called from ``_handle_errors`` wrapper
      - ``metrics``      — aggregated latency + error stats for one tool
      - ``recent``       — raw rows for the last N invocations of a tool
    """

    def __init__(self, db_path: Path = _DEFAULT_DB) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._init_schema()

    # ------------------------------------------------------------------ #
    # Schema                                                               #
    # ------------------------------------------------------------------ #

    def _init_schema(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS tool_invocations (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                ts             REAL    NOT NULL,
                tool_name      TEXT    NOT NULL,
                inputs_json    TEXT,
                output_preview TEXT,
                error_class    TEXT,
                latency_ms     REAL,
                risk_tier      TEXT,
                operator       TEXT,
                session_id     TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_ti_tool ON tool_invocations(tool_name);
            CREATE INDEX IF NOT EXISTS idx_ti_ts   ON tool_invocations(ts);
            CREATE INDEX IF NOT EXISTS idx_ti_err  ON tool_invocations(error_class)
                WHERE error_class IS NOT NULL;
        """)
        self._conn.commit()

    # ------------------------------------------------------------------ #
    # Write                                                                #
    # ------------------------------------------------------------------ #

    def record_sync(
        self,
        *,
        tool_name: str,
        inputs_json: str,
        output_preview: str,
        error_class: str | None,
        latency_ms: float,
        risk_tier: str,
        operator: str,
        session_id: str = "",
    ) -> None:
        """Insert one invocation row.  Silently suppresses any write error."""
        try:
            self._conn.execute(
                "INSERT INTO tool_invocations "
                "(ts,tool_name,inputs_json,output_preview,error_class,"
                "latency_ms,risk_tier,operator,session_id) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    time.time(),
                    tool_name,
                    inputs_json,
                    output_preview,
                    error_class,
                    latency_ms,
                    risk_tier,
                    operator,
                    session_id,
                ),
            )
            self._conn.commit()
        except Exception:  # noqa: BLE001
            pass  # telemetry must never break a tool call

    # ------------------------------------------------------------------ #
    # Read                                                                 #
    # ------------------------------------------------------------------ #

    def metrics(self, tool_name: str, days: int = 7) -> dict:
        """Return latency + error-rate stats for one tool over the last N days."""
        since = time.time() - days * 86_400
        rows = self._conn.execute(
            "SELECT latency_ms, error_class FROM tool_invocations "
            "WHERE tool_name=? AND ts>?",
            (tool_name, since),
        ).fetchall()
        if not rows:
            return {"tool": tool_name, "calls": 0, "days": days}
        latencies = sorted(r[0] for r in rows if r[0] is not None)
        errors = [r[1] for r in rows if r[1] is not None]
        n = len(rows)
        return {
            "tool": tool_name,
            "calls": n,
            "days": days,
            "error_count": len(errors),
            "error_rate": round(len(errors) / n, 3),
            "error_classes": list(set(errors)),
            "p50_ms": latencies[n // 2] if latencies else None,
            "p95_ms": latencies[max(0, int(n * 0.95) - 1)] if latencies else None,
            "min_ms": latencies[0] if latencies else None,
            "max_ms": latencies[-1] if latencies else None,
        }

    def recent(self, tool_name: str, limit: int = 20) -> list[dict]:
        """Return the last N invocation rows for a tool."""
        rows = self._conn.execute(
            "SELECT ts,tool_name,output_preview,error_class,latency_ms,"
            "risk_tier,operator,session_id "
            "FROM tool_invocations WHERE tool_name=? "
            "ORDER BY ts DESC LIMIT ?",
            (tool_name, limit),
        ).fetchall()
        cols = [
            "ts", "tool_name", "output_preview", "error_class",
            "latency_ms", "risk_tier", "operator", "session_id",
        ]
        return [dict(zip(cols, r, strict=False)) for r in rows]

    def top_failing_tools(self, days: int = 7, min_failures: int = 3) -> list[dict]:
        """Return tools with >= min_failures errors in the last N days."""
        since = time.time() - days * 86_400
        rows = self._conn.execute(
            "SELECT tool_name, error_class, COUNT(*) as cnt "
            "FROM tool_invocations "
            "WHERE error_class IS NOT NULL AND ts > ? "
            "GROUP BY tool_name, error_class "
            "ORDER BY cnt DESC",
            (since,),
        ).fetchall()
        # Aggregate by tool_name
        by_tool: dict[str, dict] = {}
        for tool_name, error_class, cnt in rows:
            if tool_name not in by_tool:
                by_tool[tool_name] = {"tool_name": tool_name, "total": 0, "errors": {}}
            by_tool[tool_name]["total"] += cnt
            by_tool[tool_name]["errors"][error_class] = cnt
        return [v for v in by_tool.values() if v["total"] >= min_failures]

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    def close(self) -> None:
        self._conn.close()

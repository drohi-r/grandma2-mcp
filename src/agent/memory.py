"""Workflow memory — SQLite-backed operational memory for reusable patterns.

Separate from the RAG doc search pipeline. Stores:
- Conventions (naming standards, patch templates, venue practices)
- Recipes (reusable multi-step workflows)
- Run history (past execution traces for reference)
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_DB_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "agent_data")
DEFAULT_DB_PATH = os.path.join(DEFAULT_DB_DIR, "memory.db")

SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS conventions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    key TEXT NOT NULL,
    value_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(category, key)
);

CREATE TABLE IF NOT EXISTS recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    steps_json TEXT NOT NULL,
    tags_json TEXT NOT NULL,
    use_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    last_used_at TEXT
);

CREATE TABLE IF NOT EXISTS run_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT UNIQUE NOT NULL,
    goal TEXT NOT NULL,
    result TEXT NOT NULL,
    trace_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


class WorkflowMemory:
    """SQLite-backed operational memory for the agent harness."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self._db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA_SQL)
        logger.debug("WorkflowMemory initialized at %s", db_path)

    def close(self) -> None:
        self._conn.close()

    # ---------------------------------------------------------------- conventions

    def store_convention(self, category: str, key: str, value: dict[str, Any]) -> None:
        """Store or update a show convention."""
        now = datetime.now(UTC).isoformat()
        self._conn.execute(
            """\
            INSERT INTO conventions (category, key, value_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(category, key) DO UPDATE SET
                value_json = excluded.value_json,
                updated_at = excluded.updated_at
            """,
            (category, key, json.dumps(value), now, now),
        )
        self._conn.commit()

    def recall_convention(
        self, category: str, key: str | None = None
    ) -> list[dict[str, Any]]:
        """Recall conventions by category, optionally filtered by key."""
        if key is not None:
            rows = self._conn.execute(
                "SELECT category, key, value_json, created_at, updated_at "
                "FROM conventions WHERE category = ? AND key = ?",
                (category, key),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT category, key, value_json, created_at, updated_at "
                "FROM conventions WHERE category = ?",
                (category,),
            ).fetchall()

        return [
            {
                "category": r["category"],
                "key": r["key"],
                "value": json.loads(r["value_json"]),
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
            for r in rows
        ]

    # ---------------------------------------------------------------- recipes

    def store_recipe(
        self, name: str, steps: list[dict[str, Any]], tags: list[str]
    ) -> None:
        """Store a reusable workflow recipe."""
        now = datetime.now(UTC).isoformat()
        self._conn.execute(
            """\
            INSERT INTO recipes (name, steps_json, tags_json, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                steps_json = excluded.steps_json,
                tags_json = excluded.tags_json
            """,
            (name, json.dumps(steps), json.dumps(tags), now),
        )
        self._conn.commit()

    def recall_recipe(
        self, name: str | None = None, tags: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Find recipes by name or tags."""
        if name is not None:
            rows = self._conn.execute(
                "SELECT name, steps_json, tags_json, use_count, created_at, last_used_at "
                "FROM recipes WHERE name = ?",
                (name,),
            ).fetchall()
        elif tags:
            # Match recipes that have ANY of the requested tags
            ", ".join("?" for _ in tags)
            # SQLite JSON: check if tags_json contains any of the given tags
            conditions = " OR ".join(
                "tags_json LIKE '%' || ? || '%'" for _ in tags
            )
            rows = self._conn.execute(
                f"SELECT name, steps_json, tags_json, use_count, created_at, last_used_at "
                f"FROM recipes WHERE {conditions}",
                tags,
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT name, steps_json, tags_json, use_count, created_at, last_used_at "
                "FROM recipes"
            ).fetchall()

        return [
            {
                "name": r["name"],
                "steps": json.loads(r["steps_json"]),
                "tags": json.loads(r["tags_json"]),
                "use_count": r["use_count"],
                "created_at": r["created_at"],
                "last_used_at": r["last_used_at"],
            }
            for r in rows
        ]

    def increment_recipe_usage(self, name: str) -> None:
        """Increment use_count and set last_used_at for a recipe."""
        now = datetime.now(UTC).isoformat()
        self._conn.execute(
            "UPDATE recipes SET use_count = use_count + 1, last_used_at = ? WHERE name = ?",
            (now, name),
        )
        self._conn.commit()

    # ---------------------------------------------------------------- run history

    def record_run_summary(
        self, run_id: str, goal: str, result: str, trace_json: str
    ) -> None:
        """Store a completed run for future reference."""
        now = datetime.now(UTC).isoformat()
        self._conn.execute(
            """\
            INSERT OR REPLACE INTO run_history (run_id, goal, result, trace_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (run_id, goal, result, trace_json, now),
        )
        self._conn.commit()

    def recall_runs(
        self, result_filter: str | None = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Recall recent runs, optionally filtered by result status."""
        if result_filter:
            rows = self._conn.execute(
                "SELECT run_id, goal, result, trace_json, created_at "
                "FROM run_history WHERE result = ? ORDER BY created_at DESC LIMIT ?",
                (result_filter, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT run_id, goal, result, trace_json, created_at "
                "FROM run_history ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()

        return [
            {
                "run_id": r["run_id"],
                "goal": r["goal"],
                "result": r["result"],
                "trace": json.loads(r["trace_json"]),
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    def search_runs_by_goal(self, keyword: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search run history by goal keyword."""
        rows = self._conn.execute(
            "SELECT run_id, goal, result, created_at "
            "FROM run_history WHERE goal LIKE ? ORDER BY created_at DESC LIMIT ?",
            (f"%{keyword}%", limit),
        ).fetchall()

        return [
            {
                "run_id": r["run_id"],
                "goal": r["goal"],
                "result": r["result"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]

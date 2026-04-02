"""Tests for src/agent/memory.py — SQLite workflow memory."""

import os
import tempfile

import pytest

from src.agent.memory import WorkflowMemory


@pytest.fixture
def memory():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_memory.db")
        mem = WorkflowMemory(db_path=db_path)
        yield mem
        mem.close()


class TestConventions:
    def test_store_and_recall(self, memory):
        memory.store_convention("naming", "fixtures", {"prefix": "Mac700"})
        result = memory.recall_convention("naming", "fixtures")
        assert len(result) == 1
        assert result[0]["value"]["prefix"] == "Mac700"

    def test_recall_by_category(self, memory):
        memory.store_convention("naming", "fixtures", {"prefix": "Mac"})
        memory.store_convention("naming", "groups", {"prefix": "GRP"})
        memory.store_convention("layout", "page1", {"rows": 4})
        result = memory.recall_convention("naming")
        assert len(result) == 2

    def test_upsert_convention(self, memory):
        memory.store_convention("naming", "fixtures", {"prefix": "Mac"})
        memory.store_convention("naming", "fixtures", {"prefix": "Martin"})
        result = memory.recall_convention("naming", "fixtures")
        assert len(result) == 1
        assert result[0]["value"]["prefix"] == "Martin"

    def test_recall_nonexistent(self, memory):
        result = memory.recall_convention("nonexistent")
        assert result == []


class TestRecipes:
    def test_store_and_recall(self, memory):
        steps = [{"tool": "patch_fixture", "args": {"fixture_id": 1}}]
        memory.store_recipe("basic_patch", steps, ["patch", "mac700"])
        result = memory.recall_recipe(name="basic_patch")
        assert len(result) == 1
        assert result[0]["name"] == "basic_patch"
        assert result[0]["steps"] == steps
        assert result[0]["tags"] == ["patch", "mac700"]

    def test_recall_by_tags(self, memory):
        memory.store_recipe("r1", [{"tool": "a"}], ["patch", "mac700"])
        memory.store_recipe("r2", [{"tool": "b"}], ["preset", "color"])
        result = memory.recall_recipe(tags=["patch"])
        assert len(result) == 1
        assert result[0]["name"] == "r1"

    def test_recall_all(self, memory):
        memory.store_recipe("r1", [], ["a"])
        memory.store_recipe("r2", [], ["b"])
        result = memory.recall_recipe()
        assert len(result) == 2

    def test_increment_usage(self, memory):
        memory.store_recipe("r1", [], ["a"])
        memory.increment_recipe_usage("r1")
        memory.increment_recipe_usage("r1")
        result = memory.recall_recipe(name="r1")
        assert result[0]["use_count"] == 2
        assert result[0]["last_used_at"] is not None


class TestRunHistory:
    def test_record_and_recall(self, memory):
        memory.record_run_summary(
            run_id="run_abc",
            goal="List groups",
            result="success",
            trace_json='{"steps": []}',
        )
        result = memory.recall_runs()
        assert len(result) == 1
        assert result[0]["run_id"] == "run_abc"
        assert result[0]["result"] == "success"

    def test_recall_filtered(self, memory):
        memory.record_run_summary("r1", "g1", "success", "{}")
        memory.record_run_summary("r2", "g2", "failure", "{}")
        success = memory.recall_runs(result_filter="success")
        assert len(success) == 1
        failures = memory.recall_runs(result_filter="failure")
        assert len(failures) == 1

    def test_search_by_goal(self, memory):
        memory.record_run_summary("r1", "Patch 8 Mac 700 fixtures", "success", "{}")
        memory.record_run_summary("r2", "List all groups", "success", "{}")
        result = memory.search_runs_by_goal("Mac 700")
        assert len(result) == 1
        assert result[0]["run_id"] == "r1"

    def test_recall_limit(self, memory):
        for i in range(25):
            memory.record_run_summary(f"r{i}", f"goal {i}", "success", "{}")
        result = memory.recall_runs(limit=10)
        assert len(result) == 10

    def test_upsert_run(self, memory):
        memory.record_run_summary("r1", "goal", "failure", "{}")
        memory.record_run_summary("r1", "goal", "success", '{"retry": true}')
        result = memory.recall_runs()
        assert len(result) == 1
        assert result[0]["result"] == "success"

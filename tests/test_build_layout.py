"""build_layout_for_screen — template population + collision detection."""

from __future__ import annotations

import json

import pytest


# ---------------------------------------------------------------------------
# Template table
# ---------------------------------------------------------------------------

def test_template_table_has_six_entries():
    from src.layout_templates import TEMPLATES
    assert set(TEMPLATES.keys()) == {
        "busking-master", "preset-access", "executor-monitor",
        "macro-page", "programmer-view", "troubleshoot-view",
    }


def test_template_unknown_raises():
    from src.layout_templates import get_template
    with pytest.raises(ValueError, match="unknown template"):
        get_template("space-opera-view")


# ---------------------------------------------------------------------------
# Plan builder
# ---------------------------------------------------------------------------

def test_busking_master_template_populates_required_roles():
    from src.layout_templates import build_layout_for, get_template
    _, content = build_layout_for(template="busking-master", screen=1, options=None)
    roles = {c.get("role") for c in content if c.get("role")}
    required = set(get_template("busking-master").required_roles)
    assert required.issubset(roles), (
        f"missing roles: {required - roles}"
    )


def test_each_template_produces_non_empty_plan_and_content():
    from src.layout_templates import TEMPLATES, build_layout_for
    for tmpl in TEMPLATES:
        plan, content = build_layout_for(template=tmpl, screen=1, options=None)
        assert plan, f"{tmpl}: empty plan"
        assert content, f"{tmpl}: empty content"


def test_plan_steps_have_required_fields():
    from src.layout_templates import build_layout_for
    plan, _ = build_layout_for(template="busking-master", screen=1, options=None)
    for s in plan:
        for field in ("order", "kind", "command", "purpose", "meta"):
            assert field in s, f"step {s.get('order')} missing {field}"


def test_first_plan_step_sets_screen():
    from src.layout_templates import build_layout_for
    plan, _ = build_layout_for(template="macro-page", screen=3, options=None)
    assert plan[0]["kind"] == "set-screen"
    assert "Screen 3" in plan[0]["command"]


def test_ascii_preview_marks_used_cells():
    from src.layout_templates import build_layout_for, render_ascii_preview
    _, content = build_layout_for(template="busking-master", screen=1, options=None)
    preview = render_ascii_preview(content, grid_cols=8, grid_rows=5)
    assert preview.count("E") >= 5  # executor cells
    assert "." in preview          # some empty cells


# ---------------------------------------------------------------------------
# Tool envelope
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_build_layout_for_screen_dry_run(monkeypatch):
    monkeypatch.setenv("GMA_MOCK", "schema")
    monkeypatch.setattr("src.server._session_manager", None)
    from src.server import build_layout_for_screen
    raw = await build_layout_for_screen(
        screen=1, template="busking-master", dry_run=True,
    )
    data = json.loads(raw)
    assert data["screen"] == 1
    assert data["template"] == "busking-master"
    assert data["dry_run"] is True
    assert data["plan"]
    assert "preview_ascii" in data
    assert "expert_review" in data


@pytest.mark.asyncio
async def test_build_layout_for_screen_template_unknown_blocks(monkeypatch):
    monkeypatch.setenv("GMA_MOCK", "schema")
    monkeypatch.setattr("src.server._session_manager", None)
    from src.server import build_layout_for_screen
    raw = await build_layout_for_screen(
        screen=1, template="space-opera-view", dry_run=True,
    )
    data = json.loads(raw)
    assert data.get("blocked") is True or "error" in data


@pytest.mark.asyncio
async def test_build_layout_for_screen_requires_template_or_content(monkeypatch):
    """Neither template nor content → blocked with a helpful error."""
    monkeypatch.setenv("GMA_MOCK", "schema")
    monkeypatch.setattr("src.server._session_manager", None)
    from src.server import build_layout_for_screen
    raw = await build_layout_for_screen(screen=1, dry_run=True)
    data = json.loads(raw)
    assert data.get("blocked") is True or "error" in data


@pytest.mark.asyncio
async def test_build_layout_for_screen_blocks_destructive_without_confirm(monkeypatch):
    monkeypatch.setenv("GMA_MOCK", "schema")
    monkeypatch.setattr("src.server._session_manager", None)
    from src.server import build_layout_for_screen
    raw = await build_layout_for_screen(
        screen=1, template="busking-master",
        dry_run=False, confirm_destructive=False,
    )
    data = json.loads(raw)
    assert data.get("blocked") is True
    assert data.get("executed_steps", 0) == 0


@pytest.mark.asyncio
async def test_build_layout_for_screen_custom_content(monkeypatch):
    """Caller-supplied content list goes through expert_lint."""
    monkeypatch.setenv("GMA_MOCK", "schema")
    monkeypatch.setattr("src.server._session_manager", None)
    from src.server import build_layout_for_screen
    content = [
        {"kind": "executor", "target": "1.1.1", "label": "A",
         "grid_x": 0, "grid_y": 0, "width": 1, "height": 1},
        {"kind": "executor", "target": "1.1.2", "label": "B",
         "grid_x": 1, "grid_y": 0, "width": 1, "height": 1},
    ]
    raw = await build_layout_for_screen(screen=1, content=content, dry_run=True)
    data = json.loads(raw)
    assert data["dry_run"] is True
    assert len(data["plan"]) >= 2


@pytest.mark.asyncio
async def test_build_layout_collision_surfaces_in_lint(monkeypatch):
    """Overlapping content cells produce LAYOUT-COLLIDE-001 in the lint report."""
    monkeypatch.setenv("GMA_MOCK", "schema")
    monkeypatch.setattr("src.server._session_manager", None)
    from src.server import build_layout_for_screen
    content = [
        {"kind": "executor", "target": "1.1.1", "label": "A",
         "grid_x": 0, "grid_y": 0, "width": 2, "height": 1},
        {"kind": "executor", "target": "1.1.2", "label": "B",
         "grid_x": 1, "grid_y": 0, "width": 1, "height": 1},
    ]
    raw = await build_layout_for_screen(screen=1, content=content, dry_run=True)
    data = json.loads(raw)
    lint = data.get("expert_review", [])
    assert any(v.get("rule_id") == "LAYOUT-COLLIDE-001" for v in lint), lint

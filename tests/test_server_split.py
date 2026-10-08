"""
server.py split into src/mcp_tools/: one FastMCP instance, every tool reachable
and patchable through src.server.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
PKG = REPO / "src" / "mcp_tools"

# Names tests patch on src.server — tool modules must reach them as _srv.<name>.
CALL_TIME_NAMES = {"get_client", "navigate", "list_destination", "set_property", "get_current_location",
                   "active_context", "_orchestrator", "_session_manager", "_get_session_manager"}


def _tool_modules() -> list[Path]:
    return sorted(p for p in PKG.glob("*.py") if p.name != "__init__.py")


def test_every_tool_is_importable_from_server():
    import src.server as server

    # Orchestration tools are registered inside register_orchestration_tools()
    # closures and were never module attributes — only check the split tools.
    split = {
        name for name, tool in server._ALL_TOOLS.items()
        if tool.fn.__module__ in ("src.server",) or tool.fn.__module__.startswith("src.mcp_tools.")
    }
    assert len(split) == len(server._ALL_TOOLS) - 34
    missing = sorted(name for name in split if not hasattr(server, name))
    assert not missing, missing


def test_tool_modules_register_on_the_server_instance():
    import src.server as server

    for path in _tool_modules():
        module = __import__(f"src.mcp_tools.{path.stem}", fromlist=["mcp"])
        assert getattr(module, "mcp", server.mcp) is server.mcp, path.name


@pytest.mark.parametrize("path", _tool_modules(), ids=lambda p: p.stem)
def test_tool_modules_look_up_patchable_names_at_call_time(path):
    """A direct `get_client()` call in a tool module would ignore patch('src.server.get_client')."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "src.server":
            imported |= {a.asname or a.name for a in node.names}
    bad = sorted(imported & (CALL_TIME_NAMES - {"mcp"}))
    assert not bad, f"{path.name} imports {bad} directly; use _srv.<name> inside functions"


def test_python_dash_m_runs_with_all_tools_on_one_instance():
    """`python -m src.server` hands over to the canonical module (no second FastMCP)."""
    env = {**os.environ, "GMA_TRANSPORT": "not-a-transport", "GMA_TELEMETRY": "0"}
    proc = subprocess.run(
        [sys.executable, "-m", "src.server"], cwd=REPO, env=env,
        capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode != 0
    assert "Invalid GMA_TRANSPORT" in proc.stderr
    assert "ImportError" not in proc.stderr and "circular" not in proc.stderr.lower()

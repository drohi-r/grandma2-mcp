"""MCP tools — agent. Split out of src/server.py.

Tools register on ``src.server.mcp`` at import. Names that tests patch or
that live in other tool modules are looked up as ``_srv.<name>`` at call time.
"""

# ruff: noqa: E501

import json

import src.server as _srv
from src.auth import OAuthScope, require_scope
from src.mcp_features import (
    ask_destructive_confirmation,
)
from src.server import (
    _handle_errors,
    mcp,
)

# ============================================================
# Agent Harness
# ============================================================


def _build_tool_registry() -> dict:
    """Build a registry mapping tool names to their async callables.

    This enables the agent runtime to call MCP tools directly as Python
    functions, without going through the MCP protocol.

    Uses FastMCP's tool manager as the authoritative source so that the
    registry is always exactly the set of registered MCP tools — no more,
    no less. Falls back to globals() introspection if the FastMCP internals
    change in a future version.
    """
    registry: dict = {}
    try:
        # All registered tools — a GMA_TOOL_PROFILE only hides them from clients.
        all_tools = getattr(_srv, "_ALL_TOOLS", None) or _srv.mcp._tool_manager._tools
        for tool_name, tool_obj in all_tools.items():
            fn = getattr(tool_obj, "fn", None)
            if fn is not None:
                registry[tool_name] = fn
    except AttributeError:
        # Fallback: scan module globals for @_handle_errors-wrapped async fns
        import inspect

        for name, obj in vars(_srv).items():
            if callable(obj) and hasattr(obj, "__wrapped__") or inspect.iscoroutinefunction(obj) and not name.startswith("_"):
                registry[name] = obj
    return registry


@mcp.tool()
@require_scope(OAuthScope.SYSTEM_ADMIN)
@_handle_errors
async def run_agent_goal(
    goal: str,
    auto_confirm: bool = False,
    dry_run: bool = False,
) -> str:
    """Execute a high-level production goal using the agent runtime.

    The agent runtime decomposes the goal into a sequenced plan, validates
    it against safety policies, executes steps with verification, and
    produces a structured execution trace.

    SAFETY: Destructive steps require confirmation. Set auto_confirm=True
    to skip confirmation prompts (use with caution).

    Args:
        goal: Natural language goal, e.g. "Patch 8 Mac 700 fixtures
            starting at address 1.001 and assign to executor 1"
        auto_confirm: If True, auto-confirm all destructive steps.
            If False (default), destructive steps remain blocked unless
            the runtime can obtain an explicit confirmation callback.
        dry_run: If True, generate and validate the plan but do NOT
            execute it. Returns the plan and policy warnings.

    Returns:
        str: JSON execution trace with goal, plan, steps, result,
            and timing information.

    Examples:
        - "List all groups" → discovery workflow
        - "Patch 4 Mac 700 fixtures at 1.001" → patch workflow
        - "Create a color preset for group 1" → preset workflow
    """
    from src.agent.runtime import AgentRuntime

    registry = _srv._build_tool_registry()
    runtime = AgentRuntime(tool_registry=registry)

    if dry_run:
        parsed_goal, plan, warnings = await runtime.plan_only(goal)
        return json.dumps({
            "dry_run": True,
            "goal": goal,
            "intent": parsed_goal.intent.value,
            "confidence": parsed_goal.confidence,
            "notes": getattr(parsed_goal, "notes", []),
            "plan": [s.to_dict() for s in plan],
            "policy_warnings": warnings,
        }, indent=2)

    # Auto-confirm callback for the agent runtime
    async def _auto_confirm(step) -> bool:
        return True

    # Without auto_confirm, ask the human per destructive step when the client
    # supports elicitation; otherwise the run stops at the first destructive step.
    ctx = _srv.active_context(_srv.mcp)

    async def _elicit_confirm(step) -> bool:
        answer = await ask_destructive_confirmation(
            ctx, step.tool_name, dict(step.tool_args), f"Agent step: {step.description}",
        )
        return answer is True

    on_confirm = _auto_confirm if auto_confirm else None
    if on_confirm is None and ctx is not None:
        from src.mcp_features import client_supports_elicitation, elicitation_enabled

        if elicitation_enabled() and client_supports_elicitation(ctx):
            on_confirm = _elicit_confirm

    trace = await runtime.run(goal, on_confirm=on_confirm)
    return trace.to_json()


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def plan_agent_goal(goal: str) -> str:
    """Generate a plan for a goal WITHOUT executing it.

    Useful for previewing what the agent would do before committing.
    Returns the parsed goal, generated plan steps, and any policy warnings.

    Args:
        goal: Natural language goal to plan for.

    Returns:
        str: JSON with intent, plan steps, confidence, and warnings.
    """
    from src.agent.runtime import AgentRuntime

    registry = _srv._build_tool_registry()
    runtime = AgentRuntime(tool_registry=registry)

    parsed_goal, plan, warnings = await runtime.plan_only(goal)
    return json.dumps({
        "goal": goal,
        "intent": parsed_goal.intent.value,
        "object_type": parsed_goal.object_type,
        "confidence": parsed_goal.confidence,
        "notes": parsed_goal.notes,
        "step_count": len(plan),
        "plan": [
            {
                "description": s.description,
                "tool": s.tool_name,
                "risk_tier": s.risk_tier.value,
                "depends_on_count": len(s.depends_on),
            }
            for s in plan
        ],
        "policy_warnings": warnings,
    }, indent=2)

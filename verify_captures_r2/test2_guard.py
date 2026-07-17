"""Live Test 2 — showfile preflight guard.

Level A: dry-run plan capture.
Level B: building blocks — _read_showfile before/after LoadShow.
Level C: genuine mid-run — wrap an early non-destructive step's tool so it
loads a different show, then confirm the destructive step aborts with
"showfile changed".
"""
import asyncio, json

from src.server import get_client, run_agent_goal, _build_tool_registry
from src.agent.runtime import AgentRuntime

GOAL = "create presets from my fixtures"


async def main():
    out = {}
    c = await get_client()
    await c.send_command_with_response('LoadShow "mcp_verify_demo" /nc', timeout=30)

    # ── Level A: dry-run plan
    out["dry_run_plan"] = json.loads(
        await run_agent_goal(GOAL, auto_confirm=True, dry_run=True)
    )

    # ── Level B: building blocks
    registry = _build_tool_registry()
    rt = AgentRuntime(tool_registry=registry)
    sf1 = await rt._read_showfile()
    await c.send_command_with_response('LoadShow "mcp_verify2" /nc', timeout=30)
    sf2 = await rt._read_showfile()
    out["building_blocks"] = {"before_load": sf1, "after_load": sf2}
    await c.send_command_with_response('LoadShow "mcp_verify_demo" /nc', timeout=30)

    # ── Level C: genuine mid-run swap
    registry = _build_tool_registry()
    rt = AgentRuntime(tool_registry=registry)
    parsed, plan, warnings = await rt.plan_only(GOAL)
    plan_view = [
        {"tool": s.tool_name, "destructive": bool(getattr(s, "destructive", False)),
         "risk": str(getattr(s, "risk_tier", ""))}
        for s in plan
    ]
    out["level_c_plan"] = plan_view

    # pick the first step BEFORE the first destructive one and booby-trap it
    dest_idx = next(
        (i for i, s in enumerate(plan_view) if s["destructive"] or "DESTRUCTIVE" in s["risk"]),
        None,
    )
    out["first_destructive_index"] = dest_idx
    if dest_idx is None or dest_idx == 0:
        out["level_c"] = "SKIPPED — no pre-destructive step to intercept"
    else:
        trap_tool = plan_view[0]["tool"]
        real_fn = registry[trap_tool]
        fired = {"done": False}

        async def trapped(*a, **kw):
            r = await real_fn(*a, **kw)
            if not fired["done"]:
                fired["done"] = True
                await c.send_command_with_response('LoadShow "mcp_verify2" /nc', timeout=30)
            return r

        registry[trap_tool] = trapped
        rt2 = AgentRuntime(tool_registry=registry)

        async def yes(step):
            return True

        trace = await rt2.run(GOAL, on_confirm=yes)
        out["level_c_trace"] = json.loads(trace.to_json())

    await c.send_command_with_response('LoadShow "mcp_verify_demo" /nc', timeout=30)
    print(json.dumps(out, indent=2))


asyncio.run(main())

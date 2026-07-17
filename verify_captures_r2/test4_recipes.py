"""Live Test 4 — recipe store/reuse loop + destructive sanitization."""
import asyncio, json, logging

logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")

import src.server as s
from src.agent.memory import WorkflowMemory

SAFE_GOAL = "list all groups"
DEST_GOAL = 'make a color chaser with 4 cues into sequence 92 on executor 17'


async def main():
    out = {}

    t1 = json.loads(await s.run_agent_goal(SAFE_GOAL, auto_confirm=True))
    out["safe_run1"] = t1["result"]
    mem = WorkflowMemory()
    r1 = mem.recall_recipe(SAFE_GOAL)
    out["recipe_after_run1"] = r1

    t2 = json.loads(await s.run_agent_goal(SAFE_GOAL, auto_confirm=True))
    out["safe_run2"] = t2["result"]
    r2 = mem.recall_recipe(SAFE_GOAL)
    out["recipe_after_run2"] = r2

    # Destructive goal twice
    d1 = json.loads(await s.run_agent_goal(DEST_GOAL, auto_confirm=True))
    out["dest_run1"] = d1["result"]
    rd = mem.recall_recipe(DEST_GOAL)
    out["dest_recipe"] = rd
    out["dest_recipe_confirm_flags"] = [
        {"tool": st.get("tool_name"), "confirm": st.get("tool_args", {}).get("confirm_destructive")}
        for st in (rd[0].get("steps", []) if rd else [])
    ]

    d2 = json.loads(await s.run_agent_goal(DEST_GOAL, auto_confirm=True))
    out["dest_run2"] = d2["result"]
    out["dest_run2_steps"] = [
        {"tool": st["tool_name"], "status": st["status"],
         "confirm": st.get("tool_args", {}).get("confirm_destructive")}
        for st in d2["steps"]
    ]
    rd2 = mem.recall_recipe(DEST_GOAL)
    out["dest_recipe_after_replay"] = [
        {"name": r.get("name"), "use_count": r.get("use_count")} for r in (rd2 or [])
    ]

    print("===JSON===")
    print(json.dumps(out, indent=2, default=str))


asyncio.run(main())

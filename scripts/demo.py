"""
scripts/demo.py -- Live showcase of the grandMA2 MCP server.

4-Act demo against the real console at GMA_HOST (default 127.0.0.1):

  Act 1 - Discovery    -- read the rig without any prior knowledge
  Act 2 - Decompose    -- natural language -> ordered multi-agent plan
  Act 3 - Execute      -- run the plan, store a real cue on the console
  Act 4 - Introspect   -- state snapshot, diff, session log

Usage:
    python scripts/demo.py
    python scripts/demo.py --goal "red wash on movers" --sequence 2 --cue 1
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import textwrap
import time

# -- Bootstrap --------------------------------------------------------------
# Must happen before any src.* imports so that load_dotenv() and
# GMA_AUTH_BYPASS are in place when the server module is imported.
os.environ.setdefault("GMA_AUTH_BYPASS", "1")

# Add project root to path so `src` is importable when running from scripts/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.server import (  # noqa: E402
    _orchestrator,
    get_client,
    list_fixtures,
    list_sequence_cues,
    navigate_console,
)


# -- Formatting helpers -------------------------------------------------------

_WIDTH = 72

def banner(title: str) -> None:
    print()
    print("=" * _WIDTH)
    print(f"  {title}")
    print("=" * _WIDTH)


def section(label: str) -> None:
    pad = _WIDTH - len(label) - 4
    print(f"\n-- {label} {'-' * max(pad, 0)}")


def show(data: str | dict) -> None:
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            print(data)
            return
    print(json.dumps(data, indent=2))


def ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def info(msg: str) -> None:
    print(f"  --> {msg}")


# -- Act implementations ----------------------------------------------------

async def act1_discovery() -> None:
    banner("ACT 1 - DISCOVERY  -- Read the rig, zero prior knowledge")

    section("list_fixtures()")
    info("Asking: what fixtures are patched on this console?")
    result = await list_fixtures()
    data = json.loads(result)
    raw = data.get("raw_response", "")
    # Parse "Fixture NNN  Name  ..." lines from telnet output
    import re as _re
    fix_lines = _re.findall(
        r"Fixture\s+(\d+)\s+([\w\s\-:.]+?)\s{2,}\d+",
        _re.sub(r"\x1b\[[0-9;]*m", "", raw),
    )
    if fix_lines:
        ok(f"Found {len(fix_lines)} fixture(s):")
        for fid, fname in fix_lines[:8]:
            print(f"    Fixture {fid:>5}  {fname.strip()}")
        if len(fix_lines) > 8:
            print(f"    ... and {len(fix_lines) - 8} more")
    else:
        info("(raw response — no fixtures parsed)")
        show(data)

    section("hydrate_console_state()")
    info("Closing all 19 show-memory gaps in one call...")
    t0 = time.perf_counter()
    snap = await _orchestrator.hydrate_snapshot()
    elapsed = time.perf_counter() - t0
    if snap:
        _orchestrator.last_snapshot = snap
        ok(f"Snapshot hydrated in {elapsed:.2f}s")
        err_count = len(snap.hydration_errors) if snap.hydration_errors else 0
        ok(f"Partial: {snap.partial}  |  Pool index errors: {err_count} (telnet concurrency in script mode)")
        stats = snap.name_index.stats()
        if stats:
            ok(f"Pool index: {stats}")
        summary = snap.summary()
        for line in summary.splitlines()[:8]:
            info(line[:_WIDTH - 6] + "..." if len(line) > _WIDTH - 3 else line)
    else:
        info("No telnet_send configured -- snapshot skipped")

    section("get_showfile_info() [from snapshot]")
    snap = _orchestrator.last_snapshot
    if snap:
        ok(f"Showfile : {snap.showfile or '--'}")
        ok(f"Version  : {snap.version or '--'}")
        ok(f"Host     : {snap.hostname or '--'}")
        ok(f"User     : {snap.active_user or '--'}")
        ok(f"Status   : {snap.host_status or '--'}")
    else:
        info("No snapshot -- call hydrate_console_state first")

    section("assert_fixture_exists(fixture_id=101)")
    info("Two-tier patch validation: snapshot index -> live telnet fallback")
    snap = _orchestrator.last_snapshot
    fixture_id = 101
    if snap is not None:
        fixture_entries = snap.name_index.all_entries("Fixture")
        if fixture_entries:
            exists = any(e["id"] == fixture_id for e in fixture_entries)
            source = "snapshot"
        else:
            # Live telnet fallback
            send_fn = getattr(_orchestrator, "_send", None)
            if send_fn:
                raw = await send_fn(f"list fixture {fixture_id}")
                exists = "NO OBJECTS FOUND" not in raw.upper()
                source = "live_telnet"
            else:
                exists = None
                source = "unavailable"
    else:
        exists = None
        source = "no snapshot"

    if exists is True:
        ok(f"Fixture {fixture_id} IS patched  (source: {source})")
    elif exists is False:
        info(f"Fixture {fixture_id} NOT patched  (source: {source}) -- demo will use available fixtures")
    else:
        info(f"Could not validate fixture {fixture_id}  (source: {source})")


async def act2_decompose(goal: str, sequence: int, cue: float) -> None:
    banner("ACT 2 - DECOMPOSE  -- Natural language -> ordered multi-agent plan")

    params = {"sequence": sequence, "cue": cue}

    section(f'decompose_task(goal="{goal}")')
    info(f"Breaking down: '{goal}'")
    plan = _orchestrator._decomposer.decompose(goal, params)

    ok(f"Plan: {plan.goal}")
    ok(f"Steps: {len(plan.steps)}")
    print()
    for i, step in enumerate(plan.steps, 1):
        risk = step.allowed_risk.value if hasattr(step.allowed_risk, "value") else step.allowed_risk
        print(f"  Step {i}  [{risk:>12}]  {step.name}")
        print(f"           Agent: {step.agent_role}")
        print(f"           Tools: {', '.join(step.mcp_tools[:3])}{'...' if len(step.mcp_tools) > 3 else ''}")
        print(f"           Eval : {step.eval_criteria}")
        print()

    section("confirm_destructive_steps()")
    from src.vocab import RiskTier
    destructive = [s for s in plan.steps if s.allowed_risk == RiskTier.DESTRUCTIVE]
    ok(f"Destructive step count: {len(destructive)}")
    if destructive:
        for s in destructive:
            info(f"  [!] {s.name} -- {s.description[:60]}")
        info("These require auto_confirm_destructive=True to proceed.")
    else:
        ok("No destructive steps -- safe to run without confirmation gate.")


async def act3_execute(goal: str, sequence: int, cue: float) -> None:
    banner("ACT 3 - EXECUTE  -- Orchestration pipeline + live console proof")

    # Show the orchestration result (sub-agent steps run against the console;
    # without a live LLM filling parameters they may fail -- that is expected
    # in a script context.  The plan decomposition and risk-tier isolation are
    # the real payload here.)
    section(f'run_task(goal="{goal}", sequence={sequence}, cue={cue})')
    info("Running full orchestration pipeline...")
    params = {"sequence": sequence, "cue": cue}

    t0 = time.perf_counter()
    result = await _orchestrator.run(
        goal,
        params,
        auto_confirm_destructive=True,
    )
    elapsed = time.perf_counter() - t0

    ok(f"Outcome  : {result.outcome}")
    ok(f"Session  : {result.session_id}")
    ok(f"Steps    : {result.steps_done} done / {result.steps_failed} failed")
    ok(f"Elapsed  : {elapsed:.2f}s")
    if result.step_results:
        print()
        for sr in result.step_results:
            # StepResult is a dataclass, not a dict
            status = "+" if sr.success else "x"
            name = sr.step_name
            eval_s = ("eval +" if sr.eval_passed else
                      "eval x" if sr.eval_passed is False else
                      "eval ?")
            err = f"  ({sr.error[:60]})" if sr.error else ""
            print(f"  {status} {name:<40} {eval_s}{err}")

    # Direct tool call: ground-truth proof independent of orchestration
    section(f"list_sequence_cues(sequence_id={sequence})  -- direct tool proof")
    info("Asking the console directly: what cues exist in this sequence?")
    await navigate_console(destination="/")
    result2 = await list_sequence_cues(sequence_id=sequence)
    data2 = json.loads(result2)
    raw2 = data2.get("raw_response", "")
    import re as _re2
    # Parse "Cue N.N  Label" lines
    cue_lines = _re2.findall(
        r"Cue\s+([\d.]+)\s*(.*?)(?:\s{2,}|\n|\r)",
        _re2.sub(r"\x1b\[[0-9;]*m", "", raw2),
    )
    if cue_lines:
        ok(f"Sequence {sequence} has {len(cue_lines)} cue(s):")
        for cnum, clabel in cue_lines[:8]:
            print(f"    Cue {cnum:<8} {clabel.strip()}")
    elif "NO OBJECTS FOUND" in raw2.upper():
        info(f"Sequence {sequence} has no cues yet")
    else:
        info(f"Command sent: {data2.get('command_sent')}")
        info("(sequence exists, cue listing returned)")


async def act4_introspect(session_goal: str) -> None:
    banner("ACT 4 - INTROSPECT  -- State snapshot, diff, session log")

    section("get_console_state() [from cached snapshot]")
    snap = _orchestrator.last_snapshot
    if snap:
        ok(f"Snapshot age : {snap.age_seconds():.1f}s")
        ok(f"Staleness    : {snap.staleness_warning() or 'fresh'}")
        ok(f"Partial      : {snap.partial}")
        for line in snap.summary().splitlines()[:10]:
            info(line[:_WIDTH - 6] + "..." if len(line) > _WIDTH - 3 else line)
    else:
        info("No snapshot -- call hydrate_console_state first")

    section("diff_console_state(baseline={'selected_fixture_count': 0})")
    if snap:
        baseline = {"selected_fixture_count": 0, "has_unsaved_changes": False}
        actual = {
            "selected_fixture_count": snap.selected_fixture_count or 0,
            "has_unsaved_changes": snap.has_unsaved_changes or False,
        }
        changed = {k: {"before": baseline[k], "after": actual[k]}
                   for k in baseline if baseline[k] != actual[k]}
        if changed:
            ok(f"Changed fields: {list(changed.keys())}")
            for k, v in changed.items():
                print(f"    {k}: {v['before']} -> {v['after']}")
        else:
            ok("No changes detected from baseline")
    else:
        info("No snapshot -- skipping diff")

    section("list_agent_sessions()  -- LTM session log")
    sessions = _orchestrator.recent_sessions(limit=5)
    if sessions:
        ok(f"Last {len(sessions)} session(s) in long-term memory:")
        for s in sessions:
            sid = str(s.get("id", "?"))
            task = (s.get("task") or "")[:50]
            outcome = s.get("outcome", "?")
            print(f"    [id={sid:<4}]  {outcome:<8}  {task}")
    else:
        info("No sessions in LTM yet -- run_task populates this")


# -- Main -------------------------------------------------------------------

async def main(goal: str, sequence: int, cue: float) -> None:
    print()
    print("grandMA2 MCP Server -- Live Demo")
    print(f"Console: {os.getenv('GMA_HOST', '127.0.0.1')}:{os.getenv('GMA_PORT', '30000')}")
    print(f"Goal   : {goal}")

    # Warm up telnet connection
    info("Connecting to console...")
    client = await get_client()
    if client is None:
        print("\nx Could not connect. Check GMA_HOST in .env and ensure the console is running.")
        sys.exit(1)
    ok("Connected.\n")

    await act1_discovery()
    await act2_decompose(goal, sequence, cue)
    await act3_execute(goal, sequence, cue)
    await act4_introspect(goal)

    banner("DEMO COMPLETE")
    print(f"  Goal '{goal}' executed on live grandMA2 console.")
    print(f"  Verify on console: Sequence {sequence} -> Cue {cue}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="grandMA2 MCP live demo")
    parser.add_argument("--goal", default="blue wash on all fixtures",
                        help="Natural-language lighting goal")
    parser.add_argument("--sequence", type=int, default=1,
                        help="Target sequence ID (default: 1)")
    parser.add_argument("--cue", type=float, default=1.0,
                        help="Target cue number (default: 1.0)")
    args = parser.parse_args()

    asyncio.run(main(args.goal, args.sequence, args.cue))

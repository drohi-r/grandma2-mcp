"""
Agent harness contracts: planned steps must be callable, read-backs must be
real checks, and a failed check must fail the step.
"""

import inspect
import json
from unittest.mock import AsyncMock

import pytest

from src.agent.executor import StepExecutor
from src.agent.planner import DomainPlanner
from src.agent.policy import PolicyEngine
from src.agent.state import GoalIntent, PlanStep, RunContext, StepStatus
from src.agent.verification import VERIFICATION_STRATEGIES, Verifier, build_verification_call
from src.vocab import RiskTier

# One goal per intent plus the phrasings that used to mis-plan.
GOALS = [
    'patch 12 "Mac 700 Profile" fixtures at universe 1 address 1',
    "patch 4 fixtures at 2.101",
    "create color preset 4.1 red for group 1",
    "store position preset 2.5 for fixtures 1-8",
    "store cue 1 in sequence 5 and assign executor 201",
    "store cue 3 in sequence 7 and assign to executor 2.105",
    "create group 5 from fixtures 1-10",
    'create group 5 from fixtures 1-10 named "Front Wash"',
    "create group 5",
    'label group 3 "Back Truss"',
    'rename executor 1.201 "Intro"',
    "list all sequences",
    "create presets from my patch",
    "run the color picker plugin",
    "renumber fixture ids into blocks",
    "dimmer wave effect on group 2",
    "color chaser on executor 5 with fixtures 1-8",
    "every other fixture matricks interleave 2 on group 1",
    "patch 4 fixtures and create a preset and store cue 1 in sequence 2",
    "make it look nice",
]


@pytest.fixture(scope="module")
def tools():
    from src.server import mcp

    return {name: t.fn for name, t in mcp._tool_manager._tools.items()}


def _assert_callable(tool_name, args, tools, where):
    assert tool_name in tools, f"{where}: unknown tool {tool_name}"
    params = inspect.signature(tools[tool_name]).parameters
    unknown = sorted(set(args) - set(params))
    required = {
        n for n, p in params.items()
        if p.default is inspect.Parameter.empty and p.kind not in (p.VAR_KEYWORD, p.VAR_POSITIONAL)
    }
    missing = sorted(required - set(args))
    assert not unknown and not missing, f"{where}: {tool_name} unknown={unknown} missing={missing} args={args}"


@pytest.mark.parametrize("goal", GOALS)
def test_planned_steps_match_tool_signatures(goal, tools):
    _, steps = DomainPlanner().plan_from_text(goal)
    for step in steps:
        _assert_callable(step.tool_name, step.tool_args, tools, f"{goal!r} step {step.description!r}")


@pytest.mark.parametrize("goal", GOALS)
def test_verification_calls_match_tool_signatures(goal, tools):
    _, steps = DomainPlanner().plan_from_text(goal)
    for step in steps:
        call = build_verification_call(step)
        if call is not None:
            verify_tool, verify_args = call
            _assert_callable(verify_tool, verify_args, tools, f"verify {step.tool_name}")


def test_every_strategy_tool_is_registered(tools):
    for name, strategy in VERIFICATION_STRATEGIES.items():
        assert name in tools
        assert strategy.verify_tool in tools


# --- planner extraction ---


def _plan(goal):
    return DomainPlanner().plan_from_text(goal)


def _step(steps, tool_name):
    matches = [s for s in steps if s.tool_name == tool_name]
    assert matches, f"no {tool_name} step in {[s.tool_name for s in steps]}"
    return matches[0]


def test_playback_uses_ids_from_goal():
    _, steps = _plan("store cue 3 in sequence 7 and assign to executor 2.105")
    store = _step(steps, "store_current_cue")
    assert store.tool_args["sequence_id"] == 7
    assert store.tool_args["cue_number"] == 3
    assign = _step(steps, "assign_object")
    assert assign.tool_args["source_id"] == 7
    assert assign.tool_args["target_id"] == "2.105"


def test_preset_uses_type_and_id_from_goal():
    _, steps = _plan("create color preset 4.1 red for group 1")
    store = _step(steps, "store_new_preset")
    assert store.tool_args["preset_type"] == "color"
    assert store.tool_args["preset_id"] == 1
    assert _step(steps, "select_fixtures_by_group").tool_args["group_id"] == 1


def test_preset_dotted_id_sets_type():
    _, steps = _plan("store preset 2.5 for fixtures 1-8")
    store = _step(steps, "store_new_preset")
    assert (store.tool_args["preset_type"], store.tool_args["preset_id"]) == ("position", 5)


def test_patch_uses_universe_and_address():
    _, steps = _plan("patch 4 fixtures at 2.101")
    patches = [s for s in steps if s.tool_name == "patch_fixture"]
    assert [(p.tool_args["dmx_universe"], p.tool_args["dmx_address"]) for p in patches][0] == (2, 101)


def test_label_goal_labels_instead_of_creating_group():
    parsed, steps = _plan('label group 3 "Back Truss"')
    assert parsed.intent == GoalIntent.LABEL
    assert all(s.tool_name != "create_fixture_group" for s in steps)
    label = _step(steps, "label_or_appearance")
    assert label.tool_args["object_id"] == 3 and label.tool_args["name"] == "Back Truss"


def test_group_without_fixture_range_does_not_invent_one():
    parsed, steps = _plan("create group 5")
    assert all(s.tool_name != "create_fixture_group" for s in steps)
    assert any("fixture range" in n for n in parsed.notes)


def test_unrecognized_goal_is_flagged_low_confidence():
    parsed, steps = _plan("make it look nice")
    assert parsed.confidence < 0.5
    assert any("not recognized" in n for n in parsed.notes)
    assert all(s.risk_tier == RiskTier.SAFE_READ for s in steps)


def test_explicit_discovery_goal_keeps_high_confidence():
    parsed, _ = _plan("list all sequences")
    assert parsed.confidence >= 0.9
    assert parsed.notes == []


# --- verification behaviour ---


def _reply(raw, **extra):
    return json.dumps({"command_sent": "list", "raw_response": raw, "ok": True, **extra})


def _group_step():
    return PlanStep(
        tool_name="create_fixture_group",
        tool_args={"start_fixture": 1, "end_fixture": 10, "group_id": 5, "confirm_destructive": True},
        description="Create group 5",
        risk_tier=RiskTier.DESTRUCTIVE,
    )


@pytest.mark.asyncio
async def test_group_verification_reads_back_the_specific_group():
    query = AsyncMock(return_value=_reply("Group 5  Front Wash  10 fixtures\r\n[Channel]>"))
    result = await Verifier({"query_object_list": query}).verify_step(_group_step(), RunContext(goal="g", plan=[]))
    query.assert_awaited_once_with(object_type="group", object_id=5)
    assert result.passed


@pytest.mark.asyncio
async def test_group_verification_fails_when_console_has_no_such_object():
    query = AsyncMock(return_value=_reply("NO OBJECTS FOUND FOR LIST", console_warnings=["NO OBJECTS FOUND"]))
    result = await Verifier({"query_object_list": query}).verify_step(_group_step(), RunContext(goal="g", plan=[]))
    assert not result.passed


@pytest.mark.asyncio
async def test_label_verification_checks_the_name():
    step = PlanStep(
        tool_name="label_or_appearance",
        tool_args={"action": "label", "object_type": "group", "object_id": 3, "name": "Back Truss"},
        description="Label group 3",
        risk_tier=RiskTier.DESTRUCTIVE,
    )
    good = AsyncMock(return_value=_reply("Group 3  Back Truss\r\n[Channel]>"))
    bad = AsyncMock(return_value=_reply("Group 3  Old Name\r\n[Channel]>"))
    assert (await Verifier({"query_object_list": good}).verify_step(step, RunContext(goal="g", plan=[]))).passed
    assert not (await Verifier({"query_object_list": bad}).verify_step(step, RunContext(goal="g", plan=[]))).passed


@pytest.mark.asyncio
async def test_assign_verification_checks_executor_sequence():
    step = PlanStep(
        tool_name="assign_object",
        tool_args={"mode": "assign", "source_type": "Sequence", "source_id": 7,
                   "target_type": "Executor", "target_id": "2.105"},
        description="Assign",
        risk_tier=RiskTier.DESTRUCTIVE,
    )
    good = AsyncMock(return_value=_reply("Exec 2.105 Sequence=Seq 7 Width=1\r\n[Channel]>"))
    wrong = AsyncMock(return_value=_reply("Exec 2.105 Sequence=Seq 77 Width=1\r\n[Channel]>"))
    assert (await Verifier({"get_executor_status": good}).verify_step(step, RunContext(goal="g", plan=[]))).passed
    good.assert_awaited_once_with(executor_id=105, page=2)
    assert not (await Verifier({"get_executor_status": wrong}).verify_step(step, RunContext(goal="g", plan=[]))).passed


@pytest.mark.asyncio
async def test_delete_verification_passes_only_when_gone():
    step = PlanStep(
        tool_name="delete_object",
        tool_args={"object_type": "group", "object_id": 5, "confirm_destructive": True},
        description="Delete group 5",
        risk_tier=RiskTier.DESTRUCTIVE,
    )
    gone = AsyncMock(return_value=_reply("NO OBJECTS FOUND FOR LIST", console_warnings=["NO OBJECTS FOUND"]))
    there = AsyncMock(return_value=_reply("Group 5  Wash\r\n[Channel]>"))
    assert (await Verifier({"query_object_list": gone}).verify_step(step, RunContext(goal="g", plan=[]))).passed
    assert not (await Verifier({"query_object_list": there}).verify_step(step, RunContext(goal="g", plan=[]))).passed


@pytest.mark.asyncio
async def test_read_back_failure_fails_verification():
    query = AsyncMock(return_value=json.dumps({"ok": False, "error": "Connection failed"}))
    result = await Verifier({"query_object_list": query}).verify_step(_group_step(), RunContext(goal="g", plan=[]))
    assert not result.passed


# --- executor behaviour ---


def _executor(tools, **kw):
    return StepExecutor(tools, PolicyEngine(), Verifier(tools), **kw)


@pytest.mark.asyncio
async def test_failed_verification_fails_the_step_and_skips_dependents():
    create = AsyncMock(return_value=json.dumps({"command_sent": "Group 1 Thru 10", "raw_response": "[Channel]>", "ok": True}))
    query = AsyncMock(return_value=_reply("NO OBJECTS FOUND FOR LIST", console_warnings=["NO OBJECTS FOUND"]))
    label = AsyncMock(return_value=json.dumps({"ok": True}))
    step = _group_step()
    dependent = PlanStep(tool_name="label_or_appearance",
                         tool_args={"action": "label", "object_type": "group", "object_id": 5, "name": "X"},
                         description="Label", depends_on=[step.id], risk_tier=RiskTier.DESTRUCTIVE)
    ctx = RunContext(goal="g", plan=[step, dependent])

    await _executor({"create_fixture_group": create, "query_object_list": query,
                     "label_or_appearance": label}).execute_plan(ctx, on_confirm=AsyncMock(return_value=True))

    assert step.status == StepStatus.FAILED
    assert "Verification failed" in step.error
    assert dependent.status == StepStatus.SKIPPED
    create.assert_awaited_once()  # a failed check is not retried
    label.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("reply", [
    {"blocked": True, "error": "Set confirm_destructive=True", "ok": False},
    {"command_sent": "x", "raw_response": "Error #66 CANNOT ASSIGN", "ok": False,
     "console_errors": [{"code": 66, "message": "CANNOT ASSIGN", "kind": "rejected"}],
     "error": "Console rejected the command: Error #66 CANNOT ASSIGN"},
])
async def test_refusals_are_not_retried(reply):
    tool = AsyncMock(return_value=json.dumps(reply))
    step = PlanStep(tool_name="go_tool", tool_args={}, description="go", risk_tier=RiskTier.SAFE_WRITE)
    ctx = RunContext(goal="g", plan=[step])
    await _executor({"go_tool": tool}).execute_plan(ctx)
    assert step.status == StepStatus.FAILED
    tool.assert_awaited_once()


@pytest.mark.asyncio
async def test_ok_false_without_error_key_is_a_failure():
    tool = AsyncMock(return_value=json.dumps({"ok": False}))
    step = PlanStep(tool_name="t", tool_args={}, description="t", risk_tier=RiskTier.SAFE_READ)
    ctx = RunContext(goal="g", plan=[step])
    await _executor({"t": tool}, max_retries=0).execute_plan(ctx)
    assert step.status == StepStatus.FAILED


@pytest.mark.asyncio
async def test_error_none_is_not_a_failure():
    tool = AsyncMock(return_value=json.dumps({"error": None, "result": 1}))
    step = PlanStep(tool_name="t", tool_args={}, description="t", risk_tier=RiskTier.SAFE_READ)
    ctx = RunContext(goal="g", plan=[step])
    await _executor({"t": tool}).execute_plan(ctx)
    assert step.status == StepStatus.COMPLETED


# --- legacy orchestration: registered rules must reach decompose_task ---


@pytest.mark.asyncio
async def test_decompose_task_uses_registered_rules():
    from src.server import mcp

    t = mcp._tool_manager._tools
    await t["register_decomposition_rule"].fn(
        pattern=r"zz contract probe",
        steps_json=json.dumps([{"name": "probe_rule_step", "description": "probe rule",
                                "mcp_tools": ["list_system_variables"]}]),
    )
    data = json.loads(await t["decompose_task"].fn(goal="zz contract probe"))
    assert any("probe" in (s.get("description") or "") or "probe" in (s.get("name") or "")
               for s in data["step_list"]), data

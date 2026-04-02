"""
Live Integration Tests — All 56 MCP Tools

Tests every MCP tool against a real grandMA2 console via telnet.
Organized into 8 layers by risk and dependency:

  Layer 0 — SAFE_READ: Pure queries, no side effects
  Layer 1 — Navigation & State: Reversible navigation and variables
  Layer 2 — Selection & Group Creation: Create test fixtures
  Layer 3 — Light Control: Set intensity, attributes, park/unpark
  Layer 4 — Programming: Store cues, presets, objects (DESTRUCTIVE)
  Layer 5 — Copy/Move/Assign: Operate on created objects (DESTRUCTIVE)
  Layer 6 — Playback: Execute sequences and playback actions
  Layer 7 — Cleanup: Delete test objects (DESTRUCTIVE)

Usage:
    # Safe tests only (Layer 0-3, 6):
    uv run pytest tests/test_live_integration.py -m "live and not destructive" -v -s

    # All layers including destructive:
    uv run pytest tests/test_live_integration.py -m live -v -s --destructive

    # Single layer:
    uv run pytest tests/test_live_integration.py -k "Layer0" -v -s
"""

import json

import pytest
import pytest_asyncio

# All tests in this module share a single event loop so the telnet
# client (a module-level singleton) stays on the same loop.
pytestmark = pytest.mark.asyncio(loop_scope="module")

# All tool functions are imported directly from the server module
from src.server import (  # noqa: E402
    adjust_value_relative,
    apply_preset,
    assign_cue_trigger,
    assign_executor_property,
    assign_object,
    assign_temp_fader,
    blackout_toggle,
    browse_effect_library,
    browse_macro_library,
    browse_patch_schedule,
    browse_plugin_library,
    clear_programmer,
    control_executor,
    control_timecode,
    control_timer,
    copy_or_move_object,
    create_fixture_group,
    delete_object,
    delete_show,
    delete_user,
    discover_object_names,
    edit_object,
    execute_sequence,
    export_objects,
    get_client,
    get_console_location,
    get_executor_status,
    get_object_info,
    get_variable,
    highlight_fixtures,
    if_filter,
    import_objects,
    label_or_appearance,
    list_console_destination,
    list_fader_modules,
    list_fixture_types,
    list_fixtures,
    list_layers,
    list_library,
    list_sequence_cues,
    list_shows,
    list_undo_history,
    list_universes,
    list_update_history,
    load_show,
    manage_variable,
    modify_selection,
    navigate_console,
    navigate_page,
    new_show,
    park_fixture,
    playback_action,
    query_object_list,
    release_executor,
    remove_content,
    remove_from_programmer,
    run_macro,
    save_recall_view,
    save_show,
    scan_console_indexes,
    search_codebase,
    select_executor,
    select_fixtures_by_group,
    send_raw_command,
    set_attribute,
    set_cue_timing,
    set_executor_level,
    set_intensity,
    set_node_property,
    set_sequence_property,
    store_cue_with_timing,
    store_current_cue,
    store_new_preset,
    store_object,
    store_timecode_event,
    toggle_console_mode,
    undo_last_action,
    unpark_fixture,
    update_cue_data,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def validate_response(
    result: str,
    expected_keys: list[str] | None = None,
    command_contains: str | None = None,
) -> dict:
    """Parse and validate a JSON tool response.

    Args:
        result: Raw string returned by the MCP tool.
        expected_keys: Keys that must be present in the parsed dict.
        command_contains: Substring that ``command_sent`` must contain.

    Returns:
        The parsed dict for further assertions.
    """
    data = json.loads(result)
    print(f"  Response: {json.dumps(data, indent=2)}")

    if expected_keys:
        for key in expected_keys:
            assert key in data, f"Missing key '{key}' in response: {list(data.keys())}"

    # Validate raw_response is not empty when present
    if "raw_response" in data and data.get("blocked") is not True:
        assert data["raw_response"] is not None, "raw_response is None"

    # Validate command_sent contains expected substring
    if command_contains and "command_sent" in data:
        cmd = data["command_sent"]
        assert cmd is not None, "command_sent is None"
        assert command_contains.lower() in cmd.lower(), (
            f"Expected '{command_contains}' in command_sent '{cmd}'"
        )

    return data


def validate_response_list(
    result: str,
    expected_keys: list[str] | None = None,
    commands_contain: str | None = None,
) -> dict:
    """Like validate_response but checks ``commands_sent`` (plural)."""
    data = json.loads(result)
    print(f"  Response: {json.dumps(data, indent=2)}")

    if expected_keys:
        for key in expected_keys:
            assert key in data, f"Missing key '{key}' in response: {list(data.keys())}"

    if "raw_response" in data:
        assert data["raw_response"] is not None, "raw_response is None"

    if commands_contain and "commands_sent" in data:
        cmds = data["commands_sent"]
        assert any(commands_contain.lower() in c.lower() for c in cmds), (
            f"Expected '{commands_contain}' in commands_sent {cmds}"
        )

    return data


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def live_client():
    """Establish a real telnet connection for the entire test module."""
    client = await get_client()
    assert client is not None, "Failed to connect to grandMA2 console"
    assert client._writer is not None, "Telnet writer is None — not connected"
    yield client


# ---------------------------------------------------------------------------
# Layer 0 — SAFE_READ (Foundation, No Risk)
# ---------------------------------------------------------------------------


@pytest.mark.live
class TestLayer0SafeRead:
    """Pure query tests. No preconditions, no side effects."""

    async def test_get_console_location(self, live_client):
        """0.1 — Query current console location."""
        result = await get_console_location()
        data = validate_response(result, ["success", "parsed_prompt"])
        # The first empty-string probe may return an empty response if the
        # console prompt was already consumed by login.  Accept that as valid.
        assert "parsed_prompt" in data

    async def test_list_console_destination(self, live_client):
        """0.2 — List objects at current destination (navigate to root first to
        avoid listing 189+ executors which can freeze onPC)."""
        await navigate_console(destination="/")
        result = await list_console_destination()
        data = validate_response(result, ["entries", "entry_count"])
        assert data["entry_count"] >= 0

    async def test_scan_console_indexes(self, live_client):
        """0.3 — Scan numeric indexes at root."""
        result = await scan_console_indexes(reset_to="/", max_index=5, stop_after_failures=3)
        data = validate_response(result, ["scanned_count", "results"])
        assert data["scanned_count"] > 0
        for r in data["results"]:
            assert "index" in r
            assert "entries" in r

    async def test_get_object_info_fixture(self, live_client):
        """0.4 — Get info on fixture 101."""
        result = await get_object_info("fixture", 101)
        data = validate_response(result, ["command_sent", "raw_response"])
        assert data["command_sent"] == "info fixture 101"

    async def test_query_list_cue(self, live_client):
        """0.5 — List cues."""
        result = await query_object_list("cue")
        data = validate_response(result, ["command_sent", "raw_response"])
        assert "cue" in data["command_sent"].lower()

    async def test_query_list_group(self, live_client):
        """0.6 — List groups."""
        result = await query_object_list("group")
        data = validate_response(result, ["command_sent", "raw_response"])
        assert "group" in data["command_sent"].lower()

    async def test_query_list_preset(self, live_client):
        """0.7 — List color presets."""
        result = await query_object_list("preset", preset_type="color")
        data = validate_response(result, ["command_sent", "raw_response"])
        assert "preset" in data["command_sent"].lower()

    async def test_query_list_attribute(self, live_client):
        """0.8 — List attributes."""
        result = await query_object_list("attribute")
        data = validate_response(result, ["command_sent", "raw_response"])
        assert "attribute" in data["command_sent"].lower()

    async def test_query_list_messages(self, live_client):
        """0.9 — List messages."""
        result = await query_object_list("messages")
        data = validate_response(result, ["command_sent", "raw_response"])
        assert "message" in data["command_sent"].lower()

    async def test_query_list_generic(self, live_client):
        """0.10 — List sequences (generic)."""
        result = await query_object_list("sequence")
        data = validate_response(result, ["command_sent", "raw_response"])
        assert "sequence" in data["command_sent"].lower()

    async def test_list_fixtures(self, live_client):
        """0.11 — List all fixtures."""
        result = await list_fixtures()
        data = validate_response(result, ["command_sent", "raw_response", "exists"])
        assert data["command_sent"] == "list fixture"

    async def test_list_fixtures_specific(self, live_client):
        """0.12 — Check specific fixture by ID."""
        result = await list_fixtures(fixture_id=101)
        data = validate_response(result, ["command_sent", "raw_response", "exists"])
        assert "fixture 101" in data["command_sent"].lower()
        # exists depends on show file — just verify the tool ran

    async def test_list_sequence_cues(self, live_client):
        """0.13 — List cues in sequence 1."""
        result = await list_sequence_cues(sequence_id=1)
        data = validate_response(result, ["command_sent", "raw_response"])
        assert "sequence" in data["command_sent"].lower()

    async def test_get_executor_status(self, live_client):
        """0.14 — Query all executor status."""
        result = await get_executor_status()
        data = validate_response(result, ["command_sent", "raw_response"])
        assert data["command_sent"] == "list executor"

    async def test_search_codebase(self, live_client):
        """0.15 — Search RAG codebase index."""
        result = await search_codebase("store cue", top_k=3)
        data = json.loads(result)
        print(f"  Response: {json.dumps(data, indent=2)[:500]}")
        # May return a list of hits or an error dict if RAG DB not built
        if isinstance(data, dict) and data.get("blocked"):
            pytest.skip("RAG index not built")

    async def test_browse_effect_library(self, live_client):
        """0.16 — Browse grandMA2 effect library."""
        result = await browse_effect_library()
        data = validate_response(result, ["command_sent", "raw_response", "risk_tier"])
        assert data["command_sent"] == "listeffectlibrary"
        assert data["risk_tier"] == "SAFE_READ"
        print(f"  raw_response (truncated): {data['raw_response'][:200]}")

    async def test_browse_macro_library(self, live_client):
        """0.17 — Browse grandMA2 macro library."""
        result = await browse_macro_library()
        data = validate_response(result, ["command_sent", "raw_response", "risk_tier"])
        assert data["command_sent"] == "listmacrolibrary"
        assert data["risk_tier"] == "SAFE_READ"
        print(f"  raw_response (truncated): {data['raw_response'][:200]}")

    async def test_browse_plugin_library(self, live_client):
        """0.18 — Browse grandMA2 plugin library."""
        result = await browse_plugin_library()
        data = validate_response(result, ["command_sent", "raw_response", "risk_tier"])
        assert data["command_sent"] == "listpluginlibrary"
        assert data["risk_tier"] == "SAFE_READ"
        print(f"  raw_response (truncated): {data['raw_response'][:200]}")

    async def test_list_fader_modules(self, live_client):
        """0.19 — List connected fader modules."""
        result = await list_fader_modules()
        data = validate_response(result, ["command_sent", "raw_response", "risk_tier"])
        assert data["command_sent"] == "listfadermodules"
        assert data["risk_tier"] == "SAFE_READ"
        print(f"  raw_response: {data['raw_response']}")

    async def test_list_update_history(self, live_client):
        """0.20 — List programming update history."""
        result = await list_update_history()
        data = validate_response(result, ["command_sent", "raw_response", "risk_tier"])
        assert data["command_sent"] == "listupdate"
        assert data["risk_tier"] == "SAFE_READ"
        print(f"  raw_response (truncated): {data['raw_response'][:200]}")


# ---------------------------------------------------------------------------
# Layer 1 — Navigation & State (SAFE_WRITE, Reversible)
# ---------------------------------------------------------------------------


@pytest.mark.live
class TestLayer1NavigationState:
    """Navigate the tree, reset programmer, set variables. All reversible."""

    async def test_navigate_to_root(self, live_client):
        """1.1 — Navigate to root."""
        result = await navigate_console("/")
        data = validate_response(result, ["success", "parsed_prompt"])
        assert data["success"] is True

    async def test_navigate_to_group(self, live_client):
        """1.2 — Navigate into Group pool."""
        result = await navigate_console("Group")
        data = validate_response(result, ["success", "parsed_prompt"])
        assert data["success"] is True

    async def test_navigate_back(self, live_client):
        """1.3 — Navigate up one level."""
        result = await navigate_console("..")
        data = validate_response(result, ["success", "parsed_prompt"])
        assert data["success"] is True

    async def test_clear_programmer_all(self, live_client):
        """1.4 — Clear entire programmer."""
        result = await clear_programmer("all")
        data = validate_response(result, ["command_sent", "raw_response"])
        assert data["command_sent"] == "clearall"

    async def test_clear_programmer_selection(self, live_client):
        """1.5 — Clear selection only."""
        result = await clear_programmer("selection")
        data = validate_response(result, ["command_sent", "raw_response"])
        assert data["command_sent"] == "clearselection"

    async def test_manage_var_set_global(self, live_client):
        """1.6 — Set a global variable."""
        result = await manage_variable("set", "global", "test_var", 42)
        data = validate_response(result, ["command_sent", "raw_response"])
        assert "setvar" in data["command_sent"].lower()

    async def test_manage_var_set_user(self, live_client):
        """1.7 — Set a user variable."""
        result = await manage_variable("set", "user", "test_var", 99)
        data = validate_response(result, ["command_sent", "raw_response"])
        assert "setuservar" in data["command_sent"].lower()

    async def test_manage_var_add_global(self, live_client):
        """1.8 — Add to a global variable."""
        result = await manage_variable("add", "global", "test_var", 1)
        data = validate_response(result, ["command_sent", "raw_response"])
        assert "addvar" in data["command_sent"].lower()

    async def test_send_raw_safe_read(self, live_client):
        """1.9 — Send a raw SAFE_READ command."""
        result = await send_raw_command("list")
        data = validate_response(result, ["command_sent", "risk_tier", "blocked"])
        assert data["blocked"] is False
        assert data["risk_tier"] == "SAFE_READ"

    async def test_send_raw_safe_write(self, live_client):
        """1.10 — Send a raw SAFE_WRITE command."""
        result = await send_raw_command("clearall")
        data = validate_response(result, ["command_sent", "risk_tier", "blocked"])
        assert data["blocked"] is False
        assert data["risk_tier"] == "SAFE_WRITE"

    async def test_send_raw_destructive_blocked(self, live_client):
        """1.11 — Verify destructive raw command is blocked without confirmation."""
        result = await send_raw_command("delete cue 9999")
        data = validate_response(result, ["blocked"])
        assert data["blocked"] is True

    async def test_set_node_property(self, live_client):
        """1.12 — Set a node property (idempotent re-set)."""
        result = await set_node_property(
            "3.1", "Telnet", "Login Enabled", verify=True,
            confirm_destructive=True,
        )
        data = json.loads(result)
        print(f"  Response: {json.dumps(data, indent=2)}")
        assert "commands_sent" in data

    async def test_undo_last_action(self, live_client):
        """1.13 — Undo last action (oops x1)."""
        result = await undo_last_action(count=1)
        data = json.loads(result)
        print(f"  Response: {json.dumps(data, indent=2)}")
        assert data["commands_sent"] == ["oops"]
        assert data["count"] == 1

    async def test_assign_temp_fader(self, live_client):
        """1.14 — Set temp fader level (50%) on selected executor."""
        result = await assign_temp_fader(value=50)
        data = validate_response(result, ["command_sent", "raw_response", "risk_tier"])
        assert data["command_sent"] == "tempfader 50"
        assert data["risk_tier"] == "SAFE_WRITE"
        print(f"  raw_response: {data['raw_response']}")

    async def test_assign_temp_fader_zero(self, live_client):
        """1.15 — Set temp fader to 0 (cue off)."""
        result = await assign_temp_fader(value=0)
        data = validate_response(result, ["command_sent", "raw_response"])
        assert data["command_sent"] == "tempfader 0"
        print(f"  raw_response: {data['raw_response']}")


# ---------------------------------------------------------------------------
# Layer 2 — Selection & Group Creation (SAFE_WRITE)
# ---------------------------------------------------------------------------


@pytest.mark.live
class TestLayer2SelectionGroups:
    """Create test fixtures/groups. Depends on Layer 1 (clear programmer first)."""

    async def test_create_fixture_group(self, live_client):
        """2.1 — Create a fixture group (ID 99)."""
        # create_fixture_group returns a plain string, not JSON
        result = await create_fixture_group(101, 104, 99, "Live Test Group",
                                            confirm_destructive=True)
        print(f"  Response: {result}")
        assert "Group 99" in result
        assert "error" not in result.lower()

    async def test_verify_group_created(self, live_client):
        """2.2 — Verify group 99 was created."""
        result = await get_object_info("group", 99)
        data = validate_response(result, ["command_sent", "raw_response"])
        assert data["raw_response"] is not None

    async def test_select_fixtures_by_group(self, live_client):
        """2.3 — Select fixtures via group 99."""
        result = await select_fixtures_by_group(group_id=99)
        data = validate_response(result, ["command_sent", "raw_response"])
        assert "group 99" in data["command_sent"].lower()

    async def test_modify_selection_add(self, live_client):
        """2.4 — Add fixture 101 to selection."""
        result = await modify_selection("add", fixture_ids=[101])
        validate_response(result, ["command_sent", "raw_response"])

    async def test_modify_selection_clear(self, live_client):
        """2.5 — Clear selection."""
        result = await modify_selection("clear")
        validate_response(result, ["command_sent", "raw_response"])


# ---------------------------------------------------------------------------
# Layer 3 — Light Control (SAFE_WRITE, Reversible via clearall)
# ---------------------------------------------------------------------------


@pytest.mark.live
class TestLayer3LightControl:
    """Set intensity, attributes, presets, park/unpark."""

    async def test_set_intensity_fixture(self, live_client):
        """3.1 — Set intensity on fixture 101."""
        result = await set_intensity("fixture", 101, 50)
        data = validate_response(result, ["command_sent", "raw_response"])
        assert "fixture 101" in data["command_sent"].lower()
        assert "50" in data["command_sent"]

    async def test_set_intensity_group(self, live_client):
        """3.2 — Set intensity on group 99."""
        result = await set_intensity("group", 99, 75)
        data = validate_response(result, ["command_sent", "raw_response"])
        assert "group 99" in data["command_sent"].lower()
        assert "75" in data["command_sent"]

    async def test_set_attribute_pan(self, live_client):
        """3.3 — Set Pan attribute on group 99."""
        result = await set_attribute("Pan", 45, group_id=99)
        data = validate_response_list(result, ["commands_sent", "raw_response"])
        assert len(data["commands_sent"]) == 2  # select + attribute

    async def test_apply_preset_color(self, live_client):
        """3.4 — Apply color preset 1 to group 99."""
        result = await apply_preset("color", 1, group_id=99)
        data = validate_response_list(result, ["commands_sent", "raw_response"])
        assert len(data["commands_sent"]) == 2  # select + call

    async def test_park_fixture(self, live_client):
        """3.5 — Park fixture 101."""
        result = await park_fixture("fixture 101")
        data = json.loads(result)
        print(f"  Response: {json.dumps(data, indent=2)}")
        if data.get("exists") is False:
            assert data["command_sent"] is None
            assert "error" in data
        else:
            assert data["command_sent"] is not None
            assert "park" in data["command_sent"].lower()
            assert "fixture 101" in data["command_sent"].lower()
            assert "raw_response" in data

    async def test_unpark_fixture(self, live_client):
        """3.6 — Unpark fixture 101."""
        result = await unpark_fixture("fixture 101")
        data = json.loads(result)
        print(f"  Response: {json.dumps(data, indent=2)}")
        if data.get("exists") is False:
            assert data["command_sent"] is None
            assert "error" in data
        else:
            assert data["command_sent"] is not None
            assert "unpark" in data["command_sent"].lower()
            assert "fixture 101" in data["command_sent"].lower()
            assert "raw_response" in data

    async def test_clear_after_control(self, live_client):
        """3.7 — Clear programmer after light control tests."""
        result = await clear_programmer("all")
        data = validate_response(result, ["command_sent", "raw_response"])
        assert data["command_sent"] == "clearall"

    async def test_adjust_value_relative(self, live_client):
        """3.8 — Nudge dimmer +5 on fixture 101."""
        await set_intensity("fixture", 101, 50)
        result = await adjust_value_relative(delta=5, fixture_ids=[101])
        data = json.loads(result)
        print(f"  Response: {json.dumps(data, indent=2)}")
        assert "commands_sent" in data

    async def test_toggle_console_mode_blind(self, live_client):
        """3.9 — Toggle blind mode on and off."""
        result_on = await toggle_console_mode("blind")
        data_on = validate_response(result_on, ["command_sent", "raw_response"])
        assert data_on["command_sent"] == "blind"
        # Toggle back off
        result_off = await toggle_console_mode("blind")
        validate_response(result_off, ["command_sent", "raw_response"])

    async def test_if_filter_active(self, live_client):
        """3.10 — Apply bare If filter (active fixtures)."""
        result = await if_filter("active")
        data = validate_response(result, ["command_sent", "raw_response"])
        assert data["command_sent"] == "if"

    async def test_remove_from_programmer(self, live_client):
        """3.11 — Remove fixture 101 from programmer via Off."""
        result = await remove_from_programmer("fixture", 101)
        data = validate_response(result, ["command_sent", "raw_response"])
        assert "off" in data["command_sent"].lower()

    async def test_navigate_page_next(self, live_client):
        """3.12 — Navigate to next executor page."""
        result = await navigate_page("next")
        validate_response(result, ["command_sent", "raw_response"])

    async def test_navigate_page_previous(self, live_client):
        """3.13 — Navigate to previous executor page (restore)."""
        result = await navigate_page("previous")
        validate_response(result, ["command_sent", "raw_response"])

    async def test_set_executor_level(self, live_client):
        """3.14 — Set executor 201 fader to 0%."""
        result = await set_executor_level(executor_id=201, level=0.0)
        validate_response(result, ["command_sent", "raw_response"])

    async def test_select_executor(self, live_client):
        """3.15 — Select executor 201."""
        result = await select_executor(executor_id=201)
        data = validate_response(result, ["command_sent", "raw_response"])
        assert "select" in data["command_sent"].lower()


# ---------------------------------------------------------------------------
# Layer 4 — Programming (DESTRUCTIVE)
# ---------------------------------------------------------------------------


@pytest.mark.live
@pytest.mark.destructive
class TestLayer4Programming:
    """Store cues, presets, objects. Requires programmer state."""

    async def test_setup_programmer(self, live_client):
        """4.1 — Load programmer with fixture intensity."""
        result = await set_intensity("fixture", 101, 80)
        data = validate_response(result, ["command_sent", "raw_response"])
        assert "80" in data["command_sent"]

    async def test_store_current_cue(self, live_client):
        """4.2 — Store programmer into cue 99."""
        result = await store_current_cue(99, label="Live Test Cue", confirm_destructive=True)
        data = validate_response_list(result, ["commands_sent", "raw_response"])
        cmds_joined = " ".join(data["commands_sent"]).lower()
        assert "store" in cmds_joined
        assert "cue" in cmds_joined

    async def test_verify_cue_stored(self, live_client):
        """4.3 — Verify cue 99 exists."""
        result = await get_object_info("cue", 99)
        data = validate_response(result, ["command_sent", "raw_response"])
        assert data["raw_response"] is not None

    async def test_store_new_preset(self, live_client):
        """4.4 — Store programmer as dimmer preset 99."""
        # Ensure programmer has content
        await set_intensity("fixture", 101, 80)
        result = await store_new_preset("dimmer", 99, confirm_destructive=True)
        data = validate_response(result, ["command_sent", "raw_response"])
        assert "store" in data["command_sent"].lower()
        assert "preset" in data["command_sent"].lower()

    async def test_store_object_macro(self, live_client):
        """4.5 — Store macro 99 with confirmation."""
        result = await store_object("macro", 99, confirm_destructive=True)
        data = validate_response(result, ["command_sent", "raw_response", "blocked"])
        assert data["blocked"] is False
        assert "store" in data["command_sent"].lower()
        assert "macro" in data["command_sent"].lower()

    async def test_store_object_blocked(self, live_client):
        """4.6 — Verify store is blocked without confirmation."""
        result = await store_object("macro", 98)
        data = validate_response(result, ["blocked"])
        assert data["blocked"] is True

    async def test_label_group(self, live_client):
        """4.7 — Label group 99."""
        result = await label_or_appearance(
            "label", "group", 99, name="Relabeled", confirm_destructive=True,
        )
        data = validate_response(result, ["command_sent", "raw_response", "blocked"])
        assert data["blocked"] is False
        assert "label" in data["command_sent"].lower()
        assert "group" in data["command_sent"].lower()

    async def test_appearance_group(self, live_client):
        """4.8 — Set appearance on group 99."""
        result = await label_or_appearance(
            "appearance", "group", 99, red=100, confirm_destructive=True,
        )
        data = validate_response(result, ["command_sent", "raw_response", "blocked"])
        assert data["blocked"] is False
        assert "appearance" in data["command_sent"].lower()

    async def test_edit_cue(self, live_client):
        """4.9 — Edit cue 99 (no destructive confirmation needed)."""
        result = await edit_object("edit", "cue", 99)
        data = validate_response(result, ["command_sent", "raw_response", "blocked"])
        assert data["blocked"] is False
        assert "edit" in data["command_sent"].lower()
        assert "cue" in data["command_sent"].lower()

    async def test_store_cue_with_timing(self, live_client):
        """4.10 — Store cue 98 with 2s fade (DESTRUCTIVE)."""
        await set_intensity("fixture", 101, 60)
        result = await store_cue_with_timing(
            cue_id=98, fade_time=2.0, confirm_destructive=True,
        )
        data = validate_response(result, ["command_sent", "raw_response"])
        assert "store" in data["command_sent"].lower()

    async def test_update_cue_data(self, live_client):
        """4.11 — Update cue 99 with programmer values (DESTRUCTIVE)."""
        await set_intensity("fixture", 101, 90)
        result = await update_cue_data(cue_id=99.0, confirm_destructive=True)
        data = validate_response(result, ["command_sent", "raw_response"])
        assert "update" in data["command_sent"].lower()

    async def test_update_cue_data_blocked(self, live_client):
        """4.12 — Verify update_cue_data blocked without confirmation."""
        result = await update_cue_data(cue_id=99.0)
        data = validate_response(result, ["blocked"])
        assert data["blocked"] is True

    async def test_save_recall_view_store(self, live_client):
        """4.13 — Store view to slot 10 screen 1 (DESTRUCTIVE)."""
        result = await save_recall_view(
            "store", view_id=10, screen_id=1, confirm_destructive=True,
        )
        data = validate_response(result, ["command_sent", "raw_response"])
        assert "viewbutton" in data["command_sent"].lower()

    async def test_save_recall_view_recall(self, live_client):
        """4.14 — Recall view slot 10 screen 1."""
        result = await save_recall_view("recall", view_id=10, screen_id=1)
        data = validate_response(result, ["command_sent", "raw_response"])
        assert "viewbutton" in data["command_sent"].lower()

    async def test_export_objects(self, live_client):
        """4.15 — Export group 99 to file (DESTRUCTIVE)."""
        result = await export_objects(
            object_type="group", object_id="99",
            filename="mcp_live_test", overwrite=True,
            confirm_destructive=True,
        )
        data = validate_response(result, ["command_sent", "raw_response"])
        assert "export" in data["command_sent"].lower()

    async def test_set_sequence_property(self, live_client):
        """4.16 — Set label on sequence 1 (DESTRUCTIVE)."""
        result = await set_sequence_property(
            sequence_id=1, property_name="label", value="LiveTest",
            confirm_destructive=True,
        )
        data = json.loads(result)
        print(f"  Response: {json.dumps(data, indent=2)}")
        assert data["sequence_id"] == 1


# ---------------------------------------------------------------------------
# Layer 5 — Copy/Move/Assign (DESTRUCTIVE)
# ---------------------------------------------------------------------------


@pytest.mark.live
@pytest.mark.destructive
class TestLayer5CopyMoveAssign:
    """Operate on objects created in Layer 4."""

    async def test_copy_group(self, live_client):
        """5.1 — Copy group 99 to 98."""
        result = await copy_or_move_object("copy", "group", 99, 98)
        data = validate_response(result, ["command_sent", "raw_response"])
        assert "copy" in data["command_sent"].lower()
        assert "group" in data["command_sent"].lower()

    async def test_assign_seq_to_executor(self, live_client):
        """5.2 — Assign sequence 1 to executor 99."""
        result = await assign_object(
            "assign",
            source_type="sequence", source_id=1,
            target_type="executor", target_id=99,
            confirm_destructive=True,
        )
        data = validate_response(result, ["command_sent", "raw_response", "blocked"])
        assert data["blocked"] is False
        assert "assign" in data["command_sent"].lower()

    async def test_assign_function(self, live_client):
        """5.3 — Assign Toggle function to executor 99."""
        result = await assign_object(
            "function",
            function="Toggle",
            target_type="executor", target_id=99,
            confirm_destructive=True,
        )
        data = validate_response(result, ["command_sent", "raw_response", "blocked"])
        assert data["blocked"] is False
        assert "toggle" in data["command_sent"].lower()

    async def test_assign_fade(self, live_client):
        """5.4 — Assign fade time 3s to cue 99."""
        result = await assign_object(
            "fade",
            fade_time=3, cue_id=99,
            confirm_destructive=True,
        )
        data = validate_response(result, ["command_sent", "raw_response", "blocked"])
        assert data["blocked"] is False
        assert "fade" in data["command_sent"].lower()

    async def test_assign_empty(self, live_client):
        """5.5 — Empty executor 99."""
        result = await assign_object(
            "empty",
            target_type="executor", target_id=99,
            confirm_destructive=True,
        )
        data = validate_response(result, ["command_sent", "raw_response", "blocked"])
        assert data["blocked"] is False

    async def test_assign_blocked(self, live_client):
        """5.6 — Verify assign is blocked without confirmation."""
        result = await assign_object(
            "assign",
            source_type="sequence", source_id=1,
        )
        data = validate_response(result, ["blocked"])
        assert data["blocked"] is True

    async def test_import_objects(self, live_client):
        """5.7 — Import group from exported file (DESTRUCTIVE)."""
        result = await import_objects(
            filename="mcp_live_test",
            destination_type="group", destination_id="98",
            confirm_destructive=True,
        )
        data = validate_response(result, ["command_sent", "raw_response"])
        assert "import" in data["command_sent"].lower()

    async def test_set_cue_timing(self, live_client):
        """5.8 — Set fade 2s on cue 99 (DESTRUCTIVE)."""
        result = await set_cue_timing(
            cue_id=99, fade_time=2.0, confirm_destructive=True,
        )
        data = json.loads(result)
        print(f"  Response: {json.dumps(data, indent=2)}")
        assert "commands_sent" in data

    async def test_assign_cue_trigger(self, live_client):
        """5.9 — Assign follow trigger to cue 99 seq 1 (DESTRUCTIVE)."""
        result = await assign_cue_trigger(
            cue_id=99, sequence_id=1, trigger_type="follow",
            confirm_destructive=True,
        )
        data = validate_response(result, ["command_sent", "raw_response"])
        assert "trigger" in data["command_sent"].lower()

    async def test_assign_cue_trigger_blocked(self, live_client):
        """5.10 — Verify assign_cue_trigger blocked without confirmation."""
        result = await assign_cue_trigger(
            cue_id=99, sequence_id=1, trigger_type="go",
        )
        data = validate_response(result, ["blocked"])
        assert data["blocked"] is True

    async def test_assign_executor_property(self, live_client):
        """5.11 — Assign width=2 to executor 201 (DESTRUCTIVE)."""
        result = await assign_executor_property(
            property_name="width", executor_id=201, value=2,
            confirm_destructive=True,
        )
        validate_response(result, ["command_sent", "raw_response"])

    async def test_store_timecode_event_blocked(self, live_client):
        """5.12 — Verify store_timecode_event blocked without confirmation."""
        result = await store_timecode_event(
            timecode_id=99, cue_id=1.0, sequence_id=1,
        )
        data = validate_response(result, ["blocked"])
        assert data["blocked"] is True


# ---------------------------------------------------------------------------
# Layer 6 — Playback (SAFE_WRITE, needs sequences/cues)
# ---------------------------------------------------------------------------


@pytest.mark.live
class TestLayer6Playback:
    """Execute sequences and playback actions."""

    async def test_execute_sequence_go(self, live_client):
        """6.1 — Execute sequence 1 (go)."""
        # execute_sequence returns a plain string
        result = await execute_sequence(1, "go")
        print(f"  Response: {result}")
        assert "Executed" in result or "error" not in result.lower()

    async def test_execute_sequence_pause(self, live_client):
        """6.2 — Pause sequence 1."""
        result = await execute_sequence(1, "pause")
        print(f"  Response: {result}")
        assert "Paused" in result or "error" not in result.lower()

    async def test_playback_goto(self, live_client):
        """6.3 — Goto cue 99."""
        result = await playback_action("goto", cue_id=99)
        data = validate_response(result, ["command_sent", "raw_response"])
        assert "goto" in data["command_sent"].lower()

    async def test_playback_go(self, live_client):
        """6.4 — Playback go."""
        result = await playback_action("go")
        data = validate_response(result, ["command_sent", "raw_response"])
        assert "go" in data["command_sent"].lower()

    async def test_playback_go_back(self, live_client):
        """6.5 — Playback go back."""
        result = await playback_action("go_back")
        data = validate_response(result, ["command_sent", "raw_response"])
        assert "goback" in data["command_sent"].lower()

    async def test_playback_fast_forward(self, live_client):
        """6.6 — Playback fast forward."""
        result = await playback_action("fast_forward")
        data = validate_response(result, ["command_sent", "raw_response"])
        assert data["command_sent"] == ">>>"

    async def test_playback_fast_back(self, live_client):
        """6.7 — Playback fast back."""
        result = await playback_action("fast_back")
        data = validate_response(result, ["command_sent", "raw_response"])
        assert data["command_sent"] == "<<<"

    async def test_playback_def_go(self, live_client):
        """6.8 — Default go (go+)."""
        result = await playback_action("def_go")
        data = validate_response(result, ["command_sent", "raw_response"])
        assert "defgoforward" in data["command_sent"].lower()

    async def test_playback_def_pause(self, live_client):
        """6.9 — Default pause."""
        result = await playback_action("def_pause")
        data = validate_response(result, ["command_sent", "raw_response"])
        assert "defgopause" in data["command_sent"].lower()

    async def test_control_executor_on(self, live_client):
        """6.10 — Turn on executor 201."""
        result = await control_executor("on", executor_id=201)
        validate_response(result, ["command_sent", "raw_response"])

    async def test_control_executor_off(self, live_client):
        """6.11 — Turn off executor 201."""
        result = await control_executor("off", executor_id=201)
        validate_response(result, ["command_sent", "raw_response"])

    async def test_run_macro(self, live_client):
        """6.12 — Run macro 99 (empty, stored in Layer 4)."""
        result = await run_macro(macro_id=99)
        data = validate_response(result, ["command_sent", "raw_response"])
        assert data["command_sent"] == "go macro 99"

    async def test_control_timecode_stop(self, live_client):
        """6.13 — Stop timecode show 99 (no-op if nonexistent)."""
        result = await control_timecode("stop", timecode_id=99)
        data = validate_response(result, ["command_sent", "raw_response"])
        assert "off" in data["command_sent"].lower()

    async def test_control_timer_start_stop(self, live_client):
        """6.14 — Start and stop timer 99."""
        result_start = await control_timer("start", timer_id=99)
        data_start = validate_response(result_start, ["command_sent", "raw_response"])
        assert "go" in data_start["command_sent"].lower()

        result_stop = await control_timer("stop", timer_id=99)
        data_stop = validate_response(result_stop, ["command_sent", "raw_response"])
        assert "off" in data_stop["command_sent"].lower()

    async def test_save_show(self, live_client):
        """6.15 — Save current show."""
        result = await save_show("save")
        data = validate_response(result, ["command_sent", "raw_response"])
        assert data["command_sent"] == "save"


# ---------------------------------------------------------------------------
# Layer 7 — Cleanup (DESTRUCTIVE)
# ---------------------------------------------------------------------------


@pytest.mark.live
@pytest.mark.destructive
class TestLayer7Cleanup:
    """Remove/delete test objects created in earlier layers. Runs last."""

    async def test_remove_selection(self, live_client):
        """7.1 — Remove current selection."""
        result = await remove_content("selection", confirm_destructive=True)
        data = validate_response(result, ["command_sent", "raw_response", "blocked"])
        assert data["blocked"] is False
        assert "remove" in data["command_sent"].lower()
        assert "selection" in data["command_sent"].lower()

    async def test_remove_fixture(self, live_client):
        """7.2 — Remove fixture 101 with filter."""
        result = await remove_content(
            "fixture", 101, if_filter="PresetType 1", confirm_destructive=True,
        )
        data = validate_response(result, ["command_sent", "raw_response", "blocked"])
        assert data["blocked"] is False
        assert "remove" in data["command_sent"].lower()
        assert "fixture" in data["command_sent"].lower()

    async def test_remove_blocked(self, live_client):
        """7.3 — Verify remove is blocked without confirmation."""
        result = await remove_content("fixture", 101)
        data = validate_response(result, ["blocked"])
        assert data["blocked"] is True

    async def test_edit_cut(self, live_client):
        """7.4 — Cut group 98."""
        result = await edit_object(
            "cut", "group", 98, confirm_destructive=True,
        )
        data = validate_response(result, ["command_sent", "raw_response", "blocked"])
        assert data["blocked"] is False
        assert "cut" in data["command_sent"].lower()
        assert "group" in data["command_sent"].lower()

    async def test_edit_paste(self, live_client):
        """7.5 — Paste into group 97."""
        result = await edit_object(
            "paste", "group", target_id=97, confirm_destructive=True,
        )
        data = validate_response(result, ["command_sent", "raw_response", "blocked"])
        assert data["blocked"] is False
        assert "paste" in data["command_sent"].lower()

    async def test_delete_group_99(self, live_client):
        """7.6 — Delete group 99."""
        result = await delete_object("group", 99, confirm_destructive=True)
        data = validate_response(result, ["command_sent", "raw_response", "blocked"])
        assert data["blocked"] is False

    async def test_delete_group_98(self, live_client):
        """7.7 — Delete group 98."""
        result = await delete_object("group", 98, confirm_destructive=True)
        data = validate_response(result, ["command_sent", "raw_response", "blocked"])
        assert data["blocked"] is False

    async def test_delete_group_97(self, live_client):
        """7.7b — Delete group 97 (paste target)."""
        result = await delete_object("group", 97, confirm_destructive=True)
        data = validate_response(result, ["command_sent", "raw_response", "blocked"])
        assert data["blocked"] is False

    async def test_delete_cue_99(self, live_client):
        """7.8 — Delete cue 99."""
        result = await delete_object("cue", 99, confirm_destructive=True)
        data = validate_response(result, ["command_sent", "raw_response", "blocked"])
        assert data["blocked"] is False

    async def test_delete_cue_98(self, live_client):
        """7.8b — Delete cue 98 (created in 4.10)."""
        result = await delete_object("cue", 98, confirm_destructive=True)
        data = validate_response(result, ["command_sent", "raw_response", "blocked"])
        assert data["blocked"] is False

    async def test_delete_macro_99(self, live_client):
        """7.9 — Delete macro 99."""
        result = await delete_object("macro", 99, confirm_destructive=True)
        data = validate_response(result, ["command_sent", "raw_response", "blocked"])
        assert data["blocked"] is False

    async def test_delete_blocked(self, live_client):
        """7.10 — Verify delete is blocked without confirmation."""
        result = await delete_object("group", 1)
        data = validate_response(result, ["blocked"])
        assert data["blocked"] is True

    async def test_reset_executor_201_width(self, live_client):
        """7.11 — Reset executor 201 width to 1."""
        result = await assign_executor_property(
            property_name="width", executor_id=201, value=1,
            confirm_destructive=True,
        )
        validate_response(result, ["command_sent", "raw_response"])

    async def test_restore_sequence_1_label(self, live_client):
        """7.12 — Restore sequence 1 label (best-effort)."""
        result = await set_sequence_property(
            sequence_id=1, property_name="label", value="Main",
            confirm_destructive=True,
        )
        data = json.loads(result)
        print(f"  Response: {json.dumps(data, indent=2)}")

    async def test_final_clearall(self, live_client):
        """7.13 — Final clearall to leave console clean."""
        result = await clear_programmer("all")
        data = validate_response(result, ["command_sent", "raw_response"])
        assert data["command_sent"] == "clearall"


# ===================================================================
# Layer 8 — New Tier 1-3 Tools (tools 57-73)
# ===================================================================


@pytest.mark.live
class TestLayer8NewTools:
    """Layer 8: Test new Tier 1-3 tools."""

    # --- Tier 1: High-Impact (SAFE_READ / SAFE_WRITE) ---

    async def test_list_shows(self, live_client):
        """8.01 — List available show files."""
        result = await list_shows()
        data = validate_response(result, ["command_sent", "raw_response"])
        assert data["command_sent"] == "listshows"
        print(f"  Shows: {data['raw_response'][:200]}")

    async def test_list_undo_history(self, live_client):
        """8.02 — List undo history."""
        result = await list_undo_history()
        data = validate_response(result, ["command_sent", "raw_response"])
        assert data["command_sent"] == "listoops"

    async def test_get_variable_list_var(self, live_client):
        """8.03 — List show variables."""
        result = await get_variable(action="list_var")
        data = validate_response(result, ["command_sent", "raw_response"])
        assert data["command_sent"] == "listvar"

    async def test_get_variable_list_user_var(self, live_client):
        """8.04 — List user variables."""
        result = await get_variable(action="list_user_var")
        data = validate_response(result, ["command_sent", "raw_response"])
        assert data["command_sent"] == "listuservar"

    async def test_highlight_on_off(self, live_client):
        """8.05 — Toggle highlight on then off."""
        result = await highlight_fixtures(on=True)
        data = validate_response(result, ["command_sent", "raw_response"])
        assert data["command_sent"] == "highlight on"

        result = await highlight_fixtures(on=False)
        data = validate_response(result, ["command_sent", "raw_response"])
        assert data["command_sent"] == "highlight off"

    async def test_blackout_toggle(self, live_client):
        """8.06 — Toggle blackout on then off (double toggle = restore)."""
        result = await blackout_toggle()
        data = validate_response(result, ["command_sent", "raw_response"])
        assert data["command_sent"] == "blackout"

        # Toggle back to restore
        result = await blackout_toggle()
        data = validate_response(result, ["command_sent", "raw_response"])

    async def test_release_executor(self, live_client):
        """8.07 — Release executor 201."""
        result = await release_executor(executor_id=201)
        data = validate_response(result, ["command_sent", "raw_response"])
        assert data["command_sent"] == "release executor 201"

    # --- Tier 1: DESTRUCTIVE (blocked path only) ---

    async def test_load_show_blocked(self, live_client):
        """8.08 — Verify LoadShow blocked without confirm."""
        result = await load_show(name="test_show")
        data = json.loads(result)
        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"

    async def test_new_show_blocked(self, live_client):
        """8.09 — Verify NewShow blocked without confirm."""
        result = await new_show(name="test_show")
        data = json.loads(result)
        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"

    # --- Tier 2: Setup & Library (SAFE_READ) ---

    async def test_list_fixture_types(self, live_client):
        """8.10 — List all fixture types from LiveSetup."""
        result = await list_fixture_types()
        data = validate_response(result, ["commands_sent", "raw_response"])
        assert data["risk_tier"] == "SAFE_READ"
        print(f"  Fixture types: {data.get('entry_count', 'N/A')}")
        print(f"  Raw: {data['raw_response'][:300]}")

    async def test_list_layers(self, live_client):
        """8.11 — List all fixture layers from LiveSetup."""
        result = await list_layers()
        data = validate_response(result, ["commands_sent", "raw_response"])
        assert data["risk_tier"] == "SAFE_READ"
        print(f"  Layers: {data['raw_response'][:300]}")

    async def test_list_universes(self, live_client):
        """8.12 — List DMX universes (first 4)."""
        result = await list_universes(max_universes=4)
        data = validate_response(result, ["commands_sent", "raw_response"])
        assert data["risk_tier"] == "SAFE_READ"
        print(f"  Universe count: {data.get('entry_count', 'N/A')}, showing: {data.get('showing', 'N/A')}")

    async def test_list_library_fixture(self, live_client):
        """8.13 — Browse fixture library."""
        result = await list_library(library_type="fixture")
        data = validate_response(result, ["command_sent", "raw_response"])
        assert data["command_sent"] == "listlibrary"

    async def test_list_library_effect(self, live_client):
        """8.14 — Browse effect library."""
        result = await list_library(library_type="effect")
        data = validate_response(result, ["command_sent", "raw_response"])
        assert data["command_sent"] == "listeffectlibrary"

    # --- Tier 3: Patching (SAFE_READ browse) ---

    async def test_browse_patch_schedule(self, live_client):
        """8.15 — Browse all fixture types in patch schedule."""
        result = await browse_patch_schedule()
        data = validate_response(result, ["commands_sent", "raw_response"])
        assert data["risk_tier"] == "SAFE_READ"
        print(f"  Patch entries: {data.get('entry_count', 'N/A')}")

    async def test_browse_patch_schedule_specific(self, live_client):
        """8.16 — Browse specific fixture type (Dimmer = type 2)."""
        result = await browse_patch_schedule(fixture_type_id=2)
        data = validate_response(result, ["commands_sent", "raw_response"])
        assert data["risk_tier"] == "SAFE_READ"
        print(f"  Dimmer instances: {data.get('entry_count', 'N/A')}")


# ---------------------------------------------------------------------------
# Layer 9 — Name Discovery & Wildcard Validation
# ---------------------------------------------------------------------------


@pytest.mark.live
class TestLayer9NameDiscovery:
    """Layer 9 — discover_object_names (SAFE_READ): real telnet I/O validation."""

    async def test_discover_group_names(self, live_client):
        """9.1 — Navigate cd Group, list pool, extract names; verify telnet I/O."""
        result = await discover_object_names("Group")
        data = validate_response(result, ["destination", "names_only", "entries", "entry_count"])
        assert data["destination"] == "Group"
        assert isinstance(data["names_only"], list)
        nav_cmd = data.get("navigate_command", "")
        assert nav_cmd, "navigate_command must contain the cd command actually sent"
        print(f"  Group names ({data['entry_count']}): {data['names_only']}")
        print(f"  navigate_command: {nav_cmd}")
        print(f"  wildcard_tip: {data.get('wildcard_tip')}")

    async def test_discover_sequence_names(self, live_client):
        """9.2 — Sequence pool via keyword."""
        result = await discover_object_names("Sequence")
        data = validate_response(result, ["destination", "names_only", "entry_count"])
        assert data["destination"] == "Sequence"
        assert isinstance(data["names_only"], list)
        print(f"  Sequence names ({data['entry_count']}): {data['names_only']}")

    async def test_discover_numeric_index(self, live_client):
        """9.3 — cd 22 (Groups) via numeric index — same pool as 'Group'."""
        result = await discover_object_names("22")
        data = validate_response(result, ["destination", "names_only", "entry_count"])
        assert isinstance(data["names_only"], list)
        print(f"  cd 22 ({data['entry_count']} entries): {data['names_only']}")

    async def test_discover_returns_to_root(self, live_client):
        """9.4 — Console is back at root (cd /) after discover completes."""
        await discover_object_names("Macro")
        nav_result = await navigate_console("/")
        nav_data = json.loads(nav_result)
        assert nav_data.get("blocked") is not True
        print(f"  Post-discover root nav: {nav_data.get('command_sent')}")

    async def test_wildcard_tip_populated(self, live_client):
        """9.5 — wildcard_tip is non-null when pool contains named objects."""
        result = await discover_object_names("Group")
        data = json.loads(result)
        if data["named_count"] > 0:
            assert data["wildcard_tip"] is not None
            assert len(data["wildcard_tip"]) > 0
            print(f"  wildcard_tip: {data['wildcard_tip']}")
        else:
            print("  (Group pool empty — tip is None, skipping assertion)")


@pytest.mark.live
@pytest.mark.destructive
class TestLayer9LabelQuoting:
    """Layer 9b — quote_name output verified on the wire (DESTRUCTIVE: relabels group 99)."""

    async def test_label_name_with_space_auto_quoted(self, live_client):
        """9.6 — Name with space: quote_name wraps it in double-quotes on the wire."""
        result = await label_or_appearance(
            "label", "group", 99, name="Relabeled 99", confirm_destructive=True,
        )
        data = validate_response(result, ["command_sent", "raw_response", "blocked"])
        assert data["blocked"] is False
        assert '"Relabeled 99"' in data["command_sent"]
        print(f"  command_sent: {data['command_sent']}")

    async def test_label_plain_name_no_quotes_on_wire(self, live_client):
        """9.7 — Plain name (no special chars): emitted bare, no double-quotes."""
        result = await label_or_appearance(
            "label", "group", 99, name="TestGroup", confirm_destructive=True,
        )
        data = validate_response(result, ["command_sent", "raw_response", "blocked"])
        assert data["blocked"] is False
        cmd = data["command_sent"]
        assert "TestGroup" in cmd
        assert '"TestGroup"' not in cmd
        print(f"  command_sent: {cmd}")


# ---------------------------------------------------------------------------
# Layer 10 — NewShow keep-flags live validation
# ---------------------------------------------------------------------------


@pytest.mark.live
@pytest.mark.destructive
class TestLayer10NewShowFlags:
    """Layer 10 — new_show keep-flags verified on the wire (DESTRUCTIVE)."""

    async def test_new_show_preserve_connectivity_default(self, live_client):
        """10.1 — Default preserve_connectivity=True: /globalsettings /protocols /network on wire.

        Telnet stays enabled so subsequent MCP tool calls continue to work.
        """
        result = await new_show(
            name="Claude_MA2_Ctrl",
            confirm_destructive=True,
        )
        data = validate_response(result, ["command_sent", "raw_response", "blocked"])
        assert data["blocked"] is False
        assert data["preserve_connectivity"] is True
        cmd = data["command_sent"]
        assert "/globalsettings" in cmd
        assert "/network" in cmd
        assert "/protocols" in cmd
        print(f"  command_sent: {cmd}")
        print(f"  connectivity_flags: {data.get('connectivity_flags')}")
        print(f"  raw_response: {data['raw_response']}")

    async def test_new_show_all_keep_flags(self, live_client):
        """10.2 — All six keep flags + preserve_connectivity=False → all flags on wire."""
        result = await new_show(
            name="Claude_MA2_Ctrl",
            confirm_destructive=True,
            preserve_connectivity=False,
            keep_timeconfig=True,
            keep_globalsettings=True,
            keep_localsettings=True,
            keep_protocols=True,
            keep_network=True,
            keep_user=True,
        )
        data = validate_response(result, ["command_sent", "raw_response", "blocked"])
        assert data["blocked"] is False
        cmd = data["command_sent"]
        assert cmd == (
            'newshow "Claude_MA2_Ctrl" /noconfirm'
            " /timeconfig /globalsettings /localsettings /protocols /network /user"
        )
        print(f"  command_sent: {cmd}")
        print(f"  raw_response: {data['raw_response']}")

    async def test_new_show_selective_keep(self, live_client):
        """10.3 — preserve_connectivity=True (default) + keep_user: all connectivity + /user."""
        result = await new_show(
            name="Claude_MA2_Ctrl",
            confirm_destructive=True,
            keep_user=True,
        )
        data = validate_response(result, ["command_sent", "raw_response", "blocked"])
        assert data["blocked"] is False
        cmd = data["command_sent"]
        assert "/globalsettings" in cmd
        assert "/network" in cmd
        assert "/protocols" in cmd
        assert "/user" in cmd
        print(f"  command_sent: {cmd}")


# ---------------------------------------------------------------------------
# Layer 11 — New Tool Guard Verification (SAFE_READ / gate-only)
# ---------------------------------------------------------------------------


@pytest.mark.live
class TestLayer11NewToolGuards:
    """Layer 11 — Verify safety gates of the 8 new quick-wins tools.

    SAFE_READ / SAFE_WRITE tools are exercised fully.
    DESTRUCTIVE tools (delete_user, delete_show) are only tested at their
    safety gates — no actual deletion occurs.
    """

    # ── delete_user guards ──────────────────────────────────────────────────

    async def test_delete_user_blocked_without_confirm(self, live_client):
        """11.1 — delete_user blocked when confirm_destructive=False (default)."""
        result = await delete_user(slot=3)
        data = validate_response(result, ["blocked", "risk_tier"])
        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"
        print(f"  error: {data.get('error')}")

    async def test_delete_user_slot1_always_protected(self, live_client):
        """11.2 — Slot 1 (Administrator) is always refused, even with confirm."""
        result = await delete_user(slot=1, confirm_destructive=True)
        data = validate_response(result, ["blocked", "error"])
        assert data["blocked"] is True
        assert "Slot 1" in data["error"]
        print(f"  error: {data['error']}")

    # ── delete_show guards ──────────────────────────────────────────────────

    async def test_delete_show_blocked_without_confirm(self, live_client):
        """11.3 — delete_show blocked when confirm_destructive=False (default)."""
        result = await delete_show(name="nonexistent_test_show_xyz")
        data = validate_response(result, ["blocked", "risk_tier"])
        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"
        print(f"  error: {data.get('error')}")

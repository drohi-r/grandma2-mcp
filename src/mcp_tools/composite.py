"""MCP tools — composite. Split out of src/server.py.

Tools register on ``src.server.mcp`` at import. Names that tests patch or
that live in other tool modules are looked up as ``_srv.<name>`` at call time.
"""

# ruff: noqa: E501

import json

import src.server as _srv
from src.auth import OAuthScope, require_scope
from src.commands import (
    add_user_var as build_add_user_var,
    add_var as build_add_var,
    appearance as build_appearance,
    # assign_object
    assign as build_assign,
    assign_fade as build_assign_fade,
    assign_function as build_assign_function,
    assign_to_layout as build_assign_to_layout,
    cut as build_cut,
    def_go_back as build_def_go_back,
    def_go_forward as build_def_go_forward,
    def_go_pause as build_def_go_pause,
    # edit_object
    edit as build_edit,
    # playback_action
    go as build_go,
    go_back as build_go_back,
    go_fast_back as build_go_fast_back,
    go_fast_forward as build_go_fast_forward,
    goto as build_goto,
    label as build_label,
    # label_or_appearance
    label_preset as build_label_preset,
    list_attribute as build_list_attribute,
    list_cue as build_list_cue,
    list_group as build_list_group,
    list_messages as build_list_messages,
    # query_object_list
    list_objects as build_list_objects,
    list_preset as build_list_preset,
    list_user_var as build_list_user_var,
    list_var as build_list_var,
    paste as build_paste,
    # remove_content
    remove as build_remove,
    remove_effect as build_remove_effect,
    remove_fixture as build_remove_fixture,
    remove_preset_type as build_remove_preset_type,
    remove_selection as build_remove_selection,
    set_user_var as build_set_user_var,
    # manage_variable
    set_var as build_set_var,
    # store_object
    store as build_store_generic,
)
from src.server import (
    _get_sequence_for_executor,
    _handle_errors,
    _validate_object_exists,
    mcp,
)

# ============================================================
# New Composite Tools (Tools 20-27)
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def query_object_list(
    object_type: str | None = None,
    object_id: int | str | None = None,
    end: int | None = None,
    sequence_id: int | None = None,
    preset_type: str | int | None = None,
    filename: str | None = None,
    condition: str | None = None,
) -> str:
    """
    List objects from the show file by type — cues, groups, presets, etc.

    Sends typed `list <type>` commands with type-specific options.
    Different from list_console_destination (which lists at the current
    navigation location). This tool queries named object pools directly.

    Args:
        object_type: Object type to list. Typed shortcuts:
            "cue", "group", "preset", "attribute", "messages".
            Or any generic type (e.g. "sequence", "macro", "executor").
            If omitted, lists all objects at the default scope.
        object_id: Optional object ID to list a specific item
        end: Optional end ID for range listing (e.g. cue 1 thru 10)
        sequence_id: Sequence to list cues from (only for object_type="cue")
        preset_type: Preset type name or number (only for object_type="preset",
            e.g. "color", "position", "4")
        filename: Optional filename to export the list output
        condition: Optional filter condition (for "messages" or generic types)

    Returns:
        str: JSON with command_sent and raw_response.

    Examples:
        - List all cues: object_type="cue"
        - List cues in sequence 2: object_type="cue", sequence_id=2
        - List groups: object_type="group"
        - List color presets: object_type="preset", preset_type="color"
        - List attributes: object_type="attribute"
    """
    otype = (object_type or "").lower()

    if otype == "cue":
        cmd = build_list_cue(
            cue_id=object_id, end=end, sequence_id=sequence_id,
            filename=filename,
        )
    elif otype == "group":
        cmd = build_list_group(
            group_id=object_id, end=end, filename=filename,
        )
    elif otype == "preset":
        cmd = build_list_preset(
            preset_type=preset_type, preset_id=object_id,
            end=end, filename=filename,
        )
    elif otype == "attribute":
        cmd = build_list_attribute(filename=filename)
    elif otype == "messages":
        cmd = build_list_messages(condition=condition, filename=filename)
    else:
        cmd = build_list_objects(
            object_type=object_type, object_id=object_id,
            end=end, filename=filename, condition=condition,
        )

    client = await _srv.get_client()
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
    }, indent=2)


def _parse_listvar(raw: str, filter_prefix: str | None = None) -> dict[str, str]:
    """Parse ListVar telnet output into a {$NAME: value} dict.

    ListVar lines have the format:  $Global : $VARNAME = VALUE
    """
    variables: dict[str, str] = {}
    for line in raw.splitlines():
        line = line.strip()
        if "=" not in line or line.startswith("["):
            continue
        # Strip scope prefix: "$Global : $VARNAME = VALUE" → "$VARNAME = VALUE"
        if " : " in line:
            _, _, line = line.partition(" : ")
            line = line.strip()
        name, _, value = line.partition("=")
        name = name.strip().lstrip("$")
        value = value.strip()
        if not name:
            continue
        if filter_prefix is None or name.upper().startswith(filter_prefix.upper()):
            variables[f"${name}"] = value
    return variables


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def list_system_variables(
    filter_prefix: str | None = None,
) -> str:
    """
    List all grandMA2 built-in system variables (SAFE_READ).

    Sends `ListVar` to the console and returns parsed key=value pairs.
    System variables include $SELECTEDEXEC, $TIME, $DATE, $VERSION, $HOSTSTATUS,
    $FADERPAGE, $BUTTONPAGE, $SELECTEDFIXTURESCOUNT, $USER, $HOSTNAME, etc.

    Args:
        filter_prefix: Optional prefix filter (case-insensitive).
            e.g. "SELECTED" returns only $SELECTEDEXEC, $SELECTEDEXECCUE, etc.
            Omit to return all variables.

    Returns:
        str: JSON with `variables` dict (name→value), `variable_count`, and `raw_response`.
    """
    client = await _srv.get_client()
    raw = await client.send_command_with_response("ListVar")

    variables = _srv._parse_listvar(raw, filter_prefix=filter_prefix)
    return json.dumps({
        "variables": variables,
        "variable_count": len(variables),
        "raw_response": raw,
    }, indent=2)


async def _read_selected_exec(client) -> tuple[str | None, str | None]:
    """Read $SELECTEDEXEC and $SELECTEDEXECCUE from the console.

    Returns (exec_value, cue_value). Both are None if ListVar fails or the
    variables are absent in the response.
    """
    try:
        raw = await client.send_command_with_response("ListVar")
        variables = _srv._parse_listvar(raw)
        return variables.get("$SELECTEDEXEC"), variables.get("$SELECTEDEXECCUE")
    except Exception:
        return None, None


@mcp.tool()
@require_scope(OAuthScope.PLAYBACK_GO)
@_handle_errors
async def playback_action(
    action: str,
    object_type: str | None = None,
    object_id: int | list[int] | None = None,
    cue_id: int | float | None = None,
    end: int | None = None,
    cue_mode: str | None = None,
    executor: int | list[int] | None = None,
    sequence: int | None = None,
) -> str:
    """
    Execute playback operations — go, go back, goto, fast forward/back, etc.

    Full-featured playback control with cue_mode and executor targeting.
    Coexists with execute_sequence (which uses legacy go_sequence/pause_sequence).

    Args:
        action: Playback action to perform:
            "go" — fire the next cue (optionally on a specific executor/sequence)
            "go_back" — fire the previous cue
            "goto" — jump to a specific cue (requires cue_id)
            "fast_forward" — skip forward (>>>)
            "fast_back" — skip backward (<<<)
            "def_go" — go on the selected executor (go+); response includes
                       selected_executor and selected_cue_before
            "def_go_back" / "def_goback" — go back on the selected executor;
                       response includes selected_executor and selected_cue_before
            "def_pause" — pause the selected executor; response includes
                       selected_executor and selected_cue_before
        object_type: Object type for go/go_back (e.g. "executor", "sequence")
        object_id: Object ID for go/go_back — single int or list of ints.
                   List produces "N + M + ..." syntax for multi-executor targeting.
        cue_id: Target cue number (required for "goto")
        end: End ID for range (go/go_back)
        cue_mode: Cue execution mode: "normal", "assert", "xassert", "release"
        executor: Executor ID for goto/fast_forward/fast_back — single int or list of ints.
                  List produces "N + M + ..." syntax (e.g. [1,2,3] → ">>> executor 1 + 2 + 3").
        sequence: Sequence ID for goto/fast_forward/fast_back

    Returns:
        str: JSON with command_sent and raw_response.
             def_go/def_go_back/def_pause also include selected_executor and
             selected_cue_before (read from $SELECTEDEXEC before firing).

    Examples:
        - Go on executor 1: action="go", object_type="executor", object_id=1
        - Go on executors 1+2+3: action="go", object_type="executor", object_id=[1,2,3]
        - Go back: action="go_back"
        - Goto cue 5: action="goto", cue_id=5
        - Goto cue 3 on sequence 2: action="goto", cue_id=3, sequence=2
        - Fast forward: action="fast_forward"
        - Fast forward executors 1,2,3: action="fast_forward", executor=[1,2,3]
        - Go on selected executor: action="def_go"
        - Go back on selected executor: action="def_go_back"
    """
    action = action.lower()

    if action == "go":
        cmd = build_go(
            object_type=object_type, object_id=object_id,
            end=end, cue_mode=cue_mode,
        )
    elif action == "go_back":
        cmd = build_go_back(
            object_type=object_type, object_id=object_id,
            end=end, cue_mode=cue_mode,
        )
    elif action == "goto":
        if cue_id is None:
            return json.dumps({
                "error": "goto action requires cue_id to be specified.",
                "blocked": True,
            }, indent=2)

        # Pre-flight: validate cue exists before sending goto
        client = await _srv.get_client()
        validation_info: dict = {}
        resolved_sequence = sequence

        if resolved_sequence is None and executor is not None:
            # Derive sequence from the executor assignment
            resolved_sequence, exec_raw = await _get_sequence_for_executor(
                client, executor
            )
            validation_info["executor_probe_response"] = exec_raw

        if resolved_sequence is not None:
            cue_probe_arg = f"{cue_id} sequence {resolved_sequence}"
            cue_exists, cue_raw = await _validate_object_exists(
                client, "cue", cue_probe_arg
            )
            validation_info["cue_exists"] = cue_exists
            validation_info["cue_probe_response"] = cue_raw
            if not cue_exists:
                return json.dumps({
                    "command_sent": None,
                    "error": (
                        f"Cue {cue_id} does not exist in sequence {resolved_sequence}. "
                        "MA2 would return Error #72 (COMMAND NOT EXECUTED)."
                    ),
                    "hint": "Use list_sequence_cues(sequence_id) to see available cues.",
                    **validation_info,
                    "blocked": True,
                }, indent=2)
        else:
            validation_info["warning"] = (
                "Could not resolve sequence context — command sent without cue "
                "pre-flight check. Provide sequence or executor for validation."
            )

        cmd = build_goto(
            cue_id, executor=executor, sequence=sequence,
            cue_mode=cue_mode,
        )
        raw_response = await client.send_command_with_response(cmd)
        return json.dumps({
            "command_sent": cmd,
            "raw_response": raw_response,
            **validation_info,
        }, indent=2)
    elif action == "fast_forward":
        cmd = build_go_fast_forward(executor=executor, sequence=sequence)
    elif action == "fast_back":
        cmd = build_go_fast_back(executor=executor, sequence=sequence)
    elif action in ("def_go", "def_go_back", "def_goback", "def_pause"):
        client = await _srv.get_client()
        sel_exec, sel_cue = await _srv._read_selected_exec(client)

        if action == "def_go":
            cmd = build_def_go_forward()
        elif action in ("def_go_back", "def_goback"):
            cmd = build_def_go_back()
        else:  # def_pause
            cmd = build_def_go_pause()

        raw_response = await client.send_command_with_response(cmd)
        return json.dumps({
            "command_sent": cmd,
            "raw_response": raw_response,
            "selected_executor": sel_exec,
            "selected_cue_before": sel_cue,
        }, indent=2)
    else:
        return json.dumps({
            "error": (
                f"Unknown action: {action}. Use 'go', 'go_back', 'goto', "
                f"'fast_forward', 'fast_back', 'def_go', 'def_go_back', or 'def_pause'."
            ),
            "blocked": True,
        }, indent=2)

    client = await _srv.get_client()
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def manage_variable(
    action: str,
    scope: str,
    var_name: str,
    value: int | float | str | None = None,
    input_dialog: bool = False,
) -> str:
    """
    Set, add to, or list console variables (global or user-scoped).

    Variables are named values stored on the console that can be used in
    macros and command line expressions. The $ prefix is automatically
    added to var_name if not already present.

    Args:
        action: "set" to assign a value, "add" to increment, "list" to show all variables
        scope: "global" for system variables, "user" for user-scoped variables
        var_name: Variable name (e.g. "myvar" or "$myvar" — $ auto-added)
        value: Value to set or add. Required for "add", optional for "set",
            ignored for "list"
        input_dialog: If True with action="set", shows an input dialog
            on the console for the user to enter a value

    Returns:
        str: JSON with command_sent and raw_response.

    Examples:
        - Set global var: action="set", scope="global", var_name="myvar", value=42
        - Set user var: action="set", scope="user", var_name="speed", value=100
        - Add to global: action="add", scope="global", var_name="counter", value=1
        - List global vars: action="list", scope="global"
        - List user vars: action="list", scope="user"
    """
    action = action.lower()
    scope = scope.lower()

    # Auto-prepend $ if not present (MA2 syntax requires $variablename)
    if var_name and not var_name.startswith("$"):
        var_name = f"${var_name}"

    if action == "list":
        if scope == "global":
            cmd = build_list_var()
        elif scope == "user":
            cmd = build_list_user_var()
        else:
            return json.dumps({
                "error": f"Unknown scope: {scope}. Use 'global' or 'user'.",
                "blocked": True,
            }, indent=2)
        client = await _srv.get_client()
        raw_response = await client.send_command_with_response(cmd)
        return json.dumps({
            "command_sent": cmd,
            "raw_response": raw_response,
        }, indent=2)

    if action == "set":
        if scope == "global":
            cmd = build_set_var(var_name, value, input_dialog=input_dialog)
        elif scope == "user":
            cmd = build_set_user_var(var_name, value, input_dialog=input_dialog)
        else:
            return json.dumps({
                "error": f"Unknown scope: {scope}. Use 'global' or 'user'.",
                "blocked": True,
            }, indent=2)
    elif action == "add":
        if value is None:
            return json.dumps({
                "error": "add action requires a value.",
                "blocked": True,
            }, indent=2)
        if scope == "global":
            cmd = build_add_var(var_name, value)
        elif scope == "user":
            cmd = build_add_user_var(var_name, value)
        else:
            return json.dumps({
                "error": f"Unknown scope: {scope}. Use 'global' or 'user'.",
                "blocked": True,
            }, indent=2)
    else:
        return json.dumps({
            "error": f"Unknown action: {action}. Use 'set', 'add', or 'list'.",
            "blocked": True,
        }, indent=2)

    client = await _srv.get_client()
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def label_or_appearance(
    action: str,
    object_type: str,
    object_id: int | str,
    name: str | None = None,
    end: int | None = None,
    preset_type: str | None = None,
    confirm_destructive: bool = False,
    color: str | None = None,
    red: int | None = None,
    green: int | None = None,
    blue: int | None = None,
    hue: int | None = None,
    saturation: int | None = None,
    brightness: int | None = None,
    reset: bool = False,
    source_type: str | None = None,
    source_id: int | str | None = None,
) -> str:
    """
    Label or set the appearance of console objects.

    SAFETY: This is a DESTRUCTIVE operation. Requires confirm_destructive=True.

    Args:
        action: "label" to set a name, "appearance" to set visual styling
        object_type: Object type (e.g. "group", "sequence", "cue", "preset")
        object_id: Object ID
        name: Name to assign (required for action="label")
        end: End ID for range labeling (e.g. group 1 thru 5)
        preset_type: For labeling presets, the preset type (e.g. "color", "position").
            When set, uses the specialized label_preset builder.
        confirm_destructive: Must be True to execute (safety gate)
        color: Hex color string for appearance (e.g. "FF0000")
        red: Red component (0-100) for appearance
        green: Green component (0-100) for appearance
        blue: Blue component (0-100) for appearance
        hue: Hue value for appearance
        saturation: Saturation value for appearance
        brightness: Brightness value for appearance
        reset: Reset appearance to default
        source_type: Copy appearance from this object type
        source_id: Copy appearance from this object ID

    Returns:
        str: JSON with command_sent, raw_response, or block info.

    Examples:
        - Label group 3: action="label", object_type="group", object_id=3, name="Front Wash"
        - Label color preset 1: action="label", object_type="preset", object_id=1,
          preset_type="color", name="Red"
        - Set group appearance: action="appearance", object_type="group", object_id=1,
          color="FF0000"
    """
    if not confirm_destructive:
        return json.dumps({
            "command_sent": None,
            "blocked": True,
            "error": "Label/Appearance is a DESTRUCTIVE operation. Set confirm_destructive=True to proceed.",
        }, indent=2)

    action = action.lower()

    if action == "label":
        if name is None:
            return json.dumps({
                "error": "label action requires 'name' to be specified.",
                "blocked": True,
            }, indent=2)
        if preset_type is not None:
            cmd = build_label_preset(preset_type, object_id, name)
        else:
            cmd = build_label(object_type, object_id, name, end=end)
    elif action == "appearance":
        cmd = build_appearance(
            object_type, object_id, end=end,
            source_type=source_type, source_id=source_id,
            reset=reset, color=color,
            red=red, green=green, blue=blue,
            hue=hue, saturation=saturation, brightness=brightness,
        )
    else:
        return json.dumps({
            "error": f"Unknown action: {action}. Use 'label' or 'appearance'.",
            "blocked": True,
        }, indent=2)

    client = await _srv.get_client()
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "blocked": False,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.GROUP_STORE)
@_handle_errors
async def assign_object(
    mode: str,
    confirm_destructive: bool = False,
    source_type: str | None = None,
    source_id: int | str | None = None,
    target_type: str | None = None,
    target_id: int | str | None = None,
    function: str | None = None,
    fade_time: float | None = None,
    cue_id: int | None = None,
    sequence_id: int | None = None,
    layout_id: int | None = None,
    x: int | None = None,
    y: int | None = None,
    noconfirm: bool = False,
) -> str:
    """
    Assign objects, functions, fades, or layout positions on the console.

    SAFETY: This is a DESTRUCTIVE operation. Requires confirm_destructive=True.

    Args:
        mode: Assignment mode:
            "assign" — assign source object to target (e.g. sequence to executor)
            "function" — assign a function to an executor (e.g. Toggle, Flash)
            "fade" — assign a fade time to a cue
            "layout" — assign an object to a layout position
            "empty" — deactivate an executor (assign empty function)
            "temp_fader" — assign temp fader function to an executor
        confirm_destructive: Must be True to execute (safety gate)
        source_type: Source object type (for "assign" and "layout" modes)
        source_id: Source object ID (for "assign" and "layout" modes)
        target_type: Target object type (for "assign", "function", "empty", "temp_fader")
        target_id: Target object ID
        function: Function name for "function" mode (e.g. "Toggle", "Flash", "Go")
        fade_time: Fade time in seconds for "fade" mode
        cue_id: Cue ID for "fade" mode
        sequence_id: Sequence ID for "fade" mode
        layout_id: Layout ID for "layout" mode
        x: X position for "layout" mode
        y: Y position for "layout" mode
        noconfirm: Skip console confirmation dialog

    Returns:
        str: JSON with command_sent, raw_response, or block info.

    Examples:
        - Assign sequence 1 to executor 6: mode="assign", source_type="sequence",
          source_id=1, target_type="executor", target_id=6
        - Assign Toggle to executor 101: mode="function", function="Toggle",
          target_type="executor", target_id=101
        - Assign fade 3s to cue 5: mode="fade", fade_time=3, cue_id=5
        - Assign group to layout: mode="layout", source_type="group", source_id=1,
          layout_id=1, x=5, y=2
        - Empty executor 1: mode="empty", target_type="executor", target_id=1
    """
    if not confirm_destructive:
        return json.dumps({
            "command_sent": None,
            "blocked": True,
            "error": "Assign is a DESTRUCTIVE operation. Set confirm_destructive=True to proceed.",
        }, indent=2)

    mode = mode.lower()

    if mode == "assign":
        if source_type is None or source_id is None:
            return json.dumps({
                "error": "assign mode requires source_type and source_id.",
                "blocked": True,
            }, indent=2)
        cmd = build_assign(
            source_type, source_id,
            target_type=target_type, target_id=target_id,
            noconfirm=noconfirm,
        )
    elif mode == "function":
        if function is None or target_type is None or target_id is None:
            return json.dumps({
                "error": "function mode requires function, target_type, and target_id.",
                "blocked": True,
            }, indent=2)
        cmd = build_assign_function(function, target_type, target_id)
    elif mode == "fade":
        if fade_time is None or cue_id is None:
            return json.dumps({
                "error": "fade mode requires fade_time and cue_id.",
                "blocked": True,
            }, indent=2)
        cmd = build_assign_fade(fade_time, cue_id, sequence_id=sequence_id)
    elif mode == "layout":
        if source_type is None or source_id is None or layout_id is None:
            return json.dumps({
                "error": "layout mode requires source_type, source_id, and layout_id.",
                "blocked": True,
            }, indent=2)
        cmd = build_assign_to_layout(
            source_type, source_id, layout_id, x=x, y=y,
        )
    elif mode == "empty":
        if target_type is None or target_id is None:
            return json.dumps({
                "error": "empty mode requires target_type and target_id.",
                "blocked": True,
            }, indent=2)
        cmd = build_assign_function("empty", target_type, target_id)
    elif mode == "temp_fader":
        if target_type is None or target_id is None:
            return json.dumps({
                "error": "temp_fader mode requires target_type and target_id.",
                "blocked": True,
            }, indent=2)
        cmd = build_assign_function("tempfader", target_type, target_id)
    else:
        return json.dumps({
            "error": (
                f"Unknown mode: {mode}. Use 'assign', 'function', 'fade', "
                f"'layout', 'empty', or 'temp_fader'."
            ),
            "blocked": True,
        }, indent=2)

    client = await _srv.get_client()
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "blocked": False,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def edit_object(
    action: str,
    object_type: str | None = None,
    object_id: int | str | None = None,
    target_id: int | str | None = None,
    end: int | str | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Edit, cut, or paste objects in the show.

    - edit: Opens an object for editing (SAFE_WRITE)
    - cut: Removes an object and places it on the clipboard (DESTRUCTIVE)
    - paste: Places clipboard contents at a target location (DESTRUCTIVE)

    SAFETY: cut and paste are DESTRUCTIVE and require confirm_destructive=True.
    edit does not require confirmation.

    Args:
        action: "edit", "cut", or "paste"
        object_type: Object type (e.g. "preset", "cue", "group")
        object_id: Object ID (for edit and cut)
        target_id: Target ID for paste destination
        end: End ID for range operations
        confirm_destructive: Must be True for cut/paste (safety gate)

    Returns:
        str: JSON with command_sent, raw_response, or block info.

    Examples:
        - Edit cue 1: action="edit", object_type="cue", object_id=1
        - Cut preset 4.1: action="cut", object_type="preset", object_id="4.1"
        - Paste to group 5: action="paste", object_type="group", target_id=5
    """
    action = action.lower()

    if action in ("cut", "paste") and not confirm_destructive:
        return json.dumps({
            "command_sent": None,
            "blocked": True,
            "error": f"{action.title()} is a DESTRUCTIVE operation. Set confirm_destructive=True to proceed.",
        }, indent=2)

    if action == "edit":
        cmd = build_edit(object_type=object_type, object_id=object_id, end=end)
    elif action == "cut":
        if object_type is None or object_id is None:
            return json.dumps({
                "error": "cut requires object_type and object_id.",
                "blocked": True,
            }, indent=2)
        cmd = build_cut(object_type, object_id, end=end)
    elif action == "paste":
        cmd = build_paste(object_type, target_id)
    else:
        return json.dumps({
            "error": f"Unknown action: {action}. Use 'edit', 'cut', or 'paste'.",
            "blocked": True,
        }, indent=2)

    client = await _srv.get_client()
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "blocked": False,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def remove_content(
    object_type: str,
    object_id: int | str | None = None,
    end: int | None = None,
    if_filter: str | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Remove content from objects (fixtures from groups, effects, preset types, etc.).

    Unlike delete (which removes the object itself), remove takes content out of
    an object. For example, removing a fixture from a group, or removing an effect
    from a cue.

    SAFETY: This is a DESTRUCTIVE operation. Requires confirm_destructive=True.

    Args:
        object_type: What to remove. Special types:
            "selection" — remove the current selection
            "fixture" — remove a fixture (from a group, cue, etc.)
            "effect" — remove an effect
            "presettype" — remove a preset type from the programmer
            Or any generic type for the generic remove command.
        object_id: Object ID to remove (not needed for "selection")
        end: End ID for range removal
        if_filter: Conditional filter (e.g. "PresetType 1")
        confirm_destructive: Must be True to execute (safety gate)

    Returns:
        str: JSON with command_sent, raw_response, or block info.

    Examples:
        - Remove selection: object_type="selection"
        - Remove fixture 1: object_type="fixture", object_id=1
        - Remove fixture with filter: object_type="fixture", object_id=1,
          if_filter="PresetType 1"
        - Remove effect 1: object_type="effect", object_id=1
        - Remove preset type: object_type="presettype", object_id="position"
    """
    if not confirm_destructive:
        return json.dumps({
            "command_sent": None,
            "blocked": True,
            "error": "Remove is a DESTRUCTIVE operation. Set confirm_destructive=True to proceed.",
        }, indent=2)

    otype = object_type.lower()

    if otype == "selection":
        cmd = build_remove_selection()
    elif otype == "fixture":
        if object_id is None:
            return json.dumps({
                "error": "fixture removal requires object_id.",
                "blocked": True,
            }, indent=2)
        cmd = build_remove_fixture(object_id, end=end, if_filter=if_filter)
    elif otype == "effect":
        if object_id is None:
            return json.dumps({
                "error": "effect removal requires object_id.",
                "blocked": True,
            }, indent=2)
        cmd = build_remove_effect(object_id, end=end)
    elif otype == "presettype":
        if object_id is None:
            return json.dumps({
                "error": "presettype removal requires object_id (the preset type name or number).",
                "blocked": True,
            }, indent=2)
        cmd = build_remove_preset_type(object_id, if_filter=if_filter)
    else:
        cmd = build_remove(
            object_type=object_type, object_id=object_id,
            end=end, if_filter=if_filter,
        )

    client = await _srv.get_client()
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "blocked": False,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def store_object(
    object_type: str,
    object_id: int | str,
    name: str | None = None,
    merge: bool = False,
    overwrite: bool = False,
    noconfirm: bool = False,
    confirm_destructive: bool = False,
) -> str:
    """
    Store (create) a generic object in the show — macros, effects, worlds, etc.

    For cues, use store_current_cue. For presets, use store_new_preset.
    For groups, use create_fixture_group. This tool handles everything else.

    SAFETY: This is a DESTRUCTIVE operation. Requires confirm_destructive=True.

    Args:
        object_type: Object type to store (e.g. "macro", "effect", "world",
            "sequence", "executor", "timecode")
        object_id: Object ID number or slot
        name: Optional name for the stored object
        merge: Merge into existing object if present
        overwrite: Overwrite existing object if present
        noconfirm: Skip console confirmation dialog
        confirm_destructive: Must be True to execute (safety gate)

    Returns:
        str: JSON with command_sent, raw_response, or block info.

    Examples:
        - Store macro 5: object_type="macro", object_id=5
        - Store effect 1 named "Rainbow": object_type="effect", object_id=1, name="Rainbow"
        - Overwrite sequence 3: object_type="sequence", object_id=3, overwrite=True
    """
    if not confirm_destructive:
        return json.dumps({
            "command_sent": None,
            "blocked": True,
            "error": "Store is a DESTRUCTIVE operation. Set confirm_destructive=True to proceed.",
        }, indent=2)

    cmd = build_store_generic(
        object_type, object_id, name,
        merge=merge, overwrite=overwrite, noconfirm=noconfirm,
    )

    client = await _srv.get_client()
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "blocked": False,
    }, indent=2)

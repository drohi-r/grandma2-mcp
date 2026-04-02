"""
Assign Function Keywords for grandMA2 Command Builder

Assign is used to define relationships between objects or assign values to properties.
This is a versatile keyword with many use cases:
- Assign objects to Executor, Layout
- Assign DMX addresses to Fixture/Channel
- Assign functions (Go, Toggle, etc.) to Executor buttons
- Assign properties to objects

Included functions:
- assign: Generic assign command
- assign_function: Assign function to object
- assign_fade: Assign fade time to cue
- assign_to_layout: Assign object to layout
"""



def assign(
    source_type: str,
    source_id: int | str | list[int],
    target_type: str | None = None,
    target_id: int | str | list[int] | None = None,
    *,
    source_end: int | None = None,
    target_end: int | None = None,
    break_: int | None = None,
    multipatch: int | None = None,
    reset: bool = False,
    x: int | None = None,
    y: int | None = None,
    noconfirm: bool = False,
    special: str | None = None,
    cue_mode: str | None = None,
    password: str | None = None,
) -> str:
    """
    Construct an Assign command to define relationships between objects.

    Args:
        source_type: Type of source object (e.g., "sequence", "group", "dmx")
        source_id: Source object ID (can be compound like "2.101" for DMX)
        target_type: Target object type (e.g., "executor", "channel", "layout")
        target_id: Target object ID
        source_end: End ID for source range
        target_end: End ID for target range
        break_: Patch break value (1-8)
        multipatch: Multipatch slot (0-10000)
        reset: Remove existing patch
        x: X-coordinate for layout (-10000 to +10000)
        y: Y-coordinate for layout (-10000 to +10000)
        noconfirm: Suppress confirmation popup
        special: Preset special mode (normal, default, highlight)
        cue_mode: Cue mode (assert, xassert, break, xbreak, release)
        password: Password value for user assignment

    Returns:
        str: MA command for assign operation

    Examples:
        >>> assign("sequence", 1, "executor", 6, source_end=5, target_end=10)
        'assign sequence 1 thru 5 at executor 6 thru 10'
        >>> assign("dmx", "2.101", "channel", 5)
        'assign dmx 2.101 at channel 5'
        >>> assign("group", 1, "layout", 1, x=5, y=2)
        'assign group 1 at layout 1 /x=5 /y=2'
    """
    # Build source part
    if isinstance(source_id, list):
        source = " + ".join(str(i) for i in source_id)
        cmd = f"assign {source_type} {source}"
    elif source_end is not None:
        cmd = f"assign {source_type} {source_id} thru {source_end}"
    else:
        cmd = f"assign {source_type} {source_id}"

    # Build target part (if provided)
    if target_type is not None and target_id is not None:
        if isinstance(target_id, list):
            target_str = " + ".join(str(t) for t in target_id)
            cmd += f" at {target_type} {target_str}"
        elif target_end is not None:
            cmd += f" at {target_type} {target_id} thru {target_end}"
        else:
            cmd += f" at {target_type} {target_id}"
    elif target_type is not None:
        cmd += f" {target_type}"

    # Build options
    options = []
    if break_ is not None:
        options.append(f"/break={break_}")
    if multipatch is not None:
        options.append(f"/multipatch={multipatch}")
    if reset:
        options.append("/reset")
    if x is not None:
        options.append(f"/x={x}")
    if y is not None:
        options.append(f"/y={y}")
    if noconfirm:
        options.append("/noconfirm")
    if special is not None:
        options.append(f"/special={special}")
    if cue_mode is not None:
        options.append(f"/cue_mode={cue_mode}")
    if password is not None:
        options.append(f'/password="{password}"')

    if options:
        cmd += " " + " ".join(options)

    return cmd


def assign_property(
    target_index: int | str,
    property_name: str,
    value: str,
) -> str:
    """
    Build an inline property assignment command.

    When cd'd into a parent node, sets a property on a child entry.
    Produces: ``assign [index]/property=value``

    Args:
        target_index: Child index within current listing (e.g. 1 for Global in Settings)
        property_name: Property name (e.g. "Telnet", "OutActive")
        value: Property value (e.g. "Login Enabled", "On")

    Returns:
        str: MA command for inline property assignment

    Examples:
        >>> assign_property(1, "Telnet", "Login Disabled")
        'assign 1/Telnet="Login Disabled"'
        >>> assign_property(1, "OutActive", "On")
        'assign 1/OutActive=On'
    """
    if " " in str(value):
        return f'assign {target_index}/{property_name}="{value}"'
    return f"assign {target_index}/{property_name}={value}"


def assign_function(
    function: str,
    target_type: str,
    target_id: int | str,
    *,
    cue_mode: str | None = None,
) -> str:
    """
    Assign a function (Go, Toggle, etc.) to an object.

    Args:
        function: Function name (e.g., "Toggle", "Go", "Pause")
        target_type: Target type (e.g., "executor", "execbutton1")
        target_id: Target ID
        cue_mode: Cue mode (assert, xassert, break, xbreak, release)

    Returns:
        str: MA command to assign function

    Examples:
        >>> assign_function("Toggle", "executor", 101)
        'assign toggle at executor 101'
        >>> assign_function("Go", "execbutton1", "1.1", cue_mode="xassert")
        'assign go at execbutton1 1.1 /cue_mode=xassert'
    """
    cmd = f"assign {function.lower()} at {target_type} {target_id}"
    if cue_mode is not None:
        cmd += f" /cue_mode={cue_mode}"
    return cmd


def assign_fade(
    fade_time: float,
    cue_id: int,
    *,
    sequence_id: int | None = None,
) -> str:
    """
    Assign fade time to a cue.

    Args:
        fade_time: Fade time in seconds
        cue_id: Cue ID
        sequence_id: Sequence ID (optional, uses selected executor if not given)

    Returns:
        str: MA command to assign fade time

    Examples:
        >>> assign_fade(3, 5)
        'assign fade 3 cue 5'
        >>> assign_fade(2.5, 3, sequence_id=1)
        'assign fade 2.5 cue 3 sequence 1'
    """
    cmd = f"assign fade {fade_time} cue {cue_id}"
    if sequence_id is not None:
        cmd += f" sequence {sequence_id}"
    return cmd


def assign_to_layout(
    object_type: str,
    object_id: int | list[int],
    layout_id: int,
    *,
    x: int | None = None,
    y: int | None = None,
    end: int | None = None,
) -> str:
    """
    Assign an object to a layout at a specific position.

    Args:
        object_type: Type of object (e.g., "group", "macro")
        object_id: Object ID or list of IDs
        layout_id: Layout ID
        x: X-coordinate (-10000 to +10000)
        y: Y-coordinate (-10000 to +10000)
        end: End ID for range

    Returns:
        str: MA command to assign to layout

    Examples:
        >>> assign_to_layout("group", 1, 1, x=5, y=2)
        'assign group 1 at layout 1 /x=5 /y=2'
        >>> assign_to_layout("macro", 1, 2, x=0, y=0, end=5)
        'assign macro 1 thru 5 at layout 2 /x=0 /y=0'
    """
    return assign(object_type, object_id, "layout", layout_id, source_end=end, x=x, y=y)


def assign_delay(
    delay_time: float,
    cue_id: int,
    *,
    sequence_id: int | None = None,
) -> str:
    """
    Assign delay time to a cue.

    Args:
        delay_time: Delay time in seconds
        cue_id: Cue ID
        sequence_id: Sequence ID (optional, uses selected executor if not given)

    Returns:
        str: MA command to assign delay time

    Examples:
        >>> assign_delay(1.5, 5)
        'assign delay 1.5 cue 5'
        >>> assign_delay(2.0, 3, sequence_id=1)
        'assign delay 2.0 cue 3 sequence 1'
    """
    cmd = f"assign delay {delay_time} cue {cue_id}"
    if sequence_id is not None:
        cmd += f" sequence {sequence_id}"
    return cmd


def empty() -> str:
    """
    Construct an Empty command to deactivate executors.

    Empty is a function keyword used to assign the "empty" function to executors,
    which deactivates them. It is typically used with the Assign keyword.

    Note: Empty must be used with Assign to deactivate executors.
    Shortcut: Em

    Returns:
        str: The "empty" keyword

    Examples:
        >>> empty()
        'empty'
        >>> # Typical usage with assign
        >>> f"assign {empty()} executor 101"
        'assign empty executor 101'
        >>> # Using assign_function helper
        >>> assign_function("empty", "executor", 101)
        'assign empty at executor 101'
    """
    return "empty"


def build_set_executor_priority(executor_id: int, priority: str, page: int = 1) -> str:
    """
    Build an Assign Executor /priority= command with validated priority level.

    MA2 requires a page-qualified address (page.id) for executor commands.
    Bare executor IDs cause Error #66 CANNOT ASSIGN when the console is on a
    different page. The page parameter defaults to 1 for backward compatibility.

    Args:
        executor_id: The executor ID to modify.
        priority: One of "super", "swap", "htp", "high", "normal", "low".
        page: Page number (default 1). Always included in the command address.

    Returns:
        str: e.g. "Assign Executor 1.201 /priority=high"

    Raises:
        ValueError: If priority is not a valid MA2 executor priority level.

    Examples:
        >>> build_set_executor_priority(201, "high")
        'Assign Executor 1.201 /priority=high'
        >>> build_set_executor_priority(5, "super", page=2)
        'Assign Executor 2.5 /priority=super'
    """
    from src.commands.constants import EXECUTOR_PRIORITY_VALUES
    if priority not in EXECUTOR_PRIORITY_VALUES:
        raise ValueError(
            f"Invalid priority {priority!r}. Must be one of: "
            + ", ".join(sorted(EXECUTOR_PRIORITY_VALUES))
        )
    return f"Assign Executor {page}.{executor_id} /priority={priority}"


def build_assign_executor_option(
    exec_id: int,
    option: str,
    value: str | int,
    page: int = 1,
) -> str:
    """
    Build an Assign Executor page.id /option=value command with validation.

    Supports all 24 options in EXECUTOR_ASSIGN_OPTIONS. Always uses
    page-qualified addressing — bare executor IDs cause Error #66.

    Args:
        exec_id: Executor ID (e.g. 203).
        option: Option name from EXECUTOR_ASSIGN_OPTION_NAMES, e.g. "width",
            "autostart", "crossfade", "priority", "speedmaster".
        value: Option value (e.g. 2, "on", "high", "speed1").
        page: Page number (default 1).

    Returns:
        str: e.g. "Assign Executor 1.203 /width=2"

    Raises:
        ValueError: If option is not a recognised executor assign option.

    Notes:
        crossfade (off|a|b|ab): Silently ignored by MA2 when executor Width=1.
            Requires Width>=2 (multi-fader). Query List Executor page.id and
            check Width before assigning crossfade a/b/ab.

        speed (0-65535): Sets the BPM value. The Speed= field in List Executor
            output shows state (on/off/Normal), not the BPM numeric value.

    Examples:
        >>> build_assign_executor_option(203, "width", 3)
        'Assign Executor 1.203 /width=3'
        >>> build_assign_executor_option(203, "priority", "high", page=2)
        'Assign Executor 2.203 /priority=high'
        >>> build_assign_executor_option(203, "crossfade", "a")
        'Assign Executor 1.203 /crossfade=a'
    """
    from src.commands.constants import EXECUTOR_ASSIGN_OPTION_NAMES
    if option not in EXECUTOR_ASSIGN_OPTION_NAMES:
        raise ValueError(
            f"Unknown executor option {option!r}. Valid options: "
            + ", ".join(sorted(EXECUTOR_ASSIGN_OPTION_NAMES))
        )
    return f"Assign Executor {page}.{exec_id} /{option}={value}"


def temp_fader(value: int | None = None) -> str:
    """
    Construct a TempFader command for temporary fader control.

    TempFader is a function that crossfades the cue on when pulled up,
    and crossfades the cue off when pulled down. It can be used in two ways:
    1. With Assign to assign the function to an executor
    2. Standalone to set the temp fader value for selected executor

    Note: TempFader crossfades cue on/off based on fader position.
    Shortcut: TempF

    Args:
        value: Optional fader value (0-100). If None, returns just "tempfader".
               If provided, returns "tempfader [value]".

    Returns:
        str: MA command for temp fader

    Examples:
        >>> temp_fader()
        'tempfader'
        >>> temp_fader(50)
        'tempfader 50'
        >>> temp_fader(100)
        'tempfader 100'
        >>> # Typical usage with assign
        >>> assign_function("tempfader", "executor", 28)
        'assign tempfader at executor 28'
        >>> # Set temp fader value for selected executor
        >>> temp_fader(50)
        'tempfader 50'
    """
    if value is None:
        return "tempfader"
    return f"tempfader {value}"

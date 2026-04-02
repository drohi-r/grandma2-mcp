"""
At Function Keywords for grandMA2 Command Builder

At is a special keyword that can function as both a Function Keyword and a Helping Keyword:
- As a Function Keyword: Apply values to current selection
- As a Helping Keyword: Indicate target for other functions

Note: The "@" character is different from the "At" keyword.
"@" is used in macros as a placeholder for user input.

Included functions:
- at: Generic At command
- at_full: Set to 100%
- at_zero: Set to 0%
- attribute_at: Set specific attribute value
- fixture_at: Set fixture value
- channel_at: Set channel value
- group_at: Set group value
- executor_at: Set executor value
- preset_type_at: Set preset type value
"""



def at(
    value: int | float | None = None,
    *,
    cue: int | None = None,
    sequence: int | None = None,
    fade: float | None = None,
    delay: float | None = None,
    layer: str | None = None,
    ignoreselection: bool = False,
    values: bool | None = None,
    valuetimes: bool | None = None,
    effects: bool | None = None,
    disablecolortransform: bool = False,
    prefercolorwheel: bool = False,
    prefermixcolor: bool = False,
    prefercolorboth: bool = False,
    status: bool | None = None,
) -> str:
    """
    Construct an At command to apply values to the current selection.

    At is "the exception that proves the rule" - it's one of the few
    functional keywords which accept objects before the function.

    Args:
        value: Percentage value (0-100) or absolute value
        cue: Cue ID to apply values from
        sequence: Sequence ID (used with cue parameter)
        fade: Fade time value (when used as value type)
        delay: Delay time value (when used as value type)
        layer: Destination layer
        ignoreselection: Ignore current selection
        values: Filter by value layer
        valuetimes: Filter by fade and delay layer
        effects: Filter by effect layers
        disablecolortransform: Disable color transformation
        prefercolorwheel: Prefer transforming colors to color wheel
        prefermixcolor: Prefer transforming color to MIXColor
        prefercolorboth: Prefer transforming color to both MIXColor and color wheel
        status: At with tracking values

    Returns:
        str: MA command to apply values

    Examples:
        >>> at(75)
        'at 75'
        >>> at(cue=3)
        'at cue 3'
        >>> at(cue=3, sequence=1)
        'at cue 3 sequence 1'
        >>> at(fade=2)
        'at fade 2'
        >>> at(delay=2)
        'at delay 2'
    """
    parts = ["at"]

    # Value type (Fade or Delay)
    if fade is not None:
        parts.append(f"fade {fade}")
    elif delay is not None:
        parts.append(f"delay {delay}")
    # Cue reference
    elif cue is not None:
        parts.append(f"cue {cue}")
        if sequence is not None:
            parts.append(f"sequence {sequence}")
    # Direct value
    elif value is not None:
        parts.append(str(value))
    else:
        raise ValueError("Must provide value, cue, fade, or delay")

    # Options
    options = []
    if layer is not None:
        options.append(f"/layer={layer}")
    if ignoreselection:
        options.append("/ignoreselection")
    if values is not None:
        options.append(f"/values={'true' if values else 'false'}")
    if valuetimes is not None:
        options.append(f"/valuetimes={'true' if valuetimes else 'false'}")
    if effects is not None:
        options.append(f"/effects={'true' if effects else 'false'}")
    if disablecolortransform:
        options.append("/disablecolortransform")
    if prefercolorwheel:
        options.append("/prefercolorwheel")
    if prefermixcolor:
        options.append("/prefermixcolor")
    if prefercolorboth:
        options.append("/prefercolorboth")
    if status is not None:
        options.append(f"/status={'true' if status else 'false'}")

    if options:
        parts.append(" ".join(options))

    return " ".join(parts)


def at_full() -> str:
    """
    Set current selection to full (100%).

    Returns:
        str: MA command "at full"

    Example:
        >>> at_full()
        'at full'
    """
    return "at full"


def at_zero() -> str:
    """
    Set current selection to zero (0%).

    Returns:
        str: MA command "at 0"

    Example:
        >>> at_zero()
        'at 0'
    """
    return "at 0"


def attribute_at(
    attribute: str,
    value: int | float,
) -> str:
    """
    Set a specific attribute to a value.

    Args:
        attribute: Attribute name (e.g., "Pan", "Tilt", "Dimmer")
        value: Value to set

    Returns:
        str: MA command to set attribute

    Example:
        >>> attribute_at("Pan", 20)
        'attribute "Pan" at 20'
        >>> attribute_at("Tilt", 50)
        'attribute "Tilt" at 50'
    """
    return f'attribute "{attribute}" at {value}'


def fixture_at(
    fixture_id: int,
    value: int | float | None = None,
    *,
    source_fixture: int | None = None,
    end: int | None = None,
) -> str:
    """
    Set fixture(s) to a value or copy values from another fixture.

    When using value, sets the fixture to that percentage.
    When using source_fixture, copies all values from the source.

    Args:
        fixture_id: Fixture ID to modify
        value: Percentage or value to set
        source_fixture: Source fixture ID to copy values from
        end: End fixture ID for range

    Returns:
        str: MA command to set fixture values

    Examples:
        >>> fixture_at(2, 50)
        'fixture 2 at 50'
        >>> fixture_at(2, source_fixture=3)
        'fixture 2 at fixture 3'
        >>> fixture_at(1, 100, end=10)
        'fixture 1 thru 10 at 100'
    """
    if value is None and source_fixture is None:
        raise ValueError("Must provide either value or source_fixture")

    if end is not None:
        fixture_part = f"fixture {fixture_id} thru {end}"
    else:
        fixture_part = f"fixture {fixture_id}"

    if source_fixture is not None:
        return f"{fixture_part} at fixture {source_fixture}"

    return f"{fixture_part} at {value}"


def channel_at(
    channel_id: int,
    value: int | float | None = None,
    *,
    source_channel: int | None = None,
    end: int | None = None,
) -> str:
    """
    Set channel(s) to a value or copy values from another channel.

    Args:
        channel_id: Channel ID to modify
        value: Percentage or value to set
        source_channel: Source channel ID to copy values from
        end: End channel ID for range

    Returns:
        str: MA command to set channel values

    Examples:
        >>> channel_at(1, 75)
        'channel 1 at 75'
        >>> channel_at(1, source_channel=10)
        'channel 1 at channel 10'
        >>> channel_at(1, 100, end=10)
        'channel 1 thru 10 at 100'
    """
    if value is None and source_channel is None:
        raise ValueError("Must provide either value or source_channel")

    if end is not None:
        channel_part = f"channel {channel_id} thru {end}"
    else:
        channel_part = f"channel {channel_id}"

    if source_channel is not None:
        return f"{channel_part} at channel {source_channel}"

    return f"{channel_part} at {value}"


def group_at(
    group_id: int,
    value: int | float,
) -> str:
    """
    Select group and set to a value.

    Args:
        group_id: Group ID
        value: Percentage or value to set

    Returns:
        str: MA command to set group value

    Example:
        >>> group_at(3, 50)
        'group 3 at 50'
    """
    return f"group {group_id} at {value}"


def executor_at(
    executor_id: int,
    value: int | float,
    *,
    page: int | None = None,
) -> str:
    """
    Set executor fader to a value.

    Args:
        executor_id: Executor ID
        value: Fader value (0-100)
        page: Page number for page-qualified addressing (optional)

    Returns:
        str: MA command to set executor fader

    Examples:
        >>> executor_at(3, 50)
        'executor 3 at 50'
        >>> executor_at(5, 100, page=2)
        'executor 2.5 at 100'
    """
    ref = f"{page}.{executor_id}" if page is not None else str(executor_id)
    return f"executor {ref} at {value}"


def preset_type_at(
    start_type: int,
    value: int | float,
    *,
    end_type: int | None = None,
    fade: float | None = None,
    delay: float | None = None,
) -> str:
    """
    Apply value/time to preset type range.

    Args:
        start_type: Start preset type ID
        value: Value to apply (or time if fade/delay specified)
        end_type: End preset type ID for range
        fade: If set, apply as fade time
        delay: If set, apply as delay time

    Returns:
        str: MA command for preset type at

    Examples:
        >>> preset_type_at(2, 50, end_type=9)
        'presettype 2 thru 9 at 50'
        >>> preset_type_at(2, 2, end_type=9, delay=2.0)
        'presettype 2 thru 9 at delay 2.0'
    """
    if end_type is not None:
        type_part = f"presettype {start_type} thru {end_type}"
    else:
        type_part = f"presettype {start_type}"

    if fade is not None:
        return f"{type_part} at fade {fade}"
    elif delay is not None:
        return f"{type_part} at delay {delay}"

    return f"{type_part} at {value}"

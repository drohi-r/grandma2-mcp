"""
Time Object Keywords for grandMA2 Command Builder

Contains Object Keywords related to time:
- timecode: Reference timecode shows
- timecode_slot: Reference timecode slots
- timer: Reference timers

These object types are used for time-related control and synchronization.
"""



def timecode(
    timecode_id: int | list[int] | None = None,
    *,
    end: int | None = None,
    slot: int | None = None,
    select_all: bool = False,
) -> str:
    """
    Construct a Timecode command to reference timecode shows.

    Timecode is an object type used for timecode synchronization.
    You can use timecode.slot syntax to specify a specific slot.

    Args:
        timecode_id: Timecode show number or list of numbers
        end: End number (for range selection)
        slot: Timecode slot number (for timecode.slot syntax)
        select_all: If True, select all timecodes (timecode thru)

    Returns:
        str: MA command string to reference timecodes

    Raises:
        ValueError: When timecode_id is not provided and select_all is False
        ValueError: When slot is used with multiple timecodes
        ValueError: When end is used with a list

    Examples:
        >>> timecode(1)
        'timecode 1'
        >>> timecode(1, end=3)
        'timecode 1 thru 3'
        >>> timecode([1, 2, 3])
        'timecode 1 + 2 + 3'
        >>> timecode(1, slot=2)
        'timecode 1.2'
        >>> timecode(select_all=True)
        'timecode thru'
    """
    # Handle select_all
    if select_all:
        return "timecode thru"

    if timecode_id is None:
        raise ValueError("Must provide timecode_id")

    # Handle slot syntax (timecode.slot)
    if slot is not None:
        if isinstance(timecode_id, list):
            raise ValueError("Cannot use slot with multiple timecodes")
        return f"timecode {timecode_id}.{slot}"

    # Handle list selection (using + separator)
    if isinstance(timecode_id, list):
        # Validation: cannot use list and end together
        if end is not None:
            raise ValueError("Cannot use 'end' with list")
        if len(timecode_id) == 1:
            return f"timecode {timecode_id[0]}"
        tcs_str = " + ".join(str(tid) for tid in timecode_id)
        return f"timecode {tcs_str}"

    # Handle range selection (using thru)
    if end is not None:
        if timecode_id == end:
            return f"timecode {timecode_id}"
        return f"timecode {timecode_id} thru {end}"

    # Single selection
    return f"timecode {timecode_id}"


def timecode_slot(
    slot_id: int | list[int] | None = None,
    *,
    end: int | None = None,
) -> str:
    """
    Construct a TimecodeSlot command to reference timecode slots.

    TimecodeSlot represents 8 different possible timecode streams.

    Args:
        slot_id: Slot number or list of slot numbers
        end: End slot number (for range selection)

    Returns:
        str: MA command string to reference timecode slots

    Raises:
        ValueError: When slot_id is not provided

    Examples:
        >>> timecode_slot(3)
        'timecodeslot 3'
        >>> timecode_slot(1, end=4)
        'timecodeslot 1 thru 4'
        >>> timecode_slot([1, 3, 5])
        'timecodeslot 1 + 3 + 5'
    """
    if slot_id is None:
        raise ValueError("Must provide slot_id")

    # Handle list selection (using + separator)
    if isinstance(slot_id, list):
        if len(slot_id) == 1:
            return f"timecodeslot {slot_id[0]}"
        slots_str = " + ".join(str(sid) for sid in slot_id)
        return f"timecodeslot {slots_str}"

    # Handle range selection (using thru)
    if end is not None:
        if slot_id == end:
            return f"timecodeslot {slot_id}"
        return f"timecodeslot {slot_id} thru {end}"

    # Single selection
    return f"timecodeslot {slot_id}"


def timer(
    timer_id: int | list[int] | None = None,
    *,
    end: int | None = None,
    select_all: bool = False,
) -> str:
    """
    Construct a Timer command to reference timers.

    Timer is an object type used for timer functionality.

    Args:
        timer_id: Timer number or list of timer numbers
        end: End timer number (for range selection)
        select_all: If True, select all timers (timer thru)

    Returns:
        str: MA command string to reference timers

    Raises:
        ValueError: When timer_id is not provided and select_all is False
        ValueError: When end is used with a list

    Examples:
        >>> timer(1)
        'timer 1'
        >>> timer(1, end=3)
        'timer 1 thru 3'
        >>> timer([1, 2, 3])
        'timer 1 + 2 + 3'
        >>> timer(select_all=True)
        'timer thru'
    """
    # Handle select_all
    if select_all:
        return "timer thru"

    if timer_id is None:
        raise ValueError("Must provide timer_id")

    # Handle list selection (using + separator)
    if isinstance(timer_id, list):
        # Validation: cannot use list and end together
        if end is not None:
            raise ValueError("Cannot use 'end' with list")
        if len(timer_id) == 1:
            return f"timer {timer_id[0]}"
        timers_str = " + ".join(str(tid) for tid in timer_id)
        return f"timer {timers_str}"

    # Handle range selection (using thru)
    if end is not None:
        if timer_id == end:
            return f"timer {timer_id}"
        return f"timer {timer_id} thru {end}"

    # Single selection
    return f"timer {timer_id}"

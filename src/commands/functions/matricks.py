"""
MAtricks Command Builder Functions

Pure functions that build grandMA2 MAtricks command strings.
No I/O, no imports from server/navigation/telnet.

Live-validated against grandMA2 onPC v3.9.60.65 (2026-03-11):
All keywords and syntax variants confirmed via telnet.
"""

from __future__ import annotations

from ..helpers import quote_name


def matricks_interleave(
    width: int | None = None,
    column: int | None = None,
    increment: str | None = None,
    off: bool = False,
) -> str:
    """Build a MAtricksInterleave command.

    Args:
        width: Array width (number of columns).
        column: Column to sub-select (requires width). Produces ``col.width``.
        increment: ``"+"`` or ``"-"`` to step value.
        off: Send ``MAtricksInterleave Off``.

    Returns:
        Command string, e.g. ``MAtricksInterleave 2`` or ``MAtricksInterleave 1.4``.
    """
    _check_exclusive(off=off, increment=increment, value=(width is not None or column is not None))
    if column is not None and width is None:
        raise ValueError("column requires width (produces column.width notation)")
    if off:
        return "MAtricksInterleave Off"
    if increment:
        _validate_increment(increment, allow_n=False)
        return f"MAtricksInterleave {increment}"
    if width is not None:
        if column is not None:
            return f"MAtricksInterleave {column}.{width}"
        return f"MAtricksInterleave {width}"
    return "MAtricksInterleave"


def matricks_blocks(
    size: int | None = None,
    x: int | None = None,
    y: int | None = None,
    increment: str | None = None,
    off: bool = False,
) -> str:
    """Build a MAtricksBlocks command.

    Args:
        size: Block size (single-axis shorthand, sets x).
        x: X-axis block size (for ``x.y`` notation, requires y).
        y: Y-axis block size (requires x).
        increment: ``"+ N"`` or ``"- N"`` to adjust by N.
        off: Send ``MAtricksBlocks Off``.

    Returns:
        Command string, e.g. ``MAtricksBlocks 2`` or ``MAtricksBlocks 2.3``.
    """
    _check_exclusive(off=off, increment=increment, value=(size is not None or x is not None))
    if y is not None and x is None:
        raise ValueError("y requires x (produces x.y notation)")
    if size is not None and x is not None:
        raise ValueError("size and x are mutually exclusive (size is shorthand for x)")
    if off:
        return "MAtricksBlocks Off"
    if increment:
        _validate_increment(increment, allow_n=True)
        return f"MAtricksBlocks {increment}"
    if x is not None:
        if y is not None:
            return f"MAtricksBlocks {x}.{y}"
        return f"MAtricksBlocks {x}"
    if size is not None:
        return f"MAtricksBlocks {size}"
    return "MAtricksBlocks"


def matricks_groups(
    size: int | None = None,
    x: int | None = None,
    y: int | None = None,
    increment: str | None = None,
    off: bool = False,
) -> str:
    """Build a MAtricksGroups command.

    Args:
        size: Group size (single-axis shorthand, sets x).
        x: X-axis group size (for ``x.y`` notation, requires y).
        y: Y-axis group size (requires x).
        increment: ``"+ N"`` or ``"- N"`` to adjust by N.
        off: Send ``MAtricksGroups Off``.

    Returns:
        Command string, e.g. ``MAtricksGroups 4`` or ``MAtricksGroups 2.3``.
    """
    _check_exclusive(off=off, increment=increment, value=(size is not None or x is not None))
    if y is not None and x is None:
        raise ValueError("y requires x (produces x.y notation)")
    if size is not None and x is not None:
        raise ValueError("size and x are mutually exclusive (size is shorthand for x)")
    if off:
        return "MAtricksGroups Off"
    if increment:
        _validate_increment(increment, allow_n=True)
        return f"MAtricksGroups {increment}"
    if x is not None:
        if y is not None:
            return f"MAtricksGroups {x}.{y}"
        return f"MAtricksGroups {x}"
    if size is not None:
        return f"MAtricksGroups {size}"
    return "MAtricksGroups"


def matricks_wings(
    parts: int | None = None,
    increment: str | None = None,
    off: bool = False,
) -> str:
    """Build a MAtricksWings command.

    Args:
        parts: Number of wing parts (symmetry divisions).
        increment: ``"+"`` or ``"-"`` to step value.
        off: Send ``MAtricksWings Off``.

    Returns:
        Command string, e.g. ``MAtricksWings 2``.
    """
    _check_exclusive(off=off, increment=increment, value=(parts is not None))
    if off:
        return "MAtricksWings Off"
    if increment:
        _validate_increment(increment, allow_n=False)
        return f"MAtricksWings {increment}"
    if parts is not None:
        return f"MAtricksWings {parts}"
    return "MAtricksWings"


def matricks_filter(
    filter_num: int | None = None,
    name: str | None = None,
    increment: str | None = None,
    off: bool = False,
) -> str:
    """Build a MAtricksFilter command.

    Args:
        filter_num: Filter number (numeric ID).
        name: Filter name (e.g. ``"OddID"``). Quoted via ``quote_name()``.
        increment: ``"+"`` or ``"-"`` to step through filters.
        off: Send ``MAtricksFilter Off``.

    Returns:
        Command string, e.g. ``MAtricksFilter 1`` or ``MAtricksFilter "OddID"``.
    """
    _check_exclusive(
        off=off, increment=increment,
        value=(filter_num is not None or name is not None),
    )
    if filter_num is not None and name is not None:
        raise ValueError("filter_num and name are mutually exclusive")
    if off:
        return "MAtricksFilter Off"
    if increment:
        _validate_increment(increment, allow_n=False)
        return f"MAtricksFilter {increment}"
    if filter_num is not None:
        return f"MAtricksFilter {filter_num}"
    if name is not None:
        return f"MAtricksFilter {quote_name(name)}"
    return "MAtricksFilter"


def matricks_reset() -> str:
    """Build a MAtricksReset command. Clears all active MAtricks settings."""
    return "MAtricksReset"


def recall_matricks(
    matricks_id: int | None = None,
    mode: str | None = None,
) -> str:
    """Build a MAtricks recall or mode command.

    Args:
        matricks_id: Pool object ID to recall (e.g. ``MAtricks 5``).
        mode: ``"on"``, ``"off"``, or ``"toggle"`` for mode control.

    Returns:
        Command string, e.g. ``MAtricks 5`` or ``MAtricks On``.
    """
    if matricks_id is not None and mode is not None:
        raise ValueError("matricks_id and mode are mutually exclusive")
    if matricks_id is not None:
        return f"MAtricks {matricks_id}"
    if mode is not None:
        valid = {"on", "off", "toggle"}
        if mode.lower() not in valid:
            raise ValueError(f"mode must be one of {valid}, got {mode!r}")
        # Capitalize first letter for MA2 syntax
        return f"MAtricks {mode.capitalize()}"
    return "MAtricks"


def all_sub_selection() -> str:
    """Build an All command. Resets MAtricks Single X sub-selection."""
    return "All"


def all_rows_sub_selection() -> str:
    """Build an AllRows command. Resets MAtricks Single Y sub-selection."""
    return "AllRows"


def next_sub_selection() -> str:
    """Build a Next command. Steps forward through MAtricks Single X sub-selection."""
    return "Next"


def previous_sub_selection() -> str:
    """Build a Previous command. Steps backward through MAtricks Single X sub-selection."""
    return "Previous"


def next_row_sub_selection() -> str:
    """Build a NextRow command. Steps forward through MAtricks Single Y (row) sub-selection."""
    return "NextRow"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _check_exclusive(
    off: bool,
    increment: str | None,
    value: bool,
) -> None:
    """Raise ValueError if multiple mutually exclusive modes are set."""
    count = sum([off, increment is not None, value])
    if count > 1:
        raise ValueError(
            "off, increment, and value/size parameters are mutually exclusive"
        )


def _validate_increment(increment: str, *, allow_n: bool) -> None:
    """Validate increment string format.

    Args:
        increment: The increment string to validate.
        allow_n: If True, allows ``"+ N"`` / ``"- N"`` format.
                 If False, only ``"+"`` / ``"-"`` are valid.
    """
    stripped = increment.strip()
    if stripped in ("+", "-"):
        return
    if allow_n:
        # Allow "+ N" or "- N" where N is a positive integer
        parts = stripped.split()
        if len(parts) == 2 and parts[0] in ("+", "-"):
            try:
                int(parts[1])
                return
            except ValueError:
                pass
    valid = '"+" or "-"' if not allow_n else '"+" or "-" or "+ N" or "- N"'
    raise ValueError(f"increment must be {valid}, got {increment!r}")

"""
Group/Selection Object Keywords for grandMA2 Command Builder

Contains Object Keywords related to groups and selections:
- group: Select fixture groups

Group is an object type that contains a collection of fixtures and selection order.
"""



def group(
    group_id: int | list[int] | None = None,
    end: int | None = None,
) -> str:
    """
    Construct a Group command to select groups.

    Group is an object type that contains a collection of fixtures and selection order.
    The default function is SelFix.

    Args:
        group_id: Group number or list of group numbers
        end: End group number for range selection

    Returns:
        str: MA command string for selecting groups

    Examples:
        >>> group(3)
        'group 3'
        >>> group(1, end=5)
        'group 1 thru 5'
        >>> group([1, 3, 5])
        'group 1 + 3 + 5'
    """
    if group_id is None:
        raise ValueError("Must provide group_id")

    if isinstance(group_id, list):
        if len(group_id) == 1:
            return f"group {group_id[0]}"
        groups_str = " + ".join(str(g) for g in group_id)
        return f"group {groups_str}"

    if end is not None:
        if group_id == end:
            return f"group {group_id}"
        return f"group {group_id} thru {end}"

    return f"group {group_id}"

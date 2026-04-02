"""
Helping Keywords for grandMA2 Command Builder

This module contains Plus (+) and Minus (-) helping keywords.
These keywords have various functions including:
- Combining or removing objects from lists
- Indicating relative values (positive or negative)
- Adding or removing objects from current selection
- Page navigation (next/previous)

Included functions:
- at_relative: Apply relative value change to current selection
- add_to_selection: Add objects to current selection using Plus (+)
- remove_from_selection: Remove objects from current selection using Minus (-)
- page_next: Navigate to next page
- page_previous: Navigate to previous page
"""



def at_relative(value: int | float) -> str:
    """
    Construct an At command with a relative value change.

    When using Plus (+) or Minus (-) with a space before the value,
    it indicates a relative change rather than an absolute value.
    For example:
    - "at + 10" adds 10% to the current dimmer value
    - "at - 10" subtracts 10% from the current dimmer value

    Note: Without the space, "-10" would be an absolute value (e.g., -10 degrees for Pan).

    Args:
        value: Relative value to add (positive) or subtract (negative).
               Cannot be zero.

    Returns:
        str: MA command for relative value change

    Raises:
        ValueError: If value is zero

    Examples:
        >>> at_relative(5)
        'at + 5'
        >>> at_relative(-10)
        'at - 10'
        >>> at_relative(5.5)
        'at + 5.5'
    """
    if value == 0:
        raise ValueError("Relative value cannot be zero")

    if value > 0:
        return f"at + {value}"
    else:
        # Use absolute value for display, the minus sign is the operator
        return f"at - {abs(value)}"


def add_to_selection(
    ids: int | list[int],
    *,
    end: int | None = None,
) -> str:
    """
    Construct a command to add objects to the current selection using Plus (+).

    When Plus (+) is used as a starting keyword, it creates a selection list
    that will be added to the current selection.

    Args:
        ids: Object ID(s) to add - single int or list of ints
        end: End ID for range selection (used with Thru)

    Returns:
        str: MA command to add to selection

    Examples:
        >>> add_to_selection(5)
        '+ 5'
        >>> add_to_selection(5, end=7)
        '+ 5 thru 7'
        >>> add_to_selection([1, 3, 5])
        '+ 1 + 3 + 5'
    """
    # Handle list of IDs
    if isinstance(ids, list):
        ids_str = " + ".join(str(i) for i in ids)
        return f"+ {ids_str}"

    # Handle range selection
    if end is not None:
        return f"+ {ids} thru {end}"

    # Handle single ID
    return f"+ {ids}"


def remove_from_selection(
    ids: int | list[int],
    *,
    end: int | None = None,
) -> str:
    """
    Construct a command to remove objects from the current selection using Minus (-).

    When Minus (-) is used as a starting keyword, it creates a selection list
    that will be removed from the current selection.

    Args:
        ids: Object ID(s) to remove - single int or list of ints
        end: End ID for range selection (used with Thru)

    Returns:
        str: MA command to remove from selection

    Examples:
        >>> remove_from_selection(5)
        '- 5'
        >>> remove_from_selection(5, end=7)
        '- 5 thru 7'
        >>> remove_from_selection([1, 3, 5])
        '- 1 - 3 - 5'
    """
    # Handle list of IDs
    if isinstance(ids, list):
        ids_str = " - ".join(str(i) for i in ids)
        return f"- {ids_str}"

    # Handle range selection
    if end is not None:
        return f"- {ids} thru {end}"

    # Handle single ID
    return f"- {ids}"


def page_next(steps: int | None = None) -> str:
    """
    Construct a command to navigate to the next page.

    When used without a value, "Page +" is equivalent to "Page + 1".
    Using the numeric keys automatically adds the space.

    Args:
        steps: Number of pages to advance. If None, uses default (1 page).

    Returns:
        str: MA command for page navigation

    Examples:
        >>> page_next()
        'page +'
        >>> page_next(3)
        'page + 3'
    """
    if steps is None:
        return "page +"
    return f"page + {steps}"


def page_previous(steps: int | None = None) -> str:
    """
    Construct a command to navigate to the previous page.

    When used without a value, "Page -" is equivalent to "Page - 1".
    Using the numeric keys automatically adds the space.

    Args:
        steps: Number of pages to go back. If None, uses default (1 page).

    Returns:
        str: MA command for page navigation

    Examples:
        >>> page_previous()
        'page -'
        >>> page_previous(3)
        'page - 3'
    """
    if steps is None:
        return "page -"
    return f"page - {steps}"


def condition_and(*conditions: str) -> str:
    """
    Combine multiple conditions using the And keyword.

    The And keyword is a helping keyword that adds selection or values.
    It is commonly used with the If keyword to combine multiple filter conditions.

    Args:
        *conditions: Variable number of condition strings to combine

    Returns:
        str: Conditions joined by " and "

    Raises:
        ValueError: If no conditions are provided

    Examples:
        >>> condition_and('fixture 5 attribute "pan"', 'fixture 5 attribute "tilt"')
        'fixture 5 attribute "pan" and fixture 5 attribute "tilt"'
        >>> condition_and('fixture 5 attribute "pan"')
        'fixture 5 attribute "pan"'
    """
    if not conditions:
        raise ValueError("At least one condition is required")

    return " and ".join(conditions)


def if_condition(*conditions: str) -> str:
    """
    Construct an If condition clause with optional And conditions.

    The If keyword is used to filter commands based on conditions.
    Multiple conditions can be combined using And.

    Syntax: If [Condition] And [Condition] And [Condition] ...

    Args:
        *conditions: Variable number of condition strings.
                    First condition follows If, rest are joined with And.

    Returns:
        str: If condition clause (e.g., "if fixture 5 attribute \"pan\"")

    Raises:
        ValueError: If no conditions are provided

    Examples:
        >>> if_condition('fixture 5 attribute "pan"')
        'if fixture 5 attribute "pan"'
        >>> if_condition('fixture 5 attribute "pan"', 'fixture 5 attribute "tilt"')
        'if fixture 5 attribute "pan" and fixture 5 attribute "tilt"'
    """
    if not conditions:
        raise ValueError("At least one condition is required")

    combined = condition_and(*conditions)
    return f"if {combined}"

"""
Park and Unpark Keywords for grandMA2 Command Builder

This module contains Park and Unpark function keywords.

Park:
- Locks DMX output values of attributes
- Can lock fixture selection, attributes, or DMX channels
- Optional value parameter with At keyword
- Parked DMX channels are indicated by a blue marker

Unpark:
- Unlocks previously parked DMX channels
- Can unpark fixture selection, attributes, or DMX channels

Included functions:
- park: Lock DMX output values
- unpark: Unlock previously parked DMX channels
"""



def park(
    target: str | None = None,
    *,
    at: int | float | None = None,
) -> str:
    """
    Construct a Park command to lock DMX output values.

    Park locks DMX output values of attributes. You can lock values of
    a fixture selection, group of attributes, or DMX channels.
    If no value is given, the attribute is parked at current value.

    Note: Press Pause twice on the console to get Park keyword.

    Args:
        target: Object to park (e.g., "fixture 5", "attribute \"pan\"", "dmx 1.2").
                If None, parks current selection.
        at: Optional value to park at (e.g., 100 for 100%, 255 for DMX value)

    Returns:
        str: MA command to park values

    Examples:
        >>> park("fixture 5")
        'park fixture 5'
        >>> park('attribute "pan"')
        'park attribute "pan"'
        >>> park("channel 1 thru 5", at=100)
        'park channel 1 thru 5 at 100'
        >>> park("dmx 1.2")
        'park dmx 1.2'
        >>> park()
        'park'
        >>> park(at=100)
        'park at 100'
    """
    parts = ["park"]

    if target:
        parts.append(target)

    if at is not None:
        parts.append(f"at {at}")

    return " ".join(parts)


def unpark(target: str | None = None) -> str:
    """
    Construct an Unpark command to unlock previously parked DMX channels.

    Unpark releases the lock on DMX channels that were previously parked.
    Parked channels are displayed with a blue indicator.

    Note: Press small Go+ twice on the console to get Unpark keyword.
          Shortcut: Unp

    Args:
        target: Object to unpark (e.g., "fixture 2", "dmx 1.1 thru 1.10").
                If None, unparks current selection.

    Returns:
        str: MA command to unpark values

    Examples:
        >>> unpark("fixture 2")
        'unpark fixture 2'
        >>> unpark("dmx 1.1 thru 1.10")
        'unpark dmx 1.1 thru 1.10'
        >>> unpark("dmxuniverse thru")
        'unpark dmxuniverse thru'
        >>> unpark("presettype dimmer")
        'unpark presettype dimmer'
        >>> unpark()
        'unpark'
    """
    if target:
        return f"unpark {target}"
    return "unpark"


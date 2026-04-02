"""
DMX Object Keywords for grandMA2 Command Builder

Contains Object Keywords related to DMX:
- dmx: Reference DMX addresses
- dmx_universe: Reference DMX universes

DMX is an object type used to directly control DMX output.
"""



def dmx(
    address: int | list[int] | None = None,
    *,
    end: int | None = None,
    universe: int | None = None,
    select_all: bool = False,
) -> str:
    """
    Construct a DMX command to reference DMX addresses.

    DMX is an object type used to directly control DMX output.
    DMX addresses can be specified using universe.address syntax.

    Args:
        address: DMX address (1-512) or list of addresses
        end: End address (for range selection)
        universe: DMX universe number (for universe.address syntax)
        select_all: If True, select all DMX addresses (dmx thru)

    Returns:
        str: MA command string to reference DMX addresses

    Raises:
        ValueError: When address is not provided and select_all is False

    Examples:
        >>> dmx(100)
        'dmx 100'
        >>> dmx(1, end=10)
        'dmx 1 thru 10'
        >>> dmx([1, 5, 10])
        'dmx 1 + 5 + 10'
        >>> dmx(100, universe=2)
        'dmx 2.100'
        >>> dmx(1, end=10, universe=2)
        'dmx 2.1 thru 10'
        >>> dmx([1, 5, 10], universe=2)
        'dmx 2.1 + 2.5 + 2.10'
        >>> dmx(select_all=True)
        'dmx thru'
    """
    # Handle select_all
    if select_all:
        return "dmx thru"

    if address is None:
        raise ValueError("Must provide address")

    # Handle universe syntax (universe.address)
    if universe is not None:
        # Handle list selection (using + separator)
        if isinstance(address, list):
            if len(address) == 1:
                return f"dmx {universe}.{address[0]}"
            addrs_str = " + ".join(f"{universe}.{addr}" for addr in address)
            return f"dmx {addrs_str}"

        # Handle range selection (using thru)
        if end is not None:
            if address == end:
                return f"dmx {universe}.{address}"
            return f"dmx {universe}.{address} thru {end}"

        # Single selection
        return f"dmx {universe}.{address}"

    # Handle list selection (using + separator)
    if isinstance(address, list):
        if len(address) == 1:
            return f"dmx {address[0]}"
        addrs_str = " + ".join(str(addr) for addr in address)
        return f"dmx {addrs_str}"

    # Handle range selection (using thru)
    if end is not None:
        if address == end:
            return f"dmx {address}"
        return f"dmx {address} thru {end}"

    # Single selection
    return f"dmx {address}"


def dmx_universe(
    universe_id: int | list[int] | None = None,
    *,
    end: int | None = None,
) -> str:
    """
    Construct a DmxUniverse command to reference DMX universes.

    DmxUniverse is an object type used to reference entire DMX universes.

    Args:
        universe_id: Universe number or list of universe numbers
        end: End universe number (for range selection)

    Returns:
        str: MA command string to reference DMX universes

    Raises:
        ValueError: When universe_id is not provided

    Examples:
        >>> dmx_universe(1)
        'dmxuniverse 1'
        >>> dmx_universe(1, end=4)
        'dmxuniverse 1 thru 4'
        >>> dmx_universe([1, 3, 5])
        'dmxuniverse 1 + 3 + 5'
    """
    if universe_id is None:
        raise ValueError("Must provide universe_id")

    # Handle list selection (using + separator)
    if isinstance(universe_id, list):
        if len(universe_id) == 1:
            return f"dmxuniverse {universe_id[0]}"
        univs_str = " + ".join(str(uid) for uid in universe_id)
        return f"dmxuniverse {univs_str}"

    # Handle range selection (using thru)
    if end is not None:
        if universe_id == end:
            return f"dmxuniverse {universe_id}"
        return f"dmxuniverse {universe_id} thru {end}"

    # Single selection
    return f"dmxuniverse {universe_id}"

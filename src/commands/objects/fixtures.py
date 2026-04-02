"""
Fixture/Channel Object Keywords for grandMA2 Command Builder

Contains Object Keywords related to fixtures and channels:
- fixture: Access fixtures using Fixture ID
- channel: Access fixtures using Channel ID

These are the most basic object types in grandMA2, used for selecting and controlling fixtures.
"""



def fixture(
    fixture_id: int | list[int] | None = None,
    end: int | None = None,
    *,
    sub_id: int | None = None,
    select_all: bool = False,
) -> str:
    """
    Construct a Fixture command to access fixtures using Fixture ID.

    Fixture is an object keyword for accessing fixtures using fixture ID.
    The default function is SelFix, meaning entering fixtures without specifying
    a function will select them.

    Args:
        fixture_id: Fixture number or list of fixture numbers
        end: End fixture number for range selection
        sub_id: Sub-fixture ID (e.g., fixture 11.5 means the 5th sub-fixture)
        select_all: If True, select all fixtures (fixture thru)

    Returns:
        str: MA command string for selecting fixtures

    Examples:
        >>> fixture(34)
        'fixture 34'
        >>> fixture(11, sub_id=5)
        'fixture 11.5'
        >>> fixture(1, end=10)
        'fixture 1 thru 10'
        >>> fixture([1, 5, 10])
        'fixture 1 + 5 + 10'
        >>> fixture(select_all=True)
        'fixture thru'
    """
    if select_all:
        return "fixture thru"

    if fixture_id is None:
        raise ValueError("Must provide fixture_id or set select_all=True")

    if isinstance(fixture_id, list):
        if len(fixture_id) == 1:
            return f"fixture {fixture_id[0]}"
        fixtures_str = " + ".join(str(f) for f in fixture_id)
        return f"fixture {fixtures_str}"

    if sub_id is not None:
        return f"fixture {fixture_id}.{sub_id}"

    if end is not None:
        if fixture_id == end:
            return f"fixture {fixture_id}"
        return f"fixture {fixture_id} thru {end}"

    return f"fixture {fixture_id}"


def channel(
    channel_id: int | list[int] | None = None,
    end: int | None = None,
    *,
    sub_id: int | None = None,
    select_all: bool = False,
) -> str:
    """
    Construct a Channel command to access fixtures using Channel ID.

    Channel is an object type for accessing fixtures using Channel ID.
    The default function is SelFix.

    Args:
        channel_id: Channel number or list of channel numbers
        end: End channel number for range selection
        sub_id: Sub-fixture ID
        select_all: If True, select all channels (channel thru)

    Returns:
        str: MA command string for selecting channels

    Examples:
        >>> channel(34)
        'channel 34'
        >>> channel(11, sub_id=5)
        'channel 11.5'
        >>> channel(1, end=10)
        'channel 1 thru 10'
    """
    if select_all:
        return "channel thru"

    if channel_id is None:
        raise ValueError("Must provide channel_id or set select_all=True")

    if isinstance(channel_id, list):
        if len(channel_id) == 1:
            return f"channel {channel_id[0]}"
        channels_str = " + ".join(str(c) for c in channel_id)
        return f"channel {channels_str}"

    if sub_id is not None:
        return f"channel {channel_id}.{sub_id}"

    if end is not None:
        return f"channel {channel_id} thru {end}"

    return f"channel {channel_id}"

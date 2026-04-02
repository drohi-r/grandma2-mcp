"""
Store Function Keywords for grandMA2 Command Builder

Store is used to save the programmer or current state to a specified object.
This is one of the most commonly used function keywords in grandMA2.

Included functions:
- store: Generic store command
- store_cue: Store cue
- store_group: Store group
- store_preset: Store preset
"""

from typing import Any

from ..constants import PRESET_TYPES
from ..helpers import _build_store_options


def store(
    object_type: str,
    object_id: int | str,
    name: str | None = None,
    **options: Any,
) -> str:
    """
    Construct a generic store command for any object type.

    Args:
        object_type: The type of object to store (e.g., "macro", "effect")
        object_id: The ID or identifier of the object
        name: Optional name for the stored object
        **options: Store options (merge, overwrite, noconfirm, etc.)

    Returns:
        str: MA command to store the object

    Examples:
        >>> store("macro", 5)
        'store macro 5'
        >>> store("macro", 5, name="Reset All")
        'store macro 5 "Reset All"'
    """
    cmd = f"store {object_type} {object_id}"

    if name:
        cmd += f' "{name}"'

    cmd += _build_store_options(**options)

    return cmd


def store_cue(
    cue_id: int | None = None,
    end: int | None = None,
    *,
    sequence_id: int | None = None,
    ranges: list[tuple[int, int]] | None = None,
    name: str | None = None,
    merge: bool = False,
    overwrite: bool = False,
    remove: bool = False,
    noconfirm: bool = False,
    quiet: bool = False,
    trackingshield: bool = False,
    cueonly: bool | None = None,
    tracking: bool | None = None,
    keepactive: bool | None = None,
    addnewcontent: bool | None = None,
    originalcontent: bool | None = None,
    effects: bool | None = None,
    values: bool | None = None,
    valuetimes: bool | None = None,
    source: str | None = None,
    useselection: str | None = None,
) -> str:
    """
    Construct a store cue command with full option support.

    Args:
        cue_id: The cue number to store
        end: End cue number for range (cue_id thru end)
        sequence_id: Target sequence number (appends ``sequence N`` to command)
        ranges: List of (start, end) tuples for multiple ranges
        name: Optional name for the cue
        merge: Merge new values into existing
        overwrite: Remove stored values and store new values
        remove: Remove stored values for attributes with active values
        noconfirm: Suppress store confirmation pop-up
        quiet: Suppress command feedback in the command line response area
        trackingshield: Use tracking shield for store
        cueonly: Prevent changes to track forward (True/False)
        tracking: Store with tracking
        keepactive: Keep values active after store
        addnewcontent: Add new content
        originalcontent: Store original content
        effects: Filter or enable effect layer
        values: Filter or enable value layer
        valuetimes: Filter or enable value times layer
        source: Data source (Prog, Output, DmxIn)
        useselection: Selection mode

    Returns:
        str: MA command to store cue(s)

    Examples:
        >>> store_cue(7)
        'store cue 7'
        >>> store_cue(1, end=10)
        'store cue 1 thru 10'
        >>> store_cue(ranges=[(1, 10), (20, 30)])
        'store cue 1 thru 10 + 20 thru 30'
        >>> store_cue(5, sequence_id=99)
        'store cue 5 sequence 99'
    """
    if ranges:
        range_parts = [f"{start} thru {end}" for start, end in ranges]
        cue_part = " + ".join(range_parts)
    elif cue_id is not None and end is not None:
        cue_part = f"{cue_id} thru {end}"
    elif cue_id is not None:
        cue_part = str(cue_id)
    else:
        raise ValueError("Must provide cue_id or ranges")

    cmd = f"store cue {cue_part}"

    if sequence_id is not None:
        cmd += f" sequence {sequence_id}"

    if name:
        cmd += f' "{name}"'

    cmd += _build_store_options(
        merge=merge,
        overwrite=overwrite,
        remove=remove,
        noconfirm=noconfirm,
        quiet=quiet,
        trackingshield=trackingshield,
        cueonly=cueonly,
        tracking=tracking,
        keepactive=keepactive,
        addnewcontent=addnewcontent,
        originalcontent=originalcontent,
        effects=effects,
        values=values,
        valuetimes=valuetimes,
        source=source,
        useselection=useselection,
    )

    return cmd


def update_cue(
    cue_id: int | float | None = None,
    *,
    sequence_id: int | None = None,
    merge: bool = False,
    overwrite: bool = False,
    cueonly: bool | None = None,
) -> str:
    """
    Construct an Update command to update a cue with programmer values.

    Args:
        cue_id: Cue number to update (optional; omits for current active cue)
        sequence_id: Sequence ID (optional scoping)
        merge: Merge programmer into existing cue values
        overwrite: Overwrite cue with programmer values
        cueonly: Prevent changes from tracking forward

    Returns:
        str: MA command to update a cue

    Examples:
        >>> update_cue()
        'update'
        >>> update_cue(5, merge=True)
        'update cue 5 /merge'
        >>> update_cue(3, sequence_id=1, overwrite=True)
        'update cue 3 sequence 1 /overwrite'
    """
    if cue_id is not None:
        cmd = f"update cue {cue_id}"
        if sequence_id is not None:
            cmd += f" sequence {sequence_id}"
    else:
        cmd = "update"

    options = []
    if merge:
        options.append("/merge")
    if overwrite:
        options.append("/overwrite")
    if cueonly is True:
        options.append("/cueonly=true")
    elif cueonly is False:
        options.append("/cueonly=false")

    if options:
        cmd += " " + " ".join(options)

    return cmd


def store_cue_timed(
    cue_id: int,
    *,
    name: str | None = None,
    fade_time: float | None = None,
    out_time: float | None = None,
    merge: bool = False,
    overwrite: bool = False,
) -> str:
    """
    Construct a store cue command with inline time parameters.

    MA2 syntax: store cue N [time T] [outtime T2] [/merge]

    Examples:
        >>> store_cue_timed(2, fade_time=15)
        'store cue 2 time 15'
        >>> store_cue_timed(3, name="Scene", fade_time=20, out_time=10, merge=True)
        'store cue 3 "Scene" time 20 outtime 10 /merge'
    """
    cmd = f"store cue {cue_id}"
    if name:
        cmd += f' "{name}"'
    if fade_time is not None:
        cmd += f" time {fade_time}"
    if out_time is not None:
        cmd += f" outtime {out_time}"
    options = []
    if merge:
        options.append("/merge")
    if overwrite:
        options.append("/overwrite")
    if options:
        cmd += " " + " ".join(options)
    return cmd


def load_show(name: str) -> str:
    """
    Construct a LoadShow command to load an existing show file.

    Args:
        name: Show file name

    Returns:
        str: MA command to load a show

    Examples:
        >>> load_show("my_show")
        'loadshow "my_show"'
    """
    return f'loadshow "{name}"'


def new_show(
    name: str,
    *,
    noconfirm: bool = False,
    keep_timeconfig: bool = False,
    keep_globalsettings: bool = False,
    keep_localsettings: bool = False,
    keep_protocols: bool = False,
    keep_network: bool = False,
    keep_user: bool = False,
) -> str:
    """
    Construct a NewShow command to create a new empty show.

    By default all show data and configuration is cleared.  Pass the
    ``keep_*`` flags to preserve specific sections from the current show —
    each flag corresponds to un-checking the matching "Clear …" checkbox
    in the grandMA2 New Show dialog.

    Args:
        name: New show file name
        noconfirm: Suppress the save-existing-show dialog (required when
            an existing show is loaded — stateless telnet cannot answer
            the [1]/2/3 prompt).
        keep_timeconfig: Preserve Time Config (→ /timeconfig)
        keep_globalsettings: Preserve Global Settings (→ /globalsettings)
        keep_localsettings: Preserve Local Settings (→ /localsettings)
        keep_protocols: Preserve Network Protocols (→ /protocols)
        keep_network: Preserve Network Config (→ /network)
        keep_user: Preserve User Profiles (→ /user)

    Returns:
        str: MA command to create a new show

    Examples:
        >>> new_show("my_new_show")
        'newshow "my_new_show"'
        >>> new_show("my_new_show", noconfirm=True)
        'newshow "my_new_show" /noconfirm'
        >>> new_show("my_new_show", noconfirm=True, keep_timeconfig=True, keep_network=True)
        'newshow "my_new_show" /noconfirm /timeconfig /network'
    """
    cmd = f'newshow "{name}"'
    if noconfirm:
        cmd += " /noconfirm"
    if keep_timeconfig:
        cmd += " /timeconfig"
    if keep_globalsettings:
        cmd += " /globalsettings"
    if keep_localsettings:
        cmd += " /localsettings"
    if keep_protocols:
        cmd += " /protocols"
    if keep_network:
        cmd += " /network"
    if keep_user:
        cmd += " /user"
    return cmd


def save_show(name: str | None = None) -> str:
    """
    Construct a SaveShow command to save the current show to disk.

    SaveShow is universal — accepted by all object types (live-verified).
    When called bare it saves the current show using its existing name.
    When a name is provided it saves to a new file.

    Args:
        name: Show file name (optional — omit to save current show in place)

    Returns:
        str: MA command to save the show

    Examples:
        >>> save_show()
        'saveshow'
        >>> save_show("my_show")
        'saveshow "my_show"'
    """
    if name is not None:
        return f'saveshow "{name}"'
    return "saveshow"


def delete_show(name: str, *, noconfirm: bool = False) -> str:
    """
    Construct a DeleteShow command to delete a show file from disk.

    Args:
        name: Show file name to delete
        noconfirm: Suppress the confirmation dialog

    Returns:
        str: MA command to delete a show file

    Examples:
        >>> delete_show("old_show")
        'deleteshow "old_show"'
        >>> delete_show("old_show", noconfirm=True)
        'deleteshow "old_show" /noconfirm'
    """
    cmd = f'deleteshow "{name}"'
    if noconfirm:
        cmd += " /noconfirm"
    return cmd


def update(
    object_type: str,
    object_id: int | str,
    *,
    merge: bool = False,
    overwrite: bool = False,
    cueonly: bool | None = None,
) -> str:
    """
    Construct a generic Update command for any object type.

    Update is universal — accepted by all 16 object types (live-verified).
    Use ``update_cue()`` for the richer cue-specific variant with sequence scoping.

    Args:
        object_type: Object type (group, preset, sequence, macro, etc.)
        object_id: Object ID
        merge: Merge programmer into existing values
        overwrite: Overwrite existing values
        cueonly: Prevent changes from tracking forward

    Returns:
        str: MA command to update an object

    Examples:
        >>> update("group", 3)
        'update group 3'
        >>> update("preset", "1.5", merge=True)
        'update preset 1.5 /merge'
        >>> update("sequence", 99, overwrite=True)
        'update sequence 99 /overwrite'
    """
    cmd = f"update {object_type} {object_id}"
    options = []
    if merge:
        options.append("/merge")
    if overwrite:
        options.append("/overwrite")
    if cueonly is True:
        options.append("/cueonly=true")
    elif cueonly is False:
        options.append("/cueonly=false")
    if options:
        cmd += " " + " ".join(options)
    return cmd


def store_group(group_id: int) -> str:
    """
    Construct a command to store a group.

    Args:
        group_id: Group number

    Returns:
        str: MA command to store a group
    """
    return f"store group {group_id}"


def store_matricks(
    matricks_id: int,
    *,
    overwrite: bool = False,
    noconfirm: bool = False,
) -> str:
    """
    Construct a command to store a MAtricks pool entry.

    Args:
        matricks_id: MAtricks pool slot number
        overwrite: Overwrite existing entry
        noconfirm: Suppress confirmation dialog

    Returns:
        str: MA command to store a MAtricks entry

    Examples:
        >>> store_matricks(5)
        'store matricks 5'
        >>> store_matricks(5, overwrite=True, noconfirm=True)
        'store matricks 5 /overwrite /noconfirm'
    """
    cmd = f"store matricks {matricks_id}"
    if overwrite:
        cmd += " /overwrite"
    if noconfirm:
        cmd += " /noconfirm"
    return cmd


def store_preset(
    preset_type: str,
    preset_id: int,
    *,
    global_scope: bool = False,
    selective: bool = False,
    universal: bool = False,
    auto: bool = False,
    embedded: bool = False,
    noconfirm: bool = False,
    merge: bool = False,
    overwrite: bool = False,
    presetfilter: bool | None = None,
    keepactive: bool | None = None,
    addnewcontent: bool | None = None,
    originalcontent: bool | None = None,
) -> str:
    """
    Construct a command to store a preset with full option support.

    Args:
        preset_type: Preset type (dimmer, position, gobo, color, beam, etc.)
        preset_id: Preset number
        global_scope: Store preset with global values
        selective: Store preset with selective values
        universal: Store preset with universal values
        auto: Store preset values with default preset scope
        embedded: Create embedded preset
        noconfirm: Suppress store confirmation pop-up
        merge: Merge new values into existing
        overwrite: Remove stored values and store new
        presetfilter: Set preset filter on or off
        keepactive: Keep values active
        addnewcontent: Add new content
        originalcontent: Store original content

    Returns:
        str: MA command to store a preset

    Examples:
        >>> store_preset("dimmer", 3)
        'store preset 1.3'
        >>> store_preset("dimmer", 3, global_scope=True)
        'store preset 1.3 /global'
    """
    type_num = PRESET_TYPES.get(preset_type.lower(), 1)
    cmd = f"store preset {type_num}.{preset_id}"

    cmd += _build_store_options(
        **{"global": global_scope},
        selective=selective,
        universal=universal,
        auto=auto,
        embedded=embedded,
        noconfirm=noconfirm,
        merge=merge,
        overwrite=overwrite,
        presetfilter=presetfilter,
        keepactive=keepactive,
        addnewcontent=addnewcontent,
        originalcontent=originalcontent,
    )

    return cmd


# ============================================================================
# STORELOOK FUNCTION KEYWORD
# ============================================================================


def store_look(
    look_id: int | None = None,
    *,
    merge: bool = False,
    overwrite: bool = False,
) -> str:
    """
    Construct a StoreLook command to store the programmer as a temporary look.

    Args:
        look_id: Look pool slot number (optional; stores to next available if omitted)
        merge: Merge new values into existing look
        overwrite: Overwrite existing look

    Returns:
        str: MA command string

    Examples:
        >>> store_look()
        'StoreLook'
        >>> store_look(5)
        'StoreLook 5'
        >>> store_look(3, merge=True)
        'StoreLook 3 /merge'
        >>> store_look(3, overwrite=True)
        'StoreLook 3 /overwrite'
    """
    cmd = "StoreLook"
    if look_id is not None:
        cmd += f" {look_id}"
    if merge:
        cmd += " /merge"
    if overwrite:
        cmd += " /overwrite"
    return cmd

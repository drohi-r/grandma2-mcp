"""
Playback Function Keywords for grandMA2 Command Builder

This module contains functions related to playback control.

Included functions:
- go: Execute next step of object (supports Executor, Macro, Sequence, etc.)
- go_back: Execute previous step of object
- goto: Jump to specified cue
- go_sequence (Go+): Execute sequence (simplified version)
- pause_sequence: Pause sequence
- goto_cue: Jump to specified cue (simplified version)
- go_fast_back (<<<): Fast jump to previous step
- go_fast_forward (>>>): Fast jump to next step
- def_go_back: Previous cue of selected executor
- def_go_forward: Next cue of selected executor
- def_go_pause: Pause selected executor
"""

from typing import Literal

# Cue mode type definition
CueMode = Literal["normal", "assert", "xassert", "release"]


# ============================================================================
# GO FUNCTION KEYWORD
# ============================================================================
# Go is a function keyword to activate the next step of an executing object.
# If the target object has steps, it will go to the next step.
# If the object is step-less, it will start running forward.
# ============================================================================


def go(
    object_type: str | None = None,
    object_id: int | list[int] | None = None,
    *,
    end: int | None = None,
    cue_mode: CueMode | None = None,
    userprofile: str | None = None,
) -> str:
    """
    Construct a Go command to activate the next step of an executing object.

    Go is used to activate the next step of an executing object. If the target object has steps,
    it will jump to the next step. If the object has no steps, it will start running forward.

    Args:
        object_type: Object type (executor, macro, sequence, etc.)
        object_id: Object ID or list of IDs
        end: End ID for range (used for thru)
        cue_mode: Cue mode (normal, assert, xassert, release)
        userprofile: User profile name

    Returns:
        str: MA command string

    Examples:
        >>> go("executor", 3)
        'go executor 3'
        >>> go("macro", 2)
        'go macro 2'
        >>> go("executor", 1, end=5)
        'go executor 1 thru 5'
        >>> go("executor", 3, cue_mode="assert")
        'go executor 3 /cue_mode=assert'
        >>> go("executor", 3, userprofile="Klaus")
        'go executor 3 /userprofile="Klaus"'
    """
    parts = ["go"]

    # Object type and ID
    if object_type:
        parts.append(object_type)
        if object_id is not None:
            if isinstance(object_id, list):
                id_str = " + ".join(str(i) for i in object_id)
                parts.append(id_str)
            else:
                parts.append(str(object_id))
                if end is not None:
                    parts.append(f"thru {end}")

    # Options
    if cue_mode:
        parts.append(f"/cue_mode={cue_mode}")
    if userprofile:
        parts.append(f'/userprofile="{userprofile}"')

    return " ".join(parts)


def go_executor(
    executor_id: int | list[int],
    *,
    end: int | None = None,
    cue_mode: CueMode | None = None,
    userprofile: str | None = None,
) -> str:
    """
    Construct a Go command for an executor.

    Convenience function to execute the next step of a specified executor.

    Args:
        executor_id: Executor ID or list of IDs
        end: End ID for range
        cue_mode: Cue mode
        userprofile: User profile name

    Returns:
        str: MA command string

    Examples:
        >>> go_executor(3)
        'go executor 3'
        >>> go_executor([1, 2, 3])
        'go executor 1 + 2 + 3'
    """
    return go(
        "executor", executor_id, end=end, cue_mode=cue_mode, userprofile=userprofile
    )


def go_macro(macro_id: int) -> str:
    """
    Construct a Go command to start a macro.

    Convenience function to start a specified macro.

    Args:
        macro_id: Macro ID

    Returns:
        str: MA command string

    Examples:
        >>> go_macro(2)
        'go macro 2'
    """
    return go("macro", macro_id)


# ============================================================================
# GOBACK FUNCTION KEYWORD
# ============================================================================
# GoBack is a function keyword to activate the previous step of an object.
# Set the default fade time in Setup -> Show -> Playback & MIB Timing -> GoBack.
# ============================================================================


def go_back(
    object_type: str | None = None,
    object_id: int | list[int] | None = None,
    *,
    end: int | None = None,
    cue_mode: CueMode | None = None,
    userprofile: str | None = None,
) -> str:
    """
    Construct a GoBack command to activate the previous step of an object.

    GoBack is used to activate the previous step of an executing object. If the target object has steps,
    it will jump to the previous step. If the object has no steps, it will start running backward.
    Default fade time can be set in Setup -> Show -> Playback & MIB Timing -> GoBack.

    Args:
        object_type: Object type (executor, sequence, etc.)
        object_id: Object ID or list of IDs
        end: End ID for range (used for thru)
        cue_mode: Cue mode (normal, assert, xassert, release)
        userprofile: User profile name

    Returns:
        str: MA command string

    Examples:
        >>> go_back("executor", 3)
        'goback executor 3'
        >>> go_back("executor", 3, cue_mode="assert")
        'goback executor 3 /cue_mode=assert'
    """
    parts = ["goback"]

    # Object type and ID
    if object_type:
        parts.append(object_type)
        if object_id is not None:
            if isinstance(object_id, list):
                id_str = " + ".join(str(i) for i in object_id)
                parts.append(id_str)
            else:
                parts.append(str(object_id))
                if end is not None:
                    parts.append(f"thru {end}")

    # Options
    if cue_mode:
        parts.append(f"/cue_mode={cue_mode}")
    if userprofile:
        parts.append(f'/userprofile="{userprofile}"')

    return " ".join(parts)


def go_back_executor(
    executor_id: int | list[int],
    *,
    end: int | None = None,
    cue_mode: CueMode | None = None,
    userprofile: str | None = None,
) -> str:
    """
    Construct a GoBack command for an executor.

    Convenience function to execute the previous step of a specified executor.

    Args:
        executor_id: Executor ID or list of IDs
        end: End ID for range
        cue_mode: Cue mode
        userprofile: User profile name

    Returns:
        str: MA command string

    Examples:
        >>> go_back_executor(3)
        'goback executor 3'
    """
    return go_back(
        "executor", executor_id, end=end, cue_mode=cue_mode, userprofile=userprofile
    )


# ============================================================================
# GOTO FUNCTION KEYWORD
# ============================================================================
# Goto is a function keyword to jump to a specific cue in a list.
# Set the fade time in Setup -> Show -> Playback & MIB Timing -> Goto.
# ============================================================================


def goto(
    cue_id: int | float,
    *,
    executor: int | None = None,
    sequence: int | None = None,
    cue_mode: CueMode | None = None,
    userprofile: str | None = None,
) -> str:
    """
    Construct a Goto command to jump to a specific cue.

    Goto is used to jump to a specified cue.
    Default fade time can be set in Setup -> Show -> Playback & MIB Timing -> Goto.

    Args:
        cue_id: Cue number
        executor: Executor number (optional)
        sequence: Sequence number (optional)
        cue_mode: Cue mode (normal, assert, xassert, release)
        userprofile: User profile name

    Returns:
        str: MA command string

    Examples:
        >>> goto(3)
        'goto cue 3'
        >>> goto(5, executor=4)
        'goto cue 5 executor 4'
        >>> goto(3, sequence=1)
        'goto cue 3 sequence 1'
        >>> goto(3, cue_mode="assert")
        'goto cue 3 /cue_mode=assert'
    """
    parts = ["goto", "cue", str(cue_id)]

    # Executor or Sequence
    if executor is not None:
        parts.append(f"executor {executor}")
    elif sequence is not None:
        parts.append(f"sequence {sequence}")

    # Options
    if cue_mode:
        parts.append(f"/cue_mode={cue_mode}")
    if userprofile:
        parts.append(f'/userprofile="{userprofile}"')

    return " ".join(parts)


# ============================================================================
# LEGACY CONVENIENCE FUNCTIONS (maintain backward compatibility)
# ============================================================================


def go_sequence(sequence_id: int) -> str:
    """
    Construct a command to execute a sequence (legacy).

    This is a legacy convenience function. It is recommended to use go("sequence", id) instead.

    Args:
        sequence_id: Sequence number

    Returns:
        str: MA command to execute a sequence
    """
    return f"go+ sequence {sequence_id}"


def pause_sequence(sequence_id: int) -> str:
    """
    Construct a command to pause a sequence.

    Args:
        sequence_id: Sequence number

    Returns:
        str: MA command to pause a sequence
    """
    return f"pause sequence {sequence_id}"


def goto_cue(sequence_id: int, cue_id: int) -> str:
    """
    Construct a command to jump to a specific cue (legacy).

    This is a legacy convenience function. It is recommended to use goto(cue_id, sequence=sequence_id) instead.

    Args:
        sequence_id: Sequence number
        cue_id: Cue number

    Returns:
        str: MA command to jump to a cue
    """
    return f"goto cue {cue_id} sequence {sequence_id}"


# ============================================================================
# <<< (GOFASTBACK) AND >>> (GOFASTFORWARD) FUNCTION KEYWORDS
# ============================================================================
# These keywords are used to quickly jump to previous/next cue step.
# The timing can be adjusted via Setup -> Show -> Playback + MIB Timing.
# ============================================================================


def go_fast_back(
    *,
    executor: int | list[int] | None = None,
    sequence: int | None = None,
) -> str:
    """
    Construct a GoFastBack (<<<) command to jump quickly to the previous step.

    <<< is used to quickly jump to the previous step (no time by default, can be adjusted in setup).
    Timing can be adjusted via Setup -> Show -> Playback + MIB Timing GoFast property.

    Args:
        executor: Executor number or list of numbers
        sequence: Sequence number

    Returns:
        str: MA command string

    Examples:
        >>> go_fast_back()
        '<<<'
        >>> go_fast_back(executor=3)
        '<<< executor 3'
        >>> go_fast_back(executor=[1, 2, 3])
        '<<< executor 1 + 2 + 3'
        >>> go_fast_back(sequence=5)
        '<<< sequence 5'
    """
    if executor is not None:
        if isinstance(executor, list):
            exec_str = " + ".join(str(e) for e in executor)
            return f"<<< executor {exec_str}"
        return f"<<< executor {executor}"

    if sequence is not None:
        return f"<<< sequence {sequence}"

    return "<<<"


def go_fast_forward(
    *,
    executor: int | list[int] | None = None,
    sequence: int | None = None,
) -> str:
    """
    Construct a GoFastForward (>>>) command to jump quickly to the next step.

    >>> is used to quickly jump to the next step (no time by default, can be adjusted in setup).
    Timing can be adjusted via Setup -> Show -> Playback + MIB Timing GoFast property.

    Args:
        executor: Executor number or list of numbers
        sequence: Sequence number

    Returns:
        str: MA command string

    Examples:
        >>> go_fast_forward()
        '>>>'
        >>> go_fast_forward(executor=3)
        '>>> executor 3'
        >>> go_fast_forward(executor=[1, 2, 3])
        '>>> executor 1 + 2 + 3'
        >>> go_fast_forward(sequence=5)
        '>>> sequence 5'
    """
    if executor is not None:
        if isinstance(executor, list):
            exec_str = " + ".join(str(e) for e in executor)
            return f">>> executor {exec_str}"
        return f">>> executor {executor}"

    if sequence is not None:
        return f">>> sequence {sequence}"

    return ">>>"


# ============================================================================
# DEFGOBACK / DEFGOFORWARD / DEFGOPAUSE FUNCTION KEYWORDS
# ============================================================================
# These keywords operate on the **selected executor** (default executor).
# They are equivalent to pressing the physical Go-, Go+, and Pause buttons.
# ============================================================================


def on_executor(executor_id: int, *, page: int | None = None) -> str:
    """
    Start (Go) an executor.

    Args:
        executor_id: Executor ID
        page: Page number for page-qualified addressing (optional)

    Returns:
        str: MA command to start executor

    Examples:
        >>> on_executor(3)
        'on executor 3'
        >>> on_executor(5, page=2)
        'on executor 2.5'
    """
    ref = f"{page}.{executor_id}" if page is not None else str(executor_id)
    return f"on executor {ref}"


def off_executor(executor_id: int, *, page: int | None = None) -> str:
    """
    Release (Off) an executor.

    Args:
        executor_id: Executor ID
        page: Page number for page-qualified addressing (optional)

    Returns:
        str: MA command to release executor

    Examples:
        >>> off_executor(3)
        'off executor 3'
        >>> off_executor(5, page=2)
        'off executor 2.5'
    """
    ref = f"{page}.{executor_id}" if page is not None else str(executor_id)
    return f"off executor {ref}"


def flash_executor(executor_id: int, *, page: int | None = None) -> str:
    """
    Flash an executor.

    Args:
        executor_id: Executor ID
        page: Page number for page-qualified addressing (optional)

    Returns:
        str: MA command to flash executor

    Examples:
        >>> flash_executor(3)
        'flash executor 3'
    """
    ref = f"{page}.{executor_id}" if page is not None else str(executor_id)
    return f"flash executor {ref}"


def solo_executor(executor_id: int, *, page: int | None = None) -> str:
    """
    Solo an executor.

    Args:
        executor_id: Executor ID
        page: Page number for page-qualified addressing (optional)

    Returns:
        str: MA command to solo executor

    Examples:
        >>> solo_executor(3)
        'solo executor 3'
    """
    ref = f"{page}.{executor_id}" if page is not None else str(executor_id)
    return f"solo executor {ref}"


def goto_timecode(timecode_id: int, position: str | None = None) -> str:
    """
    Jump to a position in a timecode show, or reset to start.

    Args:
        timecode_id: Timecode show ID
        position: HH:MM:SS:FF position string (optional; omit to reset to start)

    Returns:
        str: MA command to jump timecode position

    Examples:
        >>> goto_timecode(1, "00:01:30:00")
        'goto timecode 1 "00:01:30:00"'
        >>> goto_timecode(1)
        'goto timecode 1'
    """
    if position is not None:
        return f'goto timecode {timecode_id} "{position}"'
    return f"goto timecode {timecode_id}"


def def_go_back() -> str:
    """
    Construct a DefGoBack command to call the previous cue in the selected executor.

    DefGoBack is used to call the previous cue on the selected executor.
    Equivalent to pressing the large Go- button on the console.

    Returns:
        str: MA command string

    Examples:
        >>> def_go_back()
        'defgoback'
    """
    return "defgoback"


def def_go_forward() -> str:
    """
    Construct a DefGoForward command to call the next cue in the selected executor.

    DefGoForward is used to call the next cue on the selected executor.
    Equivalent to pressing the large Go+ button on the console.

    Returns:
        str: MA command string

    Examples:
        >>> def_go_forward()
        'defgoforward'
    """
    return "defgoforward"


def release_executor(executor_id: int, *, page: int | None = None) -> str:
    """
    Release an executor (return to default state).

    Args:
        executor_id: Executor ID
        page: Page number for page-qualified addressing (optional)

    Returns:
        str: MA command to release executor

    Examples:
        >>> release_executor(3)
        'release executor 3'
        >>> release_executor(5, page=2)
        'release executor 2.5'
    """
    ref = f"{page}.{executor_id}" if page is not None else str(executor_id)
    return f"release executor {ref}"


def blackout() -> str:
    """
    Toggle master blackout.

    Returns:
        str: MA command to toggle blackout

    Examples:
        >>> blackout()
        'blackout'
    """
    return "blackout"


def def_go_pause() -> str:
    """
    Construct a DefGoPause command to pause the current fade in the selected executor.

    DefGoPause is used to pause the current fade and effects on the selected executor.
    If the "Link effect to rate" option in the assign menu is enabled, it will also pause effects.
    Equivalent to pressing the large Pause button on the console.

    Returns:
        str: MA command string

    Examples:
        >>> def_go_pause()
        'defgopause'
    """
    return "defgopause"


# ============================================================================
# SWOP FUNCTION KEYWORD
# ============================================================================
# Swop activates an executor while muting all others (HTP priority swap).
# ============================================================================


def swop_executor(executor_id: int, *, page: int | None = None) -> str:
    """
    Swop an executor (activate while muting all others).

    Args:
        executor_id: Executor ID
        page: Page number for page-qualified addressing (optional)

    Returns:
        str: MA command string

    Examples:
        >>> swop_executor(3)
        'swop executor 3'
        >>> swop_executor(5, page=2)
        'swop executor 2.5'
    """
    ref = f"{page}.{executor_id}" if page is not None else str(executor_id)
    return f"swop executor {ref}"


# ============================================================================
# TOP FUNCTION KEYWORD
# ============================================================================
# Top restarts an executor from the first cue.
# ============================================================================


def top_executor(executor_id: int, *, page: int | None = None) -> str:
    """
    Restart an executor from the top (first cue).

    Args:
        executor_id: Executor ID
        page: Page number for page-qualified addressing (optional)

    Returns:
        str: MA command string

    Examples:
        >>> top_executor(3)
        'top executor 3'
        >>> top_executor(5, page=2)
        'top executor 2.5'
    """
    ref = f"{page}.{executor_id}" if page is not None else str(executor_id)
    return f"top executor {ref}"


# ============================================================================
# STOMP FUNCTION KEYWORD
# ============================================================================
# Stomp stops all running effects for a sequence or executor.
# ============================================================================


def stomp_executor(executor_id: int, *, page: int | None = None) -> str:
    """
    Stomp an executor (stop all running effects).

    Args:
        executor_id: Executor ID
        page: Page number for page-qualified addressing (optional)

    Returns:
        str: MA command string

    Examples:
        >>> stomp_executor(3)
        'stomp executor 3'
        >>> stomp_executor(5, page=2)
        'stomp executor 2.5'
    """
    ref = f"{page}.{executor_id}" if page is not None else str(executor_id)
    return f"stomp executor {ref}"


# ============================================================================
# LOADNEXT / LOADPREV FUNCTION KEYWORDS
# ============================================================================
# LoadNext / LoadPrev pre-load the next or previous cue without executing it.
# ============================================================================


def load_next(*, executor: int | None = None, sequence: int | None = None) -> str:
    """
    Pre-load the next cue of an executor or sequence without executing it.

    Args:
        executor: Executor ID (optional)
        sequence: Sequence ID (optional)

    Returns:
        str: MA command string

    Examples:
        >>> load_next()
        'loadnext'
        >>> load_next(executor=3)
        'loadnext executor 3'
        >>> load_next(sequence=5)
        'loadnext sequence 5'
    """
    if executor is not None:
        return f"loadnext executor {executor}"
    if sequence is not None:
        return f"loadnext sequence {sequence}"
    return "loadnext"


def load_prev(*, executor: int | None = None, sequence: int | None = None) -> str:
    """
    Pre-load the previous cue of an executor or sequence without executing it.

    Args:
        executor: Executor ID (optional)
        sequence: Sequence ID (optional)

    Returns:
        str: MA command string

    Examples:
        >>> load_prev()
        'loadprev'
        >>> load_prev(executor=3)
        'loadprev executor 3'
        >>> load_prev(sequence=5)
        'loadprev sequence 5'
    """
    if executor is not None:
        return f"loadprev executor {executor}"
    if sequence is not None:
        return f"loadprev sequence {sequence}"
    return "loadprev"


def solo(
    object_type: str | None = None,
    object_id: int | str | None = None,
) -> str:
    """
    Construct a Solo command to isolate an object (mute all others).

    Solo is universal — accepted by all 16 object types (live-verified).
    When called bare (no arguments) it solos the current selection.

    Args:
        object_type: Object type (executor, sequence, group, fixture, etc.)
        object_id: Object ID

    Returns:
        str: MA command string

    Examples:
        >>> solo()
        'solo'
        >>> solo("executor", 3)
        'solo executor 3'
        >>> solo("group", 5)
        'solo group 5'
        >>> solo("sequence", 99)
        'solo sequence 99'
    """
    if object_type is not None and object_id is not None:
        return f"solo {object_type} {object_id}"
    if object_type is not None:
        return f"solo {object_type}"
    return "solo"


def blind(
    object_type: str | None = None,
    object_id: int | str | None = None,
) -> str:
    """
    Construct a Blind command to toggle blind mode.

    Blind is universal — accepted by all 16 object types (live-verified).
    When called bare (no arguments) it toggles the global blind mode.

    Args:
        object_type: Object type (optional — scopes blind to an object)
        object_id: Object ID

    Returns:
        str: MA command string

    Examples:
        >>> blind()
        'blind'
        >>> blind("executor", 3)
        'blind executor 3'
        >>> blind("sequence", 5)
        'blind sequence 5'
    """
    if object_type is not None and object_id is not None:
        return f"blind {object_type} {object_id}"
    if object_type is not None:
        return f"blind {object_type}"
    return "blind"


def freeze(
    object_type: str | None = None,
    object_id: int | str | None = None,
) -> str:
    """
    Construct a Freeze command to freeze playback output.

    Freeze is universal — accepted by all 16 object types (live-verified).
    When called bare (no arguments) it freezes all output.

    Args:
        object_type: Object type (optional — scopes freeze to an object)
        object_id: Object ID

    Returns:
        str: MA command string

    Examples:
        >>> freeze()
        'freeze'
        >>> freeze("executor", 3)
        'freeze executor 3'
        >>> freeze("sequence", 5)
        'freeze sequence 5'
        >>> freeze("fixture", 10)
        'freeze fixture 10'
    """
    if object_type is not None and object_id is not None:
        return f"freeze {object_type} {object_id}"
    if object_type is not None:
        return f"freeze {object_type}"
    return "freeze"


# ============================================================================
# BLOCK / UNBLOCK FUNCTION KEYWORDS
# ============================================================================


def block_cue(
    cue_id: int | float,
    *,
    sequence_id: int | None = None,
) -> str:
    """
    Construct a Block command to block tracking for a cue.

    Blocked cues do not allow tracked values to pass through them.

    Args:
        cue_id: Cue number to block
        sequence_id: Sequence number (optional scoping)

    Returns:
        str: MA command string

    Examples:
        >>> block_cue(5)
        'Block Cue 5'
        >>> block_cue(3, sequence_id=1)
        'Block Cue 3 Sequence 1'
    """
    cmd = f"Block Cue {cue_id}"
    if sequence_id is not None:
        cmd += f" Sequence {sequence_id}"
    return cmd


def unblock_cue(
    cue_id: int | float,
    *,
    sequence_id: int | None = None,
) -> str:
    """
    Construct an Unblock command to unblock tracking for a cue.

    Args:
        cue_id: Cue number to unblock
        sequence_id: Sequence number (optional scoping)

    Returns:
        str: MA command string

    Examples:
        >>> unblock_cue(5)
        'Unblock Cue 5'
        >>> unblock_cue(3, sequence_id=1)
        'Unblock Cue 3 Sequence 1'
    """
    cmd = f"Unblock Cue {cue_id}"
    if sequence_id is not None:
        cmd += f" Sequence {sequence_id}"
    return cmd


# ============================================================================
# LEARN FUNCTION KEYWORD
# ============================================================================


def learn_executor(
    executor_id: int,
    *,
    page: int | None = None,
) -> str:
    """
    Construct a Learn command to capture timing from a manual crossfade.

    Args:
        executor_id: Executor ID
        page: Page number for page-qualified addressing (optional)

    Returns:
        str: MA command string

    Examples:
        >>> learn_executor(1)
        'Learn Executor 1'
        >>> learn_executor(5, page=2)
        'Learn Executor 2.5'
    """
    ref = f"{page}.{executor_id}" if page is not None else str(executor_id)
    return f"Learn Executor {ref}"


# ============================================================================
# KILL / TOGGLE / FREEZE EXECUTOR KEYWORDS
# ============================================================================


def kill_executor(executor_id: int, *, page: int | None = None) -> str:
    """
    Construct a Kill command to immediately stop an executor.

    Args:
        executor_id: Executor ID
        page: Page number for page-qualified addressing (optional)

    Returns:
        str: MA command string

    Examples:
        >>> kill_executor(3)
        'Kill Executor 3'
        >>> kill_executor(5, page=2)
        'Kill Executor 2.5'
    """
    ref = f"{page}.{executor_id}" if page is not None else str(executor_id)
    return f"Kill Executor {ref}"


def toggle_executor(executor_id: int, *, page: int | None = None) -> str:
    """
    Construct a Toggle command to toggle an executor on/off.

    Args:
        executor_id: Executor ID
        page: Page number for page-qualified addressing (optional)

    Returns:
        str: MA command string

    Examples:
        >>> toggle_executor(3)
        'Toggle Executor 3'
        >>> toggle_executor(5, page=2)
        'Toggle Executor 2.5'
    """
    ref = f"{page}.{executor_id}" if page is not None else str(executor_id)
    return f"Toggle Executor {ref}"


def freeze_executor(executor_id: int, *, page: int | None = None) -> str:
    """
    Construct a Freeze command scoped to a specific executor.

    Args:
        executor_id: Executor ID
        page: Page number for page-qualified addressing (optional)

    Returns:
        str: MA command string

    Examples:
        >>> freeze_executor(3)
        'Freeze Executor 3'
        >>> freeze_executor(5, page=2)
        'Freeze Executor 2.5'
    """
    ref = f"{page}.{executor_id}" if page is not None else str(executor_id)
    return f"Freeze Executor {ref}"


# ============================================================================
# RATE / SPEED MODIFIERS
# ============================================================================


def double_rate(*, executor: int | None = None) -> str:
    """
    Construct a DoubleRate command to double the rate of an executor or selection.

    Args:
        executor: Executor number (optional; applies globally if omitted)

    Returns:
        str: MA command string

    Examples:
        >>> double_rate()
        'DoubleRate'
        >>> double_rate(executor=3)
        'DoubleRate Executor 3'
    """
    if executor is not None:
        return f"DoubleRate Executor {executor}"
    return "DoubleRate"


def half_rate(*, executor: int | None = None) -> str:
    """
    Construct a HalfRate command to halve the rate of an executor or selection.

    Args:
        executor: Executor number (optional; applies globally if omitted)

    Returns:
        str: MA command string

    Examples:
        >>> half_rate()
        'HalfRate'
        >>> half_rate(executor=3)
        'HalfRate Executor 3'
    """
    if executor is not None:
        return f"HalfRate Executor {executor}"
    return "HalfRate"


def double_speed(*, executor: int | None = None) -> str:
    """
    Construct a DoubleSpeed command to double the playback speed.

    Args:
        executor: Executor number (optional)

    Returns:
        str: MA command string

    Examples:
        >>> double_speed()
        'DoubleSpeed'
        >>> double_speed(executor=3)
        'DoubleSpeed Executor 3'
    """
    if executor is not None:
        return f"DoubleSpeed Executor {executor}"
    return "DoubleSpeed"


def half_speed(*, executor: int | None = None) -> str:
    """
    Construct a HalfSpeed command to halve the playback speed.

    Args:
        executor: Executor number (optional)

    Returns:
        str: MA command string

    Examples:
        >>> half_speed()
        'HalfSpeed'
        >>> half_speed(executor=3)
        'HalfSpeed Executor 3'
    """
    if executor is not None:
        return f"HalfSpeed Executor {executor}"
    return "HalfSpeed"

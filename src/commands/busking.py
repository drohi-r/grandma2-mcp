"""
src/commands/busking.py — Pure command builders for busking/performance mode.

Busking model: the LD performs live using faders as real-time effect modulators.
Each function returns a raw grandMA2 command string — no I/O, no side effects.

Design notes:
- Effects run on executors; the fader controls intensity, not cue progression.
- Rate/speed commands affect the *selected* effect's phase speed globally.
- Batch release and zero commands chain multiple MA2 commands with '; '.
"""

from __future__ import annotations


def assign_effect_to_executor(
    effect_id: int,
    executor_id: int,
    *,
    page: int | None = None,
) -> str:
    """
    Build 'Assign Effect {id} Executor {id}' command.

    Binds an effect template from the effect library to a fader executor slot
    so the fader controls effect intensity in live busking mode.

    Args:
        effect_id: Effect pool ID (1-based).
        executor_id: Executor slot number on the page (1-based).
        page: Optional page number. When given, qualifies as 'Page {page}.{exec}'.

    Returns:
        e.g. "Assign Effect 3 Executor 5" or "Assign Effect 3 Page 2.5"
    """
    if page is not None:
        return f"Assign Effect {effect_id} Page {page}.{executor_id}"
    return f"Assign Effect {effect_id} Executor {executor_id}"


def set_effect_rate(rate: int) -> str:
    """
    Build 'EffectRate {rate}' command.

    Sets the rate multiplier for the selected/active effects.
    Rate 100 = normal speed; Rate 200 = double speed; Rate 50 = half speed.

    Args:
        rate: Rate value 1-200 (100 = normal).

    Returns:
        e.g. "EffectRate 100"
    """
    return f"EffectRate {rate}"


def set_effect_speed(speed: int) -> str:
    """
    Build 'EffectSpeed {speed}' command.

    Sets the absolute speed in BPM for the selected/active effects.
    Unlike rate (relative multiplier), speed sets an absolute BPM target.

    Args:
        speed: Speed in BPM (typical range 20-300).

    Returns:
        e.g. "EffectSpeed 120"
    """
    return f"EffectSpeed {speed}"


def release_effects_on_page(
    page: int,
    *,
    start_exec: int = 1,
    end_exec: int = 20,
) -> str:
    """
    Build an 'Off Page {page}.{exec}' chain for a range of executors.

    Releases (kills) all running effects across the specified executor range
    without changing fader positions. Use for live song transition cleanup.

    Args:
        page: Fader page number.
        start_exec: First executor slot to release (inclusive).
        end_exec: Last executor slot to release (inclusive).

    Returns:
        e.g. "Off Page 3.1 ; Off Page 3.2 ; ... ; Off Page 3.20"
    """
    cmds = [f"Off Page {page}.{i}" for i in range(start_exec, end_exec + 1)]
    return " ; ".join(cmds)


def zero_page_faders(
    page: int,
    *,
    start_exec: int = 1,
    end_exec: int = 20,
) -> str:
    """
    Build an 'Executor {page}.{exec} At 0' chain for a range of executors.

    Sets all fader levels to 0 without releasing the executors. This silences
    all effects while keeping them armed for instant recall — the standard
    busking 'blackout' technique.

    Args:
        page: Fader page number.
        start_exec: First executor slot (inclusive).
        end_exec: Last executor slot (inclusive).

    Returns:
        e.g. "Executor 3.1 At 0 ; Executor 3.2 At 0 ; ..."
    """
    cmds = [f"Executor {page}.{i} At 0" for i in range(start_exec, end_exec + 1)]
    return " ; ".join(cmds)


def executor_page_range(page: int, start_exec: int, end_exec: int) -> str:
    """
    Build a 'Page {page}.{start} Thru {end}' range string.

    Used as an argument to Assign, Off, or At commands that accept a range.

    Args:
        page: Fader page number.
        start_exec: First executor in range.
        end_exec: Last executor in range.

    Returns:
        e.g. "Page 2.1 Thru 8"
    """
    return f"Page {page}.{start_exec} Thru {end_exec}"

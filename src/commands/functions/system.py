"""
System Function Keywords for grandMA2 Command Builder

Covers console-level operations not tied to a specific pool:
- lock / unlock: UI lock for the console
- call_plugin: Execute a plugin by ID or name
- run_lua: Execute an inline Lua script
- reload_plugins: Reload all plugins from disk
- special_master: Read/set Grand Master, Speed Masters, Rate Masters
- rdm_*: Remote Device Management (autopatch, match, info, set parameter)
- chaser_rate / chaser_speed / chaser_skip / chaser_xfade: Live chaser control
- effect_*: Effect programmer parameter setters (BPM, high, low, phase, etc.)
"""


# ============================================================================
# CONSOLE LOCK / UNLOCK
# ============================================================================


def lock_console(password: str | None = None) -> str:
    """
    Lock the grandMA2 console UI (prevents accidental input).

    Args:
        password: Optional lock password.

    Returns:
        str: MA command string

    Examples:
        >>> lock_console()
        'Lock'
        >>> lock_console("secret")
        'Lock "secret"'
    """
    if password is not None:
        return f'Lock "{password}"'
    return "Lock"


def unlock_console(password: str | None = None) -> str:
    """
    Unlock the grandMA2 console UI.

    Args:
        password: Optional unlock password.

    Returns:
        str: MA command string

    Examples:
        >>> unlock_console()
        'Unlock'
        >>> unlock_console("1234")
        'Unlock "1234"'
    """
    if password:
        return f'Unlock "{password}"'
    return "Unlock"


# ============================================================================
# PLUGIN / LUA
# ============================================================================


def call_plugin(plugin_id: int | str) -> str:
    """
    Execute a plugin by ID or name.

    Args:
        plugin_id: Plugin number or name.

    Returns:
        str: MA command string

    Examples:
        >>> call_plugin(1)
        'Plugin 1'
        >>> call_plugin("LUA")
        'Plugin "LUA"'
    """
    if isinstance(plugin_id, str):
        return f'Plugin "{plugin_id}"'
    return f"Plugin {plugin_id}"


def run_lua(script: str) -> str:
    """
    Execute an inline Lua script on the console.

    Args:
        script: Lua source code string.

    Returns:
        str: MA command string

    Examples:
        >>> run_lua('print("hello")')
        'Lua "print(\\"hello\\")"'
    """
    escaped = script.replace('"', '\\"')
    return f'Lua "{escaped}"'


def reload_plugins() -> str:
    """
    Reload all plugins from disk.

    Returns:
        str: MA command string

    Examples:
        >>> reload_plugins()
        'ReloadPlugins'
    """
    return "ReloadPlugins"


# ============================================================================
# SPECIAL MASTER
# ============================================================================

_SPECIAL_MASTER_TARGETS = {
    "grandmaster": "GrandMaster",
    "playbackmaster": "PlaybackMaster",
    "speed1": "Speed1Master",
    "speed2": "Speed2Master",
    "speed3": "Speed3Master",
    "speed4": "Speed4Master",
    "speed5": "Speed5Master",
    "speed6": "Speed6Master",
    "speed7": "Speed7Master",
    "speed8": "Speed8Master",
    "speed9": "Speed9Master",
    "speed10": "Speed10Master",
    "speed11": "Speed11Master",
    "speed12": "Speed12Master",
    "speed13": "Speed13Master",
    "speed14": "Speed14Master",
    "speed15": "Speed15Master",
    "speed16": "Speed16Master",
    "rate1": "Rate1Master",
    "rate2": "Rate2Master",
    "rate3": "Rate3Master",
    "rate4": "Rate4Master",
    "rate5": "Rate5Master",
    "rate6": "Rate6Master",
    "rate7": "Rate7Master",
    "rate8": "Rate8Master",
    "rate9": "Rate9Master",
    "rate10": "Rate10Master",
    "rate11": "Rate11Master",
    "rate12": "Rate12Master",
    "rate13": "Rate13Master",
    "rate14": "Rate14Master",
    "rate15": "Rate15Master",
    "rate16": "Rate16Master",
}

SPECIAL_MASTER_NAMES: frozenset[str] = frozenset(_SPECIAL_MASTER_TARGETS)


def set_special_master(master: str, value: float) -> str:
    """
    Set the level of a SpecialMaster (Grand Master, Speed/Rate masters).

    Args:
        master: One of 'grandmaster', 'playbackmaster', 'speed1'..'speed16',
                'rate1'..'rate16'.
        value: Level 0-100 for Grand/Playback Master; BPM for Speed masters;
               percent for Rate masters.

    Returns:
        str: MA command string

    Raises:
        ValueError: If master name is not recognised.

    Examples:
        >>> set_special_master("grandmaster", 80)
        'SpecialMaster GrandMaster At 80'
        >>> set_special_master("speed1", 120)
        'SpecialMaster Speed1Master At 120'
    """
    key = master.lower()
    if key not in _SPECIAL_MASTER_TARGETS:
        raise ValueError(
            f"Unknown master {master!r}. Valid: {sorted(SPECIAL_MASTER_NAMES)}"
        )
    return f"SpecialMaster {_SPECIAL_MASTER_TARGETS[key]} At {value}"


# ============================================================================
# RDM — Remote Device Management
# ============================================================================


def rdm_automatch() -> str:
    """
    Auto-match discovered RDM devices to existing fixture types.

    Returns:
        str: MA command string

    Examples:
        >>> rdm_automatch()
        'RdmAutomatch'
    """
    return "RdmAutomatch"


def rdm_autopatch() -> str:
    """
    Auto-patch discovered RDM devices to free DMX addresses.

    Returns:
        str: MA command string

    Examples:
        >>> rdm_autopatch()
        'RdmAutopatch'
    """
    return "RdmAutopatch"


def rdm_list(universe: int | None = None) -> str:
    """
    List discovered RDM devices, optionally filtered by universe.

    Args:
        universe: Universe number (optional).

    Returns:
        str: MA command string

    Examples:
        >>> rdm_list()
        'RdmList'
        >>> rdm_list(1)
        'RdmList Universe 1'
    """
    if universe is not None:
        return f"RdmList Universe {universe}"
    return "RdmList"


def rdm_info(fixture_id: int) -> str:
    """
    Get RDM device information for a fixture.

    Args:
        fixture_id: Fixture ID.

    Returns:
        str: MA command string

    Examples:
        >>> rdm_info(101)
        'RdmInfo Fixture 101'
    """
    return f"RdmInfo Fixture {fixture_id}"


def rdm_setpatch(fixture_id: int, universe: int, address: int) -> str:
    """
    Set the DMX patch address for an RDM device.

    Args:
        fixture_id: Fixture ID.
        universe: Target universe number.
        address: Target DMX address (1-512).

    Returns:
        str: MA command string

    Examples:
        >>> rdm_setpatch(101, 1, 1)
        'RdmSetpatch Fixture 101 Universe 1 Address 1'
    """
    return f"RdmSetpatch Fixture {fixture_id} Universe {universe} Address {address}"


def rdm_unmatch(fixture_id: int) -> str:
    """
    Remove RDM match for a fixture (detach from discovered device).

    Args:
        fixture_id: Fixture ID.

    Returns:
        str: MA command string

    Examples:
        >>> rdm_unmatch(101)
        'RdmUnmatch Fixture 101'
    """
    return f"RdmUnmatch Fixture {fixture_id}"


# ============================================================================
# CHASER LIVE CONTROL
# ============================================================================


def chaser_rate(value: float, executor_id: int | None = None, page: int = 1) -> str:
    """
    Set the rate of a running chaser.

    Args:
        value: Rate value (0-200, where 100 = normal speed).
        executor_id: Executor ID (optional; uses selected executor if omitted).
        page: Page number (default 1).

    Returns:
        str: MA command string

    Examples:
        >>> chaser_rate(100)
        'Rate 100'
        >>> chaser_rate(50, 201)
        'Rate 50 Executor 1.201'
    """
    if executor_id is not None:
        return f"Rate {value} Executor {page}.{executor_id}"
    return f"Rate {value}"


def chaser_speed(value: float, executor_id: int | None = None, page: int = 1) -> str:
    """
    Set the BPM speed of a running chaser.

    Args:
        value: BPM value (0-65535).
        executor_id: Executor ID (optional; uses selected executor if omitted).
        page: Page number (default 1).

    Returns:
        str: MA command string

    Examples:
        >>> chaser_speed(120)
        'Speed 120'
        >>> chaser_speed(60, 201)
        'Speed 60 Executor 1.201'
    """
    if executor_id is not None:
        return f"Speed {value} Executor {page}.{executor_id}"
    return f"Speed {value}"


def chaser_skip(
    direction: str,
    executor_id: int | None = None,
    page: int = 1,
) -> str:
    """
    Skip forward or backward one step in a running chaser.

    Args:
        direction: 'plus' (forward) or 'minus' (backward).
        executor_id: Executor ID (optional).
        page: Page number (default 1).

    Returns:
        str: MA command string

    Raises:
        ValueError: If direction is not 'plus' or 'minus'.

    Examples:
        >>> chaser_skip("plus")
        'SkipPlus'
        >>> chaser_skip("minus", 201)
        'SkipMinus Executor 1.201'
    """
    if direction not in ("plus", "minus"):
        raise ValueError("direction must be 'plus' or 'minus'")
    keyword = "SkipPlus" if direction == "plus" else "SkipMinus"
    if executor_id is not None:
        return f"{keyword} Executor {page}.{executor_id}"
    return keyword


def chaser_xfade(
    mode: str,
    executor_id: int | None = None,
    page: int = 1,
) -> str:
    """
    Set the crossfade mode of a running chaser.

    Args:
        mode: 'a', 'b', or 'ab'.
        executor_id: Executor ID (optional).
        page: Page number (default 1).

    Returns:
        str: MA command string

    Raises:
        ValueError: If mode is not 'a', 'b', or 'ab'.

    Examples:
        >>> chaser_xfade("a")
        'CrossFadeA'
        >>> chaser_xfade("ab", 201)
        'CrossFadeAB Executor 1.201'
    """
    mode = mode.lower()
    if mode not in ("a", "b", "ab"):
        raise ValueError("mode must be 'a', 'b', or 'ab'")
    keyword = {"a": "CrossFadeA", "b": "CrossFadeB", "ab": "CrossFadeAB"}[mode]
    if executor_id is not None:
        return f"{keyword} Executor {page}.{executor_id}"
    return keyword


# ============================================================================
# EFFECT PROGRAMMER PARAMETERS
# ============================================================================

_EFFECT_PARAM_KEYWORDS = frozenset({
    "bpm", "hz", "high", "low", "phase", "width", "attack", "decay",
})


def set_effect_parameter(param: str, value: float) -> str:
    """
    Set an effect parameter in the programmer for the current selection.

    Valid parameters: bpm, hz, high, low, phase, width, attack, decay.

    Args:
        param: Parameter name (case-insensitive).
        value: Numeric value (e.g. 120 for BPM, 0-100 for high/low/width, 0-359 for phase).

    Returns:
        str: MA command string

    Raises:
        ValueError: If param is not a recognised effect parameter.

    Examples:
        >>> set_effect_parameter("bpm", 120)
        'EffectBPM 120'
        >>> set_effect_parameter("phase", 45)
        'EffectPhase 45'
        >>> set_effect_parameter("high", 80)
        'EffectHigh 80'
    """
    key = param.lower()
    if key not in _EFFECT_PARAM_KEYWORDS:
        raise ValueError(
            f"Unknown effect parameter {param!r}. "
            f"Valid: {sorted(_EFFECT_PARAM_KEYWORDS)}"
        )
    keyword = f"Effect{key.capitalize()}" if key not in ("bpm", "hz") else f"Effect{key.upper()}"
    return f"{keyword} {value}"


# ============================================================================
# LUA EXECUTE ALIAS
# ============================================================================


def lua_execute(script: str) -> str:
    """
    Construct a Lua command to execute an inline Lua script.

    Alias for run_lua() with a clearer name for use in MCP tools.

    Args:
        script: Lua script string

    Returns:
        str: MA command string

    Examples:
        >>> lua_execute("gma.echo('hello')")
        "Lua \\"gma.echo('hello')\\""
    """
    return f'Lua "{script}"'


# ============================================================================
# CONSOLE LIFECYCLE
# ============================================================================


def reboot_console() -> str:
    """
    Construct a Reboot command to reboot the console hardware.

    Returns:
        str: MA command string

    Examples:
        >>> reboot_console()
        'Reboot'
    """
    return "Reboot"


def restart_console() -> str:
    """
    Construct a Restart command to restart the console software.

    Returns:
        str: MA command string

    Examples:
        >>> restart_console()
        'Restart'
    """
    return "Restart"


def shutdown_console() -> str:
    """
    Construct a Shutdown command to shut down the console.

    Returns:
        str: MA command string

    Examples:
        >>> shutdown_console()
        'Shutdown'
    """
    return "Shutdown"


# ============================================================================
# CHAT FUNCTION KEYWORD
# ============================================================================


def send_chat(message: str) -> str:
    """
    Construct a Chat command to send a message to other consoles in the session.

    Args:
        message: Chat message text

    Returns:
        str: MA command string

    Examples:
        >>> send_chat("Hello from onPC")
        'Chat "Hello from onPC"'
    """
    return f'Chat "{message}"'

"""
Constants for grandMA2 Command Builder

This module contains all constants used by the command builder,
including preset type mappings, store option classifications,
and filter attribute groupings.
"""

# ============================================================================
# PRESET TYPE MAPPINGS
# ============================================================================
# grandMA2 uses numbers to distinguish preset types.
# These mappings convert human-readable names to numeric IDs.

PRESET_TYPES = {
    "dimmer": 1,
    "position": 2,
    "gobo": 3,
    "color": 4,
    "beam": 5,
    "focus": 6,
    "control": 7,
    "shapers": 8,
    "video": 9,
}


# ============================================================================
# STORE OPTION CLASSIFICATIONS
# ============================================================================
# Store options are classified into three types based on their value format.

# Store options that require no value (flag-only options)
# Usage: /merge, /overwrite, /noconfirm
STORE_FLAG_OPTIONS = {
    "merge",
    "overwrite",
    "remove",
    "noconfirm",
    "quiet",
    "global",
    "selective",
    "universal",
    "auto",
    "trackingshield",
    "embedded",
}

# Store options that require a boolean value
# Usage: /cueonly=true, /tracking=false
STORE_BOOL_OPTIONS = {
    "cueonly",
    "tracking",
    "keepactive",
    "presetfilter",
    "addnewcontent",
    "originalcontent",
    "effects",
    "values",
    "valuetimes",
}

# Store options that require a specific value
# Usage: /source=output, /screen=1
STORE_VALUE_OPTIONS = {
    "source",  # Prog, Output, DmxIn
    "useselection",  # Active, Allforselected, Activeforselected, All, Look
    "screen",  # 1..6
    "x",  # x coordinate
    "y",  # y coordinate
}


# ============================================================================
# FILTER ATTRIBUTE GROUPS BY PRESET TYPE (FIXTURE-DEPENDENT DEFAULTS)
# ============================================================================
# Attribute names grouped by PresetType, live-verified from Export Filter XML
# on grandMA2 onPC v3.9.60.65 (2026-03-11, show: claude_ma2_ctrl).
# These correspond to the AttributeLink names in MA2 Filter XML schema.
#
# WARNING: These are DEFAULTS for Mac 700 Profile Extended + Generic Dimmer.
# Shows with different fixtures (Rogue R1, SL Nitro, Elation Fuze, etc.)
# will have different attributes. Use discover_filter_attributes() MCP tool
# to get accurate values for the current show, then pass them to
# create_filter_library(fixture_attributes=...) for correct filter generation.

FILTER_ATTRIBUTES: dict[str, list[str]] = {
    "dimmer": ["DIM"],
    "position": [
        "PAN", "TILT", "POSITIONBLINK",
        "POSITIONOPTIMISATIONMODE", "POSITIONMSPEED",
    ],
    "gobo": [
        "GOBO1", "GOBO1_POS", "GOBO2",
        "ANIMATIONWHEEL", "ANIMATIONINDEXROTATE",
        "ANIMATIONWHEELINCLINE", "ANIMATIONINDEXROTATEMODE",
    ],
    "color": [
        "COLOR1", "COLOR1WHEELOFFSET", "COLOR1WHEELSELECTBLINK",
        "COLORRGB1", "COLORRGB2", "COLORRGB3",
        "COLORMIXER", "CYANMINIMUM", "MAGENTAMINIMUM", "YELLOWMINIMUM",
    ],
    "beam": [
        "SHUTTER", "IRIS", "PRISMA1",
        "EFFECTINDEXROTATE", "EFFECTWHEEL",
    ],
    "focus": ["FOCUS", "ZOOM"],
    "control": [
        "LAMPCONTROL", "LAMPPOWER", "FIXTUREGLOBALRESET",
        "WHEELMODE", "DUMMY", "INTENSITYMSPEED",
    ],
}

# Color scheme for filter pool appearance (hex RRGGBB, no # prefix).
# Used by create_filter_library to color-code filter categories.
FILTER_COLORS: dict[str, str] = {
    "dimmer":   "FFCC00",  # warm yellow
    "position": "0088FF",  # blue
    "gobo":     "00CC44",  # green
    "color":    "FF00CC",  # magenta
    "beam":     "FF6600",  # orange
    "focus":    "00CCCC",  # cyan
    "control":  "999999",  # grey
    "combo":    "CC44FF",  # purple (multi-type combos)
    "exclude":  "FF3333",  # red (No X filters)
}

# Value/ValueTimes/Effects on/off combinations (excluding all-off).
# Each tuple: (suffix, value, value_timing, effect).
# XML attributes: value="false", value_timing="false", effect="false"
# MA2 omits attributes that are true (the default).
# Live-verified on grandMA2 onPC v3.9.60.65 (2026-03-11).
FILTER_VTE_COMBOS: list[tuple[str, bool, bool, bool]] = [
    ("V",      True,  False, False),
    ("VT",     False, True,  False),
    ("E",      False, False, True),
    ("V+VT",   True,  True,  False),
    ("V+E",    True,  False, True),
    ("VT+E",   False, True,  True),
    ("V+VT+E", True,  True,  True),
]


# ============================================================================
# EXECUTOR PRIORITY SYSTEM
# ============================================================================
# Source: grandMA2_KMeans_Complete.json — executor_priority_system
# Priority order (highest to lowest): Freeze > Super > Swap > HTP > High > Programmer > Normal > Low
# Syntax: Assign Executor [ID] /priority=[cmd_value]

EXECUTOR_PRIORITIES: list[dict] = [
    {
        "rank": 1,
        "name": "Super",
        "cmd_value": "super",
        "syntax": "Assign Executor [ID] /priority=super",
        "behavior": "LTP above ALL playbacks AND programmer. Only Freeze overrides Super.",
    },
    {
        "rank": 2,
        "name": "Swap",
        "cmd_value": "swap",
        "syntax": "Assign Executor [ID] /priority=swap",
        "behavior": "Intensity LTP > HTP (negative override possible). Affects ALL attributes.",
    },
    {
        "rank": 3,
        "name": "HTP",
        "cmd_value": "htp",
        "syntax": "Assign Executor [ID] /priority=htp",
        "behavior": "Highest intensity value wins for dimmer. CAUTION: changes priority of ALL attributes.",
    },
    {
        "rank": 4,
        "name": "High",
        "cmd_value": "high",
        "syntax": "Assign Executor [ID] /priority=high",
        "behavior": "High LTP priority. Overrides Normal and Low. Cannot override HTP intensity.",
    },
    {
        "rank": 5,
        "name": "Normal",
        "cmd_value": "normal",
        "syntax": "Assign Executor [ID] /priority=normal",
        "behavior": "Latest Takes Precedence. Default priority. Last triggered value wins.",
    },
    {
        "rank": 6,
        "name": "Low",
        "cmd_value": "low",
        "syntax": "Assign Executor [ID] /priority=low",
        "behavior": "Lowest playback priority. Overridden by all other levels.",
    },
]

# Valid /priority= values (for input validation)
EXECUTOR_PRIORITY_VALUES: frozenset[str] = frozenset(
    p["cmd_value"] for p in EXECUTOR_PRIORITIES
)


# ============================================================================
# EXECUTOR ASSIGN OPTIONS
# ============================================================================
# All options accepted by: Assign Executor [ID] /option=value
# Source: grandMA2_KMeans_Complete.json — executor_priority_system.executor_assign_options

EXECUTOR_ASSIGN_OPTIONS: list[dict] = [
    # Start behaviour
    {"category": "Start", "option": "autostomp",   "syntax": "/autostomp=on|off"},
    {"category": "Start", "option": "autostart",   "syntax": "/autostart=on|off"},
    {"category": "Start", "option": "autostop",    "syntax": "/autostop=on|off"},
    {"category": "Start", "option": "autofix",     "syntax": "/autofix=on|off"},
    {"category": "Start", "option": "restart",     "syntax": "/restart=current|first|next"},
    # Protect
    {"category": "Protect", "option": "ooo",          "syntax": "/ooo=on|off"},
    {"category": "Protect", "option": "swopprotect",  "syntax": "/swopprotect=on|off"},
    {"category": "Protect", "option": "killprotect",  "syntax": "/killprotect=on|off"},
    # MIB (Move In Black)
    {"category": "MIB", "option": "mibalways",  "syntax": "/mibalways=on|off"},
    {"category": "MIB", "option": "mibnever",   "syntax": "/mibnever=on|off"},
    {"category": "MIB", "option": "prepos",     "syntax": "/prepos=on|off"},
    # Function
    {"category": "Function", "option": "chaser",     "syntax": "/chaser=on|off"},
    {"category": "Function", "option": "softltp",    "syntax": "/softltp=on|off"},
    {"category": "Function", "option": "wrap",       "syntax": "/wrap=on|off"},
    {"category": "Function", "option": "crossfade",  "syntax": "/crossfade=off|a|b|ab",
     "note": "Silently ignored when executor Width=1. Requires Width>=2 (multi-fader)."},
    # Priority
    {"category": "Priority", "option": "priority",   "syntax": "/priority=low|normal|high|htp|swap|super"},
    # Timing
    {"category": "Timing", "option": "triggerisgo",  "syntax": "/triggerisgo=on|off"},
    {"category": "Timing", "option": "cmddisable",   "syntax": "/cmddisable=on|off"},
    {"category": "Timing", "option": "effectspeed",  "syntax": "/effectspeed=on|off"},
    {"category": "Timing", "option": "autogo",       "syntax": "/autogo=on|off"},
    # Speed
    {"category": "Speed", "option": "speed",         "syntax": "/speed=[0-65535]"},
    {"category": "Speed", "option": "speedmaster",   "syntax": "/speedmaster=speed1..speed16"},
    {"category": "Speed", "option": "ratemaster",    "syntax": "/ratemaster=rate_individual|rate1..rate16"},
    # Layout
    {"category": "Layout", "option": "width",        "syntax": "/width=1|2|3|4|5"},
]

# Valid option names (for input validation)
EXECUTOR_ASSIGN_OPTION_NAMES: frozenset[str] = frozenset(
    o["option"] for o in EXECUTOR_ASSIGN_OPTIONS
)


# ============================================================================
# EXECUTOR BUTTON & FADER ASSIGNABLE FUNCTIONS
# ============================================================================
# Source: grandMA2_KMeans_Complete.json — executor_priority_system

EXECUTOR_BUTTON_FUNCTIONS: tuple[str, ...] = (
    "Go", "GoBack", "Pause", "Flash", "FlashGo", "FlashOn",
    "Swop", "SwopGo", "SwopOn", "Temp", "Toggle", "On", "Off",
    "Kill", "Select", "SelFix", "Top", "Fix", "Freeze", "Solo",
    "Unpark", "ToFull", ">>>", "<<<", "Load", "LoadNext", "LoadPrev",
    "Rate1", "Learn", "Black", "DoubleSpeed", "DoubleRate",
    "HalfSpeed", "HalfRate", "Release", "Call", "At", "Empty",
)

EXECUTOR_FADER_FUNCTIONS: tuple[str, ...] = (
    "Master", "Crossfade", "CrossfadeA", "CrossfadeB",
    "Temp", "Speed", "Rate", "MasterFade", "StepFade",
    "StepInFade", "StepOutFade", "ManualXFade", "ChannelFader",
)


# ============================================================================
# HARDKEY CHAINS (PHYSICAL KEY MULTI-PRESS BEHAVIOR)
# ============================================================================
# Source: grandMA2_KMeans_Complete.json — hardkey_chains
# Web-validated from help.malighting.com individual key pages.
# chain_type: multi_press | press_and_hold | time_hold | multi_press_gap | multi_press_cycle

HARDKEY_CHAINS: list[dict] = [
    {
        "physical_key": "Assign",
        "chain_type": "multi_press",
        "presses": [
            {"press": "1x", "keyword": "Assign",     "type": "function", "description": "Define relationships between objects or set properties"},
            {"press": "2x", "keyword": "Label",      "type": "function", "description": "Give names to objects"},
            {"press": "3x", "keyword": "Appearance", "type": "function", "description": "Change frame/background colors of pool objects"},
        ],
    },
    {
        "physical_key": "At",
        "chain_type": "multi_press_and_hold",
        "presses": [
            {"press": "1x",   "keyword": "At",     "type": "helping", "description": "Set attribute values"},
            {"press": "2x",   "keyword": "Normal", "type": "helping", "description": "Reset to default/normal values (100% dimmer)"},
            {"press": "hold", "keyword": "Filter", "type": "object",  "description": "Opens Filter command"},
        ],
    },
    {
        "physical_key": "Please",
        "chain_type": "multi_press_cycle",
        "presses": [
            {"press": "1x",      "keyword": "Execute",      "type": "action", "description": "Execute current command line (= Enter)"},
            {"press": "2x",      "keyword": "Activate All", "type": "action", "description": "Activate all attributes of selection in programmer"},
            {"press": "3x",      "keyword": "Deactivate All", "type": "action", "description": "Deactivate all attributes of selection in programmer"},
            {"press": "4x",      "keyword": "Knock In",     "type": "action", "description": "Knock in times and effect values from playbacks"},
            {"press": "MA+hold", "keyword": "Set Cursor",   "type": "action", "description": "Set cursor in command line"},
        ],
    },
    {
        "physical_key": "Help",
        "chain_type": "multi_press",
        "presses": [
            {"press": "1x", "keyword": "Help",    "type": "function", "description": "Open help system"},
            {"press": "2x", "keyword": "CmdHelp", "type": "function", "description": "List all keywords with shortcuts in command feedback"},
        ],
    },
    {
        "physical_key": "If",
        "chain_type": "multi_press_gap",
        "note": "Unique 4-press chain with gap — 1x is helping, 4x is function. No documented 2x/3x behavior.",
        "presses": [
            {"press": "1x", "keyword": "If", "type": "helping",  "description": "If as helping keyword — filter for operations"},
            {"press": "4x", "keyword": "If", "type": "function", "description": "If as function — deselect fixtures not in selection list"},
        ],
    },
    {
        "physical_key": "Fixture",
        "chain_type": "multi_press",
        "presses": [
            {"press": "1x", "keyword": "Fixture",   "type": "object", "description": "Enter Fixture keyword / set default keyword"},
            {"press": "2x", "keyword": "Selection", "type": "object", "description": "Current programmer fixture/channel selection"},
        ],
    },
    {
        "physical_key": "Full",
        "chain_type": "multi_press",
        "presses": [
            {"press": "1x", "keyword": "Full",          "type": "helping",  "description": "Set selection to 100% dimmer"},
            {"press": "2x", "keyword": "FullHighlight", "type": "function", "description": "Load highlight values into programmer"},
        ],
    },
    {
        "physical_key": "Macro",
        "chain_type": "multi_press",
        "presses": [
            {"press": "1x", "keyword": "Macro",    "type": "object", "description": "Enter Macro keyword / set default keyword"},
            {"press": "2x", "keyword": "Timecode", "type": "object", "description": "Enter Timecode keyword"},
            {"press": "3x", "keyword": "Agenda",   "type": "object", "description": "Enter Agenda keyword"},
        ],
    },
    {
        "physical_key": "Effect",
        "chain_type": "multi_press",
        "presses": [
            {"press": "1x", "keyword": "Effect", "type": "object", "description": "Enter Effect keyword / set default keyword"},
            {"press": "2x", "keyword": "Form",   "type": "object", "description": "Enter Form keyword (effect form library)"},
        ],
    },
    {
        "physical_key": "Blind",
        "chain_type": "time_hold",
        "presses": [
            {"press": "1x",      "keyword": "Blind",     "type": "function", "description": "Toggle live programmer to black"},
            {"press": "hold_2s", "keyword": "BlindEdit", "type": "function", "description": "Switch between Live and separate Blind programmer"},
        ],
    },
    {
        "physical_key": "Backup",
        "chain_type": "multi_press",
        "presses": [
            {"press": "1x", "keyword": "Backup",    "type": "action", "description": "Open Backup menu"},
            {"press": "2x", "keyword": "QuickSave", "type": "action", "description": "Immediate show save (double-tap)"},
        ],
    },
    {
        "physical_key": "Group",
        "chain_type": "press_and_hold",
        "presses": [
            {"press": "1x",   "keyword": "Group",           "type": "object", "description": "Enter Group keyword / set default keyword"},
            {"press": "hold", "keyword": "GroupMasterView", "type": "action", "description": "Opens group master view temporarily while held"},
        ],
    },
]


# ============================================================================
# MA+KEY COMBINATIONS
# ============================================================================
# Source: grandMA2_KMeans_Complete.json — hardkey_chains.ma_key_combinations
# Usage: hold MA key + press secondary key

MA_KEY_COMBOS: list[dict] = [
    {"combo": "MA+List",    "keyword": "List",            "type": "function"},
    {"combo": "MA+Macro",   "keyword": "Timer",           "type": "object"},
    {"combo": "MA+Goto",    "keyword": "Load",            "type": "function"},
    {"combo": "MA+Store",   "keyword": "StoreLook",       "type": "function"},
    {"combo": "MA+Copy",    "keyword": "Export",          "type": "function"},
    {"combo": "MA+Move",    "keyword": "Import",          "type": "function"},
    {"combo": "MA+Update",  "keyword": "AutoCreate",      "type": "function"},
    {"combo": "MA+Off",     "keyword": "Kill",            "type": "function"},
    {"combo": "MA+Next",    "keyword": "NextRow",         "type": "helping"},
    {"combo": "MA+Previous","keyword": "PrevRow",         "type": "helping"},
    {"combo": "MA+Go+",     "keyword": "DefGoForward",    "type": "function"},
    {"combo": "MA+Go-",     "keyword": "DefGoBack",       "type": "function"},
    {"combo": "MA+Pause",   "keyword": "DefGoPause",      "type": "function"},
    {"combo": "MA+Edit",    "keyword": "BlindEdit",       "type": "function"},
    {"combo": "MA+Fix",     "keyword": "SelFix",          "type": "helping"},
    {"combo": "MA+Clear",   "keyword": "ClearAll",        "type": "function"},
    {"combo": "MA+Preview", "keyword": "PreviewEdit",     "type": "function"},
    {"combo": "MA+Group",   "keyword": "Layout",          "type": "object"},
    {"combo": "MA+On",      "keyword": "On (latch)",      "type": "function"},
    {"combo": "MA+Select",  "keyword": "SearchResult",    "type": "object"},
    {"combo": "MA+Oops",    "keyword": "ListOops",        "type": "function"},
    {"combo": "MA+B.O.",    "keyword": "BlackScreen",     "type": "function"},
    {"combo": "MA+Top",     "keyword": "SnapPercent",     "type": "helping"},
    {"combo": "MA+Align",   "keyword": "ShuffleSelection","type": "function"},
    {"combo": "MA+Thru",    "keyword": "AllRows",         "type": "helping"},
    {"combo": "MA+Down",    "keyword": "ToZero",          "type": "helping"},
    {"combo": "MA+Full",    "keyword": "ToFull",          "type": "helping"},
    {"combo": "MA+Time",    "keyword": "CmdDelay",        "type": "helping"},
    {"combo": "MA+Please",  "keyword": "SetCursor",       "type": "action"},
]


# ============================================================================
# OAUTH 2.1 SCOPE DEFINITIONS (MCP Authorization Layer)
# ============================================================================
# Hierarchical colon-separated scopes following the gma2:category:action pattern.
# Tiers are cumulative: tier N implies all scopes from tiers 0..N-1.
# Used by src/auth.py to enforce per-tool authorization.
# Reference: MCP Authorization spec (2025-06), OAuth 2.1 RFC 9700

from enum import StrEnum as _StrEnum  # noqa: E402


class OAuthScope(_StrEnum):
    """OAuth 2.1 scopes for the grandMA2 MCP server."""

    # Tier 0 — discovery (no console connection required)
    DISCOVER         = "gma2:discover"
    STATE_READ       = "gma2:state:read"

    # Tier 1 — playback operators
    PLAYBACK_GO      = "gma2:playback:go"
    EXECUTOR_CTRL    = "gma2:executor:control"

    # Tier 2 — preset/programmer operators
    PROGRAMMER_WRITE = "gma2:programmer:write"
    PRESET_UPDATE    = "gma2:preset:update"

    # Tier 3 — show programmers (full programming access)
    CUE_STORE        = "gma2:cue:store"
    SEQUENCE_EDIT    = "gma2:sequence:edit"
    GROUP_STORE      = "gma2:group:store"
    MACRO_EDIT       = "gma2:macro:edit"
    EFFECT_EDIT      = "gma2:effect:edit"
    FILTER_MANAGE    = "gma2:filter:manage"

    # Tier 4 — technical directors / setup
    SETUP_CONSOLE    = "gma2:setup:console"
    NETWORK_CONFIG   = "gma2:network:config"
    PATCH_WRITE      = "gma2:patch:write"
    FIXTURE_IMPORT   = "gma2:fixture:import"

    # Tier 5 — admin only
    USER_MANAGE      = "gma2:user:manage"
    SESSION_MANAGE   = "gma2:session:manage"
    SHOW_LOAD        = "gma2:show:load"
    SYSTEM_ADMIN     = "gma2:system:admin"


# Tier → scopes defined at that tier (non-cumulative; see auth.py for expansion).
OAUTH_TIER_SCOPES: dict[int, list[OAuthScope]] = {
    0: [OAuthScope.DISCOVER, OAuthScope.STATE_READ],
    1: [OAuthScope.PLAYBACK_GO, OAuthScope.EXECUTOR_CTRL],
    2: [OAuthScope.PROGRAMMER_WRITE, OAuthScope.PRESET_UPDATE],
    3: [OAuthScope.CUE_STORE, OAuthScope.SEQUENCE_EDIT, OAuthScope.GROUP_STORE,
        OAuthScope.MACRO_EDIT, OAuthScope.EFFECT_EDIT, OAuthScope.FILTER_MANAGE],
    4: [OAuthScope.SETUP_CONSOLE, OAuthScope.NETWORK_CONFIG,
        OAuthScope.PATCH_WRITE, OAuthScope.FIXTURE_IMPORT],
    5: [OAuthScope.USER_MANAGE, OAuthScope.SESSION_MANAGE,
        OAuthScope.SHOW_LOAD, OAuthScope.SYSTEM_ADMIN],
}

# MA2 console rights level names (for documentation and bootstrap scripts).
# Maps the integer rights level (0-5) to its display name.
MA2_RIGHTS_LEVELS: dict[int, str] = {
    0: "None",
    1: "Playback",
    2: "Presets",
    3: "Program",
    4: "Setup",
    5: "Admin",
}

# MA2 console usernames for the dual-enforcement bootstrap.
# Each user is pre-created in the show file with the corresponding rights level.
# Passwords are stored in the credential vault (never hardcoded here).
MA2_BOOTSTRAP_USERS: list[dict] = [
    {"slot": 1, "name": "administrator",  "rights": 5, "scope_tier": 5,
     "description": "Full admin — created by MA2 default, remapped with strong password"},
    {"slot": 2, "name": "operator",       "rights": 1, "scope_tier": 1,
     "description": "House lighting operator — Go/Off/On playback only"},
    {"slot": 3, "name": "presets_editor", "rights": 2, "scope_tier": 2,
     "description": "Preset editor — update existing presets, no new cue/sequence store"},
    {"slot": 4, "name": "programmer",     "rights": 3, "scope_tier": 3,
     "description": "Show programmer — full cue/preset/group/sequence access"},
    {"slot": 5, "name": "tech_director",  "rights": 4, "scope_tier": 4,
     "description": "Technical director — patch, fixture import, console setup"},
    {"slot": 6, "name": "guest",          "rights": 0, "scope_tier": 0,
     "description": "Read-only monitoring — no programmer access"},
]


# ============================================================================
# MA2 NATIVE RIGHTS ↔ OAUTH SCOPE MAPPING
# ============================================================================
# grandMA2 has a 6-tier native rights ladder that maps directly onto the
# OAuth scope tiers defined above.  Use MA2Right as the single source of
# truth when annotating tools — derive the required OAuthScope from it.

class MA2Right(_StrEnum):
    """grandMA2 native rights levels (6-tier ladder, lowest→highest)."""
    NONE     = "none"      # rights=0  Guest / monitoring — no programming
    PLAYBACK = "playback"  # rights=1  Operator — Go/Flash/Off only
    PRESETS  = "presets"   # rights=2  Preset editor — update existing presets
    PROGRAM  = "program"   # rights=3  Programmer — full cue/group/sequence store
    SETUP    = "setup"     # rights=4  Technical director — patch + console setup
    ADMIN    = "admin"     # rights=5  Administrator — user management + show ops


# Maps MA2Right to the lowest OAuthScope that satisfies that rights level.
# Cumulative: PROGRAM rights implies PRESETS, PLAYBACK, and NONE are also granted.
MA2RIGHT_TO_OAUTH_SCOPE: dict[MA2Right, OAuthScope] = {
    MA2Right.NONE:     OAuthScope.STATE_READ,
    MA2Right.PLAYBACK: OAuthScope.PLAYBACK_GO,
    MA2Right.PRESETS:  OAuthScope.PROGRAMMER_WRITE,
    MA2Right.PROGRAM:  OAuthScope.CUE_STORE,
    MA2Right.SETUP:    OAuthScope.SETUP_CONSOLE,
    MA2Right.ADMIN:    OAuthScope.USER_MANAGE,
}


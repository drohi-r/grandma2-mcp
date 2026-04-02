"""
Command Builder Module for grandMA2

This module provides high-level functions to construct grandMA2 command strings.
These functions are responsible only for generating correctly formatted commands,
not for sending them.

According to coding-standards.md, these functions are "thin wrappers" that
only construct MA commands without any Telnet logic.

=============================================================================
grandMA2 Keyword Classification
=============================================================================

The grandMA2 command line syntax follows these general rules:
- Basic syntax: [Function] [Object]
- All objects have a default function which is used if no function is given.
- Most functions have a default object or object type.
- Objects are arranged in a hierarchical tree structure.

Keywords are classified into three types:

1. HELPING KEYWORDS (Prepositions/Conjunctions)
   - Used to create relations between functions and objects
   - Examples: At, Thru, +, If, While

2. OBJECT KEYWORDS (Nouns)
   - Used to allocate objects in your show file
   - Usually used with numbers, IDs, names, and labels
   - Examples: Fixture, Channel, Group, Preset, Cue, Sequence, Executor

3. FUNCTION KEYWORDS (Verbs)
   - Perform a task or function
   - Often followed by objects to which the function applies
   - Some functions are global and don't need objects (e.g., Blackout)
   - Examples: Store, Delete, Copy, Goto, Clear, Label, SelFix

=============================================================================
"""

# Constants
# Busking / Performance Layer
from .busking import (
    assign_effect_to_executor,
    executor_page_range,
    release_effects_on_page,
    set_effect_rate,
    set_effect_speed,
    zero_page_faders,
)
from .constants import (
    MA2RIGHT_TO_OAUTH_SCOPE,
    PRESET_TYPES,
    STORE_BOOL_OPTIONS,
    STORE_FLAG_OPTIONS,
    STORE_VALUE_OPTIONS,
    MA2Right,
)

# Function Keywords
from .functions import (
    # Helping Keywords (Plus +, Minus -, And, If)
    add_to_selection,
    add_user_var,
    add_var,
    # Align / Invert / Fix / Locate
    align,
    # MAtricks Command Keywords
    all_rows_sub_selection,
    all_sub_selection,
    # Appearance Function Keyword
    appearance,
    # Assign Function Keyword
    assign,
    assign_delay,
    assign_fade,
    assign_function,
    assign_property,
    assign_to_layout,
    # At Function Keyword
    at,
    at_full,
    at_relative,
    at_zero,
    attribute_at,
    # Blackout
    blackout,
    blind,
    # Block / Unblock (generic + sequence-scoped)
    block,
    block_cue,
    unblock_cue,
    # Masters
    master_at,
    special_master_at,
    list_masters,
    build_assign_world_to_user_profile,
    build_delete_user,
    build_list_users,
    build_login,
    build_logout,
    build_assign_executor_option,
    build_set_executor_priority,
    build_store_user,
    call_plugin,
    chaser_rate,
    chaser_skip,
    chaser_speed,
    chaser_xfade,
    lock_console,
    rdm_automatch,
    rdm_autopatch,
    rdm_info,
    rdm_list,
    rdm_setpatch,
    rdm_unmatch,
    reload_plugins,
    run_lua,
    set_effect_parameter,
    set_special_master,
    unlock_console,
    lua_execute,
    reboot_console,
    restart_console,
    shutdown_console,
    send_chat,
    SPECIAL_MASTER_NAMES,
    # Call Function Keywords
    call,
    # Other Function Keywords
    call_preset,
    # Navigation Function Keywords
    changedest,
    channel_at,
    clear,
    clear_active,
    clear_all,
    clear_selection,
    # Clone
    clone,
    condition_and,
    # Copy Function Keyword
    copy,
    copy_cue,
    # Cut Function Keyword
    cut,
    def_go_back,
    def_go_forward,
    def_go_pause,
    # Delete Function Keyword
    delete,
    delete_cue,
    delete_fixture,
    delete_group,
    delete_messages,
    delete_preset,
    delete_show,
    # Edit Function Keyword
    edit,
    empty,
    executor_at,
    # Import/Export Function Keywords
    export_object,
    fix_fixture,
    fixture_at,
    flash_executor,
    extract,
    flip,
    freeze,
    freeze_executor,
    get_user_var,
    go,
    go_back,
    go_back_executor,
    go_executor,
    go_fast_back,
    go_fast_forward,
    go_macro,
    go_sequence,
    goto,
    goto_cue,
    goto_timecode,
    group_at,
    highlight,
    if_condition,
    import_fixture_type_cmd,
    import_layer_cmd,
    import_object,
    # Info Function Keyword
    info,
    info_cue,
    info_group,
    info_preset,
    # Invert
    invert,
    # Label Function Keyword
    label,
    label_group,
    label_preset,
    list_attribute,
    list_cue,
    list_effect_library,
    list_fader_modules,
    list_group,
    list_library,
    list_macro_library,
    list_messages,
    # List Function Keyword
    list_objects,
    list_oops,
    list_plugin_library,
    list_preset,
    list_shows,
    list_update,
    list_user_var,
    list_var,
    load_next,
    load_prev,
    load_show,
    locate,
    # Macro Placeholder / Condition
    macro_with_input_after,
    macro_with_input_before,
    macro_condition_line,
    record_macro,
    VALID_CONDITION_OPERATORS,
    # Masters
    double_rate,
    half_rate,
    double_speed,
    half_speed,
    kill_executor,
    learn_executor,
    toggle_executor,
    matricks_blocks,
    matricks_filter,
    matricks_groups,
    matricks_interleave,
    matricks_reset,
    matricks_wings,
    # Move Function Keyword
    move,
    new_show,
    next_row_sub_selection,
    next_sub_selection,
    off_executor,
    on_executor,
    oops,
    page_next,
    page_previous,
    # Park Function Keywords
    park,
    # Paste Function Keyword
    paste,
    pause_sequence,
    preset_type_at,
    previous_sub_selection,
    recall_matricks,
    release_executor,
    # Remove Function Keyword
    remove,
    remove_effect,
    remove_fixture,
    remove_from_selection,
    remove_preset_type,
    remove_selection,
    save_show,
    select_fixture,
    select_group,
    # Variable Function Keywords
    set_user_var,
    set_var,
    solo,
    solo_executor,
    stomp_executor,
    store,
    store_cue,
    store_cue_timed,
    store_group,
    store_look,
    store_matricks,
    store_preset,
    swop_executor,
    temp_fader,
    top_executor,
    unblock,
    unpark,
    update,
    update_cue,
)

# Helpers (public API)
from .helpers import MA2_SPECIAL_CHARS, quote_name

# Object Keywords
from .objects import (
    attribute,
    channel,
    cue,
    cue_part,
    dmx,
    dmx_universe,
    executor,
    feature,
    fixture,
    group,
    layout,
    preset,
    preset_type,
    sequence,
    timecode,
    timecode_slot,
    timer,
)

__all__ = [
    # Constants
    "MA2Right",
    "MA2RIGHT_TO_OAUTH_SCOPE",
    "PRESET_TYPES",
    "STORE_FLAG_OPTIONS",
    "STORE_BOOL_OPTIONS",
    "STORE_VALUE_OPTIONS",
    # Helpers (wildcard spec)
    "MA2_SPECIAL_CHARS",
    "quote_name",
    # Object Keywords
    "attribute",
    "feature",
    "fixture",
    "channel",
    "group",
    "layout",
    "preset",
    "preset_type",
    "cue",
    "cue_part",
    "sequence",
    "executor",
    "dmx",
    "dmx_universe",
    "timecode",
    "timecode_slot",
    "timer",
    # Blackout
    "blackout",
    # Import/Export Function Keywords
    "export_object",
    "import_object",
    "import_fixture_type_cmd",
    "import_layer_cmd",
    # Assign Function Keyword
    "assign",
    "assign_delay",
    "assign_property",
    "assign_fade",
    "assign_function",
    "assign_to_layout",
    "build_assign_executor_option",
    "build_set_executor_priority",
    "empty",
    "temp_fader",
    # Label Function Keyword
    "label",
    # Appearance Function Keyword
    "appearance",
    # At Function Keyword
    "at",
    "at_full",
    "at_zero",
    "attribute_at",
    "fixture_at",
    "channel_at",
    "group_at",
    "executor_at",
    "preset_type_at",
    # Edit Function Keyword
    "edit",
    # Cut Function Keyword
    "cut",
    # Paste Function Keyword
    "paste",
    # Copy Function Keyword
    "copy",
    "copy_cue",
    # Move Function Keyword
    "move",
    # Clone (DESTRUCTIVE)
    "clone",
    # Block / Unblock (DESTRUCTIVE)
    "block",
    "unblock",
    # Macro Placeholder (@ Character)
    "macro_with_input_after",
    "macro_with_input_before",
    # MAtricks Command Keywords
    "matricks_interleave",
    "matricks_blocks",
    "matricks_groups",
    "matricks_wings",
    "matricks_filter",
    "matricks_reset",
    "recall_matricks",
    "all_sub_selection",
    "all_rows_sub_selection",
    "next_sub_selection",
    "previous_sub_selection",
    "next_row_sub_selection",
    # Other Function Keywords
    "store",
    "store_cue",
    "store_group",
    "store_matricks",
    "store_preset",
    "select_fixture",
    "clear",
    "clear_selection",
    "clear_active",
    "clear_all",
    # Fix / Locate / Invert / Align
    "fix_fixture",
    "locate",
    "invert",
    "align",
    "label_group",
    "label_preset",
    # Delete Function Keyword
    "delete",
    "delete_cue",
    "delete_fixture",
    "delete_group",
    "delete_messages",
    "delete_preset",
    # Remove Function Keyword
    "remove",
    "remove_effect",
    "remove_fixture",
    "remove_preset_type",
    "remove_selection",
    # List Function Keyword
    "list_objects",
    "list_attribute",
    "list_cue",
    "list_group",
    "list_messages",
    "list_preset",
    # List* (specialized)
    "list_shows",
    "list_oops",
    "list_library",
    "list_effect_library",
    "list_macro_library",
    "list_plugin_library",
    "list_fader_modules",
    "list_update",
    # Info Function Keyword
    "info",
    "info_cue",
    "info_group",
    "info_preset",
    # Go
    "go",
    "go_executor",
    "go_macro",
    # GoBack
    "go_back",
    "go_back_executor",
    # Goto
    "goto",
    # Go/Pause/Goto (Legacy)
    "go_sequence",
    "pause_sequence",
    "goto_cue",
    # GoFast (<<< and >>>)
    "go_fast_back",
    "go_fast_forward",
    # DefGo (Selected Executor)
    "def_go_back",
    "def_go_forward",
    "def_go_pause",
    # Executor on/off/flash/swop/top/stomp/solo/release
    "on_executor",
    "off_executor",
    "flash_executor",
    "swop_executor",
    "top_executor",
    "stomp_executor",
    "solo",
    "solo_executor",
    "release_executor",
    # Load next/prev cue
    "load_next",
    "load_prev",
    # Blind / Freeze
    "blind",
    "freeze",
    # Highlight
    "highlight",
    # Timecode goto
    "goto_timecode",
    # Helping Keywords (Plus +, Minus -, And, If)
    "at_relative",
    "add_to_selection",
    "remove_from_selection",
    "page_next",
    "page_previous",
    "condition_and",
    "if_condition",
    # Park Function Keywords
    "park",
    "unpark",
    # Call Function Keywords
    "call",
    # Variable Function Keywords
    "set_user_var",
    "set_var",
    "add_user_var",
    "add_var",
    "get_user_var",
    "list_var",
    "list_user_var",
    # Show Management
    "load_show",
    "new_show",
    "save_show",
    "delete_show",
    # Navigation Function Keywords
    "changedest",
    # Store / Update
    "store_cue_timed",
    "update",
    "update_cue",
    # Oops (undo)
    "oops",
    # Backward Compatibility Aliases
    "select_group",
    "call_preset",
    # User Management
    "build_login",
    "build_logout",
    "build_list_users",
    "build_store_user",
    "build_delete_user",
    "build_assign_world_to_user_profile",
    # System / Console
    "lock_console",
    "unlock_console",
    # Plugin / Lua
    "call_plugin",
    "run_lua",
    "lua_execute",
    "reload_plugins",
    # Special Master
    "set_special_master",
    "SPECIAL_MASTER_NAMES",
    # RDM
    "rdm_automatch",
    "rdm_autopatch",
    "rdm_list",
    "rdm_info",
    "rdm_setpatch",
    "rdm_unmatch",
    # Chaser live control
    "chaser_rate",
    "chaser_speed",
    "chaser_skip",
    "chaser_xfade",
    # Effect programmer parameters
    "set_effect_parameter",
    # Masters
    "master_at",
    "special_master_at",
    "list_masters",
    # Executor — block/unblock (sequence-scoped)
    "block_cue",
    "unblock_cue",
    # Executor — learn / kill / toggle / freeze
    "learn_executor",
    "kill_executor",
    "toggle_executor",
    "freeze_executor",
    # Rate / speed modifiers
    "double_rate",
    "half_rate",
    "double_speed",
    "half_speed",
    # Selection — flip
    "flip",
    # Store — look
    "store_look",
    # Edit — extract
    "extract",
    # Macro — conditional / record
    "VALID_CONDITION_OPERATORS",
    "macro_condition_line",
    "record_macro",
    # Console lifecycle
    "reboot_console",
    "restart_console",
    "shutdown_console",
    "send_chat",
    # Lua alias
    "lua_execute",
    # Busking / Performance Layer
    "assign_effect_to_executor",
    "set_effect_rate",
    "set_effect_speed",
    "release_effects_on_page",
    "zero_page_faders",
    "executor_page_range",
]

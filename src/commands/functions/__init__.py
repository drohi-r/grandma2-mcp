"""
Function Keywords for grandMA2 Command Builder

This module organizes Function Keywords by functionality into multiple submodules:
- store.py: Store-related functions
- selection.py: Selection and clear-related functions
- playback.py: Playback control-related functions
- edit.py: Edit operations (Copy, Move, Delete, Remove)
- assignment.py: Assignment-related functions
- labeling.py: Label and appearance-related functions
- values.py: Value setting functions (At keyword)
- info.py: Information query functions (List, Info)
- macro.py: Macro placeholder-related functions

Function keywords are the "verbs" of the console. They perform a task or
function and are often followed by objects to which the function applies.
Some functions are global and do not need to be followed by objects.

Examples: Store, Delete, Copy, Goto, Clear, Label, SelFix, Go, Pause
"""

# Store Function Keywords
# Backward Compatibility Aliases
# select_group -> group (from objects.py)
# call_preset -> preset (from objects.py)
from ..objects import group as select_group
from ..objects import preset as call_preset

# Assignment Function Keywords
from .assignment import (
    assign,
    assign_delay,
    assign_fade,
    assign_function,
    assign_property,
    assign_to_layout,
    build_assign_executor_option,
    build_set_executor_priority,
    empty,
    temp_fader,
)

# Call Function Keywords
from .call import (
    call,
)

# Edit Function Keywords (Edit, Cut, Paste, Copy, Move, Delete, Remove, Clone, Block, Unblock, Extract)
from .edit import (
    block,
    clone,
    copy,
    copy_cue,
    cut,
    delete,
    delete_cue,
    delete_fixture,
    delete_group,
    delete_messages,
    delete_preset,
    edit,
    extract,
    move,
    oops,
    paste,
    remove,
    remove_effect,
    remove_fixture,
    remove_preset_type,
    remove_selection,
    unblock,
)

# Helping Keywords (Plus +, Minus -, And, If)
from .helping import (
    add_to_selection,
    at_relative,
    condition_and,
    if_condition,
    page_next,
    page_previous,
    remove_from_selection,
)

# Import/Export Function Keywords
from .importexport import (
    export_object,
    import_fixture_type_cmd,
    import_layer_cmd,
    import_object,
)

# Info Function Keywords (List, Info)
from .info import (
    info,
    info_cue,
    info_group,
    info_preset,
    list_attribute,
    list_cue,
    list_effect_library,
    list_fader_modules,
    list_group,
    list_library,
    list_macro_library,
    list_messages,
    list_objects,
    list_oops,
    list_plugin_library,
    list_preset,
    list_shows,
    list_update,
)

# Labeling Function Keywords (Label, Appearance)
from .labeling import (
    appearance,
    label,
    label_group,
    label_preset,
)

# Macro Placeholder / Condition Function Keywords
from .macro import (
    macro_with_input_after,
    macro_with_input_before,
    macro_condition_line,
    record_macro,
    VALID_CONDITION_OPERATORS,
)

# Master Function Keywords
from .masters import (
    master_at,
    special_master_at,
    list_masters,
)

# MAtricks Command Keywords
from .matricks import (
    all_rows_sub_selection,
    all_sub_selection,
    matricks_blocks,
    matricks_filter,
    matricks_groups,
    matricks_interleave,
    matricks_reset,
    matricks_wings,
    next_row_sub_selection,
    next_sub_selection,
    previous_sub_selection,
    recall_matricks,
)

# Navigation Function Keywords (ChangeDest / cd)
from .navigation import (
    changedest,
)

# Park Function Keywords (Park, Unpark)
from .park import (
    park,
    unpark,
)

# Playback Function Keywords (Go, Pause, Goto, GoFast, DefGo, Swop, Top, Stomp, Load)
from .playback import (
    blackout,
    blind,
    block_cue,
    def_go_back,
    def_go_forward,
    def_go_pause,
    double_rate,
    double_speed,
    flash_executor,
    freeze,
    freeze_executor,
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
    half_rate,
    half_speed,
    kill_executor,
    learn_executor,
    load_next,
    load_prev,
    off_executor,
    on_executor,
    pause_sequence,
    release_executor,
    solo,
    solo_executor,
    stomp_executor,
    swop_executor,
    toggle_executor,
    top_executor,
    unblock_cue,
)

# Selection Function Keywords (SelFix, Clear, Fix, Locate, Invert, Align, Flip)
from .selection import (
    align,
    clear,
    clear_active,
    clear_all,
    clear_selection,
    fix_fixture,
    flip,
    highlight,
    invert,
    locate,
    select_fixture,
)
from .store import (
    delete_show,
    load_show,
    new_show,
    save_show,
    store,
    store_cue,
    store_cue_timed,
    store_group,
    store_look,
    store_matricks,
    store_preset,
    update,
    update_cue,
)

# User Management Function Keywords (Login, Logout, Store/Delete User)
from .users import (
    build_assign_world_to_user_profile,
    build_delete_user,
    build_list_users,
    build_login,
    build_logout,
    build_store_user,
)

# System / Console / RDM / Chaser / Effect parameter builders
from .system import (
    lock_console,
    unlock_console,
    call_plugin,
    run_lua,
    lua_execute,
    reload_plugins,
    reboot_console,
    restart_console,
    shutdown_console,
    send_chat,
    set_special_master,
    SPECIAL_MASTER_NAMES,
    rdm_automatch,
    rdm_autopatch,
    rdm_list,
    rdm_info,
    rdm_setpatch,
    rdm_unmatch,
    chaser_rate,
    chaser_speed,
    chaser_skip,
    chaser_xfade,
    set_effect_parameter,
)

# Values Function Keywords (At)
from .values import (
    at,
    at_full,
    at_zero,
    attribute_at,
    channel_at,
    executor_at,
    fixture_at,
    group_at,
    preset_type_at,
)

# Variable Function Keywords
from .variables import (
    add_user_var,
    add_var,
    get_user_var,
    list_user_var,
    list_var,
    set_user_var,
    set_var,
)

__all__ = [
    # Import/Export Function Keywords
    "export_object",
    "import_object",
    "import_fixture_type_cmd",
    "import_layer_cmd",
    # Store / Update / Show management
    "store",
    "store_cue",
    "store_cue_timed",
    "store_group",
    "store_matricks",
    "store_preset",
    "save_show",
    "delete_show",
    "update",
    "update_cue",
    # SelFix
    "select_fixture",
    # Clear
    "clear",
    "clear_selection",
    "clear_active",
    "clear_all",
    # Fix / Locate / Invert / Align
    "fix_fixture",
    "locate",
    "invert",
    "align",
    # Label
    "label",
    "label_group",
    "label_preset",
    # Delete
    "delete",
    "delete_cue",
    "delete_group",
    "delete_preset",
    "delete_fixture",
    "delete_messages",
    # Remove
    "remove",
    "remove_selection",
    "remove_preset_type",
    "remove_fixture",
    "remove_effect",
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
    # GoFast
    "go_fast_back",
    "go_fast_forward",
    # DefGo (Selected Executor)
    "def_go_back",
    "def_go_forward",
    "def_go_pause",
    # Executor on/off/flash/swop/solo/top/stomp/release
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
    # Blackout
    "blackout",
    # Blind / Freeze (universal toggles)
    "blind",
    "freeze",
    # Highlight
    "highlight",
    # Timecode goto
    "goto_timecode",
    # Edit
    "edit",
    # Cut
    "cut",
    # Paste
    "paste",
    # Copy
    "copy",
    "copy_cue",
    # Move
    "move",
    # Clone (DESTRUCTIVE)
    "clone",
    # Block / Unblock (DESTRUCTIVE)
    "block",
    "unblock",
    # Oops (undo)
    "oops",
    # Assign
    "assign",
    "assign_delay",
    "assign_property",
    "assign_function",
    "assign_fade",
    "assign_to_layout",
    "build_assign_executor_option",
    "build_set_executor_priority",
    "empty",
    "temp_fader",
    # Appearance
    "appearance",
    # At
    "at",
    "at_full",
    "at_zero",
    "fixture_at",
    "channel_at",
    "group_at",
    "executor_at",
    "preset_type_at",
    "attribute_at",
    # List
    "list_objects",
    "list_cue",
    "list_group",
    "list_preset",
    "list_attribute",
    "list_messages",
    # List* (specialized)
    "list_shows",
    "list_oops",
    "list_library",
    "list_effect_library",
    "list_macro_library",
    "list_plugin_library",
    "list_fader_modules",
    "list_update",
    # Info
    "info",
    "info_group",
    "info_cue",
    "info_preset",
    # Macro Placeholder
    "macro_with_input_after",
    "macro_with_input_before",
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
    # Navigation Function Keywords
    "changedest",
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
    # Playback — executor control
    "block_cue",
    "unblock_cue",
    "learn_executor",
    "kill_executor",
    "toggle_executor",
    "freeze_executor",
    # Playback — rate / speed modifiers
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
    # System — lifecycle / lua alias / chat
    "lua_execute",
    "reboot_console",
    "restart_console",
    "shutdown_console",
    "send_chat",
]

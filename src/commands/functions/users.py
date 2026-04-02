"""
User Management Command Builders for grandMA2

Pure command-builder functions for managing console users and user profiles.
These functions return MA2 command strings only — no I/O.

grandMA2 user rights levels:
    0 = None     (view/playback only, no programmer)
    1 = Playback (run show, no store)
    2 = Presets  (update existing presets only)
    3 = Program  (full show programming)
    4 = Setup    (patch, fixture import, console setup; no user/session management)
    5 = Admin    (full access including user management and show load)

The two built-in users (Administrator rights=5, Guest rights=0) exist in all shows
and cannot be deleted. Additional users are created via Store User commands.

Telnet syntax (v3.9.60):
    Login "username" "password"
    Logout
    list user
    Store User [slot]           — creates/overwrites user in slot N
    Delete User [slot] /noconfirm
"""

from __future__ import annotations

from ..constants import MA2_RIGHTS_LEVELS


def build_login(username: str, password: str) -> str:
    """
    Authenticate to the grandMA2 console as a specific user.

    Args:
        username: Console username
        password: Console password

    Returns:
        str: MA command string

    Examples:
        >>> build_login("operator", "pw123")
        'Login "operator" "pw123"'
    """
    return f'Login "{username}" "{password}"'


def build_logout() -> str:
    """
    Log out the current Telnet session user.

    Returns:
        str: MA command string

    Examples:
        >>> build_logout()
        'Logout'
    """
    return "Logout"


def build_list_users() -> str:
    """
    List all user accounts in the current show file.

    Returns:
        str: MA command string

    Examples:
        >>> build_list_users()
        'list user'
    """
    return "list user"


def build_store_user(
    slot: int,
    name: str,
    password: str,
    rights_level: int,
) -> str:
    """
    Create or overwrite a user account in the show file.

    Requires Admin (rights=5) Telnet session. Writes to show-file user table.
    The command does NOT create a new User Profile — the user will be assigned
    to the Default profile until explicitly changed.

    Args:
        slot: User slot number (1-N; slot 1 = Administrator, always exists)
        name: Username (alphanumeric, no spaces)
        password: Password string (empty string disables password check)
        rights_level: 0=None, 1=Playback, 2=Presets, 3=Program, 4=Setup, 5=Admin

    Returns:
        str: MA command string

    Examples:
        >>> build_store_user(2, "operator", "show123", 1)
        'Store User 2 /name="operator" /password="show123" /rights=1'
        >>> build_store_user(5, "guest", "", 0)
        'Store User 5 /name="guest" /password="" /rights=0'
    """
    if rights_level not in MA2_RIGHTS_LEVELS:
        raise ValueError(
            f"rights_level must be 0-5, got {rights_level}. "
            f"Valid levels: {MA2_RIGHTS_LEVELS}"
        )
    return f'Store User {slot} /name="{name}" /password="{password}" /rights={rights_level}'


def build_delete_user(slot: int) -> str:
    """
    Delete a user account from the show file.

    The built-in Administrator (slot 1) and Guest accounts cannot be deleted.

    Args:
        slot: User slot number to delete

    Returns:
        str: MA command string

    Examples:
        >>> build_delete_user(3)
        'Delete User 3 /noconfirm'
    """
    return f"Delete User {slot} /noconfirm"


def build_assign_world_to_user_profile(
    user_profile_slot: int,
    world_slot: int,
) -> str:
    """
    Assign a World (fixture visibility mask) to a User Profile.

    Restricts all Users with this profile to only access fixtures/attributes
    visible in the specified World. Use world_slot=0 to remove restriction.

    Args:
        user_profile_slot: UserProfile slot number
        world_slot: World slot number (0 = no restriction / remove assignment)

    Returns:
        str: MA command string

    Examples:
        >>> build_assign_world_to_user_profile(3, 4)
        'Assign World 4 At UserProfile 3'
        >>> build_assign_world_to_user_profile(3, 0)
        'Assign World 0 At UserProfile 3'
    """
    return f"Assign World {world_slot} At UserProfile {user_profile_slot}"

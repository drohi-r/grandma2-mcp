"""
Bootstrap grandMA2 Console Users for Dual-Enforcement Authorization Architecture.

Creates (or verifies) the 5 required user accounts in the current show file.
Must be run as the Administrator account (rights=5).

Run once per show file after creating or loading a fresh show:
    python scripts/bootstrap_console_users.py [--dry-run] [--verify-only]

Requires .env or environment:
    GMA_HOST=127.0.0.1
    GMA_PORT=30000
    GMA_USER=administrator
    GMA_PASSWORD=admin   (change this before production!)

Created users:
    Slot 1: administrator  (rights=5, Admin)   — existing MA2 built-in, password change only
    Slot 2: operator       (rights=1, Playback) — house lighting operators
    Slot 3: presets_editor (rights=2, Presets)  — update existing presets, no new cue store
    Slot 4: programmer     (rights=3, Program)  — show programmers
    Slot 5: tech_director  (rights=4, Setup)    — technical directors
    Slot 6: guest          (rights=0, None)     — read-only monitoring

Security notes:
    - Passwords are read from environment variables (see --help for env var names)
    - Default passwords must be changed before network deployment
    - The Guest account has no programmer access and cannot store anything
    - Only the Administrator account can load different show files

MA2 Rights → OAuth Scope Tier mapping:
    rights=0 (None)     → GMA_SCOPE="tier:0"  → gma2:discover, gma2:state:read
    rights=1 (Playback) → GMA_SCOPE="tier:1"  → + gma2:playback:go, gma2:executor:control
    rights=2 (Presets)  → GMA_SCOPE="tier:2"  → + gma2:programmer:write, gma2:preset:update
    rights=3 (Program)  → GMA_SCOPE="tier:3"  → + gma2:cue:store, gma2:sequence:edit, ...
    rights=4 (Setup)    → GMA_SCOPE="tier:4"  → + gma2:setup:console, gma2:patch:write, ...
    rights=5 (Admin)    → GMA_SCOPE="tier:5"  → + gma2:user:manage, gma2:show:load, ...
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from dotenv import load_dotenv

# Load .env before importing project modules
load_dotenv()

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.commands.constants import MA2_BOOTSTRAP_USERS, MA2_RIGHTS_LEVELS
from src.commands import build_list_users, build_store_user
from src.telnet_client import GMA2TelnetClient


# ── Password configuration ────────────────────────────────────────────────────
# Each user's password is read from an environment variable.
# Change these in .env before deploying to a network-connected console.
PASSWORD_ENV_VARS: dict[str, str] = {
    "administrator":  "GMA_ADMIN_PASSWORD",
    "operator":       "GMA_OPERATOR_PASSWORD",
    "presets_editor": "GMA_PRESETS_PASSWORD",
    "programmer":     "GMA_PROGRAMMER_PASSWORD",
    "tech_director":  "GMA_TECH_DIR_PASSWORD",
    "guest":          "GMA_GUEST_PASSWORD",
}

DEFAULT_PASSWORDS: dict[str, str] = {
    "administrator":  os.getenv("GMA_ADMIN_PASSWORD",    "admin"),
    "operator":       os.getenv("GMA_OPERATOR_PASSWORD", "operator"),
    "presets_editor": os.getenv("GMA_PRESETS_PASSWORD",  "presets"),
    "programmer":     os.getenv("GMA_PROGRAMMER_PASSWORD", "programmer"),
    "tech_director":  os.getenv("GMA_TECH_DIR_PASSWORD", "techdir"),
    "guest":          os.getenv("GMA_GUEST_PASSWORD",    ""),  # empty = no password
}


# ── Bootstrap logic ───────────────────────────────────────────────────────────

async def bootstrap(
    host: str,
    port: int,
    admin_user: str,
    admin_password: str,
    dry_run: bool = False,
    verify_only: bool = False,
) -> bool:
    """
    Connect to MA2 console and create/verify all 5 bootstrap user accounts.

    Returns True if all users were created/verified successfully.
    """
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Connecting to grandMA2 at {host}:{port} ...")

    if not dry_run:
        client = GMA2TelnetClient(
            host=host,
            port=port,
            username=admin_user,
            password=admin_password,
        )
        try:
            await client.connect()
            print(f"  Connected and authenticated as '{admin_user}'")
        except Exception as e:
            print(f"  ERROR: Failed to connect — {e}")
            return False

    # List existing users
    print("\nCurrent user list:")
    if not dry_run:
        response = await client.send_command_with_response(build_list_users())
        print(f"  {response[:500]}")

    if verify_only:
        print("\n[verify-only mode] — no changes made")
        if not dry_run:
            await client.disconnect()
        return True

    # Create/update each bootstrap user
    all_ok = True
    print("\nBootstrapping users:")
    for user in MA2_BOOTSTRAP_USERS:
        slot = user["slot"]
        name = user["name"]
        rights = user["rights"]
        rights_name = MA2_RIGHTS_LEVELS[rights]
        password = DEFAULT_PASSWORDS.get(name, "")

        cmd = build_store_user(slot, name, password, rights)
        print(f"  Slot {slot}: {name!r:20s}  rights={rights} ({rights_name})")
        print(f"            cmd: {cmd}")

        if not dry_run:
            try:
                response = await client.send_command_with_response(cmd)
                status = "OK" if "error" not in response.lower() else f"WARN: {response[:80]}"
                print(f"            → {status}")
            except Exception as e:
                print(f"            → ERROR: {e}")
                all_ok = False

    # Verify by listing users again
    if not dry_run:
        print("\nVerifying user list after bootstrap:")
        response = await client.send_command_with_response(build_list_users())
        print(f"  {response[:1000]}")

        # Save the show file with the new users
        save_response = await client.send_command_with_response("SaveShow")
        print(f"\nShow saved: {save_response[:80]}")

        await client.disconnect()
        print("  Disconnected")

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Bootstrap {'completed (dry run)' if dry_run else 'complete'}.")
    print("\nNext steps:")
    print("  1. Set strong passwords via GMA_*_PASSWORD env vars and re-run")
    print("  2. Set GMA_SCOPE in .env matching the rights level of your MCP session:")
    print("     GMA_USER=operator  GMA_SCOPE='tier:1'  (playback ops)")
    print("     GMA_USER=programmer  GMA_SCOPE='tier:3'  (show programming)")
    print("     GMA_USER=administrator  GMA_SCOPE='tier:5'  (full admin)")

    return all_ok


def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap MA2 console users for dual-enforcement authorization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--host", default=os.getenv("GMA_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("GMA_PORT", "30000")))
    parser.add_argument("--user", default=os.getenv("GMA_USER", "administrator"))
    parser.add_argument("--password", default=os.getenv("GMA_PASSWORD", "admin"))
    parser.add_argument("--dry-run", action="store_true",
                        help="Print commands without connecting or executing")
    parser.add_argument("--verify-only", action="store_true",
                        help="List existing users without making changes")
    args = parser.parse_args()

    success = asyncio.run(bootstrap(
        host=args.host,
        port=args.port,
        admin_user=args.user,
        admin_password=args.password,
        dry_run=args.dry_run,
        verify_only=args.verify_only,
    ))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

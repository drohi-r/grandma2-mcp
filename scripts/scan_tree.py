"""
scan_tree.py -- Recursive grandMA2 object-tree scanner via Telnet.

Walks the MA2 console's internal object tree using list-driven traversal:
  1. cd /       — always start at root
  2. list       — enumerate children (get valid indexes from parsed entries)
  3. cd N       — navigate into each child by its parsed index
  4. list       — capture full raw output (headers + columns + values)
  5. cd ..      — return to parent (verified), recover via absolute path if skipped
  6. cd /       — return to root between top-level branches

Key behaviors (validated by live telnet testing on MA2 v3.9):
  - cd / always returns to root (location = "Fixture")
  - cd .. works at most depths but CAN SKIP LEVELS (e.g. depth 4 -> depth 2)
  - cd N to nonexistent index -> Error #72, location unchanged (MISS)
  - Circular refs -> cd N stays at same location (MISS by location check)
  - list output provides valid child indexes (no blind probing needed)
  - Leaves = nodes where list returns 0 entries (natural termination)
  - null parsed location after cd -> treated as MISS, do not recurse

Index extraction strategy:
  - Primary: parse object_id from each list entry as the cd index
  - SubForm fix: when all parsed IDs are identical (e.g. SubForm entries where
    col2=col3=parent_slot), fall back to sequential 1..N indexes
  - Gap probing: after collecting list-derived indexes, probe gaps between
    them (e.g. if list gives [1,2,3,5], probe 4) because some children
    exist but are not shown by list (e.g. VirtualFunctionBlocks at cd 4)

Usage:
    uv run python scan_tree.py [options]

Options:
    --host 127.0.0.1     Console IP (default: from .env)
    --port 30000         Telnet port (default: 30000)
    --max-depth 20       Maximum recursion depth (default: 20)
    --max-nodes 0        Stop after N nodes (0 = unlimited)
    --max-index 60       Fallback index limit when list has no parseable IDs
    --failures 3         Stop a branch after N consecutive missing indexes
    --output scan_output.json
    --delay 0.08         Seconds between commands
    --timeout 0.8        Telnet read timeout per command
    --max-gap-probe 5    Max gap between IDs to probe (default: 5)
    --empty-leaf-limit 10  Stop after N consecutive empty leaves (0=off)
    --health-check-interval 500  Health check every N nodes (0=disabled)
    --no-leaf-shortcut   Disable known-leaf-type optimization
    --progress-file PATH JSONL progress file (auto-derived if empty)
    --resume             Resume scan from progress file
    --heartbeat-every 200  Print heartbeat every N nodes (0=disabled)
    --branch-timeout 0   Per-branch timeout in seconds (0=unlimited)
    --disconnect-timeout 5  Timeout for telnet disconnect (default: 5s)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional

from dotenv import get_key

from src.navigation import navigate, list_destination
from src.prompt_parser import _strip_ansi
from src.telnet_client import GMA2TelnetClient

# Suppress info/debug noise from navigation and telnet layers
logging.basicConfig(level=logging.WARNING)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class ScanConfig:
    host: str = "127.0.0.1"
    port: int = 30000
    user: str = "administrator"
    password: str = "admin"
    max_depth: int = 20           # default 20 — drill all leaves
    max_nodes: int = 0            # 0 = unlimited; stop after N visited nodes
    max_index: int = 60           # fallback limit when list returns no entries
    stop_after_failures: int = 3  # stop probing after N consecutive misses
    output_path: str = "scan_output.json"
    delay: float = 0.08
    timeout: float = 0.8
    max_gap_probe: int = 5        # max gap between consecutive IDs to probe
    empty_leaf_limit: int = 10    # stop after N consecutive empty leaves (0=off)
    health_check_every: int = 500 # health check every N nodes (0=disabled)
    no_leaf_shortcut: bool = False # disable known-leaf optimization
    progress_path: str = ""       # JSONL progress file path (auto if empty)
    resume: bool = False          # resume from progress file
    heartbeat_every: int = 200    # print heartbeat every N nodes (0=disabled)
    branch_timeout: float = 0    # per-branch timeout in seconds (0=unlimited)
    disconnect_timeout: float = 5.0  # timeout for telnet disconnect


# ---------------------------------------------------------------------------
# Tree node
# ---------------------------------------------------------------------------

@dataclass
class TreeNode:
    path: str                        # dot-separated, e.g. "1.3.2"
    index: int                       # the cd N index that entered this node
    location: Optional[str]          # parsed_prompt.location
    object_type: Optional[str]       # parsed_prompt.object_type
    raw_list_text: str               # full stripped list output (headers + all columns)
    raw_list_entries: list[dict]     # serialized ListEntry dicts from list
    is_leaf: bool                    # True = list returned 0 entries
    children: list["TreeNode"] = field(default_factory=list)
    duplicate_of: Optional[str] = None  # path of original if this is a duplicate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LOCATION_TYPE_RE = re.compile(r'^([A-Za-z]\w*)(?:\s|/|$)')

# Types known to be leaves (no children worth scanning)
KNOWN_LEAF_TYPES = {
    "History", "Gel", "RDM_Universe", "Universe", "UserImage",
    "Color", "Effect", "Timer", "Timecode", "RDM_Personality", "SubAttribute",
}


def _structure_signature(entries) -> Optional[str]:
    """Compute a structure-only signature that ignores names and values.

    Hashes (entry_count, tuple_of_object_types) so structurally identical
    nodes match even when they have different names (e.g. UserProfile copies,
    gel libraries with different color names).

    Returns None if no entries.
    """
    if not entries:
        return None
    types = []
    for e in entries:
        otype = e.object_type if hasattr(e, 'object_type') else e.get("object_type")
        types.append(str(otype) if otype else "?")
    return f"struct:{len(entries)}:{','.join(types)}"


def _entries_signature(entries, raw_list_text: str) -> Optional[str]:
    """Compute a hashable signature from list entries for duplicate detection.

    Uses the full raw list text (all column headers + values) as the
    signature.  This is deliberately strict: two nodes match only if their
    ``list`` output is character-for-character identical after ANSI/prompt
    stripping.  This prevents false matches between nodes that share the
    same child *types* but have different content (e.g. different fixture
    types that both have Modules/Instances/Wheels as children).

    Returns None if no entries (leaves can't be dupes).
    """
    if not entries:
        return None
    # The raw list text includes all column values, names, and counts
    # — a much stricter match than just type|id|name tuples
    return raw_list_text if raw_list_text.strip() else None


def _extract_type(location: Optional[str]) -> Optional[str]:
    """Extract the leading word from a location string as the object_type."""
    if not location:
        return None
    m = _LOCATION_TYPE_RE.match(location)
    return m.group(1) if m else None


def _child_indexes_from_entries(entries, max_index: int, max_gap_probe: int = 5) -> list[int]:
    """Extract unique integer indexes from list entries, sorted.

    Uses the object_id from each parsed entry as the cd index.

    Special cases:
      - SubForm bug: if all parsed IDs are the same value (e.g. SubForm
        entries where col2=col3=parent_slot), the IDs don't represent cd
        indexes.  Fall back to sequential 1..N.
      - Smart gap probing: after collecting list-derived indexes, only fill
        gaps ≤ max_gap_probe between consecutive known IDs (e.g. [1,2,3,5]
        with max_gap=5 -> add 4, but [1,467] won't probe all 466 gaps).
      - Falls back to range(1, max_index+1) if no entries have valid IDs.
    """
    raw_ids: list[int] = []
    for e in entries:
        oid = e.object_id if hasattr(e, 'object_id') else e.get("object_id")
        if oid is not None:
            try:
                idx = int(str(oid).split(".")[0])
                raw_ids.append(idx)
            except (ValueError, AttributeError):
                pass

    if not raw_ids:
        return list(range(1, max_index + 1))

    # SubForm fix: if all parsed IDs are identical (e.g. all "2"),
    # they represent the parent's slot number, not cd indexes.
    # Fall back to sequential 1..N where N = number of entries.
    unique_ids = set(raw_ids)
    if len(unique_ids) == 1 and len(raw_ids) > 1:
        return list(range(1, len(entries) + 1))

    # Deduplicate and sort
    indexes = sorted(unique_ids)

    # Smart gap probing: only fill gaps ≤ max_gap_probe between
    # consecutive known IDs to avoid probing huge ranges like [1..467]
    if len(indexes) >= 2 and max_gap_probe > 0:
        filled = []
        for i, cur in enumerate(indexes):
            filled.append(cur)
            if i + 1 < len(indexes):
                nxt = indexes[i + 1]
                gap = nxt - cur - 1
                if 0 < gap <= max_gap_probe:
                    filled.extend(range(cur + 1, nxt))
        indexes = sorted(set(filled))

    return indexes


def _clean_list_text(raw: str) -> str:
    """Strip ANSI codes and command echo/prompt lines from raw list output.

    Returns only the data lines (column headers + entries).
    """
    stripped = _strip_ansi(raw)
    lines = stripped.strip().splitlines()
    data_lines = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith("Executing"):
            continue
        if s.startswith("WARNING"):
            continue
        if s.startswith("Error"):
            continue
        # Skip prompt lines (end with > after stripping)
        if re.search(r'>\s*$', s):
            continue
        data_lines.append(s)
    return "\n".join(data_lines)


def _serialize_entries(entries) -> list[dict]:
    """Convert parsed ListEntry objects to serializable dicts."""
    result = []
    for e in entries:
        d = {
            "object_type": e.object_type,
            "object_id": e.object_id,
            "name": e.name,
            "raw_line": e.raw_line,
        }
        col3 = getattr(e, "col3", None)
        if col3 is not None:
            d["col3"] = col3
        columns = getattr(e, "columns", None)
        if columns:
            d["columns"] = columns
        result.append(d)
    return result


def _entry_type_map(entries) -> dict:
    """Map child index -> object_type from a parent's list entries.

    Used by leaf-type shortcutting to skip ``list`` calls on children
    whose type is in KNOWN_LEAF_TYPES.

    Also stores ``_raw_entries`` (serialized dicts) so the leaf shortcut
    can look up names without navigating.
    """
    type_map: dict = {}
    for e in entries:
        oid = e.object_id if hasattr(e, 'object_id') else e.get("object_id")
        otype = e.object_type if hasattr(e, 'object_type') else e.get("object_type")
        if oid is not None and otype:
            try:
                idx = int(str(oid).split(".")[0])
                type_map[idx] = otype
            except (ValueError, AttributeError):
                pass
    # Map child index -> expected location name (for circular pre-check)
    name_map: dict[int, str] = {}
    for e in entries:
        oid = e.object_id if hasattr(e, 'object_id') else e.get("object_id")
        ename = e.name if hasattr(e, 'name') else e.get("name")
        if oid is not None and ename:
            try:
                idx = int(str(oid).split(".")[0])
                name_map[idx] = ename
            except (ValueError, AttributeError):
                pass
    type_map["_name_map"] = name_map
    # Attach serialized entries for name lookups
    type_map["_raw_entries"] = _serialize_entries(entries)
    return type_map


# ---------------------------------------------------------------------------
# Connection health & reconnect
# ---------------------------------------------------------------------------

MAX_RETRIES = 3           # reconnect attempts per failed command


async def _is_alive(client: GMA2TelnetClient) -> bool:
    """Quick health check: send empty line, expect *some* response."""
    try:
        resp = await client.send_command_with_response(
            "", timeout=0.5, delay=0.02, subsequent_timeout=0.05,
        )
        return resp is not None and len(resp) > 0
    except Exception:
        return False


async def _reconnect(client: GMA2TelnetClient, cfg: ScanConfig) -> None:
    """Disconnect and re-establish the telnet session."""
    print("  [RECONNECT] Connection lost — reconnecting...")
    try:
        await client.disconnect()
    except Exception:
        pass
    await asyncio.sleep(0.5)
    await client.connect()
    await client.login()
    await asyncio.sleep(0.3)
    print("  [RECONNECT] Reconnected and logged in.")


async def _safe_navigate(
    client: GMA2TelnetClient,
    destination: str,
    cfg: ScanConfig,
    abs_path: Optional[list[int]] = None,
):
    """Navigate with automatic reconnect on failure.

    If the command returns an empty response or raises an exception,
    reconnects and re-navigates to abs_path before retrying.
    """
    for attempt in range(MAX_RETRIES):
        try:
            result = await navigate(
                client, destination, timeout=cfg.timeout, delay=cfg.delay
            )
            # Detect dead connection: empty raw response
            if result.raw_response is not None and len(result.raw_response) > 0:
                return result
            if attempt < MAX_RETRIES - 1:
                print(f"  [RECONNECT] Empty response on cd {destination} (attempt {attempt+1})")
                await _reconnect(client, cfg)
                if abs_path is not None:
                    await _navigate_to_path_raw(client, abs_path, cfg)
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                print(f"  [RECONNECT] Error on cd {destination}: {e} (attempt {attempt+1})")
                await _reconnect(client, cfg)
                if abs_path is not None:
                    await _navigate_to_path_raw(client, abs_path, cfg)
            else:
                raise
    # Return last result even if empty
    return await navigate(client, destination, timeout=cfg.timeout, delay=cfg.delay)


async def _safe_list(
    client: GMA2TelnetClient,
    cfg: ScanConfig,
    abs_path: Optional[list[int]] = None,
):
    """List with automatic reconnect on failure."""
    for attempt in range(MAX_RETRIES):
        try:
            result = await list_destination(
                client, timeout=cfg.timeout, delay=cfg.delay
            )
            if result.raw_response is not None and len(result.raw_response) > 0:
                return result
            if attempt < MAX_RETRIES - 1:
                print(f"  [RECONNECT] Empty list response (attempt {attempt+1})")
                await _reconnect(client, cfg)
                if abs_path is not None:
                    await _navigate_to_path_raw(client, abs_path, cfg)
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                print(f"  [RECONNECT] Error on list: {e} (attempt {attempt+1})")
                await _reconnect(client, cfg)
                if abs_path is not None:
                    await _navigate_to_path_raw(client, abs_path, cfg)
            else:
                raise
    return await list_destination(client, timeout=cfg.timeout, delay=cfg.delay)


# ---------------------------------------------------------------------------
# Absolute navigation
# ---------------------------------------------------------------------------

async def _navigate_to_path_raw(
    client: GMA2TelnetClient,
    abs_path: list[int],
    cfg: ScanConfig,
) -> Optional[str]:
    """Navigate from root to an absolute path (no reconnect wrapper).

    Used internally by _reconnect recovery to avoid infinite loops.
    """
    root_nav = await navigate(client, "/", timeout=cfg.timeout, delay=cfg.delay)
    current_loc = root_nav.parsed_prompt.location

    for idx in abs_path:
        nav = await navigate(client, str(idx), timeout=cfg.timeout, delay=cfg.delay)
        new_loc = nav.parsed_prompt.location
        if new_loc is None or new_loc == current_loc:
            return None
        current_loc = new_loc

    return current_loc


async def _navigate_to_path(
    client: GMA2TelnetClient,
    abs_path: list[int],
    cfg: ScanConfig,
) -> Optional[str]:
    """Navigate from root to an absolute path with reconnect support."""
    try:
        return await _navigate_to_path_raw(client, abs_path, cfg)
    except Exception as e:
        print(f"  [RECONNECT] Path navigation failed: {e} — reconnecting")
        await _reconnect(client, cfg)
        return await _navigate_to_path_raw(client, abs_path, cfg)


# ---------------------------------------------------------------------------
# Recursive scanner
# ---------------------------------------------------------------------------

async def _scan_children(
    client: GMA2TelnetClient,
    parent_abs_path: list[int],
    parent_location: Optional[str],
    ancestor_locations: set[str],
    child_indexes: list[int],
    depth: int,
    stats: dict,
    cfg: ScanConfig,
    sig_cache: dict,
    child_type_map: Optional[dict[int, str]] = None,
) -> list[TreeNode]:
    """Scan child indexes at the current console position.

    Assumes the console is cd'd into the parent node (at parent_abs_path).
    On return, the console is back at the parent node.

    For each child:
      1. cd N         — enter child
      2. list         — capture full output (headers + all column values)
      3. [recurse]    — if child has entries, scan its children
         (skip if entries signature matches an already-scanned node)
      4. cd ..        — try to return to parent
      5. [verify]     — if cd .. skipped levels, re-navigate via absolute path
    """
    # Check max_nodes limit
    if cfg.max_nodes > 0 and stats["visited"] >= cfg.max_nodes:
        print(f"  MAX NODES REACHED ({cfg.max_nodes}) — stopping scan")
        return []

    children: list[TreeNode] = []
    consecutive_failures = 0
    consecutive_empty_leaves = 0
    parent_path_str = ".".join(str(i) for i in parent_abs_path) if parent_abs_path else ""

    for idx in child_indexes:
        # Check max_nodes limit
        if cfg.max_nodes > 0 and stats["visited"] >= cfg.max_nodes:
            print(f"  MAX NODES REACHED ({cfg.max_nodes}) — stopping branch")
            break

        # Heartbeat: periodic status during long branches
        if (cfg.heartbeat_every > 0
                and stats["visited"] > 0
                and stats["visited"] % cfg.heartbeat_every == 0):
            elapsed = time.monotonic() - stats.get("_start_time", time.monotonic())
            rate = stats["visited"] / elapsed if elapsed > 0 else 0
            print(
                f"  [HEARTBEAT] {stats['visited']} nodes visited, "
                f"{stats.get('duplicates', 0)} dups, "
                f"{elapsed:.0f}s elapsed ({rate:.1f} nodes/s) — "
                f"depth={depth} path={parent_path_str}"
            )

        # Branch timeout check
        if cfg.branch_timeout > 0:
            branch_elapsed = time.monotonic() - stats.get("_branch_start", time.monotonic())
            if branch_elapsed > cfg.branch_timeout:
                print(
                    f"  [BRANCH TIMEOUT] {branch_elapsed:.0f}s > "
                    f"{cfg.branch_timeout:.0f}s limit — aborting branch {parent_path_str}"
                )
                break

        child_abs_path = parent_abs_path + [idx]
        child_path_str = ".".join(str(i) for i in child_abs_path)

        # Known leaf-type shortcutting: skip cd+list entirely for known leaf types.
        # Build the node from the parent's list entry data — no navigation needed.
        known_leaf = (
            not cfg.no_leaf_shortcut
            and child_type_map is not None
            and child_type_map.get(idx) in KNOWN_LEAF_TYPES
        )

        if known_leaf:
            consecutive_failures = 0
            stats["visited"] += 1
            leaf_type = child_type_map[idx]
            # Look up name from parent entries if available
            leaf_name = None
            for e_raw in (child_type_map.get("_raw_entries") or []):
                oid = e_raw.get("object_id")
                if oid is not None:
                    try:
                        if int(str(oid).split(".")[0]) == idx:
                            leaf_name = e_raw.get("name")
                            break
                    except (ValueError, AttributeError):
                        pass
            location_str = f"{leaf_type} {idx}" if not leaf_name else f"{leaf_type} {idx}/{leaf_name}"
            print(
                f"  [d={depth} | {child_path_str} | "
                f"+{stats['visited']} ~{stats['skipped']}] "
                f"idx {idx} -> {location_str!r} [LEAF-SHORTCUT, no cd]"
            )
            node = TreeNode(
                path=child_path_str,
                index=idx,
                location=location_str,
                object_type=leaf_type,
                raw_list_text="",
                raw_list_entries=[],
                is_leaf=True,
            )
            consecutive_empty_leaves += 1
            children.append(node)
            # No cd was done, so no cd .. needed — continue to next sibling
            # Consecutive empty leaf early exit
            if (cfg.empty_leaf_limit > 0
                    and consecutive_empty_leaves >= cfg.empty_leaf_limit):
                print(
                    f"  Stopping branch at depth {depth}: "
                    f"{cfg.empty_leaf_limit} consecutive empty leaves"
                )
                break
            continue

        # cd N — enter child (with reconnect support)
        nav = await _safe_navigate(client, str(idx), cfg, abs_path=parent_abs_path)
        child_location = nav.parsed_prompt.location

        # MISS: location is None or unchanged from parent
        if child_location is None or child_location == parent_location:
            stats["skipped"] += 1
            print(
                f"  [d={depth} | {child_path_str} | "
                f"+{stats['visited']} ~{stats['skipped']}] "
                f"cd {idx} -> MISS"
            )
            consecutive_failures += 1
            if consecutive_failures >= cfg.stop_after_failures:
                print(
                    f"  Stopping branch at depth {depth}: "
                    f"{cfg.stop_after_failures} consecutive misses"
                )
                break
            continue  # cd didn't move, no cd .. needed

        # CIRCULAR: child location matches an ancestor
        if child_location in ancestor_locations:
            stats["skipped"] += 1
            print(
                f"  [d={depth} | {child_path_str} | "
                f"+{stats['visited']} ~{stats['skipped']}] "
                f"cd {idx} -> CIRCULAR ({child_location!r})"
            )
            await _safe_navigate(client, "..", cfg, abs_path=parent_abs_path)
            consecutive_failures += 1
            if consecutive_failures >= cfg.stop_after_failures:
                break
            continue

        consecutive_failures = 0
        stats["visited"] += 1

        # Periodic health check
        if cfg.health_check_every > 0 and stats["visited"] % cfg.health_check_every == 0:
            if not await _is_alive(client):
                print(f"  [RECONNECT] Health check failed at node {stats['visited']}")
                await _reconnect(client, cfg)
                await _navigate_to_path_raw(client, child_abs_path, cfg)

        # list — capture full raw output + parsed entries (with reconnect)
        child_obj_type = _extract_type(child_location)
        lst = await _safe_list(client, cfg, abs_path=child_abs_path)
        entries = lst.parsed_list.entries
        raw_list_text = _clean_list_text(lst.raw_response)
        raw_entries = _serialize_entries(entries)

        is_leaf = (len(entries) == 0) or (depth >= cfg.max_depth)

        leaf_tag = " [LEAF]" if is_leaf else ""
        if depth >= cfg.max_depth and len(entries) > 0:
            leaf_tag = f" [DEPTH-CAP: {len(entries)} entries not recursed]"
        print(
            f"  [d={depth} | {child_path_str} | "
            f"+{stats['visited']} ~{stats['skipped']}] "
            f"cd {idx} -> {child_location!r} ({len(entries)} entries){leaf_tag}"
        )

        node = TreeNode(
            path=child_path_str,
            index=idx,
            location=child_location,
            object_type=child_obj_type,
            raw_list_text=raw_list_text,
            raw_list_entries=raw_entries,
            is_leaf=is_leaf,
        )

        # Track consecutive empty leaves for early exit
        if is_leaf and len(entries) == 0:
            consecutive_empty_leaves += 1
        else:
            consecutive_empty_leaves = 0

        # Recurse into grandchildren if this is not a leaf
        if not is_leaf:
            sig = _entries_signature(entries, raw_list_text)
            if sig and sig in sig_cache:
                # Duplicate: same list output as a previously scanned node
                original_path = sig_cache[sig]
                node.duplicate_of = original_path
                stats["duplicates"] = stats.get("duplicates", 0) + 1
                dup_count = stats["duplicates"]
                print(
                    f"  DUPLICATE of [{original_path}] "
                    f"-> skipping subtree (dup #{dup_count})"
                )
            else:
                grandchild_indexes = _child_indexes_from_entries(entries, cfg.max_index, cfg.max_gap_probe)
                deeper_ancestors = ancestor_locations | {child_location}
                gc_type_map = _entry_type_map(entries) if not cfg.no_leaf_shortcut else None

                node.children = await _scan_children(
                    client,
                    parent_abs_path=child_abs_path,
                    parent_location=child_location,
                    ancestor_locations=deeper_ancestors,
                    child_indexes=grandchild_indexes,
                    depth=depth + 1,
                    stats=stats,
                    cfg=cfg,
                    sig_cache=sig_cache,
                    child_type_map=gc_type_map,
                )
                # Register this signature after successful full traversal
                if sig:
                    sig_cache[sig] = child_path_str

        children.append(node)

        # cd .. — try to return to parent (with reconnect)
        back_nav = await _safe_navigate(client, "..", cfg, abs_path=child_abs_path)
        back_location = back_nav.parsed_prompt.location

        if back_location != parent_location:
            # cd .. skipped levels or went somewhere unexpected.
            # Recover by navigating to parent via absolute path.
            print(
                f"  cd .. skipped: at {back_location!r}, "
                f"expected {parent_location!r} -> re-navigating"
            )
            recovered_loc = await _navigate_to_path(client, parent_abs_path, cfg)
            if recovered_loc != parent_location:
                # Could not recover — break out of this branch
                print(
                    f"  RECOVERY FAILED: at {recovered_loc!r}, "
                    f"giving up on branch {parent_path_str}"
                )
                break

        # Consecutive empty leaf early exit
        if (cfg.empty_leaf_limit > 0
                and consecutive_empty_leaves >= cfg.empty_leaf_limit):
            print(
                f"  Stopping branch at depth {depth}: "
                f"{cfg.empty_leaf_limit} consecutive empty leaves"
            )
            break

    return children


async def scan_tree(
    client: GMA2TelnetClient,
    cfg: ScanConfig,
) -> tuple[list[TreeNode], dict]:
    """Full recursive tree scan from root.

    Algorithm:
      1. cd /  -> root
      2. list  -> get root children with their indexes + full column output
      3. For each root child:
         a. cd N -> enter child
         b. list -> capture all columns and values
         c. Recurse into sub-levels until list returns 0 entries (leaf)
         d. cd / -> return to root between top-level branches
    """
    stats = {"visited": 0, "skipped": 0, "duplicates": 0,
             "_start_time": time.monotonic(), "_branch_start": time.monotonic()}
    sig_cache: dict[str, str] = {}  # entries_signature -> first path that had it
    progress_path = _progress_file_path(cfg)

    # Resume: load previously completed branches
    resumed_branches: set[int] = set()
    resumed_nodes: list[TreeNode] = []
    if cfg.resume:
        resumed_nodes, resumed_branches, resumed_stats, resumed_sigs = _load_progress(progress_path)
        if resumed_branches:
            stats.update(resumed_stats)
            stats["_start_time"] = time.monotonic()
            sig_cache = resumed_sigs
            print(
                f"Resumed {len(resumed_branches)} branches from {progress_path}\n"
                f"  Continuing with {stats['visited']} visited, "
                f"{stats['skipped']} skipped, {stats.get('duplicates', 0)} duplicates"
            )
    else:
        # Fresh run: truncate progress file to avoid mixing data from prior runs
        import os
        if os.path.exists(progress_path):
            open(progress_path, "w").close()
            print(f"Truncated stale progress file: {progress_path}")

    # Step 1: cd / — go to root
    print("Navigating to root (cd /)...")
    root_nav = await _safe_navigate(client, "/", cfg)
    root_location = root_nav.parsed_prompt.location
    print(f"Root location: {root_location!r}")

    # Step 2: list — enumerate root children with full output
    print("Listing root children...")
    root_list = await _safe_list(client, cfg)
    root_entries = root_list.parsed_list.entries
    root_list_text = _clean_list_text(root_list.raw_response)
    print(f"Root children: {len(root_entries)} entries parsed\n")

    # Extract valid root indexes from list output
    root_indexes = _child_indexes_from_entries(root_entries, cfg.max_index, cfg.max_gap_probe)
    total_root = len(root_indexes)
    nodes_limit_msg = f", max_nodes={cfg.max_nodes}" if cfg.max_nodes > 0 else ""
    print(
        f"Starting scan: max_depth={cfg.max_depth}{nodes_limit_msg}, "
        f"{total_root} root branches: {root_indexes}\n"
    )

    root_children: list[TreeNode] = list(resumed_nodes)
    consecutive_failures = 0
    consecutive_empty_leaves = 0

    for branch_num, idx in enumerate(root_indexes, 1):
        # Skip already-completed branches (resume support)
        if idx in resumed_branches:
            print(f"\n--- Root branch {branch_num}/{total_root} (index {idx}) --- RESUMED (skipping)")
            continue

        # Check max_nodes limit
        if cfg.max_nodes > 0 and stats["visited"] >= cfg.max_nodes:
            print(f"\nMAX NODES REACHED ({cfg.max_nodes}) — stopping scan")
            break

        # Progress indicator + reset per-branch timer
        stats["_branch_start"] = time.monotonic()
        print(f"\n--- Root branch {branch_num}/{total_root} (index {idx}) ---")

        # cd N — enter root child (with reconnect)
        nav = await _safe_navigate(client, str(idx), cfg, abs_path=[])
        child_location = nav.parsed_prompt.location

        # MISS check
        if child_location is None or child_location == root_location:
            stats["skipped"] += 1
            print(
                f"  [d=1 | {idx} | "
                f"+{stats['visited']} ~{stats['skipped']}] "
                f"cd {idx} -> MISS"
            )
            consecutive_failures += 1
            if consecutive_failures >= cfg.stop_after_failures:
                print(
                    f"\nStopping root scan: {cfg.stop_after_failures} "
                    f"consecutive misses."
                )
                break
            # cd / to reset (in case cd N put us somewhere weird)
            await _safe_navigate(client, "/", cfg)
            continue

        consecutive_failures = 0
        stats["visited"] += 1

        # list at this root child — capture full output (with reconnect)
        lst = await _safe_list(client, cfg, abs_path=[idx])
        entries = lst.parsed_list.entries
        list_text = _clean_list_text(lst.raw_response)
        raw_entries = _serialize_entries(entries)

        is_leaf = len(entries) == 0

        leaf_tag = " [LEAF]" if is_leaf else ""
        print(
            f"  [d=1 | {idx} | "
            f"+{stats['visited']} ~{stats['skipped']}] "
            f"cd {idx} -> {child_location!r} ({len(entries)} entries){leaf_tag}"
        )

        node = TreeNode(
            path=str(idx),
            index=idx,
            location=child_location,
            object_type=_extract_type(child_location),
            raw_list_text=list_text,
            raw_list_entries=raw_entries,
            is_leaf=is_leaf,
        )

        # Recurse into children if not a leaf
        if not is_leaf:
            sig = _entries_signature(entries, list_text)
            if sig and sig in sig_cache:
                original_path = sig_cache[sig]
                node.duplicate_of = original_path
                stats["duplicates"] += 1
                print(
                    f"  DUPLICATE of [{original_path}] "
                    f"-> skipping subtree (dup #{stats['duplicates']})"
                )
            else:
                child_indexes = _child_indexes_from_entries(entries, cfg.max_index, cfg.max_gap_probe)
                ancestor_locations = {root_location, child_location}
                rc_type_map = _entry_type_map(entries) if not cfg.no_leaf_shortcut else None

                node.children = await _scan_children(
                    client,
                    parent_abs_path=[idx],
                    parent_location=child_location,
                    ancestor_locations=ancestor_locations,
                    child_indexes=child_indexes,
                    depth=2,
                    stats=stats,
                    cfg=cfg,
                    sig_cache=sig_cache,
                    child_type_map=rc_type_map,
                )
                if sig:
                    sig_cache[sig] = str(idx)

        # Track consecutive empty leaves for early exit
        if is_leaf and len(entries) == 0:
            consecutive_empty_leaves += 1
        else:
            consecutive_empty_leaves = 0

        root_children.append(node)

        # cd / — always return to root between top-level branches
        await _safe_navigate(client, "/", cfg)

        # Consecutive empty leaf early exit
        if (cfg.empty_leaf_limit > 0
                and consecutive_empty_leaves >= cfg.empty_leaf_limit):
            print(
                f"\nStopping root scan: "
                f"{cfg.empty_leaf_limit} consecutive empty leaves"
            )
            break

        # Save progress after each root branch
        _write_branch_progress(progress_path, idx, node, stats)

        # Progress summary after each root branch
        branch_elapsed = time.monotonic() - stats["_branch_start"]
        total_elapsed = time.monotonic() - stats["_start_time"]
        print(
            f"  Branch {branch_num}/{total_root} done in {branch_elapsed:.1f}s. "
            f"Total: {stats['visited']} visited, {stats['skipped']} skipped "
            f"({total_elapsed:.0f}s elapsed)"
        )

    return root_children, stats


# ---------------------------------------------------------------------------
# Progressive save
# ---------------------------------------------------------------------------

def _progress_file_path(cfg: ScanConfig) -> str:
    """Return the progress file path, auto-derived from output_path if empty."""
    if cfg.progress_path:
        return cfg.progress_path
    return cfg.output_path + ".progress.jsonl"


def _write_branch_progress(
    progress_path: str,
    branch_index: int,
    node: TreeNode,
    stats: dict,
) -> None:
    """Append one completed branch to the progress JSONL file."""
    record = {
        "branch_index": branch_index,
        "node": node_to_dict(node),
        "stats_snapshot": {k: v for k, v in stats.items() if not k.startswith("_")},
        "timestamp": time.time(),
    }
    with open(progress_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _dict_to_node(d: dict) -> TreeNode:
    """Reconstruct a TreeNode from a serialized dict."""
    return TreeNode(
        path=d["path"],
        index=d["index"],
        location=d.get("location"),
        object_type=d.get("object_type"),
        raw_list_text=d.get("raw_list_text", ""),
        raw_list_entries=d.get("entries", []),
        is_leaf=d.get("is_leaf", True),
        children=[_dict_to_node(c) for c in d.get("children", [])],
        duplicate_of=d.get("duplicate_of"),
    )


def _collect_signatures(node: TreeNode, sig_cache: dict[str, str]) -> None:
    """Rebuild sig_cache from a resumed node tree for duplicate detection continuity."""
    if node.raw_list_entries and not node.duplicate_of:
        sig = _entries_signature(node.raw_list_entries, node.raw_list_text)
        if sig and sig not in sig_cache:
            sig_cache[sig] = node.path
    for child in node.children:
        _collect_signatures(child, sig_cache)


def _load_progress(progress_path: str) -> tuple[list[TreeNode], set[int], dict, dict[str, str]]:
    """Load completed branches from a progress JSONL file.

    Returns:
        (nodes, completed_branch_indexes, last_stats, sig_cache)
    """
    import os
    nodes: list[TreeNode] = []
    completed: set[int] = set()
    last_stats = {"visited": 0, "skipped": 0, "duplicates": 0}
    sig_cache: dict[str, str] = {}

    if not os.path.exists(progress_path):
        return nodes, completed, last_stats, sig_cache

    with open(progress_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            branch_idx = record["branch_index"]
            node = _dict_to_node(record["node"])
            completed.add(branch_idx)
            nodes.append(node)
            last_stats = record.get("stats_snapshot", last_stats)
            # Rebuild sig_cache from this branch's node tree
            _collect_signatures(node, sig_cache)

    return nodes, completed, last_stats, sig_cache


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

def node_to_dict(node: TreeNode) -> dict:
    d = {
        "path": node.path,
        "index": node.index,
        "location": node.location,
        "object_type": node.object_type,
        "entry_count": len(node.raw_list_entries),
        "raw_list_text": node.raw_list_text,
        "entries": node.raw_list_entries,
        "is_leaf": node.is_leaf,
        "children": [node_to_dict(c) for c in node.children],
    }
    if node.duplicate_of:
        d["duplicate_of"] = node.duplicate_of
    return d


def print_tree(nodes: list[TreeNode], indent: int = 0) -> None:
    """Pretty-print the discovered tree to stdout."""
    prefix = "  " * indent
    for node in nodes:
        n_entries = len(node.raw_list_entries)
        leaf_tag = " [leaf]" if node.is_leaf else ""
        dup_tag = f" [DUPLICATE of {node.duplicate_of}]" if node.duplicate_of else ""
        n_children = len(node.children)
        children_tag = f" [{n_children} children]" if n_children else ""
        print(
            f"{prefix}[{node.path}] {node.location!r}"
            f"  ({n_entries} entries){children_tag}{leaf_tag}{dup_tag}"
        )
        if node.duplicate_of:
            # Don't expand duplicates
            continue
        if node.raw_list_entries and not node.children:
            for e in node.raw_list_entries[:5]:
                name = e.get("name") or e.get("object_id") or ""
                otype = e.get("object_type") or ""
                oid = e.get("object_id") or ""
                print(f"{prefix}  * {otype} {oid}  {name}")
            if len(node.raw_list_entries) > 5:
                print(f"{prefix}  ... ({len(node.raw_list_entries) - 5} more)")
        print_tree(node.children, indent + 1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main_async(cfg: ScanConfig) -> None:
    # Fix Windows cp1252 encoding errors when printing Unicode location names
    import sys, io
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )

    print(f"Connecting to {cfg.host}:{cfg.port} as {cfg.user}...")
    client = GMA2TelnetClient(
        host=cfg.host,
        port=cfg.port,
        user=cfg.user,
        password=cfg.password,
    )

    try:
        await client.connect()
        await client.login()
        print("Connected and logged in.\n")

        t_start = time.monotonic()
        root_children, stats = await scan_tree(client, cfg)
        elapsed = time.monotonic() - t_start

    finally:
        try:
            await asyncio.wait_for(client.disconnect(), timeout=cfg.disconnect_timeout)
            print("\nDisconnected.")
        except asyncio.TimeoutError:
            print(f"\nDisconnect timed out after {cfg.disconnect_timeout}s — forcing close.")
        except Exception as e:
            print(f"\nDisconnect error: {e} — continuing.")

    # Write JSON output
    output = {
        "scan_meta": {
            "host": cfg.host,
            "port": cfg.port,
            "max_depth": cfg.max_depth,
            "max_nodes": cfg.max_nodes,
            "max_index": cfg.max_index,
            "stop_after_failures": cfg.stop_after_failures,
            "max_gap_probe": cfg.max_gap_probe,
            "empty_leaf_limit": cfg.empty_leaf_limit,
            "health_check_every": cfg.health_check_every,
            "no_leaf_shortcut": cfg.no_leaf_shortcut,
            "elapsed_seconds": round(elapsed, 2),
            "nodes_visited": stats["visited"],
            "nodes_skipped": stats["skipped"],
            "duplicates_skipped": stats.get("duplicates", 0),
        },
        "root_children": [node_to_dict(n) for n in root_children],
    }

    with open(cfg.output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    # Print summary tree
    print("\n=== DISCOVERED TREE ===\n")
    print_tree(root_children)

    print(f"\n=== SCAN COMPLETE ===")
    print(f"  Nodes visited : {stats['visited']}")
    print(f"  Indexes missed: {stats['skipped']}")
    print(f"  Dupes skipped : {stats.get('duplicates', 0)}")
    print(f"  Elapsed time  : {elapsed:.1f}s")
    print(f"  Output written: {cfg.output_path}")


def parse_args() -> ScanConfig:
    env_host = get_key(".env", "GMA_HOST") or "127.0.0.1"
    env_user = get_key(".env", "GMA_USER") or "administrator"
    env_pass = get_key(".env", "GMA_PASSWORD") or "admin"

    p = argparse.ArgumentParser(description="Recursive grandMA2 tree scanner")
    p.add_argument("--host",       default=env_host)
    p.add_argument("--port",       type=int, default=30000)
    p.add_argument("--user",       default=env_user)
    p.add_argument("--password",   default=env_pass)
    p.add_argument("--max-depth",  type=int, default=20,   dest="max_depth")
    p.add_argument("--max-nodes",  type=int, default=0,    dest="max_nodes")
    p.add_argument("--max-index",  type=int, default=60,   dest="max_index")
    p.add_argument("--failures",   type=int, default=3)
    p.add_argument("--output",     default="scan_output.json")
    p.add_argument("--delay",      type=float, default=0.08)
    p.add_argument("--timeout",    type=float, default=0.8)
    p.add_argument("--max-gap-probe",        type=int, default=5,    dest="max_gap_probe",
                   help="Max gap between consecutive IDs to probe (default: 5)")
    p.add_argument("--empty-leaf-limit",     type=int, default=10,   dest="empty_leaf_limit",
                   help="Stop after N consecutive empty leaves, 0=off (default: 10)")
    p.add_argument("--health-check-interval", type=int, default=500, dest="health_check_every",
                   help="Health check every N nodes, 0=disabled (default: 500)")
    p.add_argument("--no-leaf-shortcut",     action="store_true",    dest="no_leaf_shortcut",
                   help="Disable known-leaf-type optimization")
    p.add_argument("--progress-file",        default="",             dest="progress_path",
                   help="JSONL progress file path (auto-derived from --output if empty)")
    p.add_argument("--resume",              action="store_true",
                   help="Resume scan from progress file")
    p.add_argument("--heartbeat-every",    type=int, default=200,  dest="heartbeat_every",
                   help="Print heartbeat every N nodes, 0=disabled (default: 200)")
    p.add_argument("--branch-timeout",     type=float, default=0,  dest="branch_timeout",
                   help="Per-branch timeout in seconds, 0=unlimited (default: 0)")
    p.add_argument("--disconnect-timeout", type=float, default=5.0, dest="disconnect_timeout",
                   help="Timeout for telnet disconnect in seconds (default: 5)")
    args = p.parse_args()

    return ScanConfig(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        max_depth=args.max_depth,
        max_nodes=args.max_nodes,
        max_index=args.max_index,
        stop_after_failures=args.failures,
        output_path=args.output,
        delay=args.delay,
        timeout=args.timeout,
        max_gap_probe=args.max_gap_probe,
        empty_leaf_limit=args.empty_leaf_limit,
        health_check_every=args.health_check_every,
        no_leaf_shortcut=args.no_leaf_shortcut,
        progress_path=args.progress_path,
        resume=args.resume,
        heartbeat_every=args.heartbeat_every,
        branch_timeout=args.branch_timeout,
        disconnect_timeout=args.disconnect_timeout,
    )


if __name__ == "__main__":
    cfg = parse_args()
    asyncio.run(main_async(cfg))

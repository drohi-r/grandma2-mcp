"""
strategic_scan.py -- 4-phase strategic validation scan for grandMA2 cd tree.

Phases:
  1. Root Validation   (~30s)  --cd+list every root index 1-50
  2. Structure Scan   (~3-5m)  --depth 2-3 for all branches, depth 1 for UserProfiles
  3. Deep Show Scan   (~5-10m) --full recursive scan of FixtureTypes, ExecutorPages, Layouts
  4. Triage           (~1-2m)  --retry failed edges with increased delay

Outputs scan_output_new.json (same format as scan_output.json) + diff summary.

Usage:
    python scripts/strategic_scan.py [options]

Options:
    --host 127.0.0.1         Console IP (default: from .env)
    --port 30000             Telnet port
    --structure-depth 3      Max depth for Phase 2 structure scan
    --deep-branches 10.3,30,38  Comma-separated paths for Phase 3
    --skip-phase N           Skip phase N (repeatable)
    --output scan_output_new.json
    --old-scan scan_output.json
    --delay 0.08             Telnet delay
    --timeout 0.8            Telnet read timeout
    --triage-retries 3       Max retries per failed edge
    --no-diff                Skip diff comparison
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import get_key

# ---------------------------------------------------------------------------
# Import helpers from scan_tree.py via importlib (avoid modifying it)
# ---------------------------------------------------------------------------
import sys

ROOT = Path(__file__).resolve().parent.parent

# Ensure project root is on sys.path so scan_tree.py can import from src.*
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location("scan_tree", ROOT / "scripts" / "scan_tree.py")
_scan_tree = importlib.util.module_from_spec(_spec)
sys.modules["scan_tree"] = _scan_tree  # Required for dataclass processing in Python 3.12+
_spec.loader.exec_module(_scan_tree)

# Re-export what we need
ScanConfig = _scan_tree.ScanConfig
TreeNode = _scan_tree.TreeNode
KNOWN_LEAF_TYPES = _scan_tree.KNOWN_LEAF_TYPES
node_to_dict = _scan_tree.node_to_dict
_safe_navigate = _scan_tree._safe_navigate
_safe_list = _scan_tree._safe_list
_is_alive = _scan_tree._is_alive
_reconnect = _scan_tree._reconnect
_navigate_to_path_raw = _scan_tree._navigate_to_path_raw
_child_indexes_from_entries = _scan_tree._child_indexes_from_entries
_entries_signature = _scan_tree._entries_signature
_entry_type_map = _scan_tree._entry_type_map
_clean_list_text = _scan_tree._clean_list_text
_serialize_entries = _scan_tree._serialize_entries
_extract_type = _scan_tree._extract_type
_scan_children = _scan_tree._scan_children
_structure_signature = _scan_tree._structure_signature

from src.navigation import navigate
from src.telnet_client import GMA2TelnetClient

logging.basicConfig(level=logging.WARNING)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Indexes confirmed invalid on MA2 3.9.60.65
KNOWN_INVALID_INDEXES: set[int] = {12, 28, 29, 32, 44, 45, 47, 48, 49, 50}

# Firmware branches --structure is show-independent
FIRMWARE_BRANCHES: set[int] = {
    2, 3, 4, 5, 6, 7, 8, 9, 15, 16, 20, 23, 27, 36, 41, 42,
}

# Branches to deep-scan in Phase 3 (dot-separated paths)
DEFAULT_DEEP_BRANCHES = ["10.3", "30", "38"]

# UserProfiles --special depth-1-only handling
USERPROFILES_INDEX = 39

# Branches with repetitive sub-structures --use reduced depth (saves ~2-3 min)
SHALLOW_DEPTH_BRANCHES: set[int] = {18}  # Worlds: each world mirrors UserProfile structure

# After N consecutive duplicate siblings at any depth, stop scanning remaining siblings
CONSECUTIVE_DUP_EARLY_EXIT = 3


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class StrategicConfig:
    host: str = "127.0.0.1"
    port: int = 30000
    user: str = "administrator"
    password: str = "admin"
    delay: float = 0.08
    timeout: float = 0.8
    disconnect_timeout: float = 5.0
    # Phase control
    skip_phases: set[int] = field(default_factory=set)
    # Phase 1
    root_probe_max: int = 50
    # Phase 2
    structure_depth: int = 3
    userprofile_depth: int = 1
    # Phase 3
    deep_branches: list[str] = field(default_factory=lambda: list(DEFAULT_DEEP_BRANCHES))
    deep_max_depth: int = 20
    # Shared scan params
    max_index: int = 60
    max_gap_probe: int = 5
    stop_after_failures: int = 3
    empty_leaf_limit: int = 10
    health_check_every: int = 300
    heartbeat_every: int = 100
    # Triage
    triage_retries: int = 3
    triage_delay_mult: float = 2.0
    # Output
    output_path: str = "scan_output_new.json"
    old_scan_path: str = "scan_output.json"
    no_diff: bool = False


@dataclass
class FailedEdge:
    parent_abs_path: list[int]
    child_index: int
    failure_type: str          # MISS, CIRCULAR, TIMEOUT, ERROR
    error_detail: str
    phase: int
    retry_count: int = 0
    resolved: bool = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scan_cfg(cfg: StrategicConfig, max_depth: int = 20) -> ScanConfig:
    """Build a ScanConfig from StrategicConfig for reuse with scan_tree helpers."""
    return ScanConfig(
        host=cfg.host,
        port=cfg.port,
        user=cfg.user,
        password=cfg.password,
        max_depth=max_depth,
        max_nodes=0,
        max_index=cfg.max_index,
        stop_after_failures=cfg.stop_after_failures,
        output_path=cfg.output_path,
        delay=cfg.delay,
        timeout=cfg.timeout,
        max_gap_probe=cfg.max_gap_probe,
        empty_leaf_limit=cfg.empty_leaf_limit,
        health_check_every=cfg.health_check_every,
        no_leaf_shortcut=False,
        heartbeat_every=cfg.heartbeat_every,
        branch_timeout=0,
        disconnect_timeout=cfg.disconnect_timeout,
    )


def _find_node_by_path(root_nodes: list[TreeNode], path_parts: list[int]) -> Optional[TreeNode]:
    """Walk the tree to find a node at the given absolute path."""
    if not path_parts:
        return None
    # Find the root-level node
    current_list = root_nodes
    node = None
    for idx in path_parts:
        node = None
        for n in current_list:
            if n.index == idx:
                node = n
                break
        if node is None:
            return None
        current_list = node.children
    return node


# ---------------------------------------------------------------------------
# Phase 1: Root Validation
# ---------------------------------------------------------------------------

async def phase1_root_validation(
    client: GMA2TelnetClient,
    cfg: StrategicConfig,
    stats: dict,
    failed_edges: list[FailedEdge],
    raw_entries_cache: dict[int, list],
    sig_cache: dict[str, str],
) -> list[TreeNode]:
    """cd+list every root index 1..root_probe_max. Returns placeholder TreeNodes.

    raw_entries_cache: populated with {root_index: [ListEntry, ...]} for Phase 2
    to call _child_indexes_from_entries / _entry_type_map on the original objects.
    sig_cache: seeded with content signatures so Phase 2 can skip duplicate branches.
    """
    print("\n=== PHASE 1: Root Validation ===")
    phase_start = time.monotonic()
    scan_cfg = _make_scan_cfg(cfg)
    root_nodes: list[TreeNode] = []

    # Start at root and detect root location name (varies by show: "Fixture", "Screen", etc.)
    root_nav = await _safe_navigate(client, "/", scan_cfg)
    root_location = root_nav.parsed_prompt.location if root_nav and root_nav.parsed_prompt else "Fixture"
    print(f"  Root location: {root_location!r}")

    for idx in range(1, cfg.root_probe_max + 1):
        if idx in KNOWN_INVALID_INDEXES:
            continue

        # cd N
        nav = await _safe_navigate(client, str(idx), scan_cfg)
        if nav is None or nav.parsed_prompt is None:
            failed_edges.append(FailedEdge(
                parent_abs_path=[], child_index=idx,
                failure_type="MISS", error_detail="Navigation returned None",
                phase=1,
            ))
            stats["skipped"] += 1
            await _safe_navigate(client, "/", scan_cfg)
            continue

        location = nav.parsed_prompt.location
        # Check if we actually moved (location should not be root)
        if location is None or location == root_location:
            stats["skipped"] += 1
            await _safe_navigate(client, "/", scan_cfg)
            continue

        # list
        list_result = await _safe_list(client, scan_cfg)
        if list_result is None:
            raw_text = ""
            raw_entries = []
            serialized_entries = []
        else:
            raw_text = _clean_list_text(list_result.raw_response)
            raw_entries = list_result.parsed_list.entries if list_result.parsed_list else []
            serialized_entries = _serialize_entries(raw_entries) if raw_entries else []

        # Cache raw ListEntry objects for Phase 2
        raw_entries_cache[idx] = raw_entries

        object_type = _extract_type(location)
        is_leaf = len(serialized_entries) == 0

        node = TreeNode(
            path=str(idx),
            index=idx,
            location=location,
            object_type=object_type,
            raw_list_text=raw_text,
            raw_list_entries=serialized_entries,
            is_leaf=is_leaf,
        )
        # Seed signature cache for early dedup in Phase 2
        if not is_leaf and raw_text:
            sig = _entries_signature(raw_entries, raw_text)
            if sig:
                if sig in sig_cache:
                    node.duplicate_of = sig_cache[sig]
                    stats["duplicates"] += 1
                else:
                    sig_cache[sig] = str(idx)

        root_nodes.append(node)
        stats["visited"] += 1

        # Return to root
        await _safe_navigate(client, "/", scan_cfg)

    dupes = sum(1 for n in root_nodes if n.duplicate_of)
    elapsed = time.monotonic() - phase_start
    print(f"  Phase 1 complete: {len(root_nodes)} valid roots, "
          f"{stats['skipped']} skipped, {dupes} duplicates, {elapsed:.1f}s")
    return root_nodes


# ---------------------------------------------------------------------------
# Phase 2: Structure Scan (depth-limited)
# ---------------------------------------------------------------------------

async def _scan_branch_to_depth(
    client: GMA2TelnetClient,
    parent_abs_path: list[int],
    parent_location: Optional[str],
    ancestor_locations: set[str],
    child_indexes: list[int],
    current_depth: int,
    max_depth: int,
    stats: dict,
    cfg: StrategicConfig,
    scan_cfg: ScanConfig,
    sig_cache: dict[str, str],
    failed_edges: list[FailedEdge],
    phase: int,
    child_type_map: Optional[dict[int, str]] = None,
) -> list[TreeNode]:
    """Depth-limited recursive scan. Stops at max_depth."""
    if current_depth > max_depth:
        return []

    children: list[TreeNode] = []
    consecutive_failures = 0
    consecutive_duplicates = 0
    parent_path_str = ".".join(str(i) for i in parent_abs_path)

    for idx in child_indexes:
        # Known leaf shortcut
        known_leaf = (
            child_type_map is not None
            and child_type_map.get(idx) in KNOWN_LEAF_TYPES
        )

        if known_leaf:
            # Build leaf node without navigating
            child_path = f"{parent_path_str}.{idx}" if parent_path_str else str(idx)
            node = TreeNode(
                path=child_path,
                index=idx,
                location=None,
                object_type=child_type_map.get(idx),
                raw_list_text="",
                raw_list_entries=[],
                is_leaf=True,
            )
            children.append(node)
            stats["visited"] += 1
            continue

        # Pre-check for circular references using expected name from list entries
        if child_type_map is not None:
            name_map = child_type_map.get("_name_map", {})
            expected_name = name_map.get(idx)
            if expected_name and (expected_name in ancestor_locations or expected_name == parent_location):
                child_path = f"{parent_path_str}.{idx}" if parent_path_str else str(idx)
                stats["skipped"] += 1
                failed_edges.append(FailedEdge(
                    parent_abs_path=parent_abs_path, child_index=idx,
                    failure_type="CIRCULAR",
                    error_detail=f"Pre-check: name {expected_name!r} in ancestors",
                    phase=phase,
                ))
                continue

        # cd N
        nav = await _safe_navigate(client, str(idx), scan_cfg)
        if nav is None or nav.parsed_prompt is None or nav.parsed_prompt.location is None:
            consecutive_failures += 1
            stats["skipped"] += 1
            if consecutive_failures >= cfg.stop_after_failures:
                break
            continue
        consecutive_failures = 0

        child_location = nav.parsed_prompt.location

        # Circular check (post-navigate, catches cases the pre-check missed)
        if child_location in ancestor_locations or child_location == parent_location:
            stats["skipped"] += 1
            failed_edges.append(FailedEdge(
                parent_abs_path=parent_abs_path, child_index=idx,
                failure_type="CIRCULAR",
                error_detail=f"Location {child_location} already in ancestors",
                phase=phase,
            ))
            await _safe_navigate(client, "..", scan_cfg)
            continue

        # list
        list_result = await _safe_list(client, scan_cfg)
        if list_result is None:
            raw_text = ""
            entries_list = []
            parsed_entries = ()
        else:
            raw_text = _clean_list_text(list_result.raw_response)
            parsed_entries = list_result.parsed_list.entries if list_result.parsed_list else ()
            entries_list = _serialize_entries(parsed_entries)

        child_path = f"{parent_path_str}.{idx}" if parent_path_str else str(idx)
        object_type = _extract_type(child_location)
        is_leaf = len(entries_list) == 0

        node = TreeNode(
            path=child_path,
            index=idx,
            location=child_location,
            object_type=object_type,
            raw_list_text=raw_text,
            raw_list_entries=entries_list,
            is_leaf=is_leaf,
        )
        stats["visited"] += 1

        # Heartbeat
        if (cfg.heartbeat_every > 0
                and stats["visited"] % cfg.heartbeat_every == 0):
            elapsed = time.monotonic() - stats["_start_time"]
            rate = stats["visited"] / elapsed if elapsed > 0 else 0
            print(f"  [HEARTBEAT] {stats['visited']} nodes, "
                  f"{elapsed:.0f}s ({rate:.1f} n/s) --depth={current_depth} path={child_path}")

        # Recurse if not leaf and not at depth limit
        if not is_leaf and current_depth < max_depth:
            sig = _entries_signature(parsed_entries, raw_text)
            struct_sig = _structure_signature(parsed_entries)
            is_dup = False

            # Check content signature (strict match)
            if sig and sig in sig_cache:
                node.duplicate_of = sig_cache[sig]
                is_dup = True
            # Fallback: structure signature (same types+count, different names)
            elif struct_sig and struct_sig in sig_cache:
                node.duplicate_of = sig_cache[struct_sig]
                is_dup = True

            if is_dup:
                stats["duplicates"] += 1
                consecutive_duplicates += 1
            else:
                consecutive_duplicates = 0
                grandchild_indexes = _child_indexes_from_entries(
                    parsed_entries, cfg.max_index, cfg.max_gap_probe
                )
                deeper_ancestors = ancestor_locations | {child_location}
                gc_type_map = _entry_type_map(parsed_entries)

                node.children = await _scan_branch_to_depth(
                    client,
                    parent_abs_path + [idx],
                    child_location,
                    deeper_ancestors,
                    grandchild_indexes,
                    current_depth + 1,
                    max_depth,
                    stats,
                    cfg,
                    scan_cfg,
                    sig_cache,
                    failed_edges,
                    phase,
                    gc_type_map,
                )
                if sig:
                    sig_cache[sig] = child_path
                if struct_sig:
                    sig_cache[struct_sig] = child_path
        else:
            consecutive_duplicates = 0

        children.append(node)

        # Early exit: stop scanning siblings after N consecutive duplicates
        if consecutive_duplicates >= CONSECUTIVE_DUP_EARLY_EXIT:
            remaining = len(child_indexes) - child_indexes.index(idx) - 1
            if remaining > 0:
                print(f"    [DEDUP] {consecutive_duplicates} consecutive dupes at "
                      f"{parent_path_str} depth {current_depth}, "
                      f"skipping {remaining} remaining siblings")
            break

        # cd .. to return to parent
        nav_back = await _safe_navigate(client, "..", scan_cfg)
        if nav_back is None or nav_back.parsed_prompt is None:
            # Recovery: navigate via absolute path
            await _safe_navigate(client, "/", scan_cfg)
            for p in parent_abs_path:
                await _safe_navigate(client, str(p), scan_cfg)

    return children


async def phase2_structure_scan(
    client: GMA2TelnetClient,
    cfg: StrategicConfig,
    root_nodes: list[TreeNode],
    stats: dict,
    sig_cache: dict[str, str],
    failed_edges: list[FailedEdge],
    raw_entries_cache: dict[int, list],
) -> None:
    """Scan depth 2-3 for all non-leaf branches. Depth 1 for UserProfiles."""
    print("\n=== PHASE 2: Structure Scan ===")
    phase_start = time.monotonic()
    scan_cfg = _make_scan_cfg(cfg, max_depth=cfg.structure_depth)

    for node in root_nodes:
        if node.is_leaf:
            continue

        # Skip branches already identified as duplicates in Phase 1
        if node.duplicate_of:
            print(f"  SKIP cd {node.index} [{node.object_type}] --duplicate of cd {node.duplicate_of}")
            continue

        # Determine depth limit
        if node.index == USERPROFILES_INDEX:
            max_depth = cfg.userprofile_depth
            label = "UserProfiles (depth 1)"
        elif node.index in SHALLOW_DEPTH_BRANCHES:
            max_depth = min(2, cfg.structure_depth)
            label = f"Shallow/{node.object_type}"
        elif node.index in FIRMWARE_BRANCHES:
            max_depth = cfg.structure_depth
            label = f"Firmware/{node.object_type}"
        else:
            max_depth = cfg.structure_depth
            label = f"Show/{node.object_type}"

        print(f"  Scanning cd {node.index} [{label}] depth {max_depth}...")

        # Navigate to this root branch
        await _safe_navigate(client, "/", scan_cfg)
        await _safe_navigate(client, str(node.index), scan_cfg)

        # Use raw ListEntry objects from cache (Phase 1 stored them)
        raw_entries = raw_entries_cache.get(node.index, [])

        # Get child indexes from raw entries
        child_indexes = _child_indexes_from_entries(
            raw_entries, cfg.max_index, cfg.max_gap_probe
        )

        if not child_indexes:
            await _safe_navigate(client, "/", scan_cfg)
            continue

        gc_type_map = _entry_type_map(raw_entries)

        node.children = await _scan_branch_to_depth(
            client,
            [node.index],
            node.location,
            {node.location} if node.location else set(),
            child_indexes,
            1,  # current depth (already inside the root branch)
            max_depth,
            stats,
            cfg,
            scan_cfg,
            sig_cache,
            failed_edges,
            phase=2,
            child_type_map=gc_type_map,
        )

        node.is_leaf = False  # Ensure not marked as leaf now that it has children
        await _safe_navigate(client, "/", scan_cfg)

    elapsed = time.monotonic() - phase_start
    print(f"  Phase 2 complete: {stats['visited']} total nodes, {elapsed:.1f}s")


# ---------------------------------------------------------------------------
# Phase 3: Deep Show Branches
# ---------------------------------------------------------------------------

async def phase3_deep_scan(
    client: GMA2TelnetClient,
    cfg: StrategicConfig,
    root_nodes: list[TreeNode],
    stats: dict,
    sig_cache: dict[str, str],
    failed_edges: list[FailedEdge],
) -> None:
    """Full recursive scan of deep branches using scan_tree._scan_children."""
    print("\n=== PHASE 3: Deep Show Branches ===")
    phase_start = time.monotonic()
    scan_cfg = _make_scan_cfg(cfg, max_depth=cfg.deep_max_depth)

    for branch_path_str in cfg.deep_branches:
        path_parts = [int(p) for p in branch_path_str.split(".")]
        target = _find_node_by_path(root_nodes, path_parts)

        if target is None:
            print(f"  SKIP cd {branch_path_str} --not found in tree")
            continue

        if target.is_leaf and not target.raw_list_entries:
            print(f"  SKIP cd {branch_path_str} [{target.object_type}] --leaf/empty")
            continue

        print(f"  Deep scanning cd {branch_path_str} [{target.object_type}] "
              f"({len(target.raw_list_entries)} entries)...")

        # Navigate to the target
        await _safe_navigate(client, "/", scan_cfg)
        for p in path_parts:
            await _safe_navigate(client, str(p), scan_cfg)

        # Re-list to get fresh raw ListEntry objects (stored entries are serialized dicts)
        list_result = await _safe_list(client, scan_cfg)
        if list_result is None or not list_result.parsed_list or not list_result.parsed_list.entries:
            print(f"    Re-list returned empty --skipping")
            await _safe_navigate(client, "/", scan_cfg)
            continue

        raw_entries = list_result.parsed_list.entries
        child_indexes = _child_indexes_from_entries(
            raw_entries, cfg.max_index, cfg.max_gap_probe
        )

        if not child_indexes:
            await _safe_navigate(client, "/", scan_cfg)
            continue

        gc_type_map = _entry_type_map(raw_entries)

        # Use scan_tree._scan_children for full recursive depth
        stats["_branch_start"] = time.monotonic()
        target.children = await _scan_children(
            client,
            path_parts,
            target.location,
            {target.location} if target.location else set(),
            child_indexes,
            len(path_parts),  # depth = how deep we already are
            stats,
            scan_cfg,
            sig_cache,
            gc_type_map,
        )

        target.is_leaf = False
        await _safe_navigate(client, "/", scan_cfg)

        branch_elapsed = time.monotonic() - stats["_branch_start"]
        child_count = sum(1 for _ in _iter_nodes(target))
        print(f"    cd {branch_path_str} done: {child_count} nodes, {branch_elapsed:.1f}s")

    elapsed = time.monotonic() - phase_start
    print(f"  Phase 3 complete: {stats['visited']} total nodes, {elapsed:.1f}s")


def _iter_nodes(node: TreeNode):
    """Yield all nodes in a subtree."""
    yield node
    for c in node.children:
        yield from _iter_nodes(c)


# ---------------------------------------------------------------------------
# Phase 4: Triage Failed Edges
# ---------------------------------------------------------------------------

async def phase4_triage(
    client: GMA2TelnetClient,
    cfg: StrategicConfig,
    root_nodes: list[TreeNode],
    failed_edges: list[FailedEdge],
    stats: dict,
    root_location: str = "Fixture",
) -> None:
    """Retry failed edges with increased delay."""
    # Filter out known-invalid and already-resolved
    retryable = [
        e for e in failed_edges
        if e.child_index not in KNOWN_INVALID_INDEXES
        and not e.resolved
        and e.failure_type in ("MISS", "TIMEOUT", "ERROR")
    ]

    if not retryable:
        print("\n=== PHASE 4: Triage ===")
        print("  No retryable failed edges. Skipping.")
        return

    print(f"\n=== PHASE 4: Triage ({len(retryable)} edges) ===")
    phase_start = time.monotonic()

    triage_cfg = _make_scan_cfg(cfg)
    triage_cfg.delay = cfg.delay * cfg.triage_delay_mult
    triage_cfg.timeout = cfg.timeout * cfg.triage_delay_mult

    resolved_count = 0
    for edge in retryable:
        for attempt in range(1, cfg.triage_retries + 1):
            edge.retry_count = attempt

            # Navigate to parent
            await _safe_navigate(client, "/", triage_cfg)
            for p in edge.parent_abs_path:
                await _safe_navigate(client, str(p), triage_cfg)

            # Retry cd child
            nav = await _safe_navigate(client, str(edge.child_index), triage_cfg)
            if nav is None or nav.parsed_prompt is None or nav.parsed_prompt.location is None:
                continue

            location = nav.parsed_prompt.location
            if location == root_location:  # Still at root --miss
                continue

            # Success! Get list and graft node
            list_result = await _safe_list(client, triage_cfg)
            raw_text = ""
            entries = []
            if list_result and list_result.parsed_list:
                raw_text = _clean_list_text(list_result.raw_response)
                entries = _serialize_entries(list_result.parsed_list.entries)

            parent_path = ".".join(str(p) for p in edge.parent_abs_path)
            child_path = f"{parent_path}.{edge.child_index}" if parent_path else str(edge.child_index)

            new_node = TreeNode(
                path=child_path,
                index=edge.child_index,
                location=location,
                object_type=_extract_type(location),
                raw_list_text=raw_text,
                raw_list_entries=entries,
                is_leaf=len(entries) == 0,
            )

            # Graft into tree
            if edge.parent_abs_path:
                parent = _find_node_by_path(root_nodes, edge.parent_abs_path)
                if parent:
                    parent.children.append(new_node)
                    parent.children.sort(key=lambda n: n.index)
            else:
                root_nodes.append(new_node)
                root_nodes.sort(key=lambda n: n.index)

            edge.resolved = True
            resolved_count += 1
            stats["visited"] += 1
            print(f"  RESOLVED cd {child_path} (attempt {attempt})")
            break

    elapsed = time.monotonic() - phase_start
    unresolved = len(retryable) - resolved_count
    print(f"  Phase 4 complete: {resolved_count} resolved, {unresolved} remaining, {elapsed:.1f}s")


# ---------------------------------------------------------------------------
# Diff
# ---------------------------------------------------------------------------

def _flatten_tree(nodes: list[TreeNode], out: Optional[dict] = None) -> dict[str, dict]:
    """Flatten tree into {path: {location, entry_count, is_leaf, object_type}}."""
    if out is None:
        out = {}
    for node in nodes:
        out[node.path] = {
            "location": node.location,
            "entry_count": len(node.raw_list_entries),
            "is_leaf": node.is_leaf,
            "object_type": node.object_type,
        }
        if node.children:
            _flatten_tree(node.children, out)
    return out


def diff_scans(old_path: str, new_nodes: list[TreeNode]) -> dict:
    """Compare new scan against old scan file."""
    try:
        with open(old_path) as f:
            old_data = json.load(f)
    except FileNotFoundError:
        return {"error": f"Old scan not found: {old_path}"}

    def _nodes_from_dicts(dicts):
        nodes = []
        for d in dicts:
            node = TreeNode(
                path=d["path"], index=d["index"],
                location=d.get("location"), object_type=d.get("object_type"),
                raw_list_text=d.get("raw_list_text", ""),
                raw_list_entries=d.get("entries", []),
                is_leaf=d.get("is_leaf", True),
            )
            for cd in d.get("children", []):
                node.children.append(_nodes_from_dicts([cd])[0])
            if d.get("duplicate_of"):
                node.duplicate_of = d["duplicate_of"]
            nodes.append(node)
        return nodes

    old_nodes = _nodes_from_dicts(old_data.get("root_children", []))
    old_flat = _flatten_tree(old_nodes)
    new_flat = _flatten_tree(new_nodes)

    old_keys = set(old_flat.keys())
    new_keys = set(new_flat.keys())

    added = sorted(new_keys - old_keys)
    removed = sorted(old_keys - new_keys)
    changed = []

    for path in sorted(old_keys & new_keys):
        old_info = old_flat[path]
        new_info = new_flat[path]
        for field_name in ("location", "entry_count", "is_leaf"):
            ov = old_info[field_name]
            nv = new_info[field_name]
            if ov != nv:
                changed.append({
                    "path": path,
                    "field": field_name,
                    "old": ov,
                    "new": nv,
                })

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "old_scan": old_path,
        "old_node_count": len(old_flat),
        "new_node_count": len(new_flat),
    }


def _print_diff(diff: dict):
    """Print diff summary to console."""
    if "error" in diff:
        print(f"  Diff error: {diff['error']}")
        return

    print(f"\n=== DIFF vs {diff['old_scan']} ===")
    print(f"  Old: {diff['old_node_count']} nodes | New: {diff['new_node_count']} nodes")

    if diff["added"]:
        # Show first 20
        sample = diff["added"][:20]
        print(f"  Added ({len(diff['added'])}): {', '.join(sample)}")
        if len(diff["added"]) > 20:
            print(f"    ... and {len(diff['added']) - 20} more")
    else:
        print("  Added: (none)")

    if diff["removed"]:
        sample = diff["removed"][:20]
        print(f"  Removed ({len(diff['removed'])}): {', '.join(sample)}")
        if len(diff["removed"]) > 20:
            print(f"    ... and {len(diff['removed']) - 20} more")
    else:
        print("  Removed: (none)")

    if diff["changed"]:
        print(f"  Changed ({len(diff['changed'])}):")
        for c in diff["changed"][:30]:
            print(f"    cd {c['path']}: {c['field']} {c['old']} -> {c['new']}")
        if len(diff["changed"]) > 30:
            print(f"    ... and {len(diff['changed']) - 30} more")
    else:
        print("  Changed: (none)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main_async(cfg: StrategicConfig) -> None:
    print("=" * 70)
    print("Strategic Validation Scan -- grandMA2 cd tree")
    print(f"Target: {cfg.host}:{cfg.port}")
    print(f"Output: {cfg.output_path}")
    print(f"Deep branches: {', '.join(cfg.deep_branches)}")
    print(f"Structure depth: {cfg.structure_depth}, UserProfile depth: {cfg.userprofile_depth}")
    print("=" * 70)

    stats = {
        "visited": 0,
        "skipped": 0,
        "duplicates": 0,
        "_start_time": time.monotonic(),
        "_branch_start": time.monotonic(),
    }
    failed_edges: list[FailedEdge] = []
    sig_cache: dict[str, str] = {}
    root_nodes: list[TreeNode] = []
    phases_completed: list[int] = []

    # Connect
    client = GMA2TelnetClient(cfg.host, cfg.port, cfg.user, cfg.password)
    try:
        await client.connect()
        await client.login()
        # Post-login stabilization --MA2 onPC may still be sending init data
        await asyncio.sleep(0.5)
        print(f"Connected and logged in to {cfg.host}:{cfg.port}")
    except Exception as e:
        print(f"FATAL: Cannot connect --{e}")
        return

    # Connectivity check: flush buffer, then verify cd / works
    scan_cfg = _make_scan_cfg(cfg)
    try:
        # First call flushes any residual login data from the buffer
        await navigate(client, "/", timeout=1.0, delay=0.3)
        await asyncio.sleep(0.2)
        # Second call should get a clean response
        warmup = await navigate(client, "/", timeout=cfg.timeout, delay=cfg.delay)
        if not warmup.raw_response or len(warmup.raw_response) == 0:
            print("WARNING: cd / returned empty response --retrying with longer delay...")
            await asyncio.sleep(1.0)
            warmup = await navigate(client, "/", timeout=2.0, delay=0.5)
            if not warmup.raw_response or len(warmup.raw_response) == 0:
                print("FATAL: Console not responding to commands after login.")
                print("  Check that grandMA2 onPC is running and Telnet is enabled.")
                try:
                    await asyncio.wait_for(client.disconnect(), timeout=cfg.disconnect_timeout)
                except Exception:
                    pass
                return
        root_location = warmup.parsed_prompt.location if warmup.parsed_prompt else None
        if root_location is None:
            # Fallback: try parsing from raw response for known root prompts
            raw = warmup.raw_response or ""
            for candidate in ("Screen", "Fixture", "Root"):
                if f"[{candidate}]" in raw:
                    root_location = candidate
                    break
            else:
                root_location = "Fixture"  # default assumption
        print(f"Connectivity verified --root location: {root_location!r}")
    except Exception as e:
        print(f"FATAL: Connectivity check failed --{e}")
        try:
            await asyncio.wait_for(client.disconnect(), timeout=cfg.disconnect_timeout)
        except Exception:
            pass
        return

    # Cache raw ListEntry objects from Phase 1 for Phase 2 to use
    raw_entries_cache: dict[int, list] = {}

    try:
        # Phase 1
        if 1 not in cfg.skip_phases:
            root_nodes = await phase1_root_validation(client, cfg, stats, failed_edges, raw_entries_cache, sig_cache)
            phases_completed.append(1)
        else:
            print("\n  [SKIP] Phase 1")

        # Phase 2
        if 2 not in cfg.skip_phases and root_nodes:
            await phase2_structure_scan(client, cfg, root_nodes, stats, sig_cache, failed_edges, raw_entries_cache)
            phases_completed.append(2)
        else:
            print("\n  [SKIP] Phase 2")

        # Phase 3
        if 3 not in cfg.skip_phases and root_nodes:
            await phase3_deep_scan(client, cfg, root_nodes, stats, sig_cache, failed_edges)
            phases_completed.append(3)
        else:
            print("\n  [SKIP] Phase 3")

        # Phase 4
        if 4 not in cfg.skip_phases and failed_edges:
            await phase4_triage(client, cfg, root_nodes, failed_edges, stats, root_location)
            phases_completed.append(4)
        else:
            print("\n  [SKIP] Phase 4")

    except Exception as e:
        print(f"\n  [ERROR] Scan interrupted: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            await asyncio.wait_for(client.disconnect(), timeout=cfg.disconnect_timeout)
        except Exception:
            pass

    # Serialize
    elapsed = time.monotonic() - stats["_start_time"]
    total_failed = len([e for e in failed_edges if not e.resolved])
    total_resolved = len([e for e in failed_edges if e.resolved])

    output = {
        "scan_meta": {
            "host": cfg.host,
            "port": cfg.port,
            "scan_type": "strategic",
            "phases_completed": phases_completed,
            "structure_depth": cfg.structure_depth,
            "deep_scan_branches": cfg.deep_branches,
            "max_depth": cfg.deep_max_depth,
            "max_index": cfg.max_index,
            "stop_after_failures": cfg.stop_after_failures,
            "max_gap_probe": cfg.max_gap_probe,
            "empty_leaf_limit": cfg.empty_leaf_limit,
            "health_check_every": cfg.health_check_every,
            "no_leaf_shortcut": False,
            "elapsed_seconds": round(elapsed, 2),
            "nodes_visited": stats["visited"],
            "nodes_skipped": stats["skipped"],
            "duplicates_skipped": stats.get("duplicates", 0),
            "failed_edges_total": len(failed_edges),
            "failed_edges_resolved": total_resolved,
            "failed_edges_remaining": total_failed,
        },
        "root_children": [node_to_dict(n) for n in root_nodes],
        "failed_edges": [
            {
                "parent_path": ".".join(str(p) for p in e.parent_abs_path),
                "child_index": e.child_index,
                "failure_type": e.failure_type,
                "error_detail": e.error_detail,
                "phase": e.phase,
                "retry_count": e.retry_count,
                "resolved": e.resolved,
            }
            for e in failed_edges
        ],
    }

    # Diff
    diff_result = None
    if not cfg.no_diff:
        diff_result = diff_scans(cfg.old_scan_path, root_nodes)
        output["diff_summary"] = diff_result

    # Write output
    with open(cfg.output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Summary
    print(f"\n{'=' * 70}")
    print(f"SCAN COMPLETE")
    print(f"  Phases completed: {phases_completed}")
    print(f"  Nodes visited:    {stats['visited']}")
    print(f"  Nodes skipped:    {stats['skipped']}")
    print(f"  Duplicates:       {stats.get('duplicates', 0)}")
    print(f"  Failed edges:     {total_failed} remaining / {total_resolved} resolved")
    print(f"  Elapsed:          {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"  Output:           {cfg.output_path}")
    print(f"{'=' * 70}")

    if diff_result:
        _print_diff(diff_result)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> StrategicConfig:
    env_host = get_key(".env", "GMA_HOST") or "127.0.0.1"
    env_user = get_key(".env", "GMA_USER") or "administrator"
    env_pass = get_key(".env", "GMA_PASSWORD") or "admin"

    p = argparse.ArgumentParser(description="Strategic validation scan for grandMA2 cd tree")
    p.add_argument("--host",             default=env_host)
    p.add_argument("--port",             type=int, default=30000)
    p.add_argument("--user",             default=env_user)
    p.add_argument("--password",         default=env_pass)
    p.add_argument("--delay",            type=float, default=0.08)
    p.add_argument("--timeout",          type=float, default=0.8)
    p.add_argument("--structure-depth",  type=int, default=3, dest="structure_depth")
    p.add_argument("--deep-branches",    default=",".join(DEFAULT_DEEP_BRANCHES), dest="deep_branches")
    p.add_argument("--skip-phase",       type=int, action="append", default=[], dest="skip_phases")
    p.add_argument("--output",           default="scan_output_new.json")
    p.add_argument("--old-scan",         default="scan_output.json", dest="old_scan")
    p.add_argument("--triage-retries",   type=int, default=3, dest="triage_retries")
    p.add_argument("--no-diff",          action="store_true", dest="no_diff")
    p.add_argument("--root-probe-max",   type=int, default=50, dest="root_probe_max")
    args = p.parse_args()

    return StrategicConfig(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        delay=args.delay,
        timeout=args.timeout,
        structure_depth=args.structure_depth,
        deep_branches=[b.strip() for b in args.deep_branches.split(",") if b.strip()],
        skip_phases=set(args.skip_phases),
        output_path=args.output,
        old_scan_path=args.old_scan,
        triage_retries=args.triage_retries,
        no_diff=args.no_diff,
        root_probe_max=args.root_probe_max,
    )


if __name__ == "__main__":
    cfg = parse_args()
    asyncio.run(main_async(cfg))

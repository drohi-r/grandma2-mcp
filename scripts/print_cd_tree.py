"""Generate a full MA2 cd tree document from scan_output.json.

Reads the recursive tree scan and writes a readable markdown document
to doc/ma2-cd-tree-full.md with root summary, full tree, and caveats.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCAN_FILE = ROOT / "scan_output.json"
DEFAULT_OUT_FILE = ROOT / "doc" / "ma2-cd-tree-full.md"

# How many consecutive similar leaves to show before collapsing
LEAF_COLLAPSE_THRESHOLD = 5
# For UserProfiles (cd 39), show first N profiles in detail
USERPROFILE_DETAIL_LIMIT = 1  # show Default only, rest as summary

INVALID_INDEXES = [12, 28, 29, 32, 44, 45, 47, 48, 49, 50]

# PresetType tree verified structure (scan_output falsely marks cd 10.2 as leaf)
PRESET_TYPE_ADDENDUM = """
> **Scanner caveat:** `scan_output.json` falsely marks `cd 10.2` (PresetTypes) as
> `is_leaf: true` because the parser misses rows with the PresetType/Feature/Attribute
> format. The tree IS navigable 6 levels deep (live-verified 2026-03-10):
>
> ```
> cd 10.2        → 9 PresetTypes (Dimmer, Position, Gobo, Color, Beam, Focus, Control, Shapers, Video)
> cd 10.2.5      → Beam features: SHUTTER(20), BEAM1(21), EFFECT(22)
> cd 10.2.5.1    → Attributes under SHUTTER: SHUTTER(22), STROBE_RATIO(0)
> cd 10.2.5.1.1  → SubAttributes of SHUTTER (Shutter, Strobe, Pulse, ...)
> cd 10.2.5.1.1.N → Leaf (NO OBJECTS FOUND)
> ```
>
> | PresetType | ID | cd path   | $PRESET  | $FEATURE (1st) | $ATTRIBUTE (1st) |
> |------------|----|-----------|----------|----------------|------------------|
> | Dimmer     | 1  | cd 10.2.1 | DIMMER   | DIMMER         | DIM              |
> | Position   | 2  | cd 10.2.2 | POSITION | POSITION       | PAN              |
> | Gobo       | 3  | cd 10.2.3 | GOBO     | GOBO1          | GOBO1            |
> | Color      | 4  | cd 10.2.4 | COLOR    | COLORRGB       | COLORRGB1        |
> | Beam       | 5  | cd 10.2.5 | BEAM     | SHUTTER        | SHUTTER          |
> | Focus      | 6  | cd 10.2.6 | FOCUS    | FOCUS          | FOCUS            |
> | Control    | 7  | cd 10.2.7 | CONTROL  | MSPEED         | INTENSITYMSPEED  |
> | Shapers    | 8  | cd 10.2.8 | —        | fixture-dep    | —                |
> | Video      | 9  | cd 10.2.9 | —        | fixture-dep    | —                |
"""


def get_max_depth(node: dict, depth: int = 1) -> int:
    children = node.get("children", [])
    if not children:
        return depth
    return max(get_max_depth(c, depth + 1) for c in children)


def count_nodes(node: dict) -> int:
    total = 1
    for c in node.get("children", []):
        total += count_nodes(c)
    return total


def is_leaf(node: dict) -> bool:
    return node.get("is_leaf", False) and not node.get("children")


def format_tree(
    nodes: list[dict],
    indent: int = 0,
    lines: list[str] | None = None,
    collapse_leaves: bool = True,
    parent_path: str = "",
) -> list[str]:
    """Recursively format tree nodes into indented text lines."""
    if lines is None:
        lines = []

    prefix = "  " * indent

    # Separate leaves from branches
    leaf_buffer: list[dict] = []

    def flush_leaves():
        if not leaf_buffer:
            return
        if len(leaf_buffer) <= LEAF_COLLAPSE_THRESHOLD or not collapse_leaves:
            for lf in leaf_buffer:
                _append_node_line(lf, indent, lines, is_leaf_node=True)
        else:
            # Show first 2, collapse middle, show last 1
            _append_node_line(leaf_buffer[0], indent, lines, is_leaf_node=True)
            _append_node_line(leaf_buffer[1], indent, lines, is_leaf_node=True)
            lines.append(
                f"{prefix}  ... ({len(leaf_buffer) - 3} more leaves) ..."
            )
            _append_node_line(leaf_buffer[-1], indent, lines, is_leaf_node=True)
        leaf_buffer.clear()

    for node in nodes:
        if is_leaf(node):
            leaf_buffer.append(node)
        else:
            flush_leaves()
            _append_node_line(node, indent, lines, is_leaf_node=False)
            children = node.get("children", [])
            if children:
                # Special handling for UserProfiles (cd 39) — collapse after first profile
                if parent_path == "" and node.get("path") == "39":
                    _format_userprofiles(node, indent, lines)
                else:
                    format_tree(
                        children,
                        indent + 1,
                        lines,
                        collapse_leaves,
                        parent_path=node.get("path", ""),
                    )

    flush_leaves()
    return lines


def _append_node_line(
    node: dict, indent: int, lines: list[str], is_leaf_node: bool
) -> None:
    prefix = "  " * indent
    path = node.get("path", "?")
    loc = node.get("location", "?")
    count = node.get("entry_count", 0)
    dup = node.get("duplicate_of")

    dup_mark = f" [DUP of cd {dup}]" if dup else ""
    leaf_mark = " [LEAF]" if is_leaf_node else ""

    if is_leaf_node:
        lines.append(f"{prefix}cd {path} → [{loc}]{leaf_mark}{dup_mark}")
    else:
        total = count_nodes(node)
        depth = get_max_depth(node)
        leaf_children = sum(1 for c in node.get("children", []) if is_leaf(c))
        leaf_info = f" + {leaf_children} leaves" if leaf_children > 0 else ""
        lines.append(
            f"{prefix}cd {path} → [{loc}] "
            f"({count} entries, {total} nodes, depth {depth})"
            f"{leaf_info}{dup_mark}"
        )


def _format_userprofiles(profiles_node: dict, indent: int, lines: list[str]):
    """Show first profile in detail, rest as summary table."""
    children = profiles_node.get("children", [])
    if not children:
        return

    # Show first profile (Default) in full detail
    detail_profiles = children[:USERPROFILE_DETAIL_LIMIT]
    remaining = children[USERPROFILE_DETAIL_LIMIT:]

    for prof in detail_profiles:
        if is_leaf(prof):
            _append_node_line(prof, indent + 1, lines, is_leaf_node=True)
        else:
            _append_node_line(prof, indent + 1, lines, is_leaf_node=False)
            format_tree(
                prof.get("children", []),
                indent + 2,
                lines,
                collapse_leaves=True,
                parent_path=prof.get("path", ""),
            )

    if remaining:
        prefix = "  " * (indent + 1)
        lines.append("")
        lines.append(
            f"{prefix}... {len(remaining)} more UserProfiles with similar structure ..."
        )
        lines.append("")
        lines.append(f"{prefix}| # | cd path | Name | Nodes | Depth |")
        lines.append(f"{prefix}|---|---------|------|-------|-------|")
        for prof in remaining:
            loc = prof.get("location", "?")
            # Extract just the profile name from location like "UserProfiles/Romar-J 2"
            name = loc.split("/")[-1] if "/" in loc else loc
            path = prof.get("path", "?")
            total = count_nodes(prof)
            depth = get_max_depth(prof)
            idx = prof.get("index", "?")
            dup = prof.get("duplicate_of")
            dup_mark = f" (DUP of cd {dup})" if dup else ""
            lines.append(
                f"{prefix}| {idx} | cd {path} | {name} | {total} | {depth} |{dup_mark}"
            )


def main():
    parser = argparse.ArgumentParser(description="Generate MA2 cd tree markdown from scan JSON")
    parser.add_argument("--input", default=str(DEFAULT_SCAN_FILE),
                        help="Path to scan output JSON (default: scan_output.json)")
    parser.add_argument("--output", default=None,
                        help="Path to output markdown (default: auto-derived from input)")
    args = parser.parse_args()

    scan_file = Path(args.input)
    if args.output:
        out_file = Path(args.output)
    elif scan_file.name == "scan_output.json":
        out_file = DEFAULT_OUT_FILE
    else:
        # Derive: scan_output_new.json -> doc/ma2-cd-tree-new.md
        stem = scan_file.stem.replace("scan_output", "ma2-cd-tree")
        out_file = ROOT / "doc" / f"{stem}.md"

    with open(scan_file) as f:
        data = json.load(f)

    meta = data["scan_meta"]
    root_children = data["root_children"]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Build root summary table
    root_rows = []
    for node in root_children:
        path = node.get("path", "?")
        loc = node.get("location", "?")
        count = node.get("entry_count", 0)
        total = count_nodes(node)
        depth = get_max_depth(node)
        leaf_mark = " [LEAF]" if is_leaf(node) else ""
        root_rows.append((path, loc, count, total, depth, leaf_mark))

    # Build full tree
    tree_lines = format_tree(root_children)

    # Write output
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(f"""---
title: "grandMA2 CD Tree — Full Validated Print"
description: "Complete recursive cd tree of grandMA2 onPC v3.9.60.65, live-scanned via telnet"
version: 1.0.0
created: {now}
last_updated: {now}
---

# grandMA2 CD Tree — Full Validated Print

**Source:** `scan_output.json` (live telnet scan of grandMA2 onPC v3.9.60.65)
**Scan stats:** {meta['nodes_visited']:,} nodes visited | {meta['duplicates_skipped']:,} duplicates | {meta['nodes_skipped']} skipped | {meta['elapsed_seconds']/60:.0f} min elapsed
**Max depth scanned:** {meta['max_depth']} | **Max index probed:** {meta['max_index']} | **Gap probe:** {meta['max_gap_probe']}

---

## Root Level Summary (`cd /`)

| cd | Location | Entries | Total Nodes | Max Depth | Notes |
|----|----------|---------|-------------|-----------|-------|
""")
        for path, loc, count, total, depth, leaf_mark in root_rows:
            f.write(
                f"| {path:>2} | {loc} | {count} | {total:,} | {depth} | {leaf_mark.strip()} |\n"
            )

        f.write(f"""
**Invalid indexes** (Error #72 COMMAND NOT EXECUTED): {', '.join(str(i) for i in INVALID_INDEXES)}

**Note:** Indexes 12, 28-29, 32, 44-45, 47-50 return errors. Index 11 (EditSetup) and
index 46 (Temp) exist but were not captured in this particular scan run.

---

## Known Caveats

### PresetType Tree (cd 10.2) — Scanner Bug

{PRESET_TYPE_ADDENDUM}

### UserProfiles (cd 39) — 89% of All Nodes

""")
        # Find UserProfiles row
        up_row = next((r for r in root_rows if r[0] == "39"), None)
        up_nodes = up_row[3] if up_row else 0
        f.write(f"""`cd 39` contains {up_nodes:,} of {meta['nodes_visited']:,} total nodes ({up_nodes*100//meta['nodes_visited']}%).
Each of the 254 profiles shares a nearly identical sub-structure (UserSettings,
Displays, Views, StoreDefaults, MatrixPool, ViewButtons, Arrangements, StoreSettings,
Cameras, RemoteDisplays, MaskPool). The full tree below shows the first profile
(Default) in detail and summarizes the rest.

---

## Full Tree

```
""")
        for line in tree_lines:
            f.write(line + "\n")

        f.write("```\n")

    print(f"Generated {out_file} ({len(tree_lines)} lines)")
    print(f"Root branches: {len(root_rows)}")


if __name__ == "__main__":
    main()

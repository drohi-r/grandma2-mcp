"""Parse scan_full_log.txt into a tree schematic."""
import re, sys

lines = open("scan_full_log.txt", encoding="utf-8").readlines()

# Parse: [d=N | path | +visited ~skipped] cd X -> 'location' (N entries) [tag]
pat = re.compile(
    r"\[d=(\d+)\s*\|\s*([\d.]+)\s*\|.*?\]\s*cd\s+(\d+)\s*->\s*'([^']+)'\s*\((\d+)\s*entries\)(.*)"
)
miss_pat = re.compile(r"\[d=(\d+)\s*\|\s*([\d.]+)\s*\|.*?\]\s*cd\s+(\d+)\s*->\s*MISS")

nodes = []  # (depth, path, index, location, entries, tag)
misses = []

for line in lines:
    m = pat.search(line)
    if m:
        depth = int(m.group(1))
        path = m.group(2)
        idx = int(m.group(3))
        loc = m.group(4)
        entries = int(m.group(5))
        tag = m.group(6).strip()
        nodes.append((depth, path, idx, loc, entries, tag))
        continue
    m = miss_pat.search(line)
    if m:
        misses.append((int(m.group(1)), m.group(2), int(m.group(3))))

# Build tree schematic
# Group by root branch
print(f"=== FULL TREE SCHEMATIC ({len(nodes)} nodes, {len(misses)} misses) ===\n")

# Find completed branches
branch_done = re.findall(r"Branch (\d+)/42 done", open("scan_full_log.txt").read())
completed = set(int(b) for b in branch_done)

# Print root info
root_line = [l for l in lines if "root branches:" in l.lower()]
if root_line:
    print(root_line[0].strip())
print(f"Completed branches: {sorted(completed)}")
print(f"Missing branches: {sorted(set(range(1,43)) - completed)}\n")

# Print tree with indentation
for depth, path, idx, loc, entries, tag in nodes:
    indent = "  " * (depth - 1)
    # Extract just the last part of location for readability
    parts = loc.split("/")
    name = parts[-1] if parts else loc
    
    leaf = ""
    if "[LEAF]" in tag:
        leaf = " [LEAF]"
    elif "DEPTH-CAP" in tag:
        leaf = f" {tag}"
    
    entry_info = ""
    if entries > 0 and "[LEAF]" not in tag:
        entry_info = f" ({entries} children)"
    
    print(f"{indent}{name}{entry_info}{leaf}")

# Print misses
if misses:
    print(f"\n=== MISSES ({len(misses)}) ===")
    for d, p, i in misses:
        print(f"  depth={d} path={p} cd {i} -> MISS")

# Stats
print(f"\n=== SUMMARY ===")
print(f"  Total nodes visited: {len(nodes)}")
print(f"  Total misses: {len(misses)}")
print(f"  Max depth reached: {max(d for d,_,_,_,_,_ in nodes)}")
print(f"  Completed root branches: {len(completed)}/42")
print(f"  Remaining root branches: {42 - len(completed)}")

# Count by depth
from collections import Counter
depth_counts = Counter(d for d,_,_,_,_,_ in nodes)
print(f"\n  Depth distribution:")
for d in sorted(depth_counts):
    print(f"    d={d}: {depth_counts[d]} nodes")


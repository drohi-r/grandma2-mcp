"""Build condensed tree: collapse leaf-only flat branches, show structure."""
import re

lines = open("scan_full_log.txt", encoding="utf-8").readlines()

pat = re.compile(
    r"\[d=(\d+)\s*\|\s*([\d.]+)\s*\|.*?\]\s*cd\s+(\d+)\s*->\s*'([^']+)'\s*\((\d+)\s*entries\)(.*)"
)

nodes = []
for line in lines:
    m = pat.search(line)
    if m:
        nodes.append({
            "depth": int(m.group(1)),
            "path": m.group(2),
            "idx": int(m.group(3)),
            "loc": m.group(4),
            "entries": int(m.group(5)),
            "leaf": "[LEAF]" in m.group(6),
        })

# Build condensed output: group consecutive leaves at same depth under same parent
i = 0
while i < len(nodes):
    n = nodes[i]
    depth = n["depth"]
    parts = n["loc"].split("/")
    name = parts[-1]
    indent = "  " * (depth - 1)
    
    if n["leaf"]:
        # Count consecutive leaves at same depth with same parent prefix
        parent = "/".join(parts[:-1])
        j = i + 1
        while j < len(nodes) and nodes[j]["leaf"] and nodes[j]["depth"] == depth:
            jp = "/".join(nodes[j]["loc"].split("/")[:-1])
            if jp != parent:
                break
            j += 1
        count = j - i
        if count > 3:
            first_name = parts[-1]
            last_name = nodes[j-1]["loc"].split("/")[-1]
            print(f"{indent}{first_name} .. {last_name}  [{count} leaves]")
        else:
            for k in range(i, j):
                lname = nodes[k]["loc"].split("/")[-1]
                print(f"{indent}{lname} [LEAF]")
        i = j
    else:
        print(f"{indent}{name} ({n['entries']} children)")
        i += 1

# What's missing
print("\n=== WHAT'S MISSING (not yet scanned) ===")
print("Completed: root branches 1-10")
print("Remaining: root branches 11-42\n")

# From the root list we know these are the 38 parsed entries
# plus gap probing 12, 28, 29, 32 (genuinely missing from MA2)
# The scan tried indexes 1-42
branch_done = {1,2,3,4,5,6,7,8,9,10}
# Branch 11 was in progress (EditSetup)
print("Branch 11 (EditSetup): IN PROGRESS when stopped")
print("  - Was on FixtureType 4/14, will mirror LiveSetup structure")
print()

# Known root names from the scan
root_names = {}
for n in nodes:
    if n["depth"] == 1:
        root_names[n["idx"]] = n["loc"]

print("Scanned root branches:")
for idx in sorted(root_names):
    print(f"  cd {idx:2d} -> {root_names[idx]}")

print("\nNot yet scanned (indexes 11-42):")
# From previous scan data we know some of these
known = {
    11: "EditSetup (IN PROGRESS)",
    13: "DMX 13",
    14: "Pools/Groups 14",
    15: "Pools/Presets 15",
    16: "Pools/Sequences 16",
    17: "Pools/Cues 17",
    18: "Pools/Effects 18",
    19: "Pools/Forms 19",
    20: "Pools/Pages 20",
    21: "Pools/Macros 21",
    22: "Pools/Views 22",
    23: "Forms 23",
    24: "Plugins 24",
    25: "Agendas 25",
    26: "Remotes 26",
    27: "AutoCreate 27",
    30: "Layout 30",
    31: "Layout 31",
    33: "MAtricks 33",
    34: "Worlds 34",
    35: "Filters 35",
    36: "Executor configs 36",
    37: "Executors 37",
    38: "Layouts 38",
    39: "Channels 39",
    40: "Outputs 40",
    41: "Stage 41",
    42: "Patch 42",
}
for idx in range(11, 43):
    if idx in root_names:
        continue
    name = known.get(idx, "UNKNOWN (may be gap-probe MISS)")
    print(f"  cd {idx:2d} -> {name}")


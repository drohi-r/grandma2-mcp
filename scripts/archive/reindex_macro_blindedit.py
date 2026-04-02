"""Insert BlindEdit On line at index 0 and reindex all macro jump targets.

One-shot transformation script for -Create FT_Pools-.xml.
Uses string/regex processing to preserve exact MA2 XML entity encodings.
"""

import re
import shutil
from pathlib import Path

MACRO_DIR = Path(
    r"C:\ProgramData\MA Lighting Technologies\grandma\gma2_V_3.9.60\macros"
)
MACRO_FILE = MACRO_DIR / "-Create FT_Pools-.xml"
BACKUP_FILE = MACRO_DIR / "archive" / "-Create FT_Pools-.xml.bak"

MACRO_NAME_ESCAPED = "-Create FT_Pools-"

# New line to insert at index 0
NEW_LINE_BLOCK = (
    '\t\t<Macroline index="0" delay="0.06">\n'
    "\t\t\t<text>BlindEdit On ; ClearAll</text>\n"
    "\t\t\t<info>INIT: blind edit on + clear</info>\n"
    "\t\t</Macroline>\n"
)

# Regex: match <Macroline index="N" but NOT <Macro index="N"
RE_MACROLINE_INDEX = re.compile(r'(<Macroline\s+index=")(\d+)(")')

# Regex: match Go Macro 1.&quot;-Create FT_Pools-&quot;.N  (with XML entity encoding)
RE_JUMP_TARGET = re.compile(
    r"(Go Macro 1\.&quot;" + re.escape(MACRO_NAME_ESCAPED) + r"&quot;\.)(\d+)"
)


def increment_match(m: re.Match) -> str:
    """Increment the captured numeric group by 1."""
    return m.group(1) + str(int(m.group(2)) + 1) + (m.group(3) if m.lastindex == 3 else "")


def main() -> None:
    if not MACRO_FILE.exists():
        print(f"ERROR: Macro file not found: {MACRO_FILE}")
        return

    content = MACRO_FILE.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)

    # --- Collect pre-transform jump targets for verification ---
    old_jumps: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        for m in RE_JUMP_TARGET.finditer(line):
            old_jumps.append((i, m.group(2)))

    print(f"Found {len(old_jumps)} Go Macro jump targets to reindex.")

    # --- Step 1: Increment all <Macroline index="N" by +1 ---
    new_lines: list[str] = []
    for line in lines:
        line = RE_MACROLINE_INDEX.sub(increment_match, line)
        new_lines.append(line)
    lines = new_lines

    # --- Step 2: Increment all Go Macro jump targets by +1 ---
    new_lines = []
    for line in lines:
        line = RE_JUMP_TARGET.sub(increment_match, line)
        new_lines.append(line)
    lines = new_lines

    # --- Step 3: Remove redundant "ClearAll ; " from old index 0 (now index 1) ---
    for i, line in enumerate(lines):
        if 'index="1"' in line and "<Macroline" in line:
            # Find the <text> line following this Macroline tag
            for j in range(i + 1, min(i + 5, len(lines))):
                if "<text>ClearAll ; FixtureType 1 Thru</text>" in lines[j]:
                    lines[j] = lines[j].replace(
                        "<text>ClearAll ; FixtureType 1 Thru</text>",
                        "<text>FixtureType 1 Thru</text>",
                    )
                    print("Removed redundant 'ClearAll ; ' from index 1.")
                    break
            break

    # --- Step 4: Insert new index 0 after <Appearance .../> line ---
    insert_pos = None
    for i, line in enumerate(lines):
        if "<Appearance " in line and "/>" in line:
            insert_pos = i + 1
            break

    if insert_pos is None:
        print("ERROR: Could not find <Appearance .../> line to insert after.")
        return

    for j, new_line in enumerate(NEW_LINE_BLOCK.splitlines(keepends=True)):
        lines.insert(insert_pos + j, new_line)

    print(f"Inserted new index 0 (BlindEdit On ; ClearAll) at file line {insert_pos + 1}.")

    # --- Verification ---
    result = "".join(lines)

    # Count Macroline elements
    macroline_count = len(re.findall(r"<Macroline\s+index=", result))
    print(f"\nTotal Macroline count: {macroline_count} (expected 104)")

    # Verify index range
    indices = [int(m.group(1)) for m in re.finditer(r'<Macroline\s+index="(\d+)"', result)]
    if indices:
        print(f"Index range: {min(indices)}-{max(indices)} (expected 0-103)")

    # Verify first and last lines
    first_text = re.search(r'index="0".*?<text>(.*?)</text>', result, re.DOTALL)
    last_text = re.search(r'index="103".*?<text>(.*?)</text>', result, re.DOTALL)
    if first_text:
        print(f"Index 0 text: {first_text.group(1)}")
    if last_text:
        print(f"Index 103 text: {last_text.group(1)}")

    # Print jump target mapping
    new_jumps: list[tuple[str, str]] = []
    for m in RE_JUMP_TARGET.finditer(result):
        new_jumps.append((m.group(0), m.group(2)))

    print(f"\nJump target verification ({len(new_jumps)} targets):")
    print(f"{'Old .N':>8}  ->  {'New .N':>8}  Section")
    print("-" * 50)
    for (_, old_n), (full_new, new_n) in zip(old_jumps, new_jumps):
        expected = str(int(old_n) + 1)
        status = "OK" if new_n == expected else f"MISMATCH (expected .{expected})"
        print(f"    .{old_n:>3}  ->    .{new_n:>3}  {status}")

    mismatches = sum(
        1
        for (_, old_n), (_, new_n) in zip(old_jumps, new_jumps)
        if new_n != str(int(old_n) + 1)
    )
    if mismatches:
        print(f"\nERROR: {mismatches} jump target mismatches! NOT writing output.")
        return

    # --- Backup and write ---
    BACKUP_FILE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MACRO_FILE, BACKUP_FILE)
    print(f"\nBackup saved to: {BACKUP_FILE}")

    MACRO_FILE.write_text(result, encoding="utf-8")
    print(f"Transformed macro written to: {MACRO_FILE}")
    print("Done.")


if __name__ == "__main__":
    main()

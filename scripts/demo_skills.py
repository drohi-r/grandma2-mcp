"""
scripts/demo_skills.py -- Showcase the .claude/skills/ instruction modules.

Reads every SKILL.md in .claude/skills/ and prints a formatted catalog.
No live console required — stdlib only.

Usage:
    python scripts/demo_skills.py                    # brief catalog (default)
    python scripts/demo_skills.py --full             # all skill bodies
    python scripts/demo_skills.py --skill cue-list   # one skill (partial match)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Locate repo root
# ---------------------------------------------------------------------------

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
_SKILLS_DIR = _REPO_ROOT / ".claude" / "skills"

_WIDTH = 72


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _parse_skill(path: Path) -> dict:
    """Parse a SKILL.md file into a metadata + body dict."""
    text = path.read_text(encoding="utf-8")

    # Split front matter
    fm: dict[str, str] = {}
    body = text
    if text.startswith("---\n"):
        end = text.index("---\n", 4)
        fm_text = text[4:end]
        body = text[end + 4:]
        for line in fm_text.splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                fm[k.strip()] = v.strip()

    # Extract H2 section headings from body for the brief summary
    sections = re.findall(r"^## (.+)", body, re.MULTILINE)

    return {
        "slug": path.parent.name,
        "title": fm.get("title", path.parent.name),
        "description": fm.get("description", ""),
        "version": fm.get("version", "?"),
        "last_updated": fm.get("last_updated", ""),
        "sections": sections,
        "body": body.strip(),
    }


def _load_all() -> list[dict]:
    skills = []
    for skill_md in sorted(_SKILLS_DIR.glob("*/SKILL.md")):
        skills.append(_parse_skill(skill_md))
    return skills


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _hr(char: str = "=") -> None:
    print(char * _WIDTH)


def _print_brief(skills: list[dict]) -> None:
    print()
    print(f"grandMA2 MCP Server -- Skill Catalog  ({len(skills)} skills)")
    _hr()
    for i, s in enumerate(skills, 1):
        slug = s["slug"]
        ver = s["version"]
        # Align slug + version
        left = f"  [{i}]  {slug}"
        right = ver
        pad = _WIDTH - len(left) - len(right) - 2
        print(f"{left}{' ' * max(pad, 1)}{right}")
        # Description (wrapped)
        desc = s["description"]
        if desc:
            # Trim to first sentence for brevity
            short = desc.split("—")[0].strip().rstrip(".")
            print(f"       {short}")
        # Section list
        if s["sections"]:
            sec_str = " · ".join(s["sections"][:4])
            if len(s["sections"]) > 4:
                sec_str += f" · (+{len(s['sections']) - 4} more)"
            # Wrap long section lists
            if len(sec_str) > _WIDTH - 10:
                sec_str = sec_str[: _WIDTH - 13] + "..."
            print(f"       Sections: {sec_str}")
        print()
    _hr()
    print("  python scripts/demo_skills.py --full              all skill bodies")
    print("  python scripts/demo_skills.py --skill <name>      one skill in full")
    print()


def _print_full_skill(s: dict) -> None:
    """Print one skill exactly as Skill.as_user_message() would inject it."""
    title = s["title"]
    ver = s["version"]
    header = f"[Skill: {title} v{ver}]"
    _hr()
    print(header)
    _hr("-")
    print(s["body"])
    print()


def _print_full(skills: list[dict]) -> None:
    print()
    print(f"grandMA2 MCP Server -- Skill Catalog  ({len(skills)} skills, full bodies)")
    print()
    for s in skills:
        _print_full_skill(s)
    _hr()
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Showcase .claude/skills/ instruction modules"
    )
    parser.add_argument(
        "--full", action="store_true",
        help="Print complete skill bodies (injection format)",
    )
    parser.add_argument(
        "--skill", metavar="NAME",
        help="Print one skill in full (partial slug match)",
    )
    args = parser.parse_args()

    if not _SKILLS_DIR.exists():
        print(f"ERROR: skills directory not found: {_SKILLS_DIR}", file=sys.stderr)
        sys.exit(1)

    skills = _load_all()
    if not skills:
        print("No SKILL.md files found.", file=sys.stderr)
        sys.exit(1)

    if args.skill:
        query = args.skill.lower()
        matches = [s for s in skills if query in s["slug"].lower()]
        if not matches:
            print(f"No skill matching '{args.skill}'. Available slugs:")
            for s in skills:
                print(f"  {s['slug']}")
            sys.exit(1)
        print()
        for s in matches:
            _print_full_skill(s)
    elif args.full:
        _print_full(skills)
    else:
        _print_brief(skills)


if __name__ == "__main__":
    main()

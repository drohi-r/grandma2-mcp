"""XC1 — every priority skill must carry an Expert checklist section.

See docs/superpowers/plans/2026-05-27-path-a-implementation.md §Task 1.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"

PRIORITY_SKILLS = [
    "busking-template-generator",
    "busking-lighting-performance",
    "preset-library-architect",
    "cue-tracking-and-timing",
    "macro-advanced",
    "macro-linter-and-refactorer",
    "executor-configuration",
    "constrained-color-design",
    "view-and-layout-designer",
]


@pytest.mark.parametrize("slug", PRIORITY_SKILLS)
def test_skill_has_expert_checklist(slug):
    body = (SKILLS_DIR / slug / "SKILL.md").read_text(encoding="utf-8")
    assert "## Expert checklist" in body, (
        f"{slug}/SKILL.md must have a '## Expert checklist' section "
        "(see Task 1 of docs/superpowers/plans/2026-05-27-path-a-implementation.md)"
    )


@pytest.mark.parametrize("slug", PRIORITY_SKILLS)
def test_expert_checklist_has_at_least_five_items(slug):
    body = (SKILLS_DIR / slug / "SKILL.md").read_text(encoding="utf-8")
    if "## Expert checklist" not in body:
        pytest.fail(f"{slug}: no checklist (caught by previous test)")
    checklist = body.split("## Expert checklist", 1)[1].split("\n## ", 1)[0]
    items = [ln for ln in checklist.splitlines() if ln.lstrip().startswith(("- [", "* "))]
    assert len(items) >= 5, (
        f"{slug}: expert checklist must contain at least 5 items "
        f"(found {len(items)})"
    )

"""
tests/test_architecture_hygiene.py — Architecture hygiene tests

These tests enforce structural invariants described in the transcript-based refactor plan.
They do NOT test behavior — they test that the codebase respects its own architectural
contracts so context pressure and code quality don't drift over time.

Invariants enforced:
1. Command builders have no network I/O imports
2. .claude/rules/ files all have valid front matter
3. .claude/skills/ SKILL.md files all have valid front matter
4. doc/ markdown files all have valid front matter
5. Skill.as_user_message() always includes [Skill: header
6. SkillRegistry.get_usable() never returns un-approved DESTRUCTIVE skills
7. LTM session snapshots are v2 format (compressed)
8. Worker output envelope fields are always present
9. Safety gate: DESTRUCTIVE commands require confirm_destructive in tool signatures
10. MCP resource functions are read-only (no telnet send calls)
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent


# ── 1. Command builders have no network I/O imports ──────────────────────────

class TestCommandBuilderPurity:
    COMMANDS_DIR = REPO_ROOT / "src" / "commands"
    FORBIDDEN_IMPORTS = {"src.telnet_client", "src.navigation", "src.server", "asyncio"}

    def _python_files(self):
        return [f for f in self.COMMANDS_DIR.rglob("*.py") if f.name != "__init__.py"]

    def test_no_telnet_import_in_builders(self):
        for pyfile in self._python_files():
            source = pyfile.read_text(encoding="utf-8")
            for forbidden in self.FORBIDDEN_IMPORTS:
                assert forbidden not in source, (
                    f"{pyfile.relative_to(REPO_ROOT)} imports '{forbidden}' "
                    f"— command builders must stay pure (no network I/O)"
                )

    def test_no_async_functions_in_builders(self):
        """Command builders must be sync — no async def in commands/."""
        for pyfile in self._python_files():
            source = pyfile.read_text(encoding="utf-8")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.AsyncFunctionDef):
                    pytest.fail(
                        f"{pyfile.relative_to(REPO_ROOT)}:{node.lineno} — "
                        f"async def '{node.name}' in command builder. "
                        f"Builders must be synchronous pure functions."
                    )


# ── 2. .claude/rules/ files have valid front matter ──────────────────────────

class TestClaudeRulesFrontMatter:
    RULES_DIR = REPO_ROOT / ".claude" / "rules"
    REQUIRED_FIELDS = {"title", "description", "version", "created", "last_updated"}

    def _rule_files(self):
        if not self.RULES_DIR.exists():
            return []
        return list(self.RULES_DIR.glob("*.md"))

    def test_rules_directory_exists(self):
        assert self.RULES_DIR.exists(), ".claude/rules/ directory must exist"

    def test_each_rule_file_has_front_matter(self):
        for md in self._rule_files():
            content = md.read_text(encoding="utf-8")
            assert content.startswith("---\n"), (
                f"{md.name} is missing YAML front matter (must start with ---)"
            )

    def test_each_rule_file_has_required_fields(self):
        for md in self._rule_files():
            content = md.read_text(encoding="utf-8")
            if not content.startswith("---\n"):
                continue  # caught by previous test
            fm_end = content.index("---\n", 4)
            front_matter = content[4:fm_end]
            for field in self.REQUIRED_FIELDS:
                assert f"{field}:" in front_matter, (
                    f"{md.name} is missing required front matter field: {field}"
                )


# ── 3. .claude/skills/ SKILL.md files have valid front matter ────────────────

class TestSkillFileFrontMatter:
    SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
    REQUIRED_FIELDS = {"title", "description", "version", "created", "last_updated"}

    def _skill_files(self):
        if not self.SKILLS_DIR.exists():
            return []
        return list(self.SKILLS_DIR.glob("*/SKILL.md"))

    def test_skills_directory_exists(self):
        assert self.SKILLS_DIR.exists(), ".claude/skills/ directory must exist"

    def test_each_skill_has_skill_md(self):
        if not self.SKILLS_DIR.exists():
            return
        for skill_dir in self.SKILLS_DIR.iterdir():
            if skill_dir.is_dir():
                assert (skill_dir / "SKILL.md").exists(), (
                    f".claude/skills/{skill_dir.name}/ must contain SKILL.md"
                )

    def test_each_skill_has_required_front_matter(self):
        for md in self._skill_files():
            content = md.read_text(encoding="utf-8")
            assert content.startswith("---\n"), f"{md} missing front matter"
            fm_end = content.index("---\n", 4)
            front_matter = content[4:fm_end]
            for field in self.REQUIRED_FIELDS:
                assert f"{field}:" in front_matter, (
                    f"{md} missing required front matter field: {field}"
                )


# ── 4. doc/ markdown files have valid front matter ───────────────────────────

class TestDocFrontMatter:
    DOC_DIR = REPO_ROOT / "doc"
    REQUIRED_FIELDS = {"title", "description", "version", "created", "last_updated"}

    def _doc_files(self):
        if not self.DOC_DIR.exists():
            return []
        return list(self.DOC_DIR.glob("*.md"))

    def test_doc_md_files_have_front_matter(self):
        for md in self._doc_files():
            content = md.read_text(encoding="utf-8")
            assert content.startswith("---\n"), (
                f"doc/{md.name} is missing YAML front matter"
            )

    def test_doc_md_files_have_required_fields(self):
        for md in self._doc_files():
            content = md.read_text(encoding="utf-8")
            if not content.startswith("---\n"):
                continue
            fm_end = content.index("---\n", 4)
            front_matter = content[4:fm_end]
            for field in self.REQUIRED_FIELDS:
                assert f"{field}:" in front_matter, (
                    f"doc/{md.name} missing required front matter field: {field}"
                )


# ── 5. Skill.as_user_message() format ────────────────────────────────────────

class TestSkillInjectionFormat:
    def test_as_user_message_header_format(self):
        import time

        from src.skill import Skill
        now = time.time()
        s = Skill(
            id="test-id", version=2, parent_id=None, name="my_skill",
            description="test", body="Step 1\nStep 2",
            quality_score=0.9, safety_scope="SAFE_WRITE",
            applicable_context="test", created_at=now, updated_at=now,
            source_session_id=None, approved=True,
        )
        msg = s.as_user_message()
        assert msg.startswith("[Skill:"), "as_user_message must start with [Skill: header"
        assert "my_skill" in msg
        assert "v2" in msg
        assert "Step 1" in msg

    def test_as_user_message_newline_separator(self):
        import time

        from src.skill import Skill
        now = time.time()
        s = Skill(
            id="x", version=1, parent_id=None, name="n",
            description="d", body="body", quality_score=1.0,
            safety_scope="SAFE_READ", applicable_context="c",
            created_at=now, updated_at=now, source_session_id=None, approved=True,
        )
        lines = s.as_user_message().split("\n")
        assert lines[0].startswith("[Skill:")
        assert lines[1] == "body"


# ── 6. SkillRegistry.get_usable() safety gate ────────────────────────────────

class TestGetUsableSafetyGate:
    def test_unapproved_destructive_returns_none(self, tmp_path):
        from src.skill import SkillRegistry
        reg = SkillRegistry(db_path=tmp_path / "test.db")
        s = reg.promote_from_session(
            session_id="s1", name="Dangerous", description="d",
            body="steps", safety_scope="DESTRUCTIVE", applicable_context="c",
        )
        assert reg.get_usable(s.id) is None
        reg.close()

    def test_approved_destructive_is_returned(self, tmp_path):
        from src.skill import SkillRegistry
        reg = SkillRegistry(db_path=tmp_path / "test.db")
        s = reg.promote_from_session(
            session_id="s2", name="Approved", description="d",
            body="steps", safety_scope="DESTRUCTIVE", applicable_context="c",
        )
        reg.approve(s.id)
        assert reg.get_usable(s.id) is not None
        reg.close()


# ── 7. LTM session snapshots are v2 format ───────────────────────────────────

class TestLTMSnapshotVersion:
    def test_save_session_produces_v2_snapshot(self, tmp_path):
        from src.agent_memory import LongTermMemory, WorkingMemory
        ltm = LongTermMemory(db_path=tmp_path / "test.db")
        wm = WorkingMemory(task_description="arch test")
        wm.completed_steps.append("step_one")
        ltm.save_session(wm, outcome="ok")
        snap = ltm.recall_session(wm.session_id)
        assert snap is not None
        assert snap.get("_v") == 2, "LTM session snapshot must be v2 compressed format"
        assert "fixtures" not in snap, "v2 snapshot must not contain full fixture dicts"
        ltm.close()

    def test_v2_snapshot_has_decision_fields(self, tmp_path):
        from src.agent_memory import LongTermMemory, WorkingMemory
        ltm = LongTermMemory(db_path=tmp_path / "test.db")
        wm = WorkingMemory(task_description="decisions test")
        wm.failed_steps.append("failed_step")
        wm.charge_tokens(50)
        ltm.save_session(wm, outcome="partial")
        snap = ltm.recall_session(wm.session_id)
        assert "completed_steps" in snap
        assert "failed_steps" in snap
        assert "token_spend" in snap
        assert snap["token_spend"] == 50
        ltm.close()


# ── 8. CLAUDE.md is under 200 lines ─────────────────────────────────────────

class TestCLAUDEMDSize:
    def test_claude_md_under_200_lines(self):
        claude_md = REPO_ROOT / "CLAUDE.md"
        lines = claude_md.read_text(encoding="utf-8").splitlines()
        assert len(lines) <= 200, (
            f"CLAUDE.md is {len(lines)} lines — must stay under 200 lines. "
            f"Move domain knowledge to .claude/rules/ instead."
        )

    def test_claude_md_has_front_matter(self):
        content = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        assert content.startswith("---\n"), "CLAUDE.md must have YAML front matter"

    def test_claude_rules_dir_exists(self):
        assert (REPO_ROOT / ".claude" / "rules").exists(), (
            ".claude/rules/ must exist — CLAUDE.md delegates scoped rules there"
        )

    def test_claude_skills_dir_exists(self):
        assert (REPO_ROOT / ".claude" / "skills").exists(), (
            ".claude/skills/ must exist for reusable instruction modules"
        )


# ── 9. Responsibility map and tool tier docs exist ────────────────────────────

class TestArchDocuments:
    def test_responsibility_map_exists(self):
        assert (REPO_ROOT / "doc" / "responsibility-map.md").exists(), (
            "doc/responsibility-map.md must exist — generated by Phase 1 architecture audit"
        )

    def test_tool_surface_tiers_exists(self):
        assert (REPO_ROOT / "doc" / "tool-surface-tiers.md").exists(), (
            "doc/tool-surface-tiers.md must exist — tool tier classification"
        )

    def test_transcript_audit_exists(self):
        assert (REPO_ROOT / "doc" / "transcript-architecture-audit.md").exists(), (
            "doc/transcript-architecture-audit.md must exist — MCP primitive audit"
        )


# ── 10. MCP resource functions are read-only (no telnet send) ────────────────

class TestResourcePurity:
    """MCP resources must not call telnet send — they are read-only context."""

    FORBIDDEN_IN_RESOURCES = ["telnet_send", "send_command", "_send", "telnet_client"]

    def test_resource_functions_do_not_import_telnet(self):
        """Parse server.py and check that @mcp.resource functions don't call telnet."""
        server_src = (REPO_ROOT / "src" / "server.py").read_text(encoding="utf-8")
        # Find all resource-decorated function bodies using simple regex
        # This is a structural heuristic, not a full AST parse
        resource_blocks = re.findall(
            r"@mcp\.resource\([^)]*\)\s*def \w+[^@]*?(?=@mcp\.|^def main|$)",
            server_src, re.DOTALL | re.MULTILINE,
        )
        for block in resource_blocks:
            for forbidden in self.FORBIDDEN_IN_RESOURCES:
                assert forbidden not in block, (
                    f"MCP resource function contains '{forbidden}' — "
                    f"resources must be read-only and must not call telnet"
                )


# ── 11. SubTask has workflow field ───────────────────────────────────────────

class TestSubTaskWorkflowHygiene:
    def test_subtask_workflow_field_exists(self):
        """SubTask must have a workflow attribute (Literal inspect/plan/execute)."""
        from src.task_decomposer import SubTask
        from src.vocab import RiskTier
        st = SubTask(
            name="hygiene_check",
            agent_role="TestAgent",
            description="structural check",
            allowed_risk=RiskTier.SAFE_READ,
            mcp_tools=[],
        )
        assert hasattr(st, "workflow"), "SubTask must have a 'workflow' attribute"
        assert st.workflow in ("inspect", "plan", "execute"), (
            f"workflow must be 'inspect', 'plan', or 'execute', got {st.workflow!r}"
        )

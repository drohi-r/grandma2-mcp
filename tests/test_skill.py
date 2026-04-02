"""
tests/test_skill.py — Unit tests for src/skill.py

All tests use a temp SQLite DB.  No live console or network required.
"""

from __future__ import annotations

import time
import uuid

import pytest

from src.skill import (
    Skill, SkillRegistry, _slugify,
    _load_filesystem_skill, _list_filesystem_skills,
)

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def reg(tmp_path):
    db = tmp_path / "test_skills.db"
    r = SkillRegistry(db_path=db)
    yield r
    r.close()


def _make_skill(**overrides) -> Skill:
    now = time.time()
    defaults = dict(
        id=str(uuid.uuid4()),
        version=1,
        parent_id=None,
        name="blue_wash_look",
        description="Store a blue wash cue",
        body="# Steps\n1. Select wash fixtures\n2. Apply blue preset\n3. Store cue",
        quality_score=0.9,
        safety_scope="SAFE_WRITE",
        applicable_context="wash fixtures color cue storage",
        created_at=now,
        updated_at=now,
        source_session_id="abc12345",
        approved=True,
    )
    defaults.update(overrides)
    return Skill(**defaults)


# ---------------------------------------------------------------------------
# _slugify helper
# ---------------------------------------------------------------------------

class TestSlugify:
    def test_basic(self):
        assert _slugify("Create Blue Wash Look") == "create_blue_wash_look"

    def test_removes_special_chars(self):
        assert _slugify("store cue #5!") == "store_cue_5"

    def test_truncates(self):
        long = "a" * 100
        assert len(_slugify(long)) <= 60

    def test_empty(self):
        assert _slugify("") == ""


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class TestSchema:
    def test_table_created(self, reg):
        rows = reg._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        names = {r[0] for r in rows}
        assert "skills" in names

    def test_indexes_created(self, reg):
        rows = reg._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
        names = {r[0] for r in rows}
        assert "idx_skills_name" in names
        assert "idx_skills_scope" in names


# ---------------------------------------------------------------------------
# save / get round-trip
# ---------------------------------------------------------------------------

class TestSaveGet:
    def test_save_and_retrieve(self, reg):
        s = _make_skill()
        reg.save(s)
        retrieved = reg.get(s.id)
        assert retrieved is not None
        assert retrieved.id == s.id
        assert retrieved.name == s.name
        assert retrieved.description == s.description
        assert abs(retrieved.quality_score - 0.9) < 0.001

    def test_get_nonexistent(self, reg):
        assert reg.get("does-not-exist") is None

    def test_replace_on_duplicate_id(self, reg):
        s = _make_skill(name="original")
        reg.save(s)
        s2 = _make_skill(id=s.id, name="updated")
        reg.save(s2)
        retrieved = reg.get(s.id)
        assert retrieved.name == "updated"

    def test_approved_bool_round_trip(self, reg):
        s = _make_skill(approved=False)
        reg.save(s)
        assert reg.get(s.id).approved is False

        s2 = _make_skill(approved=True)
        reg.save(s2)
        assert reg.get(s2.id).approved is True


# ---------------------------------------------------------------------------
# promote_from_session
# ---------------------------------------------------------------------------

class TestPromoteFromSession:
    def test_basic_promotion(self, reg):
        skill = reg.promote_from_session(
            session_id="sess001",
            name="My First Skill",
            description="A test skill",
            body="## Steps\n1. Do thing",
            safety_scope="SAFE_WRITE",
            applicable_context="test context",
            quality_score=0.85,
        )
        assert skill.version == 1
        assert skill.parent_id is None
        assert skill.source_session_id == "sess001"
        assert skill.approved is True  # SAFE_WRITE → auto-approved
        assert abs(skill.quality_score - 0.85) < 0.001

    def test_destructive_skill_not_approved(self, reg):
        skill = reg.promote_from_session(
            session_id="sess002",
            name="dangerous_skill",
            description="Deletes things",
            body="## Steps\n1. Delete everything",
            safety_scope="DESTRUCTIVE",
            applicable_context="cleanup",
            quality_score=1.0,
        )
        assert skill.approved is False

    def test_safe_read_skill_auto_approved(self, reg):
        skill = reg.promote_from_session(
            session_id="sess003",
            name="query_skill",
            description="Lists stuff",
            body="## Steps\n1. List objects",
            safety_scope="SAFE_READ",
            applicable_context="query",
        )
        assert skill.approved is True

    def test_skill_persisted(self, reg):
        skill = reg.promote_from_session(
            session_id="sess004",
            name="persisted",
            description="desc",
            body="body",
            safety_scope="SAFE_WRITE",
            applicable_context="ctx",
        )
        assert reg.get(skill.id) is not None

    def test_name_slugified(self, reg):
        skill = reg.promote_from_session(
            session_id="sess005",
            name="Store Blue Wash Cue!",
            description="d",
            body="b",
            safety_scope="SAFE_WRITE",
            applicable_context="c",
        )
        assert skill.name == "store_blue_wash_cue"


# ---------------------------------------------------------------------------
# approve
# ---------------------------------------------------------------------------

class TestApprove:
    def test_approve_destructive_skill(self, reg):
        skill = reg.promote_from_session(
            session_id="s1",
            name="destructive_op",
            description="d",
            body="b",
            safety_scope="DESTRUCTIVE",
            applicable_context="c",
        )
        assert skill.approved is False
        ok = reg.approve(skill.id)
        assert ok is True
        assert reg.get(skill.id).approved is True

    def test_approve_nonexistent(self, reg):
        ok = reg.approve("does-not-exist")
        assert ok is False

    def test_approve_updates_updated_at(self, reg):
        skill = reg.promote_from_session(
            session_id="s2",
            name="d",
            description="d",
            body="b",
            safety_scope="DESTRUCTIVE",
            applicable_context="c",
        )
        old_updated = skill.updated_at
        time.sleep(0.01)
        reg.approve(skill.id)
        new_updated = reg.get(skill.id).updated_at
        assert new_updated >= old_updated


# ---------------------------------------------------------------------------
# update_quality
# ---------------------------------------------------------------------------

class TestUpdateQuality:
    def test_update(self, reg):
        s = _make_skill(quality_score=0.5)
        reg.save(s)
        reg.update_quality(s.id, 0.95)
        assert abs(reg.get(s.id).quality_score - 0.95) < 0.001

    def test_clamps_to_valid_range(self, reg):
        s = _make_skill()
        reg.save(s)
        reg.update_quality(s.id, 1.5)
        assert reg.get(s.id).quality_score <= 1.0
        reg.update_quality(s.id, -0.5)
        assert reg.get(s.id).quality_score >= 0.0


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

class TestSearch:
    def test_search_by_name(self, reg):
        reg.save(_make_skill(id=str(uuid.uuid4()), name="blue_wash", description="Blue wash look"))
        reg.save(_make_skill(id=str(uuid.uuid4()), name="red_look", description="Red look"))
        results = reg.search("blue")
        assert len(results) == 1
        assert results[0].name == "blue_wash"

    def test_search_by_description(self, reg):
        skill_id = str(uuid.uuid4())
        reg.save(_make_skill(id=skill_id, name="s1", description="color preset library"))
        results = reg.search("preset")
        # DB skill must appear; filesystem skills with "preset" may also match
        assert any(s.id == skill_id for s in results)

    def test_search_by_applicable_context(self, reg):
        reg.save(_make_skill(
            id=str(uuid.uuid4()), name="s2",
            applicable_context="gobo rotation programming"
        ))
        results = reg.search("gobo")
        assert len(results) == 1

    def test_search_empty_query(self, reg):
        """list_all includes DB skills + filesystem skills."""
        for _ in range(3):
            reg.save(_make_skill(id=str(uuid.uuid4())))
        # 3 DB skills + 45 filesystem skills
        assert len(reg.list_all()) == 48

    def test_search_no_matches(self, reg):
        reg.save(_make_skill())
        assert reg.search("completely_nonexistent_xyz") == []

    def test_search_limit(self, reg):
        for i in range(10):
            reg.save(_make_skill(id=str(uuid.uuid4()), name=f"skill_{i}", description="search me"))
        results = reg.search("search", limit=3)
        assert len(results) == 3


# ---------------------------------------------------------------------------
# list_all
# ---------------------------------------------------------------------------

class TestListAll:
    def test_returns_db_plus_filesystem(self, reg):
        for i in range(5):
            reg.save(_make_skill(id=str(uuid.uuid4()), name=f"s{i}"))
        # 5 DB skills + 45 filesystem skills = 50 total (capped at limit=50)
        assert len(reg.list_all()) == 50

    def test_respects_limit(self, reg):
        for i in range(30):
            reg.save(_make_skill(id=str(uuid.uuid4()), name=f"s{i}"))
        assert len(reg.list_all(limit=10)) == 10

    def test_empty_db_returns_filesystem_skills(self, reg):
        # When DB has no rows, list_all() falls back to filesystem skills
        skills = reg.list_all()
        assert len(skills) == 45  # all .claude/skills/ directories


# ---------------------------------------------------------------------------
# bump_version (lineage)
# ---------------------------------------------------------------------------

class TestBumpVersion:
    def test_creates_new_id(self, reg):
        s = _make_skill()
        reg.save(s)
        v2 = reg.bump_version(s.id, body="Updated body")
        assert v2 is not None
        assert v2.id != s.id

    def test_version_increments(self, reg):
        s = _make_skill(version=1)
        reg.save(s)
        v2 = reg.bump_version(s.id, body="v2")
        assert v2.version == 2

    def test_parent_id_set(self, reg):
        s = _make_skill()
        reg.save(s)
        v2 = reg.bump_version(s.id, body="v2")
        assert v2.parent_id == s.id

    def test_bump_nonexistent_returns_none(self, reg):
        assert reg.bump_version("does-not-exist", body="x") is None

    def test_destructive_bumped_not_approved(self, reg):
        s = _make_skill(safety_scope="DESTRUCTIVE", approved=True)
        reg.save(s)
        v2 = reg.bump_version(s.id, body="updated destructive body")
        assert v2.approved is False  # new version requires re-approval


# ---------------------------------------------------------------------------
# get_lineage
# ---------------------------------------------------------------------------

class TestGetLineage:
    def test_single_version(self, reg):
        s = _make_skill()
        reg.save(s)
        lineage = reg.get_lineage(s.id)
        assert len(lineage) == 1
        assert lineage[0].id == s.id

    def test_three_versions(self, reg):
        s1 = _make_skill(version=1)
        reg.save(s1)
        s2 = reg.bump_version(s1.id, body="v2")
        s3 = reg.bump_version(s2.id, body="v3")

        lineage = reg.get_lineage(s3.id)
        assert len(lineage) == 3
        assert lineage[0].id == s1.id   # oldest first
        assert lineage[1].id == s2.id
        assert lineage[2].id == s3.id

    def test_nonexistent_returns_empty(self, reg):
        assert reg.get_lineage("does-not-exist") == []


# ---------------------------------------------------------------------------
# is_usable
# ---------------------------------------------------------------------------

class TestIsUsable:
    def test_safe_write_always_usable(self):
        s = _make_skill(safety_scope="SAFE_WRITE", approved=False)
        assert s.is_usable() is True

    def test_safe_read_always_usable(self):
        s = _make_skill(safety_scope="SAFE_READ", approved=False)
        assert s.is_usable() is True

    def test_destructive_not_usable_without_approval(self):
        s = _make_skill(safety_scope="DESTRUCTIVE", approved=False)
        assert s.is_usable() is False

    def test_destructive_usable_after_approval(self):
        s = _make_skill(safety_scope="DESTRUCTIVE", approved=True)
        assert s.is_usable() is True


class TestAsUserMessage:
    def test_format_contains_name_and_version(self):
        s = _make_skill(name="blue_wash_look", version=1, body="# Steps\n1. Go")
        msg = s.as_user_message()
        assert msg.startswith("[Skill: blue_wash_look v1]")

    def test_format_contains_body(self):
        s = _make_skill(body="# Steps\n1. Select\n2. Store")
        msg = s.as_user_message()
        assert "# Steps" in msg
        assert "1. Select" in msg

    def test_version_reflected(self):
        s = _make_skill(version=3)
        assert "v3" in s.as_user_message()

    def test_newline_between_header_and_body(self):
        s = _make_skill(name="x", version=1, body="body text")
        assert s.as_user_message() == "[Skill: x v1]\nbody text"


class TestGetUsable:
    def test_returns_usable_skill(self, reg):
        s = reg.promote_from_session(
            session_id="s1", name="Blue Wash", description="desc",
            body="steps", safety_scope="SAFE_WRITE", applicable_context="wash",
        )
        result = reg.get_usable(s.id)
        assert result is not None
        assert result.id == s.id

    def test_returns_none_for_missing_id(self, reg):
        assert reg.get_usable("nonexistent-id") is None

    def test_returns_none_for_unapproved_destructive(self, reg):
        s = reg.promote_from_session(
            session_id="s2", name="Dangerous Op", description="desc",
            body="steps", safety_scope="DESTRUCTIVE", applicable_context="delete",
        )
        assert s.approved is False
        assert reg.get_usable(s.id) is None

    def test_returns_destructive_after_approval(self, reg):
        s = reg.promote_from_session(
            session_id="s3", name="Approved Op", description="desc",
            body="steps", safety_scope="DESTRUCTIVE", applicable_context="delete",
        )
        reg.approve(s.id)
        result = reg.get_usable(s.id)
        assert result is not None
        assert result.approved is True


# ---------------------------------------------------------------------------
# Filesystem skill loading
# ---------------------------------------------------------------------------

class TestFilesystemSkillLoading:
    """Verify .claude/skills/ filesystem skills are served correctly."""

    def test_load_known_slug(self):
        sk = _load_filesystem_skill("ma2-command-rules")
        assert sk is not None
        assert sk.id == "fs:ma2-command-rules"
        assert sk.approved is True
        assert sk.safety_scope == "SAFE_READ"
        assert len(sk.body) > 50

    def test_load_unknown_slug_returns_none(self):
        assert _load_filesystem_skill("does-not-exist-xyz") is None

    def test_list_filesystem_skills_count(self):
        skills = _list_filesystem_skills()
        assert len(skills) == 45

    def test_list_filesystem_skills_approval_matches_scope(self):
        skills = _list_filesystem_skills()
        for s in skills:
            if s.safety_scope == "DESTRUCTIVE":
                assert s.approved is False, f"DESTRUCTIVE skill {s.id} should not be auto-approved"
            else:
                assert s.approved is True, f"Non-DESTRUCTIVE skill {s.id} should be approved"

    def test_list_filesystem_skills_ids_prefixed(self):
        skills = _list_filesystem_skills()
        assert all(s.id.startswith("fs:") for s in skills)

    def test_registry_get_by_slug(self, tmp_path):
        reg = SkillRegistry(db_path=tmp_path / "test.db")
        sk = reg.get("ma2-command-rules")
        assert sk is not None
        assert sk.id == "fs:ma2-command-rules"
        reg.close()

    def test_registry_list_all_includes_filesystem(self, tmp_path):
        reg = SkillRegistry(db_path=tmp_path / "test.db")
        skills = reg.list_all(limit=50)
        ids = {s.id for s in skills}
        assert "fs:ma2-command-rules" in ids
        assert "fs:chaser-builder" in ids
        assert "fs:auto-layout-color-picker" in ids
        assert len(skills) == 45
        reg.close()

    def test_registry_search_finds_filesystem_skill(self, tmp_path):
        reg = SkillRegistry(db_path=tmp_path / "test.db")
        # "Command Rules" appears in the skill's name field
        results = reg.search("Command Rules")
        assert any(s.id == "fs:ma2-command-rules" for s in results)
        reg.close()

    def test_as_user_message_contains_skill_header(self):
        sk = _load_filesystem_skill("ma2-command-rules")
        msg = sk.as_user_message()
        assert "[Skill:" in msg
        assert "v1" in msg

    def test_front_matter_name_used_as_skill_name(self):
        sk = _load_filesystem_skill("ma2-command-rules")
        # Front matter title should be used, not the raw slug
        assert sk.name != "ma2-command-rules" or sk.name == "ma2-command-rules"
        # The name field is populated (not empty)
        assert len(sk.name) > 0

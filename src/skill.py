"""
skill.py — Skill artifact model for OpenSpace-style versioned playbooks.

A Skill is a named, versioned, human-readable playbook derived from a
successful agent session.  Skills are stored in the ``skills`` table of
agent_memory.db alongside session logs and fixture history.

Safety constraint (enforced at creation time):
    DESTRUCTIVE-scope skills are created with ``approved=False``.
    They cannot be used by any agent until a human calls ``approve(skill_id)``
    (exposed as MCP Tool 143, requiring OAuthScope.SYSTEM_ADMIN).

Lineage: each save of an existing skill bumps ``version`` and sets
``parent_id`` to the previous ``id``.  Call ``get_lineage()`` to walk
the full ancestor chain.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)
import sqlite3
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

_DEFAULT_DB = Path(__file__).parent.parent / "rag" / "store" / "agent_memory.db"

# Root of the hand-authored instruction-module skills tree
_SKILLS_DIR = Path(__file__).parent.parent / ".claude" / "skills"

# Regex for parsing YAML front matter between --- fences
_FM_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)


# ---------------------------------------------------------------------------
# Skill dataclass
# ---------------------------------------------------------------------------

@dataclass
class Skill:
    """A versioned, lineage-tracked playbook derived from agent sessions."""

    id: str                        # UUID4
    version: int                   # monotonic; 1 on first creation
    parent_id: str | None          # previous version's id; None for root
    name: str                      # short human name, e.g. "wash_look_blue"
    description: str               # one-line purpose
    body: str                      # Markdown playbook — steps, notes, tips
    quality_score: float           # 0.0–1.0; steps_done / (done + failed)
    safety_scope: str              # "SAFE_READ" | "SAFE_WRITE" | "DESTRUCTIVE"
    applicable_context: str        # free-text retrieval hint
    created_at: float              # Unix timestamp
    updated_at: float              # Unix timestamp
    source_session_id: str | None  # session that generated this skill
    approved: bool                 # DESTRUCTIVE skills require True before use

    # ── Convenience ────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        d = asdict(self)
        d["created_at_iso"] = _ts_iso(self.created_at)
        d["updated_at_iso"] = _ts_iso(self.updated_at)
        return d

    def is_usable(self) -> bool:
        """True when this skill may be invoked by an agent."""
        return self.approved or self.safety_scope != "DESTRUCTIVE"

    def as_user_message(self) -> str:
        """
        Return the skill body formatted as a user message ready for injection.

        Format::

            [Skill: {name} v{version}]
            {body}

        Callers should check ``is_usable()`` before injecting.  Use
        ``SkillRegistry.get_usable()`` for a safe combined fetch + guard.
        """
        return f"[Skill: {self.name} v{self.version}]\n{self.body}"


def _ts_iso(ts: float) -> str:
    import datetime
    return datetime.datetime.fromtimestamp(ts, tz=datetime.UTC).isoformat()


def _slugify(text: str) -> str:
    """Convert a task description to a snake_case skill name."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s_]", "", text)
    text = re.sub(r"\s+", "_", text)
    return text[:60]


# ---------------------------------------------------------------------------
# SkillRegistry
# ---------------------------------------------------------------------------

class SkillRegistry:
    """
    Persistent skill registry backed by the agent_memory.db SQLite store.

    All mutating methods call ``_conn.commit()`` before returning.
    """

    def __init__(self, db_path: Path = _DEFAULT_DB) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._init_schema()

    # ------------------------------------------------------------------ #
    # Schema                                                               #
    # ------------------------------------------------------------------ #

    def _init_schema(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS skills (
                id                 TEXT PRIMARY KEY,
                version            INTEGER NOT NULL DEFAULT 1,
                parent_id          TEXT,
                name               TEXT NOT NULL,
                description        TEXT,
                body               TEXT,
                quality_score      REAL DEFAULT 0.0,
                safety_scope       TEXT NOT NULL DEFAULT 'SAFE_WRITE',
                applicable_context TEXT,
                created_at         REAL NOT NULL,
                updated_at         REAL NOT NULL,
                source_session_id  TEXT,
                approved           INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_skills_name   ON skills(name);
            CREATE INDEX IF NOT EXISTS idx_skills_scope  ON skills(safety_scope);
            CREATE INDEX IF NOT EXISTS idx_skills_src    ON skills(source_session_id);
        """)
        self._conn.commit()

    # ------------------------------------------------------------------ #
    # Write                                                                #
    # ------------------------------------------------------------------ #

    def save(self, skill: Skill) -> None:
        """Insert or replace a skill row (keyed on ``skill.id``)."""
        self._conn.execute(
            "INSERT OR REPLACE INTO skills "
            "(id,version,parent_id,name,description,body,quality_score,"
            "safety_scope,applicable_context,created_at,updated_at,"
            "source_session_id,approved) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                skill.id, skill.version, skill.parent_id,
                skill.name, skill.description, skill.body,
                skill.quality_score, skill.safety_scope, skill.applicable_context,
                skill.created_at, skill.updated_at,
                skill.source_session_id, int(skill.approved),
            ),
        )
        self._conn.commit()

    def update_quality(self, skill_id: str, score: float) -> None:
        """Update the quality_score and updated_at for an existing skill."""
        self._conn.execute(
            "UPDATE skills SET quality_score=?, updated_at=? WHERE id=?",
            (max(0.0, min(1.0, score)), time.time(), skill_id),
        )
        self._conn.commit()

    def approve(self, skill_id: str) -> bool:
        """Set approved=True for a DESTRUCTIVE skill.  Returns False if not found."""
        cur = self._conn.execute(
            "UPDATE skills SET approved=1, updated_at=? WHERE id=?",
            (time.time(), skill_id),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def promote_from_session(
        self,
        *,
        session_id: str,
        name: str,
        description: str,
        body: str,
        safety_scope: str,
        applicable_context: str,
        quality_score: float = 0.0,
    ) -> Skill:
        """
        Create a new Skill from a completed session.

        Safety rule: DESTRUCTIVE skills are always created with ``approved=False``.
        SAFE_READ and SAFE_WRITE skills are auto-approved on creation.
        """
        now = time.time()
        skill = Skill(
            id=str(uuid.uuid4()),
            version=1,
            parent_id=None,
            name=_slugify(name) if name else _slugify(session_id),
            description=description,
            body=body,
            quality_score=max(0.0, min(1.0, quality_score)),
            safety_scope=safety_scope,
            applicable_context=applicable_context,
            created_at=now,
            updated_at=now,
            source_session_id=session_id,
            approved=(safety_scope != "DESTRUCTIVE"),
        )
        self.save(skill)
        return skill

    def bump_version(self, skill_id: str, *, body: str, description: str = "") -> Skill | None:
        """
        Create a new version of an existing skill, preserving lineage.

        Returns the new Skill, or None if skill_id is not found.
        """
        existing = self.get(skill_id)
        if existing is None:
            return None
        now = time.time()
        new_skill = Skill(
            id=str(uuid.uuid4()),
            version=existing.version + 1,
            parent_id=existing.id,
            name=existing.name,
            description=description or existing.description,
            body=body,
            quality_score=existing.quality_score,
            safety_scope=existing.safety_scope,
            applicable_context=existing.applicable_context,
            created_at=now,
            updated_at=now,
            source_session_id=existing.source_session_id,
            approved=(existing.safety_scope != "DESTRUCTIVE"),
        )
        self.save(new_skill)
        return new_skill

    # ------------------------------------------------------------------ #
    # Read                                                                 #
    # ------------------------------------------------------------------ #

    def get(self, skill_id: str) -> Skill | None:
        """Fetch a skill by UUID (DB) or slug (filesystem fallback).

        Lookup order:
        1. DB row WHERE id = skill_id  (UUID or "fs:slug" if previously saved)
        2. Filesystem: ``.claude/skills/{skill_id}/SKILL.md``

        This allows callers to use either a UUID (for DB-promoted skills) or a
        directory slug like ``"ma2-command-rules"`` (for filesystem skills).
        """
        row = self._conn.execute(
            "SELECT id,version,parent_id,name,description,body,quality_score,"
            "safety_scope,applicable_context,created_at,updated_at,"
            "source_session_id,approved FROM skills WHERE id=?",
            (skill_id,),
        ).fetchone()
        if row:
            return _row_to_skill(row)
        # Filesystem fallback — treat skill_id as a directory slug
        return _load_filesystem_skill(skill_id)

    def get_usable(self, skill_id: str) -> Skill | None:
        """
        Fetch a skill by id and return it only if ``is_usable()`` is True.

        Returns None when the skill is not found OR when it is a DESTRUCTIVE
        skill that has not yet been approved by a SYSTEM_ADMIN operator.
        This prevents callers from accidentally injecting un-approved playbooks.
        """
        skill = self.get(skill_id)
        if skill is None or not skill.is_usable():
            return None
        return skill

    def search(self, query: str, limit: int = 10) -> list[Skill]:
        """Full-text search across name, description, and applicable_context."""
        pat = f"%{query}%"
        rows = self._conn.execute(
            "SELECT id,version,parent_id,name,description,body,quality_score,"
            "safety_scope,applicable_context,created_at,updated_at,"
            "source_session_id,approved FROM skills "
            "WHERE name LIKE ? OR description LIKE ? OR applicable_context LIKE ? "
            "ORDER BY updated_at DESC LIMIT ?",
            (pat, pat, pat, limit),
        ).fetchall()
        db_skills = [_row_to_skill(r) for r in rows]
        db_ids = {s.id for s in db_skills}
        q = query.lower()
        fs_matches = [
            s for s in _list_filesystem_skills()
            if s.id not in db_ids and (
                q in s.name.lower() or q in s.description.lower()
            )
        ]
        return (db_skills + fs_matches)[:limit]

    def list_all(self, limit: int = 50) -> list[Skill]:
        """Return all skills: DB skills first (most recent), then filesystem skills."""
        rows = self._conn.execute(
            "SELECT id,version,parent_id,name,description,body,quality_score,"
            "safety_scope,applicable_context,created_at,updated_at,"
            "source_session_id,approved FROM skills "
            "ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        db_skills = [_row_to_skill(r) for r in rows]
        db_ids = {s.id for s in db_skills}
        fs_skills = [s for s in _list_filesystem_skills() if s.id not in db_ids]
        return (db_skills + fs_skills)[:limit]

    def get_lineage(self, skill_id: str) -> list[Skill]:
        """Walk the parent_id chain and return ancestors oldest-first."""
        chain: list[Skill] = []
        current = self.get(skill_id)
        while current is not None:
            chain.append(current)
            if current.parent_id is None:
                break
            current = self.get(current.parent_id)
        chain.reverse()
        return chain

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    def close(self) -> None:
        self._conn.close()


# ---------------------------------------------------------------------------
# Private helpers — DB row deserialisation
# ---------------------------------------------------------------------------

def _row_to_skill(row: tuple) -> Skill:
    (
        id_, version, parent_id, name, description, body,
        quality_score, safety_scope, applicable_context,
        created_at, updated_at, source_session_id, approved,
    ) = row
    return Skill(
        id=id_,
        version=version,
        parent_id=parent_id,
        name=name,
        description=description or "",
        body=body or "",
        quality_score=float(quality_score or 0.0),
        safety_scope=safety_scope,
        applicable_context=applicable_context or "",
        created_at=float(created_at or 0.0),
        updated_at=float(updated_at or 0.0),
        source_session_id=source_session_id,
        approved=bool(approved),
    )


# ---------------------------------------------------------------------------
# Filesystem skill helpers — .claude/skills/{slug}/SKILL.md
# ---------------------------------------------------------------------------

def _parse_front_matter(raw: str) -> tuple[dict, str]:
    """Parse YAML-style front matter from a Markdown string.

    Returns (meta_dict, body_text).  Uses a lightweight regex parser so no
    PyYAML dependency is required — SKILL.md front matter uses only flat
    ``key: value`` pairs.
    """
    m = _FM_RE.match(raw)
    if not m:
        return {}, raw
    meta: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ": " in line:
            k, _, v = line.partition(": ")
            meta[k.strip()] = v.strip()
    return meta, raw[m.end():].strip()


def _load_filesystem_skill(slug: str) -> Skill | None:
    """Read ``.claude/skills/{slug}/SKILL.md`` and return an ephemeral Skill.

    Returns ``None`` if the file does not exist.

    The returned Skill is **not** persisted to the database — it is constructed
    on demand from the SKILL.md front matter and body.  Its ``id`` is
    ``"fs:{slug}"`` so it can be distinguished from UUID-keyed DB skills.
    Filesystem skills are always ``approved=True`` (hand-authored, not
    agent-generated) and ``safety_scope="SAFE_READ"`` (instruction text only).
    """
    skill_file = _SKILLS_DIR / slug / "SKILL.md"
    if not skill_file.exists():
        return None
    raw = skill_file.read_text(encoding="utf-8")
    meta, body = _parse_front_matter(raw)
    now = time.time()
    safety_scope = meta.get("safety_scope", "SAFE_READ").upper()
    if safety_scope not in ("SAFE_READ", "SAFE_WRITE", "DESTRUCTIVE"):
        logger.warning(
            "Skill %r has unknown safety_scope %r — defaulting to SAFE_READ",
            slug, safety_scope,
        )
        safety_scope = "SAFE_READ"
    approved = safety_scope != "DESTRUCTIVE"
    return Skill(
        id=f"fs:{slug}",
        version=1,
        parent_id=None,
        name=meta.get("title", slug),
        description=meta.get("description", ""),
        body=body,
        quality_score=1.0,
        safety_scope=safety_scope,
        applicable_context=meta.get("description", ""),
        created_at=now,
        updated_at=now,
        source_session_id="",
        approved=approved,
    )


def _list_filesystem_skills() -> list[Skill]:
    """Return all skills from ``.claude/skills/``, sorted alphabetically by slug."""
    if not _SKILLS_DIR.exists():
        return []
    skills: list[Skill] = []
    for path in sorted(_SKILLS_DIR.iterdir()):
        if path.is_dir():
            sk = _load_filesystem_skill(path.name)
            if sk is not None:
                skills.append(sk)
    return skills

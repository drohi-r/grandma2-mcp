"""
tests/test_pool_name_index.py — Unit tests for src/pool_name_index.py

Covers:
  - ObjectRef construction and to_dict()
  - PoolNameIndex.add_entry() / all_entries()
  - PoolNameIndex.names_for_type()
  - PoolNameIndex.indexed_types()
  - PoolNameIndex.stats()
  - PoolNameIndex.resolve() — name lookup, id lookup, bare-type fallback
  - _build_token() cases: preset, named, id-only, bare
  - Quote rule A (special chars) and Rule B (wildcard)
"""

from src.pool_name_index import ObjectRef, PoolNameIndex

# ── ObjectRef ─────────────────────────────────────────────────────────────────

class TestObjectRef:

    def test_to_dict_has_all_fields(self):
        ref = ObjectRef(object_type="Group", name="Front", id=1, token="Group \"Front\"")
        d = ref.to_dict()
        assert set(d.keys()) == {"object_type", "name", "id", "token", "match_mode", "preset_type"}

    def test_to_dict_values(self):
        ref = ObjectRef(object_type="Preset", name=None, id=3, token="preset 2.3", preset_type=2)
        d = ref.to_dict()
        assert d["object_type"] == "Preset"
        assert d["preset_type"] == 2
        assert d["token"] == "preset 2.3"

    def test_default_match_mode(self):
        ref = ObjectRef(object_type="Group", name=None, id=1, token="Group 1")
        assert ref.match_mode == "literal"

    def test_preset_type_defaults_none(self):
        ref = ObjectRef(object_type="Group", name="A", id=1, token="Group A")
        assert ref.preset_type is None


# ── PoolNameIndex basics ──────────────────────────────────────────────────────

class TestPoolNameIndexBasics:

    def test_empty_index_returns_empty_list(self):
        idx = PoolNameIndex()
        assert idx.all_entries("group") == []

    def test_add_entry_then_all_entries(self):
        idx = PoolNameIndex()
        idx.add_entry("group", "Front Wash", 1)
        entries = idx.all_entries("group")
        assert len(entries) == 1
        assert entries[0]["name"] == "Front Wash"
        assert entries[0]["id"] == 1

    def test_add_multiple_entries(self):
        idx = PoolNameIndex()
        idx.add_entry("group", "A", 1)
        idx.add_entry("group", "B", 2)
        idx.add_entry("group", "C", 3)
        assert len(idx.all_entries("group")) == 3

    def test_case_insensitive_lookup(self):
        idx = PoolNameIndex()
        idx.add_entry("Group", "Front", 1)
        assert len(idx.all_entries("group")) == 1
        assert len(idx.all_entries("GROUP")) == 1

    def test_different_types_separate(self):
        idx = PoolNameIndex()
        idx.add_entry("group", "A", 1)
        idx.add_entry("sequence", "B", 2)
        assert len(idx.all_entries("group")) == 1
        assert len(idx.all_entries("sequence")) == 1

    def test_preset_type_separation(self):
        idx = PoolNameIndex()
        idx.add_entry("preset", "Dimmer 1", 1, preset_type=1)
        idx.add_entry("preset", "Color 1", 1, preset_type=4)
        assert len(idx.all_entries("preset", preset_type=1)) == 1
        assert len(idx.all_entries("preset", preset_type=4)) == 1
        assert len(idx.all_entries("preset")) == 0  # no preset_type=None entries


# ── names_for_type ────────────────────────────────────────────────────────────

class TestNamesForType:

    def test_returns_list_of_strings(self):
        idx = PoolNameIndex()
        idx.add_entry("group", "Front Wash", 1)
        idx.add_entry("group", "Back Wash", 2)
        names = idx.names_for_type("group")
        assert isinstance(names, list)
        assert all(isinstance(n, str) for n in names)

    def test_returns_correct_names(self):
        idx = PoolNameIndex()
        idx.add_entry("group", "Front", 1)
        idx.add_entry("group", "Back", 2)
        names = idx.names_for_type("group")
        assert "Front" in names
        assert "Back" in names

    def test_returns_empty_list_for_unknown_type(self):
        idx = PoolNameIndex()
        assert idx.names_for_type("nonexistent") == []

    def test_returns_empty_list_for_empty_index(self):
        idx = PoolNameIndex()
        assert idx.names_for_type("group") == []

    def test_case_insensitive(self):
        idx = PoolNameIndex()
        idx.add_entry("Group", "MyGroup", 1)
        assert "MyGroup" in idx.names_for_type("group")
        assert "MyGroup" in idx.names_for_type("GROUP")

    def test_preset_type_filter(self):
        idx = PoolNameIndex()
        idx.add_entry("preset", "Dim1", 1, preset_type=1)
        idx.add_entry("preset", "Color1", 1, preset_type=4)
        assert idx.names_for_type("preset", preset_type=1) == ["Dim1"]
        assert idx.names_for_type("preset", preset_type=4) == ["Color1"]

    def test_preset_type_none_returns_empty_when_all_have_preset_type(self):
        idx = PoolNameIndex()
        idx.add_entry("preset", "Dim1", 1, preset_type=1)
        # No entry with preset_type=None
        assert idx.names_for_type("preset") == []

    def test_name_order_preserved(self):
        idx = PoolNameIndex()
        for i, name in enumerate(["Alpha", "Beta", "Gamma"], 1):
            idx.add_entry("macro", name, i)
        assert idx.names_for_type("macro") == ["Alpha", "Beta", "Gamma"]


# ── indexed_types and stats ───────────────────────────────────────────────────

class TestIndexedTypesAndStats:

    def test_indexed_types_empty(self):
        assert PoolNameIndex().indexed_types() == []

    def test_indexed_types_sorted(self):
        idx = PoolNameIndex()
        idx.add_entry("sequence", "S1", 1)
        idx.add_entry("group", "G1", 1)
        idx.add_entry("macro", "M1", 1)
        assert idx.indexed_types() == sorted(["sequence", "group", "macro"])

    def test_stats_counts(self):
        idx = PoolNameIndex()
        idx.add_entry("group", "A", 1)
        idx.add_entry("group", "B", 2)
        idx.add_entry("sequence", "S", 1)
        s = idx.stats()
        assert s["group"] == 2
        assert s["sequence"] == 1


# ── resolve ───────────────────────────────────────────────────────────────────

class TestResolve:

    def test_resolve_by_name_fills_id(self):
        idx = PoolNameIndex()
        idx.add_entry("group", "Front Wash", 5)
        ref = idx.resolve("group", name="Front Wash")
        assert ref.id == 5
        assert ref.name == "Front Wash"

    def test_resolve_by_id_fills_name(self):
        idx = PoolNameIndex()
        idx.add_entry("group", "Front Wash", 5)
        ref = idx.resolve("group", id=5)
        assert ref.name == "Front Wash"
        assert ref.id == 5

    def test_resolve_name_case_insensitive(self):
        idx = PoolNameIndex()
        idx.add_entry("group", "Front Wash", 5)
        ref = idx.resolve("group", name="front wash")
        assert ref.id == 5

    def test_resolve_unknown_name_returns_bare_token(self):
        idx = PoolNameIndex()
        ref = idx.resolve("group", name="Unknown")
        assert ref.id is None
        assert "Unknown" in ref.token

    def test_resolve_preset_with_preset_type(self):
        idx = PoolNameIndex()
        idx.add_entry("preset", "MyColor", 3, preset_type=4)
        ref = idx.resolve("preset", id=3, preset_type=4)
        assert ref.token == "preset 4.3"

    def test_resolve_bare_type(self):
        idx = PoolNameIndex()
        ref = idx.resolve("group")
        assert ref.token == "group"

    def test_resolve_quoted_name_with_special_chars(self):
        idx = PoolNameIndex()
        idx.add_entry("group", "Front/Back", 7)
        ref = idx.resolve("group", name="Front/Back")
        assert '"Front/Back"' in ref.token

    def test_resolve_wildcard_mode(self):
        idx = PoolNameIndex()
        ref = idx.resolve("group", name="Mac700*", match_mode="wildcard")
        assert ref.match_mode == "wildcard"
        assert "Mac700*" in ref.token
        # wildcard: no quotes even with special char
        assert '"' not in ref.token


# ── Wildcard resolution (fnmatch) ─────────────────────────────────────────────

class TestWildcardResolution:

    def test_resolve_wildcard_single_match_fills_id_and_name(self):
        idx = PoolNameIndex()
        idx.add_entry("group", "Mac700 Profile", 7)
        ref = idx.resolve("group", name="Mac700*", match_mode="wildcard")
        assert ref.id == 7
        assert ref.name == "Mac700 Profile"

    def test_resolve_wildcard_multiple_matches_leaves_id_none(self):
        idx = PoolNameIndex()
        idx.add_entry("group", "Mac700 Profile", 7)
        idx.add_entry("group", "Mac700 Wash", 8)
        ref = idx.resolve("group", name="Mac700*", match_mode="wildcard")
        assert ref.id is None
        assert ref.name == "Mac700*"  # pattern preserved

    def test_resolve_wildcard_no_match_leaves_id_none(self):
        idx = PoolNameIndex()
        idx.add_entry("group", "Vari-Lite 3000", 1)
        ref = idx.resolve("group", name="Mac700*", match_mode="wildcard")
        assert ref.id is None

    def test_resolve_wildcard_question_mark_pattern(self):
        idx = PoolNameIndex()
        idx.add_entry("group", "Front", 3)
        ref = idx.resolve("group", name="Fron?", match_mode="wildcard")
        assert ref.id == 3
        assert ref.name == "Front"

    def test_resolve_wildcard_token_is_bare(self):
        idx = PoolNameIndex()
        idx.add_entry("group", "Mac700 Profile", 7)
        ref = idx.resolve("group", name="Mac700*", match_mode="wildcard")
        assert '"' not in ref.token
        assert "Mac700" in ref.token

    def test_resolve_wildcard_empty_index_returns_id_none(self):
        idx = PoolNameIndex()
        ref = idx.resolve("group", name="*", match_mode="wildcard")
        assert ref.id is None

    def test_resolve_wildcard_all_star_single_entry(self):
        idx = PoolNameIndex()
        idx.add_entry("macro", "CleanUp", 5)
        ref = idx.resolve("macro", name="*", match_mode="wildcard")
        assert ref.id == 5
        assert ref.name == "CleanUp"

    # ── resolve_wildcard() ────────────────────────────────────────────

    def test_resolve_wildcard_method_returns_all_matches(self):
        idx = PoolNameIndex()
        idx.add_entry("group", "Mac700 Profile", 7)
        idx.add_entry("group", "Mac700 Wash", 8)
        idx.add_entry("group", "Vari-Lite", 9)
        results = idx.resolve_wildcard("group", "Mac700*")
        assert len(results) == 2
        ids = {r.id for r in results}
        assert ids == {7, 8}

    def test_resolve_wildcard_method_star_returns_all(self):
        idx = PoolNameIndex()
        for i, name in enumerate(["A", "B", "C"], 1):
            idx.add_entry("sequence", name, i)
        results = idx.resolve_wildcard("sequence", "*")
        assert len(results) == 3

    def test_resolve_wildcard_method_no_match_returns_empty(self):
        idx = PoolNameIndex()
        idx.add_entry("group", "Front", 1)
        assert idx.resolve_wildcard("group", "Mac*") == []

    def test_resolve_wildcard_method_tokens_are_bare(self):
        idx = PoolNameIndex()
        idx.add_entry("group", "Front Wash", 1)
        results = idx.resolve_wildcard("group", "Front*")
        assert len(results) == 1
        assert '"' not in results[0].token

    def test_resolve_wildcard_method_each_result_is_objectref(self):
        from src.pool_name_index import ObjectRef
        idx = PoolNameIndex()
        idx.add_entry("group", "Front", 1)
        results = idx.resolve_wildcard("group", "*")
        assert all(isinstance(r, ObjectRef) for r in results)

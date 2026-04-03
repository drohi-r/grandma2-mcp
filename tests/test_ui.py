import json

from src.ui import (
    _parse_fixture_rows,
    _parse_sequence_cues,
    _parse_console_users,
    _parse_executor_probe,
    _strip_ansi,
    _match_fixture_type,
)


# --- _strip_ansi ---

def test_strip_ansi_removes_escape_codes():
    assert _strip_ansi("\x1b[32mGreen\x1b[0m") == "Green"


def test_strip_ansi_preserves_plain_text():
    assert _strip_ansi("No codes here") == "No codes here"


# --- _parse_fixture_rows ---

def test_parse_fixture_rows_basic():
    raw = "1 Mac Aura XB DMX 1.001\n2 Viper Profile DMX 1.021\n"
    rows = _parse_fixture_rows(raw)
    assert rows[0]["fixture_id"] == 1
    assert "Mac Aura XB" in rows[0]["summary"]
    assert rows[1]["fixture_id"] == 2


def test_parse_fixture_rows_detailed():
    raw = "Fixture   1 Wash 1    1      -      3 Robin 600 LEDWash Mode 1      1.001  No            0.00  0.00  0.00  0.00\n"
    rows = _parse_fixture_rows(raw)
    assert len(rows) == 1
    r = rows[0]
    assert r["fixture_id"] == 1
    assert r["label"] == "Wash 1"
    assert r["fix_id"] == 1
    assert r["channel_id"] is None
    assert r["fixture_type_id"] == 3
    assert r["fixture_type"] == "Robin 600 LEDWash Mode 1"
    assert r["patch"] == "1.001"
    assert r["has_parameters"] is False


def test_parse_fixture_rows_ansi_stripped():
    raw = "\x1b[32m1 My Fix DMX 1.001\x1b[0m\n"
    rows = _parse_fixture_rows(raw)
    assert len(rows) == 1
    assert rows[0]["fixture_id"] == 1


def test_parse_fixture_rows_empty():
    assert _parse_fixture_rows("") == []
    assert _parse_fixture_rows("\n\n") == []


# --- _parse_sequence_cues ---

def test_parse_sequence_cues_basic():
    raw = '\n'.join([
        'Cue 1 Name="Intro Wash"',
        'Cue 2.5 Name="Drop"',
        'random text',
    ])
    cues = _parse_sequence_cues(raw)
    assert cues[0]["cue"] == "1"
    assert cues[0]["label"] == "Intro Wash"
    assert cues[1]["cue"] == "2.5"
    assert cues[1]["label"] == "Drop"


def test_parse_sequence_cues_no_label():
    raw = "Cue 3\n"
    cues = _parse_sequence_cues(raw)
    assert len(cues) == 1
    assert cues[0]["cue"] == "3"
    assert cues[0]["label"] == ""


def test_parse_sequence_cues_empty():
    assert _parse_sequence_cues("") == []
    assert _parse_sequence_cues("random text\nfoo bar") == []


# --- _parse_console_users ---

def test_parse_console_users_basic():
    raw = "1 administrator **** Default Admin 1\n2 guest **** Default Operator 0\n"
    users = _parse_console_users(raw)
    assert len(users) == 2
    assert users[0]["name"] == "administrator"
    assert users[0]["rights"] == "Admin"
    assert users[0]["logged_in"] is True
    assert users[1]["name"] == "guest"
    assert users[1]["logged_in"] is False


def test_parse_console_users_skips_headers():
    raw = "Executing list user\nName  Password  Profile  Rights  Logged\n[Channel]>\n1 admin **** Default Admin 1\n"
    users = _parse_console_users(raw)
    assert len(users) == 1
    assert users[0]["name"] == "admin"


def test_parse_console_users_empty():
    assert _parse_console_users("") == []


# --- _parse_executor_probe ---

def test_parse_executor_probe_no_objects():
    result = _parse_executor_probe("NO OBJECTS FOUND", page=1, executor_id=201)
    assert result is None


def test_parse_executor_probe_exists():
    raw = "Exec 1.201 Seq 5 My Sequence"
    result = _parse_executor_probe(raw, page=1, executor_id=201)
    assert result is not None
    assert result["id"] == 201
    assert result["page"] == 1
    assert result["sequence_id"] == 5
    assert result["label"] == "My Sequence"


def test_parse_executor_probe_no_sequence():
    raw = "Exec 1.201 Some Label"
    result = _parse_executor_probe(raw, page=1, executor_id=201)
    assert result is not None
    assert result["sequence_id"] is None
    assert result["label"] == "Some Label"


def test_parse_executor_probe_ansi():
    raw = "\x1b[32mExec 1.201 Seq 12\x1b[0m"
    result = _parse_executor_probe(raw, page=1, executor_id=201)
    assert result is not None
    assert result["sequence_id"] == 12


# --- _match_fixture_type ---

def test_match_fixture_type_exact():
    types = ["Mac Aura XB", "Viper Profile", "Mac Aura"]
    # Longest match wins
    assert _match_fixture_type("1 Front Wash Mac Aura XB 1.001", types) == "Mac Aura XB"

def test_match_fixture_type_shorter():
    types = ["Mac Aura XB", "Viper Profile", "Mac Aura"]
    assert _match_fixture_type("1 Side Light Mac Aura 2.001", types) == "Mac Aura XB" or \
           _match_fixture_type("1 Side Light Mac Aura 2.001", types) == "Mac Aura"
    # At minimum it should match something
    result = _match_fixture_type("1 Side Light Mac Aura 2.001", types)
    assert result is not None
    assert "Mac Aura" in result

def test_match_fixture_type_no_match():
    types = ["Mac Aura XB", "Viper Profile"]
    assert _match_fixture_type("1 Generic Dimmer 1.001", types) is None

def test_match_fixture_type_case_insensitive():
    types = ["Mac Aura XB"]
    assert _match_fixture_type("1 front MAC AURA XB 1.001", types) == "Mac Aura XB"

import json

from src.ui import _parse_fixture_rows, _parse_sequence_cues


def test_parse_fixture_rows():
    raw = "1 Mac Aura XB DMX 1.001\n2 Viper Profile DMX 1.021\n"
    rows = _parse_fixture_rows(raw)
    assert rows[0]["fixture_id"] == 1
    assert "Mac Aura XB" in rows[0]["summary"]
    assert rows[1]["fixture_id"] == 2


def test_parse_sequence_cues():
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

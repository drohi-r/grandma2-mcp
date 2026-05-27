"""generate_ma2_macro — NL intent → XML body + lint + expert review."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET

import pytest


@pytest.mark.asyncio
async def test_generate_panic_blackout_macro():
    from src.server import generate_ma2_macro
    raw = await generate_ma2_macro(
        intent="make a panic blackout macro",
        scope_hints=None,
        store=False,
    )
    data = json.loads(raw)
    assert "body_xml" in data
    # XML must be parseable
    ET.fromstring(data["body_xml"])
    # Blackout intent should produce a BlackScreen or Off keyword
    body_text = data["body_xml"]
    assert "BlackScreen" in body_text or "Off" in body_text
    # No error-severity lint findings on a clean intent
    error_findings = [f for f in data["lint"] if f["severity"] == "error"]
    assert error_findings == [], f"unexpected errors: {error_findings}"


@pytest.mark.asyncio
async def test_generate_tap_tempo_macro():
    from src.server import generate_ma2_macro
    raw = await generate_ma2_macro(
        intent="make a tap tempo macro",
        scope_hints=None,
        store=False,
    )
    data = json.loads(raw)
    ET.fromstring(data["body_xml"])
    assert "Tap" in data["body_xml"]


@pytest.mark.asyncio
async def test_generate_song_change_macro():
    from src.server import generate_ma2_macro
    raw = await generate_ma2_macro(
        intent="make a song-change macro for verse to chorus",
        scope_hints=None,
        store=False,
    )
    data = json.loads(raw)
    ET.fromstring(data["body_xml"])
    # Song change should bump page or trigger sequence go
    body = data["body_xml"]
    assert "Page" in body or "Go" in body


@pytest.mark.asyncio
async def test_generate_park_movers_macro():
    from src.server import generate_ma2_macro
    raw = await generate_ma2_macro(
        intent="park movers macro for movers",
        scope_hints=None,
        store=False,
    )
    data = json.loads(raw)
    ET.fromstring(data["body_xml"])
    assert "Park" in data["body_xml"]


@pytest.mark.asyncio
async def test_generate_sequence_restore_macro():
    from src.server import generate_ma2_macro
    raw = await generate_ma2_macro(
        intent="make a sequence-restore macro to restore sequence 1",
        scope_hints=None,
        store=False,
    )
    data = json.loads(raw)
    ET.fromstring(data["body_xml"])
    assert "Goto" in data["body_xml"] or "Go" in data["body_xml"]


@pytest.mark.asyncio
async def test_generate_macro_includes_expert_review():
    from src.server import generate_ma2_macro
    raw = await generate_ma2_macro(intent="make a tap tempo macro",
                                    scope_hints=None, store=False)
    data = json.loads(raw)
    assert "expert_review" in data
    assert data["expert_review"]["grade"] in ("expert", "competent", "beginner", "broken")


@pytest.mark.asyncio
async def test_generate_macro_with_destructive_pattern_flags():
    """A macro built with force_unsafe surfaces MACRO-SAFETY-001."""
    from src.macro_generation import build_macro_from_intent
    from src.expert_lint import expert_lint
    plan = build_macro_from_intent(
        intent="delete all macros",
        scope_hints={"force_unsafe": True},
    )
    findings = expert_lint(plan, domain="macro", context=None)
    assert any(v.rule_id == "MACRO-SAFETY-001" for v in findings)


@pytest.mark.asyncio
async def test_generate_macro_does_not_store_without_confirm():
    """store=True without confirm_destructive=True must return blocked."""
    from src.server import generate_ma2_macro
    raw = await generate_ma2_macro(
        intent="make a tap tempo macro",
        scope_hints=None,
        store=True,
        pool_id=99,
        confirm_destructive=False,
    )
    data = json.loads(raw)
    assert data.get("blocked") is True
    assert data.get("stored_as") is None


@pytest.mark.asyncio
async def test_generate_unknown_intent_returns_safe_default():
    """Unknown intent produces a safe ClearAll macro."""
    from src.server import generate_ma2_macro
    raw = await generate_ma2_macro(
        intent="quibble frobnicate xyzzy",
        scope_hints=None,
        store=False,
    )
    data = json.loads(raw)
    ET.fromstring(data["body_xml"])
    assert "ClearAll" in data["body_xml"]


@pytest.mark.asyncio
async def test_generate_macro_returns_validation_result():
    from src.server import generate_ma2_macro
    raw = await generate_ma2_macro(intent="panic blackout", store=False)
    data = json.loads(raw)
    assert "validation" in data
    assert data["validation"].get("xml_valid") is True

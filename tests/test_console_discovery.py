"""UDP broadcast discovery — parser + scan loop."""

from __future__ import annotations

import json
import socket

import pytest

from src.discovery import (
    discover_grandma2_broadcast,
    list_local_networks,
    parse_broadcast_packet,
)


# Sample packet derived from documented MA-Net2 announce format.
SAMPLE_PACKET = (
    b"GMA2-ANNOUNCE\x01"
    b"session=Default\x02name=onPC\x02ip=127.0.0.1\x02"
    b"port=30000\x02version=3.9.60\x00"
)


def test_parse_broadcast_packet_extracts_fields():
    candidate = parse_broadcast_packet(SAMPLE_PACKET, source_addr=("127.0.0.1", 6004))
    assert candidate is not None
    assert candidate["host"] == "127.0.0.1"
    assert candidate["port"] == 30000
    assert candidate["session_name"] == "Default"
    assert candidate["version"] == "3.9.60"
    assert candidate["source"] == "broadcast"


def test_parse_packet_uses_source_addr_when_ip_missing():
    pkt = b"GMA2-ANNOUNCE\x01session=Test\x02name=onPC\x02port=30000\x00"
    candidate = parse_broadcast_packet(pkt, source_addr=("10.0.0.5", 6004))
    assert candidate is not None
    assert candidate["host"] == "10.0.0.5"


def test_parse_packet_defaults_port_when_invalid():
    pkt = b"GMA2-ANNOUNCE\x01port=notanumber\x00"
    candidate = parse_broadcast_packet(pkt, source_addr=("127.0.0.1", 6004))
    assert candidate is not None
    assert candidate["port"] == 30000


def test_parse_unrecognised_packet_returns_none():
    assert parse_broadcast_packet(b"not a gma2 packet", ("1.2.3.4", 12345)) is None


def test_list_local_networks_returns_non_empty():
    nets = list_local_networks()
    assert isinstance(nets, list)
    assert nets, "expected at least one network"


@pytest.mark.asyncio
async def test_discover_returns_quickly_with_short_timeout():
    """With a 1s timeout on a network with no responder, returns [] in ~1s."""
    import time
    t0 = time.monotonic()
    candidates = await discover_grandma2_broadcast(network=None, timeout_seconds=1)
    elapsed = time.monotonic() - t0
    assert isinstance(candidates, list)
    assert elapsed < 5.0, f"discovery took {elapsed:.2f}s — should be ~1s"


@pytest.mark.asyncio
async def test_discover_consoles_tool_returns_envelope():
    from src.server import discover_consoles
    raw = await discover_consoles(timeout_seconds=1)
    data = json.loads(raw)
    assert "candidates" in data
    assert "elapsed_ms" in data
    assert isinstance(data["candidates"], list)


@pytest.mark.asyncio
async def test_discover_consoles_tool_mdns_note():
    """Requesting mdns method returns a note about the optional install (Path B)."""
    from src.server import discover_consoles
    raw = await discover_consoles(timeout_seconds=1, methods=["mdns"])
    data = json.loads(raw)
    assert data.get("note"), "expected a note when mdns requested"
    assert "mdns" in data["note"].lower() or "mdns" in str(data).lower()

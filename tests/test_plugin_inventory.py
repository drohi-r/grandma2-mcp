"""Plugin inventory — parse browse_plugin_library output + cached lookup."""

from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, patch

import pytest

from src.plugin_inventory import PluginInventory, parse_plugin_listing


_SAMPLE_LISTING = (
    "Executing : List Plugin\n"
    "         No.  Name                ExecuteOnLoad  Info\n"
    "Plugin 1 1    LUA                 No\n"
    "Plugin 2 2    Ecube Color Picker  No\n"      # captured from real onPC import
    "Plugin 1 3    EcubeFXEngine       No\n"
)


def test_parse_listing_extracts_records():
    records = parse_plugin_listing(_SAMPLE_LISTING)
    assert len(records) == 3
    by_id = {r["pool_id"]: r["name"] for r in records}
    assert by_id[2] == "Ecube Color Picker"      # name with embedded space
    assert by_id[3] == "EcubeFXEngine"


def test_parse_listing_ignores_headers_and_blank_lines():
    listing = (
        "Executing : List Plugin\n"
        "\n"
        "         No.  Name      ExecuteOnLoad\n"
        "\n"
        "Plugin 1 5    MyPlugin  No\n"
    )
    records = parse_plugin_listing(listing)
    assert len(records) == 1
    assert records[0]["name"] == "MyPlugin"
    assert records[0]["pool_id"] == 5


def test_parse_listing_handles_names_with_spaces():
    """Real onPC import produces 'Ecube Color Picker' with embedded spaces."""
    listing = "Plugin 2 2    Ecube Color Picker  No\n"
    records = parse_plugin_listing(listing)
    assert len(records) == 1
    assert records[0]["name"] == "Ecube Color Picker"
    assert records[0]["pool_id"] == 2


def test_parse_listing_empty_string():
    assert parse_plugin_listing("") == []


@pytest.mark.asyncio
async def test_inventory_exact_match():
    inv = PluginInventory()
    inv._records = [{"pool_id": 2, "name": "EcubeColorPicker"}]
    inv._observed_at = time.time()
    result = await inv.lookup("EcubeColorPicker", use_cache=True, cache_ttl=60)
    assert result["available"] is True
    assert result["pool_id"] == 2
    assert result["match"] == "exact"


@pytest.mark.asyncio
async def test_inventory_substring_match():
    inv = PluginInventory()
    inv._records = [{"pool_id": 2, "name": "EcubeColorPicker"}]
    inv._observed_at = time.time()
    result = await inv.lookup("colorpicker", use_cache=True, cache_ttl=60)
    assert result["available"] is True
    assert result["match"] == "substring"


@pytest.mark.asyncio
async def test_inventory_case_insensitive_exact_match():
    inv = PluginInventory()
    inv._records = [{"pool_id": 2, "name": "EcubeColorPicker"}]
    inv._observed_at = time.time()
    result = await inv.lookup("ECUBECOLORPICKER", use_cache=True, cache_ttl=60)
    assert result["available"] is True
    assert result["match"] == "exact"


@pytest.mark.asyncio
async def test_inventory_whitespace_flexible_match():
    """Query 'EcubeColorPicker' matches stored 'Ecube Color Picker' (the
    live MA2 display name)."""
    inv = PluginInventory()
    inv._records = [{"pool_id": 2, "name": "Ecube Color Picker"}]
    inv._observed_at = time.time()
    result = await inv.lookup("EcubeColorPicker", use_cache=True, cache_ttl=60)
    assert result["available"] is True
    assert result["match"] == "exact"
    assert result["pool_id"] == 2


@pytest.mark.asyncio
async def test_inventory_whitespace_flexible_reverse():
    """Query 'Ecube Color Picker' (display form) matches stored 'EcubeColorPicker'."""
    inv = PluginInventory()
    inv._records = [{"pool_id": 2, "name": "EcubeColorPicker"}]
    inv._observed_at = time.time()
    result = await inv.lookup("Ecube Color Picker", use_cache=True, cache_ttl=60)
    assert result["available"] is True
    assert result["match"] == "exact"


@pytest.mark.asyncio
async def test_inventory_missing_plugin():
    inv = PluginInventory()
    inv._records = [{"pool_id": 1, "name": "OtherPlugin"}]
    inv._observed_at = time.time()
    result = await inv.lookup("EcubeColorPicker", use_cache=True, cache_ttl=60)
    assert result["available"] is False
    assert result["pool_id"] is None
    assert result["match"] == "miss"


@pytest.mark.asyncio
async def test_inventory_refreshes_on_ttl_miss():
    """When cache is stale, a fresh fetch is triggered."""
    inv = PluginInventory()
    inv._records = []
    inv._observed_at = 0.0  # ancient
    fetch_mock = AsyncMock(return_value=[{"pool_id": 7, "name": "EcubeColorPicker"}])
    with patch.object(inv, "_fetch_records", fetch_mock):
        result = await inv.lookup("EcubeColorPicker", use_cache=True, cache_ttl=60)
    fetch_mock.assert_called_once()
    assert result["available"] is True
    assert result["pool_id"] == 7
    assert result["source"] == "live_query"


@pytest.mark.asyncio
async def test_inventory_uses_cache_when_fresh():
    inv = PluginInventory()
    inv._records = [{"pool_id": 7, "name": "EcubeColorPicker"}]
    inv._observed_at = time.time()
    fetch_mock = AsyncMock(return_value=[])
    with patch.object(inv, "_fetch_records", fetch_mock):
        result = await inv.lookup("EcubeColorPicker", use_cache=True, cache_ttl=60)
    fetch_mock.assert_not_called()
    assert result["source"] == "cache"


@pytest.mark.asyncio
async def test_inventory_use_cache_false_always_refetches():
    inv = PluginInventory()
    inv._records = [{"pool_id": 7, "name": "EcubeColorPicker"}]
    inv._observed_at = time.time()  # fresh, but use_cache=False bypasses
    fetch_mock = AsyncMock(return_value=[{"pool_id": 99, "name": "NewPlugin"}])
    with patch.object(inv, "_fetch_records", fetch_mock):
        result = await inv.lookup("NewPlugin", use_cache=False, cache_ttl=60)
    fetch_mock.assert_called_once()
    assert result["available"] is True
    assert result["pool_id"] == 99


@pytest.mark.asyncio
async def test_check_plugin_available_tool_envelope():
    """The MCP tool returns a JSON envelope with the expected fields."""
    from src.server import check_plugin_available
    from src.plugin_inventory import PluginInventory, _default_inventory

    inv = _default_inventory()
    inv._records = [{"pool_id": 2, "name": "EcubeColorPicker"}]
    inv._observed_at = time.time()
    raw = await check_plugin_available(
        "EcubeColorPicker", use_cache=True, cache_ttl_seconds=60,
    )
    data = json.loads(raw)
    assert data["plugin_name"] == "EcubeColorPicker"
    assert data["available"] is True
    assert data["pool_id"] == 2
    assert "last_checked_at" in data
    assert data["source"] in ("cache", "live_query")

"""MCP tools — integrations. Split out of src/server.py.

Tools register on ``src.server.mcp`` at import. Names that tests patch or
that live in other tool modules are looked up as ``_srv.<name>`` at call time.
"""

# ruff: noqa: E501

import json

import src.server as _srv
from src.auth import OAuthScope, require_scope
from src.server import (
    _handle_errors,
    _osc_allowed_hosts,
    mcp,
)

# ============================================================
# Bitfocus Companion Integration Tools
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def generate_companion_config(
    page: int = 1,
    companion_page: int = 1,
    grid_columns: int = 8,
) -> str:
    """
    Generate a Bitfocus Companion .companionconfig page from the current MA2 executor layout (SAFE_READ).

    Reads the executor page and builds a Companion-importable JSON config
    with one button per assigned executor. Each button sends the appropriate
    Go+ command via Companion's grandMA2 telnet module.

    The output is a JSON string in Companion v4 page-export format. Save it
    to a .companionconfig file and import via Companion UI → Buttons → Import.

    Args:
        page: MA2 executor page to export (default 1).
        companion_page: Target Companion page number (default 1).
        grid_columns: Companion grid width — 8 for Stream Deck XL, 5 for Stream Deck (default 8).

    Returns:
        str: JSON with companion_config (the importable config), executor_count, and instructions.

    Examples:
        - Export page 1: generate_companion_config()
        - Export page 2 for Stream Deck: generate_companion_config(page=2, grid_columns=5)
    """
    await _srv.get_client()  # fail fast when the console is unreachable

    # Read the executor page layout
    scan_result = await _srv.scan_page_executor_layout(page=page)
    scan_data = json.loads(scan_result) if isinstance(scan_result, str) else scan_result

    executors = scan_data.get("executors", [])
    if not executors and "error" in scan_data:
        return json.dumps({
            "error": f"Could not read executor page {page}: {scan_data.get('error')}",
            "risk_tier": "SAFE_READ",
        }, indent=2)

    # Build Companion page config
    controls: dict[str, dict] = {}
    button_count = 0

    for exec_info in executors:
        exec_id = exec_info.get("executor_id") or exec_info.get("id")
        if exec_id is None:
            continue

        label = exec_info.get("label") or exec_info.get("name") or f"Exec {exec_id}"
        has_sequence = exec_info.get("sequence_id") is not None or exec_info.get("assigned")

        # Grid position
        row = button_count // grid_columns
        col = button_count % grid_columns

        # Button color: dark blue for assigned, dark gray for empty
        bgcolor = 1315860 if has_sequence else 2105376  # #141414 vs #202020

        controls[f"{row}/{col}"] = {
            "type": "button",
            "style": {
                "text": str(label)[:12],
                "size": "auto",
                "color": 16777215,  # white text
                "bgcolor": bgcolor,
            },
            "options": {"relativeDelay": False},
            "feedbacks": [],
            "steps": {
                "0": {
                    "action_sets": {
                        "down": [
                            {
                                "actionId": "command",
                                "options": {
                                    "command": f"Go+ Executor {page}.{exec_id}",
                                },
                            }
                        ],
                        "up": [],
                    }
                }
            },
        }
        button_count += 1

    max_row = max(0, (button_count - 1) // grid_columns)
    companion_config = {
        "version": 4,
        "type": "page",
        "page": {
            "name": f"MA2 Page {page}",
            "gridSize": {
                "minColumn": 0,
                "maxColumn": grid_columns - 1,
                "minRow": 0,
                "maxRow": max_row,
            },
            "controls": controls,
        },
    }

    return json.dumps({
        "companion_config": companion_config,
        "executor_count": button_count,
        "companion_page": companion_page,
        "ma2_page": page,
        "grid_columns": grid_columns,
        "risk_tier": "SAFE_READ",
        "instructions": (
            "Save the 'companion_config' value to a .companionconfig file, "
            "then import in Companion UI → Buttons → Import. "
            "Make sure the grandMA2 connection module is configured with "
            "the correct console IP and Telnet credentials."
        ),
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PLAYBACK_GO)
@_handle_errors
async def companion_button_press(
    page: int,
    button: int,
    host: str = "localhost",
    port: int = 8000,
) -> str:
    """
    Press a button on a running Bitfocus Companion instance via HTTP API (SAFE_WRITE).

    Sends a GET request to Companion's REST API to trigger a button press.
    Companion must be running and accessible at the specified host/port.

    Args:
        page: Companion page number (1-based).
        button: Button index on the page (0-based).
        host: Companion host (default "localhost").
        port: Companion HTTP API port (default 8000).

    Returns:
        str: JSON with status, url_called, response text.

    Examples:
        - Press button 0 on page 1: companion_button_press(page=1, button=0)
        - Remote Companion: companion_button_press(page=1, button=3, host="192.168.1.50")
    """
    import urllib.error
    import urllib.request

    url = f"http://{host}:{port}/press/bank/{page}/{button}"

    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return json.dumps({
                "status": "ok",
                "http_status": resp.status,
                "url_called": url,
                "response": body[:500],
                "risk_tier": "SAFE_WRITE",
            }, indent=2)
    except urllib.error.URLError as e:
        return json.dumps({
            "status": "error",
            "error": f"Could not reach Companion at {url}: {e.reason}",
            "url_called": url,
            "hint": "Ensure Bitfocus Companion is running and the HTTP API is enabled.",
            "risk_tier": "SAFE_WRITE",
        }, indent=2)
    except TimeoutError:
        return json.dumps({
            "status": "error",
            "error": f"Timeout connecting to Companion at {url}",
            "url_called": url,
            "risk_tier": "SAFE_WRITE",
        }, indent=2)


# ============================================================
# BPM Sync / ShowKontrol Integration
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.EXECUTOR_CTRL)
@_handle_errors
async def set_bpm(
    bpm: float,
    speed_master: int = 1,
) -> str:
    """
    Set the BPM on a grandMA2 Speed Master (SAFE_WRITE).

    Designed for live BPM sync from external sources like ShowKontrol,
    Beat Link Trigger, Ableton, or any system that provides real-time BPM.
    Sends the SpecialMaster command to the console via Telnet.

    The BPM value directly controls effect speed for any executor assigned
    to this speed master. Common workflow: ShowKontrol reads CDJ BPM →
    calls this tool → MA2 effects follow the DJ's tempo in real time.

    Args:
        bpm: Beats per minute (1-300). Fractional values supported (e.g. 128.5).
        speed_master: Which speed master to control (1-16, default 1).

    Returns:
        str: JSON with command_sent, raw_response, bpm, speed_master.

    Examples:
        - Set 128 BPM on speed master 1: set_bpm(bpm=128)
        - Set 140 BPM on speed master 3: set_bpm(bpm=140, speed_master=3)
    """
    if not (1 <= bpm <= 300):
        return json.dumps({
            "error": f"BPM must be between 1 and 300, got {bpm}",
            "blocked": True,
        }, indent=2)
    if not (1 <= speed_master <= 16):
        return json.dumps({
            "error": f"Speed master must be 1-16, got {speed_master}",
            "blocked": True,
        }, indent=2)

    client = await _srv.get_client()
    cmd = f"SpecialMaster 3.{speed_master} At {bpm}"
    raw = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw,
        "bpm": bpm,
        "speed_master": speed_master,
        "risk_tier": "SAFE_WRITE",
        "tip": f"Assign executors to Speed Master {speed_master} with: assign executor X /speedmaster=speed{speed_master}",
    }, indent=2)


# ============================================================
# OSC Output (Resolume, etc.)
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.EXECUTOR_CTRL)
@_handle_errors
async def send_osc(
    address: str,
    value: float | int | str,
    host: str = "localhost",
    port: int = 7000,
) -> str:
    """
    Send an OSC message to an external application like Resolume Arena (SAFE_WRITE).

    Uses raw UDP — no extra dependencies. Works with any OSC-compatible software:
    Resolume Arena/Avenue, QLab, TouchDesigner, Ableton, etc.

    Common Resolume OSC addresses:
      /composition/tempocontroller/tempo  — set BPM (float)
      /composition/layers/N/clips/M/connect — trigger clip (int 1)
      /composition/layers/N/video/opacity — layer opacity (float 0.0-1.0)
      /composition/disconnectall — clear all clips (int 1)

    Args:
        address: OSC address pattern (e.g. "/composition/tempocontroller/tempo").
        value: Value to send — float, int, or string.
        host: Target host (default "localhost").
        port: Target OSC port (default 7000, Resolume's default).

    Returns:
        str: JSON with address, value, host, port, status.

    Examples:
        - Set Resolume BPM: send_osc(address="/composition/tempocontroller/tempo", value=128.0)
        - Trigger clip: send_osc(address="/composition/layers/1/clips/1/connect", value=1)
        - Layer opacity: send_osc(address="/composition/layers/1/video/opacity", value=0.75)
    """
    import socket
    import struct

    allowed_hosts = _osc_allowed_hosts()
    normalized_host = host.strip().lower()
    if "*" not in allowed_hosts and normalized_host not in allowed_hosts:
        return json.dumps({
            "status": "blocked",
            "error": f"Host {host!r} is not allowed. Set GMA_OSC_ALLOWED_HOSTS to permit it.",
            "host": host,
            "port": port,
            "allowed_hosts": sorted(allowed_hosts),
            "blocked": True,
            "risk_tier": "SAFE_WRITE",
        }, indent=2)

    def _build_osc_message(addr: str, val: float | int | str) -> bytes:
        """Build a minimal OSC message packet."""
        # Pad address to 4-byte boundary
        addr_bytes = addr.encode("utf-8") + b"\x00"
        while len(addr_bytes) % 4 != 0:
            addr_bytes += b"\x00"

        if isinstance(val, float):
            type_tag = b",f\x00\x00"
            val_bytes = struct.pack(">f", val)
        elif isinstance(val, int):
            type_tag = b",i\x00\x00"
            val_bytes = struct.pack(">i", val)
        else:
            # String
            s = str(val).encode("utf-8") + b"\x00"
            while len(s) % 4 != 0:
                s += b"\x00"
            type_tag = b",s\x00\x00"
            val_bytes = s

        return addr_bytes + type_tag + val_bytes

    try:
        packet = _build_osc_message(address, value)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(packet, (host, port))
        sock.close()

        return json.dumps({
            "status": "sent",
            "address": address,
            "value": value,
            "host": host,
            "port": port,
            "packet_size": len(packet),
            "risk_tier": "SAFE_WRITE",
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": str(e),
            "address": address,
            "host": host,
            "port": port,
            "risk_tier": "SAFE_WRITE",
        }, indent=2)

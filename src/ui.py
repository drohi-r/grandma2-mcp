from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from typing import Any
from urllib.parse import parse_qs, urlparse

from src import server

logger = logging.getLogger("ma2-ui")

_UI_LOOP: asyncio.AbstractEventLoop | None = None
_UI_LOOP_THREAD: threading.Thread | None = None

# Semaphore limits concurrent MA2 telnet calls (not HTTP requests).
_MA2_SEMAPHORE: asyncio.Semaphore | None = None
_MA2_CONCURRENCY = 1  # Serialize MA2 access — one telnet command at a time

# Simple TTL cache for MA2 reads — avoids re-querying on rapid page transitions.
_CACHE: dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 12.0  # seconds


def _ui_host() -> str:
    return os.environ.get("GMA_UI_HOST", "127.0.0.1")


def _ui_port() -> int:
    raw = os.environ.get("GMA_UI_PORT", "8092")
    try:
        port = int(raw)
    except ValueError:
        raise ValueError(f"GMA_UI_PORT={raw!r} is not a valid integer") from None
    if not (1 <= port <= 65535):
        raise ValueError(f"GMA_UI_PORT={port} is outside valid port range 1-65535")
    return port


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, indent=2, default=str).encode("utf-8")


def _query_value(query: dict[str, list[str]], name: str, default: str = "") -> str:
    values = query.get(name)
    if not values:
        return default
    return values[0]


def _query_int(query: dict[str, list[str]], name: str, default: int) -> int:
    raw = _query_value(query, name, str(default))
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"Query parameter {name!r} must be an integer.") from None


def _query_float(query: dict[str, list[str]], name: str, default: float) -> float:
    raw = _query_value(query, name, str(default))
    try:
        return float(raw)
    except ValueError:
        raise ValueError(f"Query parameter {name!r} must be a number.") from None


def _load_static(name: str) -> bytes:
    base = resources.files("src").joinpath("ui_static")
    return base.joinpath(name).read_bytes()


def _ensure_ui_loop() -> asyncio.AbstractEventLoop:
    global _UI_LOOP, _UI_LOOP_THREAD, _MA2_SEMAPHORE
    if _UI_LOOP is not None:
        return _UI_LOOP

    ready = threading.Event()

    def _runner() -> None:
        global _UI_LOOP, _MA2_SEMAPHORE
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _MA2_SEMAPHORE = asyncio.Semaphore(_MA2_CONCURRENCY)
        _UI_LOOP = loop
        ready.set()
        loop.run_forever()

    _UI_LOOP_THREAD = threading.Thread(target=_runner, name="ma2-ui-loop", daemon=True)
    _UI_LOOP_THREAD.start()
    ready.wait()
    assert _UI_LOOP is not None
    return _UI_LOOP


def _run_async(coro):
    """Submit coroutine to the UI event loop from any HTTP thread."""
    loop = _ensure_ui_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=30)


async def _call_json(func, *args, **kwargs) -> dict[str, Any]:
    """Call an MCP tool function, gated by the MA2 semaphore."""
    assert _MA2_SEMAPHORE is not None
    async with _MA2_SEMAPHORE:
        raw = await func(*args, **kwargs)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"ok": False, "blocked": False, "error": "Tool returned non-JSON output.", "raw": raw}


async def _cached_call(cache_key: str, func, *args, **kwargs) -> dict[str, Any]:
    """Call with TTL cache — avoids duplicate MA2 reads on rapid transitions."""
    now = time.monotonic()
    if cache_key in _CACHE:
        ts, payload = _CACHE[cache_key]
        if now - ts < _CACHE_TTL:
            return payload
    result = await _call_json(func, *args, **kwargs)
    # Don't cache errors
    if not result.get("error"):
        _CACHE[cache_key] = (now, result)
    return result


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)


def _parse_fixture_rows(raw_response: str) -> list[dict[str, Any]]:
    """Parse 'list fixture' output.

    MA2 format (per live observation):
      ID  Label FixID ChaID TypeID FixtureType  DMXPatch  Params  ...extra
    e.g.:
      1  Wash 1 1 - 3 Robin 600 LEDWash Mode 1 1.001 No 0.00 ...

    Strategy: anchor on the DMX patch address (N.NNN) + Params token, which
    are the most distinctive and unambiguous tokens in the line.  Parse the
    pre-patch portion to extract label / column fields.
    """
    rows: list[dict[str, Any]] = []
    for line in raw_response.splitlines():
        text = _strip_ansi(line).strip()
        if not text:
            continue
        # Outer: fixture_id + rest
        outer = re.match(r"^(?:Fixture\s+)?(\d+)\s+(.+)", text)
        if not outer:
            continue
        fixture_id = int(outer.group(1))
        rest = outer.group(2).strip()

        # Anchor on DMX patch + Yes/No to split the line
        # Matches "(-)" unpatched or "1.001" style addresses
        patch_anchor = re.search(r"\s+(\d+\.\d+|\(-\))\s+(No|Yes)\b", rest)

        parsed: dict[str, Any] = {
            "label": "",
            "fix_id": None,
            "channel_id": None,
            "fixture_type_id": None,
            "fixture_type": "",
            "patch": "",
            "has_parameters": None,
        }

        if patch_anchor:
            patch_raw = patch_anchor.group(1)
            params = patch_anchor.group(2)
            pre = rest[: patch_anchor.start()].strip()
            parsed["patch"] = "" if patch_raw == "(-)" else patch_raw
            parsed["has_parameters"] = params == "Yes"

            # pre = "Label FixID ChaID TypeID FixtureType"
            # FixID, ChaID, TypeID are numbers / dash — parse greedily from right
            # TypeID is last standalone number before the fixture type name
            col = re.match(r"^(?P<label>.*?)\s+(?P<fixid>\d+)\s+(?P<chaid>-|\d+)\s+(?P<typeid>\d+)\s+(?P<fixture_type>.+?)\s*$", pre)
            if col:
                parsed["label"] = col.group("label").strip()
                parsed["fix_id"] = int(col.group("fixid"))
                parsed["channel_id"] = None if col.group("chaid") == "-" else int(col.group("chaid"))
                parsed["fixture_type_id"] = int(col.group("typeid"))
                parsed["fixture_type"] = col.group("fixture_type").strip()

        rows.append({"fixture_id": fixture_id, "summary": rest, **parsed})
    return rows


def _parse_sequence_cues(raw_response: str) -> list[dict[str, Any]]:
    cues: list[dict[str, Any]] = []
    for line in raw_response.splitlines():
        text = line.strip()
        if not text or "cue" not in text.lower():
            continue
        cue_match = re.search(r"\bCue\s+([0-9]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
        label_match = re.search(r'Name\s*[=:]\s*"?(.*?)"?$', text, re.IGNORECASE)
        cues.append({
            "raw": text,
            "cue": cue_match.group(1) if cue_match else None,
            "label": label_match.group(1) if label_match else "",
        })
    return cues


def _parse_console_users(raw_response: str) -> list[dict[str, Any]]:
    users: list[dict[str, Any]] = []
    for line in raw_response.splitlines():
        text = _strip_ansi(line).strip()
        if not text or text.startswith("Executing") or text.startswith("Name ") or text.startswith("["):
            continue
        match = re.match(
            r"^(?:NewUser\s+)?(?P<id>\d+)\s+(?P<name>\S+)\s+(?P<password>\*+)?\s*(?P<profile>\S+)?\s+(?P<rights>\S+)\s+(?P<logged_in>\d+)$",
            text,
        )
        if not match:
            continue
        users.append({
            "id": int(match.group("id")),
            "name": match.group("name"),
            "profile": match.group("profile") or "",
            "rights": match.group("rights"),
            "logged_in": match.group("logged_in") == "1",
        })
    return users


def _parse_executor_probe(raw_response: str, page: int, executor_id: int) -> dict[str, Any] | None:
    text = _strip_ansi(raw_response)
    if "NO OBJECTS" in text.upper():
        return None
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    seq_id = None
    label = f"Exec {page}.{executor_id}"
    for ln in lines:
        seq_match = re.search(r"\bSeq(?:uence)?(?:=Seq)?\s+(\d+)", ln, re.IGNORECASE)
        if seq_match:
            seq_id = int(seq_match.group(1))
        if ln.lower().startswith("exec "):
            exec_match = re.match(
                r"^Exec\s+\S+(?:\s+Seq(?:uence)?(?:=Seq)?\s+\d+)?(?:\s+(?P<label>.+))?$",
                ln,
                re.IGNORECASE,
            )
            if exec_match:
                maybe_label = (exec_match.group("label") or "").strip()
                if maybe_label:
                    label = maybe_label
    return {
        "id": executor_id,
        "page": page,
        "label": label,
        "type": "exec",
        "sequence_id": seq_id,
    }


# ---------------------------------------------------------------------------
# API data-fetching coroutines
# ---------------------------------------------------------------------------

async def _scan_executors(page: int, executor_id: int | None = None) -> dict[str, Any]:
    """Probe a single executor, or return empty list for the page.
    We do NOT bulk-scan ranges — that floods the MA2 telnet session.
    The UI lets the operator pick individual executors to inspect."""
    if executor_id is None:
        return {"page": page, "executors": [], "mode": "select"}

    result = await _cached_call(f"executor_status:{page}:{executor_id}", server.get_executor_status, executor_id=executor_id, page=page)
    raw = result.get("raw_response", "")
    parsed = _parse_executor_probe(raw, page, executor_id)
    entries = [parsed] if parsed else []
    return {
        "page": page,
        "executor_id": executor_id,
        "executors": entries,
        "raw_response": raw,
    }


async def _dashboard() -> dict[str, Any]:
    """Dashboard: sessions + users only. Two reads, both lightweight.
    Fixture types is deliberately NOT loaded here — it navigates the cd tree
    (5 telnet commands) and is too heavy for a dashboard refresh."""
    sessions = await _cached_call("sessions", server.inspect_sessions)
    users = await _cached_call("users", server.list_console_users)
    return {
        "sessions": sessions,
        "users": users,
        "parsed_users": _parse_console_users(users.get("raw_response", "")),
    }


async def _executor_detail(page: int, executor_id: int) -> dict[str, Any]:
    """Get executor status + linked cues. Two telnet commands max."""
    status = await _cached_call(f"executor_status:{page}:{executor_id}", server.get_executor_status, executor_id=executor_id, page=page)
    raw_status = status.get("raw_response", "")
    parsed = _parse_executor_probe(raw_status, page, executor_id)

    cues: dict[str, Any] = {}
    parsed_cues: list[dict[str, Any]] = []
    seq_id = parsed.get("sequence_id") if parsed else None

    if seq_id is not None:
        # Use sequence_id directly — avoids the extra executor probe that
        # list_sequence_cues would do if we passed executor_id instead
        cues = await _cached_call(f"sequence:{seq_id}", server.list_sequence_cues, sequence_id=seq_id)
        parsed_cues = _parse_sequence_cues(cues.get("raw_response", ""))

    return {
        "page": page,
        "executor_id": executor_id,
        "status": status,
        "executor_info": parsed,
        "sequence": cues,
        "parsed_cues": parsed_cues,
        "has_sequence": seq_id is not None,
        "sequence_id": seq_id,
    }


def _match_fixture_type(line: str, type_names: list[str]) -> str | None:
    """Fuzzy-match a fixture line against known type names (longest match wins)."""
    normalized_line = re.sub(r"\s+", " ", line.strip().lower())
    # Sort by length descending so "Mac Aura XB" wins over "Mac Aura"
    for name in sorted(type_names, key=lambda n: -len(n)):
        escaped = re.escape(name.lower())
        if re.search(rf"(?<!\w){escaped}(?!\w)", normalized_line):
            return name
    return None


async def _fixture_inventory() -> dict[str, Any]:
    """Patch view: list fixture + cached fixture types for grouping.
    - list fixture: 1 command
    - list_fixture_types: 5 commands (cd navigation), cached 12s
    """
    fixtures = await _cached_call("fixtures", server.list_fixtures)
    types_payload = await _cached_call("fixture_types", server.list_fixture_types)

    raw = fixtures.get("raw_response", "")
    rows = _parse_fixture_rows(raw)

    # Build list of known fixture type names from the types endpoint
    type_names: list[str] = []
    for entry in types_payload.get("entries", []):
        name = entry.get("name") or ""
        if name:
            type_names.append(name)

    # Group rows by fixture type.
    # 1. Try regex-parsed fixture_type first (works when columns are clean)
    # 2. Fall back to fuzzy matching against known type names
    # 3. Fall back to "Unclassified"
    type_groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        ft = row.get("fixture_type") or ""
        if not ft and type_names:
            ft = _match_fixture_type(row.get("summary", ""), type_names) or ""
            if ft:
                row["fixture_type"] = ft
        if not ft:
            ft = "Unclassified"
        type_groups.setdefault(ft, []).append(row)

    return {
        "fixtures": fixtures,
        "fixture_rows": rows,
        "fixture_types": types_payload,
        "type_groups": {name: {"count": len(items), "fixtures": items} for name, items in type_groups.items()},
        "total_count": len(rows),
        "type_count": len(type_groups),
    }


async def _route_api(method: str, path: str, query: dict[str, list[str]], body: dict[str, Any]) -> tuple[int, bytes]:
    if method == "GET" and path == "/api/config":
        return HTTPStatus.OK, _json_bytes({
            "ui_host": _ui_host(),
            "ui_port": _ui_port(),
            "gma_host": getattr(server, "_GMA_HOST", ""),
            "gma_port": getattr(server, "_GMA_PORT", ""),
            "transport": os.environ.get("GMA_TRANSPORT", "stdio"),
        })

    if method == "GET" and path == "/api/dashboard":
        return HTTPStatus.OK, _json_bytes(await _dashboard())

    if method == "GET" and path == "/api/executor":
        # Single executor probe — NOT a bulk scan
        page = _query_int(query, "page", 1)
        exec_id_raw = query.get("executor_id", [None])[0]
        exec_id = int(exec_id_raw) if exec_id_raw not in (None, "") else None
        return HTTPStatus.OK, _json_bytes(await _scan_executors(page, exec_id))

    if method == "GET" and path == "/api/executor-detail":
        return HTTPStatus.OK, _json_bytes(await _executor_detail(
            _query_int(query, "page", 1),
            _query_int(query, "executor_id", 201),
        ))

    if method == "GET" and path == "/api/sequence":
        sequence_id = query.get("sequence_id", [None])[0]
        executor_id = query.get("executor_id", [None])[0]
        resolved_sequence = int(sequence_id) if sequence_id not in (None, "") else None
        resolved_executor = int(executor_id) if executor_id not in (None, "") else None
        executor_page = _query_int(query, "executor_page", 1)
        cue_id = _query_float(query, "cue_id", 0.0) if "cue_id" in query else None
        cache_key = f"sequence:{resolved_sequence}:{resolved_executor}:{executor_page}:{cue_id}"
        # Prefer sequence_id to avoid extra executor probe
        payload = await _cached_call(
            cache_key,
            server.list_sequence_cues,
            sequence_id=resolved_sequence,
            executor_id=resolved_executor,
            executor_page=executor_page,
            cue_id=cue_id,
        )
        payload["parsed_cues"] = _parse_sequence_cues(payload.get("raw_response", ""))
        return HTTPStatus.OK, _json_bytes(payload)

    if method == "GET" and path == "/api/fixtures":
        return HTTPStatus.OK, _json_bytes(await _fixture_inventory())

    if method == "GET" and path == "/api/fixture-types":
        return HTTPStatus.OK, _json_bytes(await _cached_call("fixture_types", server.list_fixture_types))

    if method == "GET" and path == "/api/analysis/patch":
        expected = _query_value(query, "expected")
        return HTTPStatus.OK, _json_bytes(await _call_json(server.compare_patch_to_show_expectation, expected))

    if method == "GET" and path == "/api/analysis/telemetry":
        return HTTPStatus.OK, _json_bytes(await _call_json(server.get_telemetry_report, days=_query_int(query, "days", 1)))

    if method == "POST" and path == "/api/plan":
        return HTTPStatus.OK, _json_bytes(await _call_json(server.plan_agent_goal, str(body.get("goal", ""))))

    if method == "POST" and path == "/api/run":
        return HTTPStatus.OK, _json_bytes(
            await _call_json(
                server.run_agent_goal,
                str(body.get("goal", "")),
                auto_confirm=bool(body.get("auto_confirm", False)),
                dry_run=bool(body.get("dry_run", False)),
            )
        )

    if method == "POST" and path == "/api/cache/clear":
        _CACHE.clear()
        return HTTPStatus.OK, _json_bytes({"ok": True})

    return HTTPStatus.NOT_FOUND, _json_bytes({"ok": False, "error": f"Unknown route: {method} {path}"})


class _Handler(BaseHTTPRequestHandler):
    server_version = "MA2UI/1.0"

    def _write(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self, path: str) -> tuple[int, bytes, str]:
        if path in {"/", "/index.html"}:
            return HTTPStatus.OK, _load_static("index.html"), "text/html; charset=utf-8"
        if path == "/app.js":
            return HTTPStatus.OK, _load_static("app.js"), "application/javascript; charset=utf-8"
        if path == "/styles.css":
            return HTTPStatus.OK, _load_static("styles.css"), "text/css; charset=utf-8"
        return HTTPStatus.NOT_FOUND, b"Not found", "text/plain; charset=utf-8"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            try:
                status, body = _run_async(_route_api("GET", parsed.path, parse_qs(parsed.query), {}))
            except Exception as exc:
                logger.exception("API error: %s", parsed.path)
                status, body = HTTPStatus.INTERNAL_SERVER_ERROR, _json_bytes({"ok": False, "error": str(exc)})
            self._write(status, body, "application/json; charset=utf-8")
            return
        status, body, content_type = self._serve_static(parsed.path)
        self._write(status, body, content_type)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length else b"{}"
        try:
            body = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self._write(HTTPStatus.BAD_REQUEST, _json_bytes({"ok": False, "error": "Request body must be JSON."}), "application/json; charset=utf-8")
            return
        try:
            status, payload = _run_async(_route_api("POST", parsed.path, parse_qs(parsed.query), body))
        except Exception as exc:
            logger.exception("API error: %s", parsed.path)
            status, payload = HTTPStatus.INTERNAL_SERVER_ERROR, _json_bytes({"ok": False, "error": str(exc)})
        self._write(status, payload, "application/json; charset=utf-8")

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    host = _ui_host()
    port = _ui_port()
    httpd = ThreadingHTTPServer((host, port), _Handler)
    print(f"grandMA2 MCP UI listening on http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()

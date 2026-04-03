from __future__ import annotations

import asyncio
import json
import os
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from typing import Any
from urllib.parse import parse_qs, urlparse

from src import server


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


async def _call_json(func, *args, **kwargs) -> dict[str, Any]:
    raw = await func(*args, **kwargs)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"ok": False, "blocked": False, "error": "Tool returned non-JSON output.", "raw": raw}


def _raw_lines(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("raw_response", "")
    return [line.strip() for line in str(raw).splitlines() if line.strip()]


def _parse_fixture_rows(raw_response: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in raw_response.splitlines():
        text = line.strip()
        if not text:
            continue
        match = re.match(r"^\s*(\d+)\s+(.+?)\s*$", text)
        if not match:
            continue
        fixture_id = int(match.group(1))
        rest = match.group(2)
        rows.append({
            "fixture_id": fixture_id,
            "summary": rest,
        })
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


async def _dashboard(page: int) -> dict[str, Any]:
    page_map, fixture_types, location, sessions, users = await asyncio.gather(
        _call_json(server.get_page_map, page),
        _call_json(server.list_fixture_types),
        _call_json(server.get_console_location),
        _call_json(server.inspect_sessions),
        _call_json(server.list_console_users),
    )
    return {
        "page": page,
        "page_map": page_map,
        "fixture_types": fixture_types,
        "console_location": location,
        "sessions": sessions,
        "users": users,
        "stats": {
            "executor_count": len(page_map.get("executors", [])),
            "free_slots": len(page_map.get("free_slots", [])),
            "fixture_type_count": fixture_types.get("entry_count", 0),
        },
    }


async def _executor_detail(page: int, executor_id: int) -> dict[str, Any]:
    status, cues = await asyncio.gather(
        _call_json(server.get_executor_status, executor_id=executor_id, page=page),
        _call_json(server.list_sequence_cues, executor_id=executor_id, executor_page=page),
    )
    return {
        "page": page,
        "executor_id": executor_id,
        "status": status,
        "sequence": cues,
        "parsed_cues": _parse_sequence_cues(cues.get("raw_response", "")),
    }


async def _fixture_inventory(fixture_id: int | None = None) -> dict[str, Any]:
    fixtures, types, worlds, layouts = await asyncio.gather(
        _call_json(server.list_fixtures, fixture_id=fixture_id),
        _call_json(server.list_fixture_types),
        _call_json(server.list_worlds),
        _call_json(server.list_layouts),
    )
    return {
        "fixtures": fixtures,
        "fixture_rows": _parse_fixture_rows(fixtures.get("raw_response", "")),
        "fixture_types": types,
        "worlds": worlds,
        "layouts": layouts,
    }


async def _route_api(method: str, path: str, query: dict[str, list[str]], body: dict[str, Any]) -> tuple[int, bytes]:
    if method == "GET" and path == "/api/config":
        return HTTPStatus.OK, _json_bytes({
            "ui_host": _ui_host(),
            "ui_port": _ui_port(),
            "gma_host": getattr(server, "_GMA_HOST", ""),
            "gma_port": getattr(server, "_GMA_PORT", ""),
            "transport": os.environ.get("GMA_TRANSPORT", "stdio"),
            "scope": os.environ.get("GMA_SCOPE", ""),
        })
    if method == "GET" and path == "/api/dashboard":
        return HTTPStatus.OK, _json_bytes(await _dashboard(_query_int(query, "page", 1)))
    if method == "GET" and path == "/api/executors":
        return HTTPStatus.OK, _json_bytes(await _call_json(server.get_page_map, _query_int(query, "page", 1)))
    if method == "GET" and path == "/api/executor-detail":
        return HTTPStatus.OK, _json_bytes(await _executor_detail(_query_int(query, "page", 1), _query_int(query, "executor_id", 201)))
    if method == "GET" and path == "/api/sequence":
        sequence_id = query.get("sequence_id", [None])[0]
        executor_id = query.get("executor_id", [None])[0]
        payload = await _call_json(
            server.list_sequence_cues,
            sequence_id=int(sequence_id) if sequence_id not in (None, "") else None,
            executor_id=int(executor_id) if executor_id not in (None, "") else None,
            executor_page=_query_int(query, "executor_page", 1),
            cue_id=_query_float(query, "cue_id", 0.0) if "cue_id" in query else None,
        )
        payload["parsed_cues"] = _parse_sequence_cues(payload.get("raw_response", ""))
        return HTTPStatus.OK, _json_bytes(payload)
    if method == "GET" and path == "/api/fixtures":
        fixture_id = query.get("fixture_id", [None])[0]
        payload = await _fixture_inventory(int(fixture_id) if fixture_id not in (None, "") else None)
        return HTTPStatus.OK, _json_bytes(payload)
    if method == "GET" and path == "/api/fixture-types":
        return HTTPStatus.OK, _json_bytes(await _call_json(server.list_fixture_types))
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
    if method == "GET" and path == "/api/console":
        console, telemetry = await asyncio.gather(
            _call_json(server.get_console_location),
            _call_json(server.get_telemetry_report, days=_query_int(query, "days", 1)),
        )
        return HTTPStatus.OK, _json_bytes({"console": console, "telemetry": telemetry})
    return HTTPStatus.NOT_FOUND, _json_bytes({"ok": False, "error": f"Unknown route: {method} {path}"})


class _Handler(BaseHTTPRequestHandler):
    server_version = "MA2AgentUI/1.0"

    def _write(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
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
                status, body = asyncio.run(_route_api("GET", parsed.path, parse_qs(parsed.query), {}))
            except Exception as exc:
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
            status, payload = asyncio.run(_route_api("POST", parsed.path, parse_qs(parsed.query), body))
        except Exception as exc:
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

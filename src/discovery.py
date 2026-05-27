"""Console discovery — UDP broadcast scan for grandMA2 announce packets.

Path A scope: UDP broadcast only. mDNS lives behind the optional ``[mdns]``
install (zeroconf dependency); it is enabled in Path B and returns a note
about the required install when invoked in Path A.

Public API:
    parse_broadcast_packet(packet, source_addr) -> ConsoleCandidate | None
    list_local_networks() -> list[str]
    discover_grandma2_broadcast(network, timeout_seconds) -> list[ConsoleCandidate]
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
from typing import TypedDict

logger = logging.getLogger(__name__)

_BROADCAST_PORT = 6004
_PROBE_PAYLOAD = b"GMA2-PROBE\x00"


class ConsoleCandidate(TypedDict):
    """A discovered grandMA2 console."""

    host: str
    port: int
    name: str | None
    session_name: str | None
    version: str | None
    response_ms: float
    source: str  # "broadcast" | "mdns" | "manual"


def parse_broadcast_packet(
    packet: bytes, source_addr: tuple[str, int]
) -> ConsoleCandidate | None:
    """Parse a GMA2 announce packet — returns None if unrecognised.

    Wire format (documented in MA-Net manual; verify with a real capture):

        b"GMA2-ANNOUNCE\\x01" + fields_joined_by_\\x02 + b"\\x00"

    Each field is ``key=value``; known keys are session, name, ip, port, version.
    """
    if not packet.startswith(b"GMA2-ANNOUNCE"):
        return None
    body = packet.removeprefix(b"GMA2-ANNOUNCE").strip(b"\x00\x01")
    fields: dict[str, str] = {}
    for raw in body.split(b"\x02"):
        if b"=" not in raw:
            continue
        k, _, v = raw.partition(b"=")
        try:
            fields[k.decode("ascii").strip()] = v.decode("utf-8", "replace").strip()
        except Exception:  # noqa: BLE001
            continue
    host = fields.get("ip") or source_addr[0]
    try:
        port = int(fields.get("port", "30000"))
    except ValueError:
        port = 30000
    return ConsoleCandidate(
        host=host,
        port=port,
        name=fields.get("name"),
        session_name=fields.get("session"),
        version=fields.get("version"),
        response_ms=0.0,
        source="broadcast",
    )


def list_local_networks() -> list[str]:
    """Return local CIDR strings derived from active interfaces.

    Best-effort: resolves the local hostname and adds /24 networks for each
    IPv4 it reports. Falls back to loopback if hostname resolution fails.
    """
    nets: set[str] = set()
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, family=socket.AF_INET):
            ip = info[4][0]
            try:
                net = ipaddress.IPv4Network(f"{ip}/24", strict=False)
                nets.add(str(net))
            except ValueError:
                continue
    except Exception as e:  # noqa: BLE001
        logger.debug("list_local_networks fallback: %s", e)
    if not nets:
        nets.add("127.0.0.0/8")
    return sorted(nets)


async def discover_grandma2_broadcast(
    network: str | None = None,
    timeout_seconds: int = 5,
) -> list[ConsoleCandidate]:
    """Send a broadcast probe and collect announce replies for ``timeout_seconds``."""
    loop = asyncio.get_running_loop()
    results: list[ConsoleCandidate] = []

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setblocking(False)
    try:
        sock.bind(("", 0))
    except OSError as e:
        logger.debug("sock.bind failed: %s", e)
        sock.close()
        return []

    target = "255.255.255.255"
    if network:
        try:
            net = ipaddress.IPv4Network(network, strict=False)
            target = str(net.broadcast_address)
        except ValueError:
            logger.warning("invalid network %r; using global broadcast", network)

    try:
        try:
            await loop.sock_sendto(sock, _PROBE_PAYLOAD, (target, _BROADCAST_PORT))
        except (OSError, NotImplementedError, AttributeError):
            # Some platforms / Python builds reject SOCK_DGRAM via asyncio;
            # fall back to a blocking sendto (the socket itself is non-blocking).
            try:
                sock.sendto(_PROBE_PAYLOAD, (target, _BROADCAST_PORT))
            except OSError as e:
                logger.debug("blocking sendto failed: %s", e)
                return []

        deadline = loop.time() + timeout_seconds
        while loop.time() < deadline:
            try:
                data, addr = await asyncio.wait_for(
                    loop.sock_recvfrom(sock, 1500),
                    timeout=max(0.05, deadline - loop.time()),
                )
            except (TimeoutError, asyncio.TimeoutError):
                break
            except (OSError, NotImplementedError, AttributeError) as e:
                logger.debug("sock_recvfrom failed: %s", e)
                break
            candidate = parse_broadcast_packet(data, addr)
            if candidate is not None:
                results.append(candidate)
    finally:
        sock.close()

    return results


__all__ = [
    "parse_broadcast_packet",
    "list_local_networks",
    "discover_grandma2_broadcast",
    "ConsoleCandidate",
]

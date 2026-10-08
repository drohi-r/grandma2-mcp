"""
Telnet Client Module

This module is responsible for establishing Telnet connections with grandMA2,
handling authentication, and sending commands. This is the only module in the
project permitted to directly manipulate Telnet.

According to coding-standards.md, the Telnet client is the only component that can:
- Open connections
- Execute login commands
- Perform reconnection logic
- Send raw MA commands

Uses telnetlib3 (based on asyncio) to replace the deprecated telnetlib module.
"""

import asyncio
import contextlib
import functools
import logging
import re
from collections.abc import Iterator
from contextvars import ContextVar
from typing import Any

import telnetlib3

# Configure logger
logger = logging.getLogger(__name__)

# A reply is complete once the console reprints its prompt: "[Channel]>" or "Fixture>".
_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
_PROMPT_TAIL_RE = re.compile(r"(\[[^\]\r\n]+\]|[A-Za-z][\w .:/-]*)>/?\s*$")

# Extra time to wait for the rest of a reply that has not ended in a prompt yet.
_SETTLE_TIMEOUT = 0.5

# Per-tool-call sink for transport problems (set by the server's tool wrapper).
_transport_warnings: ContextVar[list[str] | None] = ContextVar("transport_warnings", default=None)


def record_transport_warning(message: str) -> None:
    """Record a transport problem for the tool call in progress (no-op outside one)."""
    sink = _transport_warnings.get()
    if sink is not None and message not in sink:
        sink.append(message)


@contextlib.contextmanager
def collect_transport_warnings() -> Iterator[list[str]]:
    """Collect transport warnings raised by Telnet reads inside the block."""
    sink: list[str] = []
    token = _transport_warnings.set(sink)
    try:
        yield sink
    finally:
        _transport_warnings.reset(token)


def ends_with_prompt(text: str) -> bool:
    return bool(_PROMPT_TAIL_RE.search(_ANSI_RE.sub("", text)))


def hold_connection(client: Any) -> contextlib.AbstractAsyncContextManager:
    """``client.exclusive()`` for real clients; a no-op for mocks/mock-mode clients."""
    if callable(getattr(type(client), "exclusive", None)):
        return client.exclusive()
    return contextlib.nullcontext()


# The console echoes each command as "Executing : <canonical keyword> ...", with
# ANSI colour codes between the words (live, onPC 3.9.60.50).
_ECHO_MARKER_RE = re.compile(r"Executing")
_ECHO_KEYWORD_RE = re.compile(r"^\s*:\s*(\S+)")


@functools.lru_cache(maxsize=256)
def _keyword_names(token: str) -> frozenset[str]:
    """The typed first token plus its canonical MA2 keyword ("cd" → "changedest")."""
    names = {token.lower()}
    with contextlib.suppress(Exception):
        from src.vocab import classify_token

        canonical = classify_token(token, _vocab_spec()).canonical
        if canonical:
            names.add(canonical.lower())
    return frozenset(names)


@functools.lru_cache(maxsize=1)
def _vocab_spec():
    from src.vocab import build_v39_spec

    return build_v39_spec()


def frame_reply(raw: str, command: str) -> str:
    """Start the reply at the console's echo of *command*.

    Output before that echo belongs to something else — another session's
    commands, or the tail of the previous reply — and is dropped. When no echo
    names the command's keyword, the reply is returned unchanged.
    """
    tokens = command.split()
    if not tokens or not raw:
        return raw
    wanted = _keyword_names(tokens[0])
    for marker in _ECHO_MARKER_RE.finditer(raw):
        line_end = raw.find("\n", marker.end())
        echoed = _ANSI_RE.sub("", raw[marker.end(): line_end if line_end != -1 else None])
        m = _ECHO_KEYWORD_RE.match(echoed)
        if m and m.group(1).lower() in wanted:
            return raw[marker.start():]
    return raw


class GMA2TelnetClient:
    """
    grandMA2 Telnet Connection Client (Async Version)

    Provides Telnet connection management functionality for grandMA2 onPC/Console,
    including connection establishment, authentication, command sending, and
    reconnection logic.

    This version uses telnetlib3 and asyncio to avoid the deprecation of telnetlib
    in Python 3.13.

    Attributes:
        host: grandMA2 host IP address
        port: Telnet port (default 30000, 30001 is read-only)
        user: Login username
        password: Login password

    Example (Async):
        >>> async with GMA2TelnetClient(host="192.168.1.100") as client:
        ...     await client.send_command("selfix fixture 1 thru 10")

    Example (Sync - using run_sync method):
        >>> client = GMA2TelnetClient(host="192.168.1.100")
        >>> client.run_sync(client.connect())
        >>> client.run_sync(client.login())
        >>> client.run_sync(client.send_command("selfix fixture 1 thru 10"))
        >>> client.run_sync(client.disconnect())
    """

    # Default configuration values
    DEFAULT_PORT = 30000
    DEFAULT_USER = "administrator"
    DEFAULT_PASSWORD = "admin"

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_PORT,
        user: str = DEFAULT_USER,
        password: str = DEFAULT_PASSWORD,
    ):
        """
        Initialize Telnet Client.

        Args:
            host: grandMA2 host IP address
            port: Telnet port (default 30000)
            user: Login username (default "administrator")
            password: Login password (default "admin")
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        # telnetlib3 uses reader/writer pattern
        self._reader: Any | None = None
        self._writer: Any | None = None
        self._connection: Any | None = None  # Kept for compatibility checks
        # True only when the console explicitly refused the credentials.
        self.login_rejected = False
        # One exchange at a time per connection: concurrent tool calls would
        # otherwise interleave writes and read each other's replies.
        self._lock: asyncio.Lock | None = None
        self._lock_owner: asyncio.Task | None = None
        self._lock_depth = 0

        logger.debug(
            f"GMA2TelnetClient initialized: host={host}, port={port}, user={user}"
        )

    @property
    def is_connected(self) -> bool:
        """Check whether the telnet connection appears healthy."""
        if self._writer is None or self._connection is None:
            return False
        return not self._socket_closed()

    @contextlib.asynccontextmanager
    async def exclusive(self):
        """Hold the connection for a multi-command sequence (re-entrant per task).

        Every send already takes this lock; wrap a ``cd …; list; cd /`` style
        sequence in it so no other tool call lands in the middle.
        """
        task = asyncio.current_task()
        if self._lock_owner is task and task is not None:
            self._lock_depth += 1
            try:
                yield self
            finally:
                self._lock_depth -= 1
            return
        if self._lock is None:
            self._lock = asyncio.Lock()
        async with self._lock:
            self._lock_owner, self._lock_depth = task, 1
            try:
                yield self
            finally:
                self._lock_owner, self._lock_depth = None, 0

    async def _drain(self, max_reads: int = 50) -> str:
        """Discard output that arrived since the last exchange (echo of other
        sessions, a late tail of the previous reply) so it can't leak in."""
        stale: list[str] = []
        for _ in range(max_reads):
            try:
                chunk = await asyncio.wait_for(self._reader.read(4096), timeout=0.05)
            except TimeoutError:
                break
            if not chunk:
                break
            stale.append(chunk)
        return "".join(stale)

    async def ping(self) -> None:
        """Keep the socket alive and consume whatever the console printed meanwhile."""
        async with self.exclusive():
            if self._writer is None or self._reader is None:
                return
            self._writer.write("\r\n")
            await asyncio.sleep(0.1)
            await self._drain()

    def _socket_closed(self) -> bool:
        # Strict ``is True``: only a real reader/writer answers with a bool.
        at_eof = getattr(self._reader, "at_eof", None)
        is_closing = getattr(self._writer, "is_closing", None)
        return (callable(at_eof) and at_eof() is True) or (callable(is_closing) and is_closing() is True)

    def _mark_dropped(self) -> None:
        with contextlib.suppress(Exception):
            if self._writer is not None:
                self._writer.close()
        self._writer = None
        self._reader = None
        self._connection = None

    def run_sync(self, coro: Any) -> Any:
        """
        Helper function to run async methods in synchronous environments.

        Args:
            coro: The coroutine to execute

        Returns:
            The result of the coroutine execution
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            # Already inside an async context — cannot use asyncio.run()
            # Create a new task instead (caller must handle this case)
            raise RuntimeError(
                "Cannot call run_sync() from within a running event loop. "
                "Use 'await' directly instead."
            )
        return asyncio.run(coro)

    async def connect(self) -> None:
        """
        Establish a Telnet connection (async).

        Raises:
            ConnectionError: Unable to connect to grandMA2 host
        """
        logger.info(f"Connecting to {self.host}:{self.port}...")

        try:
            # telnetlib3 uses open_connection to establish connection
            self._reader, self._writer = await telnetlib3.open_connection(
                host=self.host,
                port=self.port,
            )
            # Mark connection state
            self._connection = True
            # Wait for connection to stabilize
            await asyncio.sleep(0.5)
            logger.info(f"Successfully connected to {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            raise ConnectionError(f"Unable to connect to {self.host}:{self.port}: {e}") from e

    async def login(self) -> bool:
        """
        Perform login authentication (async).

        Returns:
            bool: True if a response was received (likely successful),
                  False if no response was received (login may have failed)

        Raises:
            RuntimeError: Connection not established
        """
        if self._writer is None or self._reader is None:
            raise RuntimeError("Connection not established, call connect() first")

        logger.info(f"Logging in as {self.user}...")
        self.login_rejected = False

        # Build login command (password is not logged)
        login_cmd = f'login "{self.user}" "{self.password}"\r\n'
        self._writer.write(login_cmd)

        # Wait for login response
        await asyncio.sleep(0.5)

        # Attempt to read response (non-blocking)
        try:
            response = await asyncio.wait_for(
                self._reader.read(1024),
                timeout=1.0,
            )
            logger.debug("Login response: %d bytes received", len(response) if response else 0)
            # Check for known error patterns in the login response
            if response:
                text = (response.decode("utf-8", errors="replace") if isinstance(response, bytes) else response).lower()
                _ERROR_PATTERNS = ("error #", "login failed", "invalid", "denied", "not allowed")
                for pattern in _ERROR_PATTERNS:
                    if pattern in text:
                        logger.error("Login rejected — response contains %r: %s", pattern, text.strip())
                        self.login_rejected = True
                        return False
            logger.info("Login completed (response received)")
            return True
        except TimeoutError:
            logger.warning(
                "Login response timeout — could not verify login success. "
                "grandMA2 may not send a response on successful login, "
                "but this could also indicate invalid credentials."
            )
            return False

    async def send_command(self, command: str, delay: float = 0.3) -> None:
        """
        Send a command to grandMA2 (async).

        Args:
            command: MA command to send
            delay: Wait time in seconds after sending command to allow grandMA2 to process

        Raises:
            RuntimeError: Connection not established
        """
        if self._writer is None:
            raise RuntimeError("Connection not established, call connect() first")

        # Sanitize: strip embedded line breaks to prevent command injection
        command = command.replace("\r", "").replace("\n", "")

        logger.debug(f"Sending command: {command}")

        async with self.exclusive():
            # Send command (automatically add newline)
            full_command = f"{command}\r\n"
            self._writer.write(full_command)

            # Wait for grandMA2 to process command
            await asyncio.sleep(delay)
        logger.debug(f"Command sent, waiting {delay} seconds")

    async def send_command_with_response(
        self, command: str, timeout: float = 2.0, delay: float = 0.3,
        subsequent_timeout: float = 0.10, until_prompt: bool = False,
    ) -> str:
        """
        Send a command to grandMA2 and read the response (async).

        Sends a command and reads the response from grandMA2. Suitable for
        commands that produce output such as list and info.

        Args:
            command: MA command to send
            timeout: Maximum wait time for response in seconds
            delay: Initial delay after sending command
            subsequent_timeout: Timeout for follow-up reads after the first chunk
            until_prompt: Return as soon as the reply ends in the console prompt
                instead of waiting for the output to go quiet (batch speed).

        Returns:
            str: Response from grandMA2, starting at the echo of *command*
                when the console echoed it (earlier output is dropped)

        Raises:
            RuntimeError: Connection not established
        """
        if self._writer is None or self._reader is None:
            raise RuntimeError("Connection not established, call connect() first")

        # Sanitize: strip embedded line breaks to prevent command injection
        command = command.replace("\r", "").replace("\n", "")

        logger.debug(f"Sending command with response: {command}")

        async with self.exclusive():
            return await self._exchange(command, timeout, delay, subsequent_timeout, until_prompt)

    async def _exchange(
        self, command: str, timeout: float, delay: float,
        subsequent_timeout: float, until_prompt: bool,
    ) -> str:
        """One command → one reply. Caller holds ``exclusive()``."""
        if self._socket_closed():
            self._mark_dropped()
            raise ConnectionError("Console closed the Telnet connection; it will reconnect on the next call")
        if self._writer is None or self._reader is None:
            raise ConnectionError("Console connection was dropped; it will reconnect on the next call")

        # Clear any pending data
        await self._drain()

        # Send command
        full_command = f"{command}\r\n"
        self._writer.write(full_command)

        # Wait for grandMA2 to process
        await asyncio.sleep(delay)

        # Read until the output goes quiet. If it went quiet before the console
        # reprinted its prompt, wait once more (settle) for the rest of the reply.
        response_parts: list[str] = []
        settled = False
        eof = False
        try:
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        self._reader.read(4096), timeout=timeout
                    )
                except TimeoutError:
                    if response_parts and not settled and not ends_with_prompt("".join(response_parts)):
                        settled = True
                        timeout = _SETTLE_TIMEOUT
                        continue
                    break
                if chunk:
                    response_parts.append(chunk)
                    # Shorten timeout for subsequent reads
                    timeout = subsequent_timeout
                    if until_prompt and ends_with_prompt("".join(response_parts)):
                        break
                else:
                    eof = self._socket_closed()
                    break
        except Exception as e:
            logger.warning(f"Error reading response: {e}")
            record_transport_warning(f"read error: {e}")

        response = "".join(response_parts)
        logger.debug(f"Response received: {len(response)} characters")

        if eof:
            self._mark_dropped()
            if not response:
                raise ConnectionError("Console closed the Telnet connection; it will reconnect on the next call")
            record_transport_warning("connection closed while reading; reply may be cut off")
        elif not response:
            record_transport_warning("no reply from console within timeout")
        elif not ends_with_prompt(response):
            record_transport_warning("reply ended without a console prompt; it may be cut off")
        return frame_reply(response, command)

    async def disconnect(self) -> None:
        """Close the Telnet connection (async)."""
        if self._writer is not None:
            logger.info("Closing connection...")
            self._writer.close()
            self._writer = None
            self._reader = None
            self._connection = None
            logger.info("Connection closed")

    async def __aenter__(self) -> "GMA2TelnetClient":
        """Async context manager entry point: establish connection and login."""
        await self.connect()
        await self.login()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit point: close connection."""
        await self.disconnect()

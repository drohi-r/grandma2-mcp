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
import logging
from typing import Any

import telnetlib3

# Configure logger
logger = logging.getLogger(__name__)


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

        logger.debug(
            f"GMA2TelnetClient initialized: host={host}, port={port}, user={user}"
        )

    @property
    def is_connected(self) -> bool:
        """Check whether the telnet connection appears healthy."""
        return self._writer is not None and self._connection is not None

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

        # Send command (automatically add newline)
        full_command = f"{command}\r\n"
        self._writer.write(full_command)

        # Wait for grandMA2 to process command
        await asyncio.sleep(delay)
        logger.debug(f"Command sent, waiting {delay} seconds")

    async def send_command_with_response(
        self, command: str, timeout: float = 2.0, delay: float = 0.3,
        subsequent_timeout: float = 0.10,
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

        Returns:
            str: Response from grandMA2

        Raises:
            RuntimeError: Connection not established
        """
        if self._writer is None or self._reader is None:
            raise RuntimeError("Connection not established, call connect() first")

        # Sanitize: strip embedded line breaks to prevent command injection
        command = command.replace("\r", "").replace("\n", "")

        logger.debug(f"Sending command with response: {command}")

        # Clear any pending data
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(self._reader.read(4096), timeout=0.1)

        # Send command
        full_command = f"{command}\r\n"
        self._writer.write(full_command)

        # Wait for grandMA2 to process
        await asyncio.sleep(delay)

        # Read response
        response_parts = []
        try:
            # Continue reading until no more data
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        self._reader.read(4096), timeout=timeout
                    )
                    if chunk:
                        response_parts.append(chunk)
                        # Shorten timeout for subsequent reads
                        timeout = subsequent_timeout
                    else:
                        break
                except TimeoutError:
                    break
        except Exception as e:
            logger.warning(f"Error reading response: {e}")

        response = "".join(response_parts)
        logger.debug(f"Response received: {len(response)} characters")
        return response

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

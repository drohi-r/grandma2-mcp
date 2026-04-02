"""
MCP Tools Module

This module manages the global GMA2 telnet client instance used by
the MCP server tools defined in server.py.
"""

import logging

logger = logging.getLogger(__name__)

# Global GMA2 client instance
# This will be initialized in server.py
_gma2_client = None


def set_gma2_client(client) -> None:
    """
    Set the global GMA2 client instance.

    Args:
        client: GMA2TelnetClient instance
    """
    global _gma2_client
    _gma2_client = client



"""
Login test script for grandMA2 Telnet connection.

Uses GMA2TelnetClient (async, telnetlib3) instead of the deprecated telnetlib module.
"""

import asyncio

import dotenv

from src.telnet_client import GMA2TelnetClient

GMA_HOST = dotenv.get_key(".env", "GMA_HOST") or "127.0.0.1"
GMA_PORT = int(dotenv.get_key(".env", "GMA_PORT") or "30000")
GMA_USER = dotenv.get_key(".env", "GMA_USER") or "administrator"
GMA_PASSWORD = dotenv.get_key(".env", "GMA_PASSWORD") or "admin"


async def login():
    """Login to grandMA2 using GMA2TelnetClient."""
    client = GMA2TelnetClient(
        host=GMA_HOST,
        port=GMA_PORT,
        user=GMA_USER,
        password=GMA_PASSWORD,
    )

    try:
        await client.connect()
        print(f"Connected to {GMA_HOST}:{GMA_PORT}")

        result = await client.login()
        print(f"Login result: {result}")

    except ConnectionError as e:
        print(f"Connection error: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.disconnect()


def main():
    print("Hello from gma2-mcp!")
    print(f"Connecting to {GMA_HOST}:{GMA_PORT} as {GMA_USER}...")
    asyncio.run(login())


if __name__ == "__main__":
    main()

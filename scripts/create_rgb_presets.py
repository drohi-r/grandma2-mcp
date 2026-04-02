"""
Create universal R, G, B color presets on grandMA2 onPC.

Stores three universal Color presets:
  Preset 4.3  Red    (ColorRgb1=100, ColorRgb2=0,   ColorRgb3=0)
  Preset 4.4  Green  (ColorRgb1=0,   ColorRgb2=100, ColorRgb3=0)
  Preset 4.5  Blue   (ColorRgb1=0,   ColorRgb2=0,   ColorRgb3=100)

Uses /universal so the preset is not selective to specific fixtures.
"""

import asyncio
import os

import dotenv

from src.telnet_client import GMA2TelnetClient

GMA_HOST = dotenv.get_key(".env", "GMA_HOST") or "127.0.0.1"
GMA_PORT = int(dotenv.get_key(".env", "GMA_PORT") or "30000")
GMA_USER = dotenv.get_key(".env", "GMA_USER") or "administrator"
GMA_PASSWORD = dotenv.get_key(".env", "GMA_PASSWORD") or ""

# Color presets: (slot, label, r, g, b) — values are 0-100
RGB_PRESETS = [
    (3, "Red",   100,   0,   0),
    (4, "Green",   0, 100,   0),
    (5, "Blue",    0,   0, 100),
]


async def send(client: GMA2TelnetClient, cmd: str) -> str:
    response = await client.send_command_with_response(cmd)
    safe_resp = response.encode("ascii", errors="replace").decode("ascii")
    print(f"  CMD: {cmd!r}")
    print(f"  RSP: {safe_resp[:120]}")
    return response


async def create_rgb_presets() -> None:
    client = GMA2TelnetClient(
        host=GMA_HOST,
        port=GMA_PORT,
        user=GMA_USER,
        password=GMA_PASSWORD,
    )

    await client.connect()
    print(f"Connected to {GMA_HOST}:{GMA_PORT}")
    await client.login()
    print("Logged in\n")

    # Select all fixtures so the preset captures fixture-type data for universal storage
    print("--- Selecting all fixtures ---")
    await send(client, "SelFix 1 Thru 999")

    for slot, label, r, g, b in RGB_PRESETS:
        print(f"\n--- Creating preset {label} (Color 4.{slot}) ---")

        # Clear programmer before setting new values
        await send(client, "Clear")

        # Set RGB attributes in programmer
        await send(client, f'attribute "ColorRgb1" at {r}')
        await send(client, f'attribute "ColorRgb2" at {g}')
        await send(client, f'attribute "ColorRgb3" at {b}')

        # Store as universal color preset (overwrite if slot exists)
        await send(client, f"Store Preset 4.{slot} /universal /overwrite /noconfirm")

        # Label the preset
        await send(client, f'Label Preset 4.{slot} "{label}"')

    # Clear programmer on exit
    print("\n--- Clearing programmer ---")
    await send(client, "Clear")

    await client.disconnect()
    print("\nDone. R/G/B universal color presets stored at Preset 4.3 / 4.4 / 4.5")


def main() -> None:
    asyncio.run(create_rgb_presets())


if __name__ == "__main__":
    main()

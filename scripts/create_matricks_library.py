"""
Create a full MAtricks combinatorial library on grandMA2 onPC.

Generates every combination of Wings × Groups × Blocks × Interleave
(values 0 to --max-value, default 4) and stores each as a named MAtricks
pool item via XML import, then applies color coding by Wings value.

With max_value=4: 5^4 = 625 pool items, named W0-G0-B0-I0 through W4-G4-B4-I4.

Phase 1: XML import (instant) — creates all pool entries with properties and names.
Phase 2: Color application (~3 min) — sets appearance color per Wings value.

Usage:
    # Quick test (2^4 = 16 items)
    python -m scripts.create_matricks_library --max-value 1

    # Full run (625 items)
    python -m scripts.create_matricks_library --max-value 4

    # Generate XML only (no telnet)
    python -m scripts.create_matricks_library --xml-only

    # Import only, skip color application
    python -m scripts.create_matricks_library --no-color
"""

import argparse
import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path

import dotenv

from src.telnet_client import GMA2TelnetClient

GMA_HOST = dotenv.get_key(".env", "GMA_HOST") or "127.0.0.1"
GMA_PORT = int(dotenv.get_key(".env", "GMA_PORT") or "30000")
GMA_USER = dotenv.get_key(".env", "GMA_USER") or "administrator"
GMA_PASSWORD = dotenv.get_key(".env", "GMA_PASSWORD") or ""

# MA2 matricks XML directory
MATRICKS_DIR = Path(
    "C:/ProgramData/MA Lighting Technologies/grandma/gma2_V_3.9.60/matricks"
)

XML_FILENAME = "matricks_combinatorial_library"

# 25-color scheme: Wings=hue (5 hues), Groups=brightness (5 levels)
# MA2 HSB: hue 0-360, saturation 0-100, brightness 0-100
WINGS_HUES = {0: 0, 1: 72, 2: 144, 3: 216, 4: 288}
GROUPS_BRIGHTNESS = {0: 100, 1: 80, 2: 60, 3: 45, 4: 30}


def get_matricks_color(wings: int, groups: int) -> tuple[int, int, int]:
    """Return (hue, saturation, brightness) for a Wings×Groups combo."""
    return (WINGS_HUES.get(wings, 0), 100, GROUPS_BRIGHTNESS.get(groups, 100))


def hsb_to_hex(hue: int, saturation: int, brightness: int) -> str:
    """Convert HSB (hue 0-360, sat 0-100, bright 0-100) to 6-digit hex color."""
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(hue / 360, saturation / 100, brightness / 100)
    return f"{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def generate_xml(max_value: int) -> tuple[str, int]:
    """Generate MAtricks XML with all combinatorial entries.

    Returns:
        Tuple of (xml_string, entry_count)
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<MA xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xmlns="http://schemas.malighting.de/grandma2/xml/MA"'
        ' xsi:schemaLocation="http://schemas.malighting.de/grandma2/xml/MA'
        ' http://schemas.malighting.de/grandma2/xml/3.9.60/MA.xsd"'
        ' major_vers="3" minor_vers="9" stream_vers="60">',
        f'\t<Info datetime="{now}" showfile="claude_ma2_ctrl" />',
    ]

    index = 0  # 0-based index in XML
    for w in range(max_value + 1):
        for g in range(max_value + 1):
            h, s, br = get_matricks_color(w, g)
            hex_color = hsb_to_hex(h, s, br)
            for b in range(max_value + 1):
                for i in range(max_value + 1):
                    name = f"W{w}-G{g}-B{b}-I{i}"
                    lines.append(
                        f'\t<Matrix index="{index}" name="{name}">'
                    )
                    lines.append(
                        f'\t\t<Appearance Color="{hex_color}" />'
                    )
                    lines.append(
                        f'\t\t<Settings wings="{w}" group_x="{g}"'
                        f' block_x="{b}" interleave="{i}" />'
                    )
                    lines.append("\t</Matrix>")
                    index += 1

    lines.append("</MA>")
    return "\n".join(lines), index


async def apply_colors(
    client: GMA2TelnetClient,
    max_value: int,
    start_slot: int,
    delay: float = 0.3,
) -> None:
    """Apply 25-color HSB appearance to MAtricks pool items (Wings×Groups)."""
    total = (max_value + 1) ** 4
    slot = start_slot
    done = 0
    t0 = time.time()

    print(f"\nApplying 25-color scheme to {total} pool items...")

    for w in range(max_value + 1):
        for g in range(max_value + 1):
            h, s, br = get_matricks_color(w, g)
            entries_per_combo = (max_value + 1) ** 2  # block × interleave

            for _ in range(entries_per_combo):
                cmd = f"appearance matricks {slot} /h={h} /s={s} /br={br}"
                await client.send_command_with_response(cmd)
                await asyncio.sleep(delay)
                slot += 1
                done += 1

            elapsed = time.time() - t0
            print(f"  W={w} G={g} colored ({done}/{total}, {elapsed:.0f}s elapsed)")

    elapsed = time.time() - t0
    print(f"Color application complete in {elapsed:.0f}s")


async def import_and_color(
    max_value: int,
    start_slot: int = 2,
    apply_color: bool = True,
    delay: float = 0.3,
) -> None:
    """Connect to MA2, import XML, and optionally apply colors."""
    client = GMA2TelnetClient(
        host=GMA_HOST,
        port=GMA_PORT,
        user=GMA_USER,
        password=GMA_PASSWORD,
    )

    await client.connect()
    print(f"Connected to {GMA_HOST}:{GMA_PORT}")
    await client.login()
    print("Logged in")

    # Phase 1: Import XML
    cmd = f'import "{XML_FILENAME}" at matricks {start_slot}'
    print(f"\nPhase 1 — Importing: {cmd}")
    response = await client.send_command_with_response(cmd)
    print(f"Response: {response[:500]}")

    # Phase 2: Apply colors
    if apply_color:
        print("\nPhase 2 — Applying colors by Wings value...")
        await apply_colors(client, max_value, start_slot, delay)

    await client.disconnect()


async def color_only(
    max_value: int,
    start_slot: int = 2,
    delay: float = 0.3,
) -> None:
    """Connect to MA2 and apply colors only (no import)."""
    client = GMA2TelnetClient(
        host=GMA_HOST,
        port=GMA_PORT,
        user=GMA_USER,
        password=GMA_PASSWORD,
    )

    await client.connect()
    print(f"Connected to {GMA_HOST}:{GMA_PORT}")
    await client.login()
    print("Logged in")

    await apply_colors(client, max_value, start_slot, delay)
    await client.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create full MAtricks combinatorial library on grandMA2"
    )
    parser.add_argument(
        "--max-value", type=int, default=4,
        help="Maximum value for each property (default: 4, gives 5^4=625 items)"
    )
    parser.add_argument(
        "--start-slot", type=int, default=2,
        help="First pool slot to import into (default: 2, slot 1 is Reset)"
    )
    parser.add_argument(
        "--xml-only", action="store_true",
        help="Generate XML file only, don't import via telnet"
    )
    parser.add_argument(
        "--no-color", action="store_true",
        help="Skip color application after import"
    )
    parser.add_argument(
        "--color-only", action="store_true",
        help="Apply colors only, skip XML generation and import"
    )
    parser.add_argument(
        "--delay", type=float, default=0.3,
        help="Delay between appearance commands in seconds (default: 0.3)"
    )
    args = parser.parse_args()

    count = (args.max_value + 1) ** 4

    if args.color_only:
        # Apply colors only — no XML generation or import
        print(f"Applying colors to {count} pool items (slots {args.start_slot}-{args.start_slot + count - 1})...")
        asyncio.run(color_only(
            max_value=args.max_value,
            start_slot=args.start_slot,
            delay=args.delay,
        ))
        print(f"\nDone. Color scheme: Wings 0=White, 1=Red, 2=Green, 3=Blue, 4=Yellow")
        return

    # Generate XML
    xml_content, count = generate_xml(args.max_value)
    xml_path = MATRICKS_DIR / f"{XML_FILENAME}.xml"

    print(f"Writing {count} MAtricks entries to {xml_path}")
    xml_path.write_text(xml_content, encoding="utf-8")
    print(f"XML file written ({len(xml_content)} bytes)")

    if args.xml_only:
        print("\n--xml-only: Skipping telnet import.")
        return

    # Import and optionally color
    asyncio.run(import_and_color(
        max_value=args.max_value,
        start_slot=args.start_slot,
        apply_color=not args.no_color,
        delay=args.delay,
    ))

    last_slot = args.start_slot + count - 1
    print(f"\nDone. {count} MAtricks pool items at slots {args.start_slot}-{last_slot}")
    if not args.no_color:
        print("Color scheme: Wings 0=White, 1=Red, 2=Green, 3=Blue, 4=Yellow")


if __name__ == "__main__":
    main()

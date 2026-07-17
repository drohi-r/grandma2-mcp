"""Live Test 1 — divergence tools, single process (baseline is module-global)."""
import asyncio, json

from src.server import get_client, snapshot_console_baseline, detect_console_divergence


async def main():
    c = await get_client()
    out = {}

    out["baseline"] = json.loads(await snapshot_console_baseline())
    out["clean"] = json.loads(await detect_console_divergence())

    # Desk-side change 1: fader page
    await c.send_command_with_response("Page 2")
    out["after_page_change"] = json.loads(await detect_console_divergence())

    # Desk-side change 2: store a new group
    await c.send_command_with_response("ClearAll")
    await c.send_command_with_response("Fixture 1 Thru 3")
    await c.send_command_with_response("Store Group 99 /o")
    await c.send_command_with_response("ClearAll")
    out["after_group_store"] = json.loads(await detect_console_divergence())

    # Desk-side change 3: delete it again, restore page
    await c.send_command_with_response("Delete Group 99 /nc")
    await c.send_command_with_response("Page 1")
    out["after_group_delete"] = json.loads(await detect_console_divergence())

    print(json.dumps(out, indent=2))


asyncio.run(main())

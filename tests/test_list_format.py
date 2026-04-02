"""Capture raw list output at key locations to debug cd index parsing."""

import asyncio

from dotenv import get_key

from src.prompt_parser import _strip_ansi, parse_list_output, parse_prompt
from src.telnet_client import GMA2TelnetClient


async def main():
    host = get_key(".env", "GMA_HOST") or "127.0.0.1"
    user = get_key(".env", "GMA_USER") or "administrator"
    pw = get_key(".env", "GMA_PASSWORD") or "admin"

    client = GMA2TelnetClient(host=host, port=30000, user=user, password=pw)
    await client.connect()
    ok = await client.login()
    print(f"LOGIN: {'OK' if ok else 'FAILED'}\n")

    async def cd(target):
        raw = await client.send_command_with_response(f"cd {target}", timeout=2.0, delay=0.3)
        p = parse_prompt(raw)
        print(f"cd {target} -> location={p.location!r}")
        return p.location

    async def dump_list(label):
        raw = await client.send_command_with_response("list", timeout=3.0, delay=0.5)
        stripped = _strip_ansi(raw)
        parsed = parse_list_output(raw)
        print(f"\n=== LIST at {label} ===")
        print(f"Parsed: {len(parsed.entries)} entries")
        # Print raw lines (cleaned)
        for line in stripped.strip().splitlines():
            s = line.strip()
            if s and not s.endswith(">") and not s.startswith("Executing"):
                print(f"  RAW: {s!r}")
        # Print parsed entries
        for e in parsed.entries[:10]:
            print(f"  PARSED: type={e.object_type!r} id={e.object_id!r} name={e.name!r}")
        if len(parsed.entries) > 10:
            print(f"  ... ({len(parsed.entries) - 10} more)")
        print()
        return parsed.entries

    # Test 1: Root list (check if index 12 exists)
    await cd("/")
    entries = await dump_list("ROOT")
    root_ids = [e.object_id for e in entries]
    print(f"Root IDs: {root_ids}")
    missing = [i for i in range(1, 43) if str(i) not in root_ids]
    print(f"Missing root indexes: {missing}\n")

    # Test 2: Inside Forms/Release 2 - the SubForm bug
    await cd("/")
    await cd("23")       # Forms
    await cd("2")        # Release 2
    await dump_list("Forms/Release 2")

    # Also check Forms/Stomp 1 (which works with cd 1)
    await cd("..")
    await cd("1")        # Stomp 1
    await dump_list("Forms/Stomp 1")

    # Test 3: Inside a FixtureType to check the cd 4 gap
    await cd("/")
    await cd("10")       # LiveSetup
    await cd("3")        # FixtureTypes 3
    await cd("1")        # Universal Attributes
    await dump_list("LiveSetup/FixtureTypes/Universal Attributes")

    # Test 4: Verify cd 4 is genuinely missing
    await cd("/")
    await cd("10")
    await cd("3")
    await cd("1")
    loc4 = await cd("4")  # Try cd 4 inside FixtureType
    print(f"\ncd 4 inside FixtureType -> location={loc4!r}")
    if loc4 is None:
        print("  (cd 4 is genuinely missing - not a parser bug)")
    else:
        print("  (cd 4 EXISTS - we have a parser bug!)")

    # Test 5: DMX_Protocols children (which skip 1 and 2)
    await cd("/")
    await cd("4")        # DMX_Protocols
    await dump_list("DMX_Protocols")

    # Try cd 1 and cd 2 in DMX_Protocols
    print("\nDMX_Protocols manual cd test:")
    await cd("/")
    await cd("4")
    loc1 = await cd("1")
    print(f"  cd 1 inside DMX_Protocols -> {loc1!r}")
    await cd("..")
    loc2 = await cd("2")
    print(f"  cd 2 inside DMX_Protocols -> {loc2!r}")

    await client.disconnect()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())

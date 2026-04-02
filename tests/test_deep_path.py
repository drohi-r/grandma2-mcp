"""Quick validation: login, cd 23.3.1.1 deep path, full list output at each level."""

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
    print(f"LOGIN: {'OK' if ok else 'FAILED'}  (host={host}, user={user})")
    print()

    async def cd(target):
        raw = await client.send_command_with_response(
            f"cd {target}", timeout=2.0, delay=0.3
        )
        p = parse_prompt(raw)
        print(f"cd {target} -> location={p.location!r}")
        return p.location

    async def do_list():
        raw = await client.send_command_with_response("list", timeout=3.0, delay=0.5)
        stripped = _strip_ansi(raw)
        parsed = parse_list_output(raw)
        lines = [line.strip() for line in stripped.strip().splitlines() if line.strip()]
        # Filter out command echo and prompt lines
        data_lines = [
            line
            for line in lines
            if not line.startswith("Executing")
            and not line.rstrip().endswith(">")
            and "WARNING" not in line
        ]
        print(f"  list -> {len(parsed.entries)} parsed, {len(data_lines)} raw lines:")
        for line in data_lines:
            print(f"    | {line}")
        print()
        return parsed.entries

    # Start at root
    print("=== cd / (root) ===")
    await cd("/")

    # Navigate deep: cd 23 -> cd 3 -> cd 1 -> cd 1
    path_steps = [23, 3, 1, 1]
    cumulative = []
    for step in path_steps:
        cumulative.append(str(step))
        path_label = ".".join(cumulative)
        print(f"=== cd {path_label} ===")
        await cd(str(step))
        entries = await do_list()

        # If no entries, try one more level to confirm it's a true leaf
        if not entries:
            test_loc = await cd("1")
            raw = await client.send_command_with_response("cd ..", timeout=2.0, delay=0.3)
            p = parse_prompt(raw)
            if test_loc == p.location or test_loc is None:
                print("  (confirmed leaf - cd 1 was a MISS)")
            else:
                print(f"  (NOT a leaf - cd 1 moved to {test_loc!r})")
                # go back
                await cd("..")
            print()

    # Backtrack with cd ..
    print("=== BACKTRACK ===")
    for _i in range(len(path_steps) + 1):
        raw = await client.send_command_with_response("cd ..", timeout=2.0, delay=0.3)
        stripped = _strip_ansi(raw)
        p = parse_prompt(raw)
        has_error = "Error" in stripped
        status = "ERROR #72 (at root)" if has_error else "OK"
        print(f"  cd .. -> {p.location!r}  ({status})")
        if has_error or p.location == "Fixture":
            print("  (back at root)")
            break

    await client.disconnect()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())

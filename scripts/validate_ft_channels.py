"""
Live telnet validation: Navigate FT tree, capture ChannelType data per Module,
validate CD index order vs DMX Coarse channel order.
Also captures prompt at each CD navigation level.
"""

import asyncio
import json
import re
import sys


async def validate_ft_channels():
    from src.telnet_client import GMA2TelnetClient
    from src.prompt_parser import parse_prompt

    client = GMA2TelnetClient("127.0.0.1", 30000)
    await client.connect()
    await client.login()

    all_results = []
    prompt_trail = []

    # Navigate to FixtureTypes
    # cd / -> root
    resp = await client.send_command_with_response("cd /")
    p = parse_prompt(resp)
    prompt_trail.append(("cd /", p.prompt_line, p.location))
    print(f"cd / -> {p.prompt_line}")

    # List FixtureTypes to know how many FTs exist
    resp = await client.send_command_with_response("cd FixtureType 1")
    p = parse_prompt(resp)
    prompt_trail.append(("cd FixtureType 1", p.prompt_line, p.location))
    print(f"cd FixtureType 1 -> {p.prompt_line}")

    # Go back to root
    resp = await client.send_command_with_response("cd /")

    for ft_idx in range(1, 15):  # FT 1 through 14
        print(f"\n{'='*70}")
        print(f"  FT {ft_idx}")
        print(f"{'='*70}")

        # Navigate into FixtureType N
        resp = await client.send_command_with_response(f"cd FixtureType {ft_idx}")
        p = parse_prompt(resp)
        prompt_trail.append((f"cd FixtureType {ft_idx}", p.prompt_line, p.location))
        print(f"  cd FixtureType {ft_idx} -> {p.prompt_line}")

        # List contents
        resp = await client.send_command_with_response("List")
        print(f"  List at FT {ft_idx}:")
        # Extract FT name from the raw response
        ft_name = f"FT{ft_idx}"
        for line in resp.split("\n"):
            clean = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", line).strip()
            if clean and not clean.startswith("[") and not clean.startswith("Executing"):
                print(f"    {clean}")

        # Navigate into Modules
        resp = await client.send_command_with_response("cd Modules 1")
        p = parse_prompt(resp)
        prompt_trail.append((f"FT{ft_idx}/cd Modules 1", p.prompt_line, p.location))

        # List Modules
        resp = await client.send_command_with_response("List")
        modules_raw = resp

        # Parse how many modules by counting "Module N" lines
        module_entries = []
        for line in resp.split("\n"):
            clean = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", line).strip()
            m = re.match(r"Module\s+(\d+)\s+(\d+)\s+(.+)", clean)
            if m:
                module_entries.append({
                    "module_id": int(m.group(1)),
                    "col3": m.group(2),
                    "name": m.group(3).split("  ")[0].strip(),
                })

        print(f"  Modules: {len(module_entries)}")
        for me in module_entries:
            print(f"    Module {me['module_id']}: {me['name']}")

        ft_result = {
            "ft_index": ft_idx,
            "ft_name": ft_name,
            "module_count": len(module_entries),
            "modules": [],
        }

        for me in module_entries:
            mid = me["module_id"]
            # Navigate into this module
            resp = await client.send_command_with_response(f"cd {mid}")
            p = parse_prompt(resp)
            prompt_trail.append((f"FT{ft_idx}/Module{mid}", p.prompt_line, p.location))

            # List ChannelTypes
            resp = await client.send_command_with_response("List")

            # Parse ChannelType entries
            channels = []
            for line in resp.split("\n"):
                clean = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", line).strip()
                ct = re.match(
                    r"ChannelType\s+(\d+)\s+(\d+)\s+(.+)",
                    clean,
                )
                if ct:
                    cd_idx = int(ct.group(1))
                    rest = ct.group(3)
                    # Split on 2+ spaces to get columns
                    cols = re.split(r"\s{2,}", rest)
                    attrib_name = cols[0] if cols else rest
                    # Try to extract Break and Coarse from the columns
                    break_num = None
                    coarse = None
                    fine = None
                    if len(cols) >= 3:
                        try:
                            break_num = int(cols[1])
                        except (ValueError, IndexError):
                            pass
                        try:
                            coarse_str = cols[2]
                            if coarse_str != "None":
                                coarse = int(coarse_str)
                        except (ValueError, IndexError):
                            pass
                    if len(cols) >= 4:
                        try:
                            fine_str = cols[3]
                            if fine_str != "None":
                                fine = int(fine_str)
                        except (ValueError, IndexError):
                            pass

                    channels.append({
                        "cd_index": cd_idx,
                        "attribute": attrib_name,
                        "break": break_num,
                        "coarse_dmx": coarse,
                        "fine_dmx": fine,
                    })

            # Check if CD order matches Coarse DMX order
            coarse_values = [c["coarse_dmx"] for c in channels if c["coarse_dmx"] is not None]
            cd_matches_dmx = all(
                coarse_values[i] <= coarse_values[i + 1]
                for i in range(len(coarse_values) - 1)
            ) if len(coarse_values) > 1 else True

            module_result = {
                "module_id": mid,
                "module_name": me["name"],
                "channel_count": len(channels),
                "channels": channels,
                "coarse_order": coarse_values,
                "cd_matches_dmx_order": cd_matches_dmx,
            }
            ft_result["modules"].append(module_result)

            print(f"\n  Module {mid} ({me['name']}) - {len(channels)} ChannelTypes:")
            print(f"    {'CD':>3s}  {'Attribute':<35s}  {'Brk':>3s}  {'Coarse':>6s}  {'Fine':>6s}")
            print(f"    {'---':>3s}  {'-'*35:<35s}  {'---':>3s}  {'------':>6s}  {'------':>6s}")
            for c in channels:
                print(
                    f"    {c['cd_index']:3d}  {c['attribute']:<35s}"
                    f"  {str(c['break'] or ''):>3s}"
                    f"  {str(c['coarse_dmx'] or ''):>6s}"
                    f"  {str(c['fine_dmx'] or ''):>6s}"
                )
            order_str = "OK MATCHES" if cd_matches_dmx else "FAIL DIFFERS"
            print(f"    CD vs DMX order: {order_str}")
            print(f"    Coarse sequence: {coarse_values}")

            # Go back up
            resp = await client.send_command_with_response("cd ..")

        all_results.append(ft_result)

        # Return to root for next FT
        resp = await client.send_command_with_response("cd /")

    # Reset to Channel
    await client.send_command_with_response("Channel")
    await client.disconnect()

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY: CD Index vs DMX Coarse Order")
    print(f"{'='*70}")
    for ft in all_results:
        for mod in ft["modules"]:
            status = "OK" if mod["cd_matches_dmx_order"] else "FAIL"
            print(
                f"  FT {ft['ft_index']:2d} Module {mod['module_id']}"
                f" ({mod['module_name']:<20s})"
                f" {mod['channel_count']:2d} ch  {status}"
                f"  Coarse: {mod['coarse_order']}"
            )

    # Prompt trail
    print(f"\n{'='*70}")
    print("PROMPT TRAIL (navigation state at each CD level)")
    print(f"{'='*70}")
    for cmd, prompt, location in prompt_trail:
        print(f"  {cmd:<30s} -> {str(prompt):<45s} loc={location}")

    # Output JSON
    print("\nFULL RESULTS JSON:")
    print(json.dumps(all_results, indent=2))


if __name__ == "__main__":
    asyncio.run(validate_ft_channels())

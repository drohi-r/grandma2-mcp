"""Export all v5 FT groups to discover fixture ID patterns across all FTs."""
import asyncio
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0, ".")
from src.telnet_client import GMA2TelnetClient

IMPORTEXPORT = Path(r"C:\ProgramData\MA Lighting Technologies\grandma\gma2_V_3.9.60\importexport")


def clean(s):
    return re.sub(r"\x1b\[[0-9;]*m", "", s).replace("[K", "")


async def flush(client):
    try:
        await asyncio.wait_for(client._reader.read(16384), timeout=0.5)
    except Exception:
        pass


async def go_root(client):
    for _ in range(5):
        await client.send_command("cd /", delay=0.2)
    await asyncio.sleep(0.3)
    await flush(client)


async def cmd(client, command, delay=1.0):
    resp = await client.send_command_with_response(command, timeout=5.0, delay=delay)
    return clean(resp)


async def main():
    client = GMA2TelnetClient(host="127.0.0.1", port=30000)
    await client.connect()
    await client.login()
    await go_root(client)

    print("FT Group Fixture IDs (from v5 FT groups 1-9):")
    print("=" * 70)

    # v5 FT groups: 1=FT1, 2=FT2, 3=FT3, 4=FT4(lump), 5=FT4.1.1, 6=FT4.1.2, 7=FT5, 8=FT6, 9=FT7
    groups = [
        (1, "FT 1."),
        (2, "FT 2."),
        (3, "FT 3."),
        (4, "FT 4. (lump)"),
        (5, "FT 4.1.1"),
        (6, "FT 4.1.2"),
        (7, "FT 5."),
        (8, "FT 6."),
        (9, "FT 7."),
    ]

    for gnum, label in groups:
        fname = f"audit_ft_g{gnum}"
        fpath = IMPORTEXPORT / f"{fname}.xml"
        if fpath.exists():
            fpath.unlink()
        await cmd(client, f'Export Group {gnum} "{fname}"', delay=2.0)
        await asyncio.sleep(0.5)

        if fpath.exists():
            tree = ET.parse(fpath)
            root = tree.getroot()
            fix_ids = set()
            all_subs = []
            for elem in root.iter():
                local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                if local == "Subfixture":
                    fid = int(elem.get("fix_id", "0"))
                    sid = int(elem.get("sub_index", "0"))
                    fix_ids.add(fid)
                    all_subs.append((fid, sid))

            sorted_ids = sorted(fix_ids)
            id_range = f"{sorted_ids[0]}-{sorted_ids[-1]}" if sorted_ids else "?"
            subs_per = len(all_subs) // len(sorted_ids) if sorted_ids else 0
            print(f"  Group {gnum:2d} ({label:12s}): {len(all_subs):3d} subs, "
                  f"fix_ids=[{id_range}] ({len(sorted_ids)} fixtures, {subs_per} subs/fix)")
            fpath.unlink()
        else:
            print(f"  Group {gnum:2d} ({label:12s}): export failed")

    await client.disconnect()


asyncio.run(main())

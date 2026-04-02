"""Quick regex test for root-level list pattern."""
import re

_RE = re.compile(r'^\s*(.+?)\s+(\d+)(?:\s{2,}(.+?))?\s*$')

tests = [
    ('Art-Net  1  OutActive=Off InActive=Off', 'Art-Net, 1'),
    ('ETC Net2 2  Active=Off LocalStart=1', 'ETC Net2, 2'),
    ('Pathport 3  Active=Off LocalStart=1', 'Pathport, 3'),
    ('sACN     4  OutActive=Off', 'sACN, 4'),
    ('Showfile              1  Date=Feb 25 2026', 'Showfile, 1'),
    ('Settings              3  (6)', 'Settings, 3'),
    ('EditSetup            11', 'EditSetup, 11'),
    ('Modules             1  (1)', 'Modules, 1'),
    ('Widget 7.1 Sequence  Small Symbols  0  0  0  10  4', 'NO MATCH (widget)'),
    ('No.  Name     Color', 'NO MATCH (header)'),
    ('Type      Symbols        Display  PosX', 'NO MATCH (header)'),
]
for line, expected in tests:
    m = _RE.match(line)
    if m:
        name = m.group(1)
        oid = m.group(2)
        print(f"MATCH: name={name!r:30s} id={oid!r:5s} | expected: {expected}")
    else:
        print(f"NONE:  {line[:55]:55s} | expected: {expected}")

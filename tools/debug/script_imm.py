"""script_imm.py: which events of which scripts hold an immediate, e.g. a CG entry. Shows where to warp for a picture.

    python -X utf8 tools/debug/script_imm.py 1479 1480 1481 1482
"""
import glob
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gen_scenes import ROOT, event_codes, entry  # noqa: E402

for f in sorted(glob.glob(str(ROOT / "work/rbb/*.ssg_.bin"))):
    n = int(Path(f).name[:4])
    d = entry(n)
    codes = event_codes(d)
    for want in map(int, sys.argv[1:]):
        for at in range(0, len(d) & ~3, 4):
            w = struct.unpack_from("<I", d, at)[0]
            if w >> 26 in (0x0D, 0x09) and w & 0xFFFF == want and (w >> 21) & 31 == 0:  # ori/addiu rt,$zero,want
                ev = [k for k, (_, o, end) in codes.items() if o <= at - 8 < end]
                print(f"ssg {n} imm {want} at {at:#x}: event {ev}")

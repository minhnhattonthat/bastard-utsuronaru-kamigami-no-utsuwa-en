"""script_calls.py ENGINE_ADDR: which script events call an engine function, by way of the jal stubs in each ssg.
python -X utf8 tools/debug/script_calls.py 0x800432F8   -> rows: map id, event, immediate in $a0 if the call sets one
Script code layout: docs/re/text.md. An event's code runs from its record offset to the next record's offset.
"""
import glob
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from gen_scenes import events, maps  # noqa: E402


STUB_FILE, STUB_END = 0x1358, 0x1758  # j table, EXE RAM 0x80010B58-0x80010F58, copied to prg by 8003FA94


def stub_offset(exe, target):
    """Scripts `bal` into their first 0x800 bytes, zeros on disc and filled at load from the `j` table in the EXE.
    The bal target counts from file offset 8 and prg starts at 0x18, hence the 0x10."""
    j = 0x08000000 | ((target >> 2) & 0x3FFFFFF)
    for i in range(STUB_FILE, STUB_END, 8):
        if struct.unpack_from("<I", exe, i)[0] == j:
            return i - STUB_FILE + 0x10
    raise ValueError(f"no script stub for {target:08X}")


def calls(d, stub):
    """Yield (offset of a call, a0 immediate or None)."""
    evs, prg_end = events(d)
    code = d[8:prg_end]  # record offsets count from file offset 8 (8003F85C); `idx` is the $gp value, not an event
    for i in range(0, len(code) - 3, 4):
        w = struct.unpack_from("<I", code, i)[0]
        if w >> 16 == 0x0411 and i + 4 + struct.unpack_from("<h", code, i)[0] * 4 == stub:  # bal
            a0 = None
            for back in (i + 4, i - 4, i - 8):  # delay slot first
                w2 = struct.unpack_from("<I", code, back)[0]
                if w2 >> 16 == 0x3404:  # ori $a0,$zero,imm
                    a0 = w2 & 0xFFFF
                    break
            yield i, a0


def main(target):
    exe = (ROOT / "work/disc/SLPS_005.42").read_bytes()
    stub = stub_offset(exe, target)
    print(f"stub offset {stub:#x}")
    for _, mid, _, ssg, _ in maps(exe):
        d = Path(glob.glob(str(ROOT / f"work/rbb/{ssg:04d}.*"))[0]).read_bytes()
        if len(d) <= 0x18:
            continue
        evs, _ = events(d)
        for off, a0 in calls(d, stub):
            name = next((n for n, o in reversed(evs) if o <= off), "?")
            print(mid, name, a0)


if __name__ == "__main__":
    main(int(sys.argv[1], 16))

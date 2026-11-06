"""fmt_sites.py: every sprintf and vsprintf in the EXE: format string, stack buffer, room before the next thing on the frame.
A format that grows past the room smashes the return address (ev_1_09_0006 hung that way: docs/re/windows.md, Fixed byte limits).

    python -X utf8 tools/debug/fmt_sites.py     one line per call
"""
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import extract  # noqa: E402

SINKS = {0x800546E8: "sprintf", 0x800543F4: "vsprintf"}


def words(d, i, n):
    return [struct.unpack_from("<I", d, i + k * 4)[0] for k in range(n)]


def audit(d, base):
    """-> [(call address, sink, a0 sp offset or None, frame size, room in bytes or None, format or None)]"""
    out = []
    for i in range(0, len(d) - 4, 4):
        w = struct.unpack_from("<I", d, i)[0]
        target = 0x80000000 | (w & 0x3FFFFFF) << 2
        if w >> 26 != 3 or target not in SINKS:
            continue
        back = 40
        start = i
        frame = None
        while start > 4 and i - start < 600 * 4:  # function start: the addiu $sp,-N of this frame
            start -= 4
            v = struct.unpack_from("<I", d, start)[0]
            if v >> 16 == 0x27BD and v & 0x8000:
                frame = 0x10000 - (v & 0xFFFF)
                break
        # whole-frame scan: every sp-relative slot
        end = i
        while end < len(d) - 4:
            v = struct.unpack_from("<I", d, end)[0]
            if v >> 16 == 0x27BD and not v & 0x8000:  # addiu $sp,+N: the epilogue
                break
            end += 4
        slots = set()
        for j in range(start, end, 4):
            v = struct.unpack_from("<I", d, j)[0]
            if (v >> 26) in range(0x20, 0x2C) and (v >> 21) & 31 == 29:  # load/store ...($sp)
                slots.add(v & 0xFFFF)
            if v >> 26 == 9 and (v >> 21) & 31 == 29 and (v >> 16) & 31 != 29:  # addiu rX,$sp,N
                slots.add(v & 0xFFFF)
        # a0 and a1 at the call
        a0, a1hi, a1lo = None, None, None
        for j in range(i + 4, i - back * 4, -4):
            v = struct.unpack_from("<I", d, j)[0]
            rt = (v >> 16) & 31
            if a0 is None and v >> 26 == 9 and rt == 4 and (v >> 21) & 31 == 29:
                a0 = v & 0xFFFF
            if a1lo is None and v >> 26 == 9 and rt == 5 and (v >> 21) & 31 == 5:
                a1lo = v & 0xFFFF
            if a1hi is None and v >> 26 == 15 and rt == 5:
                a1hi = v & 0xFFFF
        room = None
        if a0 is not None:
            above = sorted(s for s in slots if s > a0)
            room = (above[0] if above else frame) - a0
        fmt = None
        if a1hi is not None and a1lo is not None:
            addr = (a1hi << 16) + (a1lo - 0x10000 if a1lo & 0x8000 else a1lo)
            off = (addr & 0xFFFFFFFF) - base
            if 0 <= off < len(d):
                fmt = d[off:off + 80].split(b"\0")[0].decode("cp932", "replace")
        out.append((base + i, SINKS[target], a0, frame, room, fmt))
    return out


def main():
    d = (ROOT / "work/disc/SLPS_005.42").read_bytes()
    for call, sink, a0, frame, room, fmt in audit(d, extract.EXE_BASE):
        print(f"{call:08X}", sink, f"sp+{a0:#x}" if a0 is not None else "a0=?", f"frame={frame:#x}" if frame else "-",
              f"room={room}" if room else "room=?", fmt, sep="\t")


if __name__ == "__main__":
    main()

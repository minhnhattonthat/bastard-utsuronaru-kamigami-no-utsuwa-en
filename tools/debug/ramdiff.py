"""ramdiff.py A.bin B.bin [BASE [LEN]]: changed byte runs between two RAM dumps (L.dump_ram), as RAM addresses and values.
BASE (hex RAM address) and LEN limit the range, so one struct can be searched while the rest of RAM churns.
"""
import sys
from pathlib import Path


def runs(a, b, lo, hi, gap=4):
    """Runs of differing bytes in [lo, hi), merging differences at most `gap` bytes apart."""
    out, start, last = [], None, None
    for i in range(lo, hi):
        if a[i] != b[i]:
            if start is None:
                start = i
            elif i - last > gap:
                out.append((start, last + 1))
                start = i
            last = i
    if start is not None:
        out.append((start, last + 1))
    return out


def main():
    a, b = Path(sys.argv[1]).read_bytes(), Path(sys.argv[2]).read_bytes()
    lo = int(sys.argv[3], 16) & 0x1FFFFF if len(sys.argv) > 3 else 0
    hi = lo + int(sys.argv[4], 16) if len(sys.argv) > 4 else len(a)
    for s, e in runs(a, b, lo, hi):
        print(f"{0x80000000 + s:08X} {e - s:5d}  {a[s:e][:24].hex(' ')}  ->  {b[s:e][:24].hex(' ')}")


if __name__ == "__main__":
    assert runs(b"\0\1\0\0\0\0\0\0", b"\0\2\0\0\0\0\0\3", 0, 8) == [(1, 2), (7, 8)]
    main()

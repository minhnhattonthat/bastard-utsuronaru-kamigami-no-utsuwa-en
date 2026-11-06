"""ramuse.py: which RAM a scene uses, from a 2 MB dump (ramuse.lua, or L.dump_ram in a probe). Runs of zeros, largest first.

    python -X utf8 tools/debug/ramuse.py DUMP [DUMP..]         the zero runs common to all dumps, and the top of used RAM
"""
import sys
from pathlib import Path

MIN_RUN = 0x800


def zero_runs(buf):
    runs, i, n = [], 0x10000, len(buf)
    while i < n:
        if buf[i:i + 16] == bytes(16):
            j = i
            while j < n and buf[j] == 0:
                j += 1
            if j - i >= MIN_RUN:
                runs.append((i, j))
            i = max(j, i + 16)
        else:
            i += 16
    return runs


def main():
    dumps = [Path(p).read_bytes() for p in sys.argv[1:]]
    merged = bytearray(len(dumps[0]))
    for d in dumps:
        for i, b in enumerate(d):
            merged[i] |= b
    runs = sorted(zero_runs(bytes(merged)), key=lambda r: r[0] - r[1])
    for lo, hi in runs[:12]:
        print(f"{0x80000000 + lo:08X}-{0x80000000 + hi:08X} {hi - lo:#x}")
    top = next(i for i in range(len(merged) - 1, 0, -1) if merged[i] and i < 0x1FE000)
    print(f"highest nonzero below 801FE000: {0x80000000 + top:08X}")


if __name__ == "__main__":
    main()

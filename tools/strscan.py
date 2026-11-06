"""strscan.py: list Shift-JIS runs in a file, keeping the engine's control bytes (0x0A newline, 0x0B page, 0x0C end) in runs.

    python -X utf8 tools/strscan.py FILE [--min N]
Prints `offset  text` with controls shown as \\n, <B>, <C>. Needs at least --min double-byte chars (default 2) and one kana or kanji.
"""
import sys


def sjis_pair(d, j):
    a = d[j]
    return (0x81 <= a <= 0x9F or 0xE0 <= a <= 0xEA) and j + 1 < len(d) and 0x40 <= d[j + 1] <= 0xFC and d[j + 1] != 0x7F


def runs(d, minlen=2):
    """-> [(offset, raw bytes)]. A run may hold 0x0A/0x0B/0x0C and half-width kana/ASCII between double-byte chars."""
    out = []
    i, n = 0, len(d)
    while i < n - 1:
        j, cnt, jp = i, 0, 0
        while j < n:
            if sjis_pair(d, j):
                cnt += 1
                jp += d[j] >= 0x82 and (d[j] != 0x82 or d[j + 1] >= 0x9F)
                j += 2
            elif cnt and d[j] in (0x0A, 0x0B):
                j += 1
            elif cnt and d[j] == 0x0C:
                j += 1
                break
            else:
                break
        if cnt >= minlen and jp:
            out.append((i, d[i:j]))
            i = j
        else:
            i = j if j > i else i + 1
    return out


def show(raw):
    return raw.decode("cp932", "replace").replace("\n", "\\n").replace("\x0b", "<B>").replace("\x0c", "<C>")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    m = int(sys.argv[sys.argv.index("--min") + 1]) if "--min" in sys.argv else 2
    for off, raw in runs(open(sys.argv[1], "rb").read(), m):
        print(f"{off:06x}  {show(raw)}")

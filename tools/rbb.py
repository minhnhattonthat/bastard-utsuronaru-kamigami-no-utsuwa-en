"""rbb.py: read RSRCALL.RBB, OpusCorp's resource archive (see docs/re/rbb.md).

`siff` container -> RSRC (banner), RIDX (offset,size per entry, offsets from RBB0's data), EXIX, GAP0, RBB0 (data).
    python -X utf8 tools/rbb.py list          # one line per entry
    python -X utf8 tools/rbb.py unpack        # work/rbb/NNNN.<tag>.bin, decompressed
"""
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RBB = ROOT / "work" / "disc" / "RSRCALL.RBB"
BASE = 0x5000  # RBB0 data start in the file


def lzss_decode(src, out_size):
    """LZSS: flag bit 1 = literal; match = pos low byte, then (length-3)<<4 | pos high nibble; 4 KB window zeroed, write head starts at 0."""
    win = bytearray(4096)
    r = 0
    out = bytearray()
    i = 0
    flags = 0
    while len(out) < out_size and i < len(src):
        flags >>= 1
        if not flags & 0x100:
            flags = src[i] | 0xFF00
            i += 1
        if flags & 1:
            c = src[i]
            i += 1
            out.append(c)
            win[r] = c
            r = (r + 1) & 0xFFF
        else:
            a, b = src[i], src[i + 1]
            i += 2
            pos = a | ((b & 0xF) << 8)
            for k in range((b >> 4) + 3):
                c = win[(pos + k) & 0xFFF]
                out.append(c)
                win[r] = c
                r = (r + 1) & 0xFFF
    return bytes(out), i


def index(data):
    assert data[:4] == b"siff" and data[0x80:0x84] == b"RIDX"
    size = struct.unpack_from("<I", data, 0x84)[0]
    return [struct.unpack_from("<II", data, 0x88 + k) for k in range(0, size - size % 8, 8)]


def entry(data, off, size):
    """-> (tag, payload). Entries start with a reversed FourCC ('00zL' = compressed, then the inner chunk)."""
    return data[BASE + off:BASE + off + size]


if __name__ == "__main__":
    data = RBB.read_bytes()
    ents = index(data)
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    for n, (off, size) in enumerate(ents):
        e = entry(data, off, size)
        if cmd == "list":
            print(n, hex(off), hex(size), e[:32].hex(), e[:16])
        elif cmd == "unpack":
            Path(ROOT / "work/rbb").mkdir(parents=True, exist_ok=True)
            if e[:4] == b"00zL":
                csize = struct.unpack_from("<I", e, 16)[0]
                usize = struct.unpack_from("<I", e, 20)[0]
                raw, used = lzss_decode(e[24:24 + csize], usize)
                assert len(raw) == usize, (n, len(raw), usize)
                tag = e[4:8][::-1]
            else:
                raw, tag = e, e[:4]
            name = "".join(chr(c) if 48 <= c < 123 and chr(c).isalnum() else "_" for c in tag)
            (ROOT / f"work/rbb/{n:04d}.{name}.bin").write_bytes(raw)
    if cmd not in ("list", "unpack"):
        sys.exit(__doc__)

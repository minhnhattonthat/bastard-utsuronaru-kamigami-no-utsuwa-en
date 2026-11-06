"""rbb.py: read and rebuild RSRCALL.RBB, OpusCorp's resource archive (see docs/re/rbb.md).

`siff` container -> RSRC (banner), RIDX (offset,size per entry, offsets from RBB0's data), EXIX, GAP0, RBB0 (data).
    python -X utf8 tools/rbb.py list          # one line per entry
    python -X utf8 tools/rbb.py unpack        # work/rbb/NNNN.<tag>.bin, decompressed
    python -X utf8 tools/rbb.py verify        # re-encode every LZSS block; exit 1 unless all match the original bytes
"""
import multiprocessing
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RBB = ROOT / "work" / "disc" / "RSRCALL.RBB"
BASE = 0x5000  # RBB0 data start in the file
EXIX = 0x30B8  # EXIX data
RBB0_SIZE = 0x4FFC
N, F = 4096, 18
NIL = N


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


def lzss_encode(src):
    """Okumura's binary-tree LZSS, write head at 0, tokens as lzss_decode reads them. Same bytes as the original tool."""
    buf = bytearray(N + F - 1)
    lson = [NIL] * (N + 1)
    rson = [NIL] * (N + 257)
    dad = [NIL] * (N + 1)
    ml = mp = 0

    def insert(r):
        nonlocal ml, mp
        cmp = 1
        p = N + 1 + buf[r]
        rson[r] = lson[r] = NIL
        ml = 0
        while True:
            if cmp >= 0:
                if rson[p] == NIL:
                    rson[p] = r
                    dad[r] = p
                    return
                p = rson[p]
            else:
                if lson[p] == NIL:
                    lson[p] = r
                    dad[r] = p
                    return
                p = lson[p]
            i = 1
            while i < F:
                cmp = buf[r + i] - buf[p + i]
                if cmp:
                    break
                i += 1
            if i > ml:
                mp, ml = p, i
                if ml >= F:
                    break
        dad[r], lson[r], rson[r] = dad[p], lson[p], rson[p]
        dad[lson[p]] = dad[rson[p]] = r
        if rson[dad[p]] == p:
            rson[dad[p]] = r
        else:
            lson[dad[p]] = r
        dad[p] = NIL

    def delete(p):
        if dad[p] == NIL:
            return
        if rson[p] == NIL:
            q = lson[p]
        elif lson[p] == NIL:
            q = rson[p]
        else:
            q = lson[p]
            if rson[q] != NIL:
                while rson[q] != NIL:
                    q = rson[q]
                rson[dad[q]] = lson[q]
                dad[lson[q]] = dad[q]
                lson[q] = lson[p]
                dad[lson[p]] = q
            rson[q] = rson[p]
            dad[rson[p]] = q
        dad[q] = dad[p]
        if rson[dad[p]] == p:
            rson[dad[p]] = q
        else:
            lson[dad[p]] = q
        dad[p] = NIL

    out = bytearray()
    group = bytearray(1)
    mask = 1
    r = 0
    s = F
    pos = length = min(F, len(src))
    buf[:pos] = src[:pos]  # the first bytes are not mirrored past N: tail tokens' ties depend on it
    insert(N - F)  # the one node for the zeroed window, unlike Okumura's F
    insert(0)
    while length > 0:
        ml = min(ml, length)
        if ml <= 2:
            ml = 1
            group[0] |= mask
            group.append(buf[r])
        else:
            group += bytes((mp & 0xFF, (ml - 3) << 4 | mp >> 8))
        mask = mask << 1 & 0xFF
        if not mask:
            out += group
            group = bytearray(1)
            mask = 1
        last = ml
        for i in range(last):
            delete(s)
            if pos < len(src):
                buf[s] = src[pos]
                if s < F - 1:
                    buf[s + N] = src[pos]
                pos += 1
                keep = True
            else:
                length -= 1
                keep = length > 0
            s = (s + 1) & (N - 1)
            r = (r + 1) & (N - 1)
            if keep:
                insert(r)
    if len(group) > 1:
        out += group
    return bytes(out)


def blocks(e):
    """(offset of the 00zL tag, csize, usize) of each compressed block in an entry's bytes; skips over block payloads."""
    p = e.find(b"00zLATAD")
    while p >= 0:
        csize, usize = struct.unpack_from("<II", e, p + 16)
        yield p, csize, usize
        p = e.find(b"00zLATAD", p + 24 + csize)


def index(data):
    assert data[:4] == b"siff" and data[0x80:0x84] == b"RIDX"
    size = struct.unpack_from("<I", data, 0x84)[0]
    return [struct.unpack_from("<II", data, 0x88 + k) for k in range(0, size - size % 8, 8)]


def entry(data, off, size):
    """-> (tag, payload). Entries start with a reversed FourCC ('00zL' = compressed, then the inner chunk)."""
    return data[BASE + off:BASE + off + size]


def pack(data, replaced={}):
    """Rebuild the archive with `replaced` = {entry id: new bytes}. Ids never move; offsets shift only after a size change."""
    body = bytearray()
    table = []
    for n, (off, size) in enumerate(index(data)):
        e = replaced.get(n, entry(data, off, size))
        body += bytes(-len(body) & 0x7FF)
        table.append((len(body), len(e)))
        body += e
    head = bytearray(data[:BASE])
    struct.pack_into("<I", head, 4, BASE + len(body))
    struct.pack_into("<I", head, RBB0_SIZE, len(body))
    for k, (off, size) in enumerate(table):
        struct.pack_into("<II", head, 0x88 + k * 8, off, size)
        struct.pack_into("<I", head, EXIX + k * 4, size)
    return bytes(head + body)


def unwrap(e):
    """An entry's raw content: decompressed if the whole entry is one 00zL block."""
    if e[:4] != b"00zL":
        return e
    csize, usize = struct.unpack_from("<II", e, 16)
    return lzss_decode(e[24:24 + csize], usize)[0]


def rewrap(old, raw):
    """New entry bytes for raw content, in the form the old entry had."""
    if old[:4] != b"00zL":
        return raw
    stream = lzss_encode(raw)
    head = old[:8] + struct.pack("<IIII", len(stream) + 12, 0x1000, len(stream), len(raw))
    return head + stream + bytes(-len(stream) & 3)


def relocate(data, replaced, spill_at):
    """Replace entries without moving any others. An entry that fits the space up to the next entry stays; a larger one goes
    to the spill area, spill_at bytes from the archive's start (the game adds an entry's offset to the file's start with no
    range check, so offsets can reach past the file: DUMMY). -> (new archive of the same size, spill bytes)."""
    table = index(data)
    out = bytearray(data)
    spill = bytearray()
    ends = sorted(off for off, _ in table) + [len(data) - BASE]
    next_of = {a: b for a, b in zip(ends, ends[1:])}
    for n, e in sorted(replaced.items()):
        off, size = table[n]
        if len(e) <= next_of[off] - off:
            out[BASE + off:BASE + off + size] = bytes(size)
            out[BASE + off:BASE + off + len(e)] = e
            new_off = off
        else:
            spill += bytes(-len(spill) & 0x7FF)
            new_off = spill_at + len(spill) - BASE
            spill += e
            out[BASE + off:BASE + off + size] = bytes(size)
        struct.pack_into("<II", out, 0x88 + n * 8, new_off, len(e))
        struct.pack_into("<I", out, EXIX + n * 4, len(e))
    return bytes(out), bytes(spill)


def _same(block):
    n, p, csize, usize, stream = block
    return n, p, lzss_encode(lzss_decode(stream, usize)[0]) == stream


def verify(data):
    """Re-encode every compressed block. -> list of (entry, block offset) that differ. A few minutes in parallel."""
    work = []
    for n, (off, size) in enumerate(index(data)):
        e = entry(data, off, size)
        work += [(n, p, c, u, e[p + 24:p + 24 + c]) for p, c, u in blocks(e)]
    with multiprocessing.Pool() as pool:
        res = pool.map(_same, work, 8)
    print(len(work), "blocks,", sum(r[2] for r in res), "identical")
    return [r[:2] for r in res if not r[2]]


if __name__ == "__main__":
    data = RBB.read_bytes()
    ents = index(data)
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "verify":
        bad = verify(data)
        sys.exit(f"differ: {bad[:40]}" if bad else 0)
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

"""fcg.py: decode the game's `fcg` image containers (RBB entries) to PNG and build survey sheets. Needs Pillow.

    python -X utf8 tools/fcg.py dump ENTRY.bin OUTDIR    # every texture of one entry -> PNG
    python -X utf8 tools/fcg.py sweep OUTDIR [--thumb W]  # every texture of every work/rbb/*.fcg_.bin -> numbered contact sheets + index.tsv

Chunk tree: tag + u32 size (bit 31 = holds chunks). `tex ` holds optional `skey` (name), `clut` and `pxel`, each with `xywh` (x,y,w,h,mode,flag:
VRAM coordinates in 16-bit units; mode 0 = 4bpp, 1 = 8bpp, 2 = 15bpp; bit 31 of the second dword = data is 00zL-compressed) and `data`.
"""
import glob
import os
import struct
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rbb import lzss_decode, lzss_encode

ROOT = Path(__file__).resolve().parents[1]


def chunks(d, o, end):
    while o + 8 <= end:
        tag = d[o:o + 4]
        raw = struct.unpack_from("<I", d, o + 4)[0]
        sz = raw & 0x7FFFFFFF
        yield tag, o + 8, sz, bool(raw & 0x80000000)
        o += 8 + sz + (sz & 1)


def parse_xywh(d, o):
    x, y, w, h, mode = struct.unpack_from("<HHHHI", d, o)
    return x, y, w, h, mode & 0xFF, bool(struct.unpack_from("<I", d, o + 8)[0] & 0x80000000 or mode & 0x80000000)


def unz(blob):
    if blob[:4] == b"00zL":
        csize, usize = struct.unpack_from("<II", blob, 16)
        return lzss_decode(blob[24:24 + csize], usize)[0]
    return blob


def textures(d):
    """yield dict(name, x, y, w, h, mode, pixels, clut, cx, cy)."""
    assert d[:4] == b"fcg "
    size = struct.unpack_from("<I", d, 4)[0] & 0x7FFFFFFF
    for tag, o, sz, _ in chunks(d, 8, 8 + size):
        if tag != b"tex ":
            continue
        t = {"name": "", "pixels": None, "clut": None}
        for tag2, o2, sz2, _ in chunks(d, o, o + sz):
            if tag2 == b"skey":
                t["name"] = d[o2:o2 + sz2].split(b"\0")[0].decode("latin1")
            elif tag2 in (b"clut", b"pxel"):
                xywh = data = None
                for tag3, o3, sz3, _ in chunks(d, o2, o2 + sz2):
                    if tag3 == b"xywh":
                        xywh = parse_xywh(d, o3)
                    elif tag3 == b"data":
                        data = unz(d[o3:o3 + sz3])
                if tag2 == b"clut":
                    t["clut"], t["cx"], t["cy"] = data, xywh[0], xywh[1]
                else:
                    t["pixels"], t["x"], t["y"], t["w"], t["h"], t["mode"] = data, *xywh[:5]
        if t["pixels"] is not None:
            yield t


def _chunk(tag, body, flags):
    return tag + struct.pack("<I", len(body) | flags) + body + bytes(len(body) & 1)


def _pack_data(old, raw):
    """A `data` chunk's body for new pixels, in the form the old one had."""
    if old[:4] != b"00zL":
        assert len(raw) == len(old)
        return raw
    stream = lzss_encode(raw)
    return old[:8] + struct.pack("<IIII", len(stream) + 12, 0x1000, len(stream), len(raw)) + stream + bytes(-len(stream) & 3)


def with_pixels(d, edits):
    """A copy of fcg bytes with {texture index: raw pixels} replaced; every other byte is kept and parent sizes follow."""
    size = struct.unpack_from("<I", d, 4)[0] & 0x7FFFFFFF

    def rebuild(o, end, depth, picked):
        out = b""
        for tag, a, sz, sub in chunks(d, o, end):
            flags = 0x80000000 if sub else 0
            if depth == 0 and tag == b"tex ":
                n = rebuild.tex
                rebuild.tex += 1
                out += _chunk(tag, rebuild(a, a + sz, 1, n) if n in edits else d[a:a + sz], flags)
            elif depth == 1 and tag == b"pxel":
                out += _chunk(tag, rebuild(a, a + sz, 2, picked), flags)
            elif depth == 2 and tag == b"data":
                out += _chunk(tag, _pack_data(d[a:a + sz], edits[picked]), flags)
            else:
                out += _chunk(tag, d[a:a + sz], flags)
        return out

    rebuild.tex = 0
    body = rebuild(8, 8 + size, 0, None)
    flag = struct.unpack_from("<I", d, 4)[0] & 0x80000000
    return d[:4] + struct.pack("<I", len(body) | flag) + body + d[8 + size:]


def to_image(t):
    w, h, px, mode = t["w"], t["h"], t["pixels"], t["mode"]
    clut = t["clut"] or b""
    pal = [struct.unpack_from("<H", clut, k)[0] for k in range(0, len(clut) - 1, 2)]

    def rgb(v):
        return ((v & 31) << 3, ((v >> 5) & 31) << 3, ((v >> 10) & 31) << 3)

    if mode == 0:
        im = Image.new("RGB", (w * 4, h))
        p = im.load()
        for y in range(h):
            for x in range(w * 4):
                i = y * w * 2 + x // 2
                if i >= len(px):
                    continue
                v = (px[i] >> (4 * (x & 1))) & 15
                p[x, y] = rgb(pal[v]) if v < len(pal) else (v * 17,) * 3
    elif mode == 1:
        im = Image.new("RGB", (w * 2, h))
        p = im.load()
        for y in range(h):
            for x in range(w * 2):
                i = y * w * 2 + x
                if i < len(px):
                    p[x, y] = rgb(pal[px[i]]) if px[i] < len(pal) else (px[i],) * 3
    else:
        im = Image.new("RGB", (w, h))
        p = im.load()
        for y in range(h):
            for x in range(w):
                i = (y * w + x) * 2
                if i + 1 < len(px):
                    p[x, y] = rgb(px[i] | px[i + 1] << 8)
    return im


def dump(path, out):
    os.makedirs(out, exist_ok=True)
    for n, t in enumerate(textures(open(path, "rb").read())):
        to_image(t).save(f"{out}/{n:03d}_{t['name'].replace('.', '_') or 'tex'}.png")
        print(n, t["name"], t["x"], t["y"], t["w"], t["h"], t["mode"])


def sweep(out, tw=152):
    os.makedirs(out, exist_ok=True)
    cols, rows = 6, 8
    cellh = tw * 192 // 304 + 12
    page, cell, sheet, draw = 0, 0, None, None
    idx = open(f"{out}/index.tsv", "w", encoding="utf-8")

    def flush():
        nonlocal sheet, page, cell
        if sheet:
            sheet.save(f"{out}/sheet{page:03d}.png")
            page += 1
            cell, sheet = 0, None

    for f in sorted(glob.glob(str(ROOT / "work/rbb/*.fcg_.bin"))):
        entry = os.path.basename(f)[:4]
        d = open(f, "rb").read()
        try:
            texs = list(textures(d))
        except Exception as e:  # never drop silently
            print("SKIPPED", entry, e)
            continue
        for n, t in enumerate(texs):
            im = to_image(t)
            idx.write(f"{page}\t{cell}\t{entry}\t{n}\t{t['name']}\t{t['x']}\t{t['y']}\t{t['w']}\t{t['h']}\t{t['mode']}\n")
            if sheet is None:
                sheet = Image.new("RGB", (cols * tw, rows * cellh), (60, 0, 60))
                draw = ImageDraw.Draw(sheet)
            r = min(tw / im.width, (cellh - 12) / im.height, 1.0 if im.width <= tw else 9)
            im2 = im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))))
            x0, y0 = (cell % cols) * tw, (cell // cols) * cellh
            sheet.paste(im2, (x0, y0 + 12))
            draw.text((x0 + 1, y0), f"{entry}/{n} {t['name'][:12]}", fill=(255, 255, 0))
            cell += 1
            if cell == cols * rows:
                flush()
    flush()
    print("pages", page)


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "dump":
        dump(sys.argv[2], sys.argv[3])
    elif len(sys.argv) >= 3 and sys.argv[1] == "sweep":
        sweep(sys.argv[2], int(sys.argv[sys.argv.index("--thumb") + 1]) if "--thumb" in sys.argv else 152)
    else:
        sys.exit(__doc__)

"""movie_text.py: redraw the burned-in captions of the ANIME movies (docs/re/graphics.md rows 4, 7, 8) from tools/movie_text.tsv.

    python -X utf8 tools/movie_text.py sheet MOVIE FROM TO STEP OUT.png   our frames, for reading, without building a disc
    python -X utf8 tools/movie_text.py edges OUT                          OUT_0.png..: every caption at its edges, to set frame ranges

A caption's box becomes a soft, darkened blur of the frame itself, so the Japanese is gone and the art's colour stays; the English
sits on it, fading like the original. Macroblocks the box does not touch keep their original bits.
"""
import hashlib
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import disc
import mdec

ROOT = Path(__file__).resolve().parents[1]
TSV = ROOT / "tools" / "movie_text.tsv"
FONTS = {"c": ROOT / "fonts/Cinzel.ttf", "b": ROOT / "fonts/LibreBaskerville.ttf"}
MOVIES = {157: (129344, 20913), 162: (214076, 8416)}  # lba, sectors
BAND_RAMP = 4  # frames for the box to arrive: faster than the caption's fade, so the Japanese never shows through
FEATHER = 5
DIM_Y, DIM_C = 0.3, 0.6
CACHE = ROOT / "work" / "fmv" / "movie_sectors"
SUPER = 4


def captions():
    out = []
    for line in TSV.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            m, a, b, fi, fo, x, y, w, h, font, size, text = line.split("\t")
            out.append({"movie": int(m), "first": int(a), "last": int(b), "fade_in": int(fi), "fade_out": int(fo), "box": tuple(map(int, (x, y, w, h))),
                        "font": font, "size": int(size), "text": text})
    return out


def _font(name, size):
    f = ImageFont.truetype(str(FONTS[name]), size * SUPER)
    if name == "c":
        f.set_variation_by_name("Bold")
    return f


def text_mask(cap, w, h):
    """Coverage of the caption's text, 0-1, full frame. Exits if a line overflows the frame."""
    x, y, bw, bh = cap["box"]
    lines = []
    for part in cap["text"].split("|"):
        size = cap["size"]
        if part[:3].rstrip(":").isdigit() and ":" in part[:3]:
            size, part = int(part.split(":")[0]), part.split(":", 1)[1]
        lines.append((part, size))
    heights = [4 if t == "---" else int(s * 1.3) for t, s in lines]
    im = Image.new("L", (w * SUPER, h * SUPER))
    d = ImageDraw.Draw(im)
    cy = y + (bh - sum(heights)) / 2
    cx = x + bw / 2
    for (t, s), lh in zip(lines, heights):
        if t == "---":
            d.rectangle([(cx - 68) * SUPER, (cy + 1) * SUPER, (cx + 68) * SUPER, (cy + 2) * SUPER], fill=255)
        else:
            f = _font(cap["font"], s)
            tw = d.textlength(t, font=f)
            if tw > (w - 8) * SUPER:
                sys.exit(f"movie_text: `{t}` is {tw / SUPER:.0f} px wide at size {s}, frame {w}")
            d.text((cx * SUPER - tw / 2, cy * SUPER), t, font=f, fill=255)
        cy += lh
    return np.asarray(im.resize((w, h), Image.BOX), float) / 255


def box_mask(cap, w, h):
    x, y, bw, bh = cap["box"]
    m = np.zeros((h, w))
    m[max(y, 0):y + bh, max(x, 0):x + bw] = 1
    soft = gaussian_filter(m, FEATHER / 2)
    return np.maximum(m, np.minimum(soft * 2, 1))


def _half(a):
    return (a[::2, ::2] + a[1::2, ::2] + a[::2, 1::2] + a[1::2, 1::2]) / 4


def compose(planes, caps, fnum, w, h):
    """Planes with these captions drawn; also the mask of what moved, for the macroblock map."""
    y, cb, cr = [p.copy() for p in planes]
    touched = np.zeros(y.shape, bool)
    for c in caps:
        t = fnum - c["first"] + 1
        e = c["last"] - fnum + 1
        band = min(1, t / BAND_RAMP if c["fade_in"] else 1, e / BAND_RAMP if c["fade_out"] else 1)
        a = box_mask(c, y.shape[1], y.shape[0]) * band
        ac = _half(a)
        # On a black screen a blur of the Japanese would show as a haze, so the fill fades out with what's around the box.
        dim = DIM_Y * min(1, y[a == 0].mean() / 12)
        fill_y, fill_b, fill_r = gaussian_filter(y, 10) * dim, gaussian_filter(cb, 5) * DIM_C, gaussian_filter(cr, 5) * DIM_C
        y = y * (1 - a) + fill_y * a
        cb = cb * (1 - ac) + fill_b * ac
        cr = cr * (1 - ac) + fill_r * ac
        touched |= a > 0
        fade = min(1, t / max(c["fade_in"], 1), e / max(c["fade_out"], 1))
        tm = text_mask(c, y.shape[1], y.shape[0]) * fade
        shadow = np.minimum(gaussian_filter(tm, 1.0) * 2.2, 1)
        y = y * (1 - shadow * 0.85)
        y = y * (1 - tm) + 244 * tm
        tc = _half(tm)
        cb, cr = cb * (1 - tc), cr * (1 - tc)
    return (y, cb, cr), touched


def _frame_job(job):
    data, w, h, cap_list, fnum, limit, max_words = job
    q, blocks, _ = mdec.parse(data, w, h)
    planes = mdec.decode(q, blocks, w, h)
    new, touched = compose(planes, cap_list, fnum, w, h)
    mh, mw = touched.shape[0] // 16, touched.shape[1] // 16
    changed = touched.reshape(mh, 16, mw, 16).any(axis=(1, 3))
    return fnum, mdec.recode(data, w, h, changed, new, limit, max_words), planes


def _write_frame(raw, f, frame):
    """Put a frame into its sectors in a raw STR: payload zero-padded, the frame fields of each sector's STR header updated."""
    body = frame.ljust(len(f["sectors"]) * mdec.PAYLOAD, b"\0")
    for n, i in enumerate(f["sectors"]):
        at = i * disc.SS
        raw[at + 24 + 32:at + 24 + 32 + mdec.PAYLOAD] = body[n * mdec.PAYLOAD:(n + 1) * mdec.PAYLOAD]
        struct.pack_into("<I", raw, at + 36, len(frame))
        raw[at + 44:at + 52] = frame[:8]


def _key():
    h = hashlib.sha1()
    for p in (TSV, Path(__file__), Path(mdec.__file__), *FONTS.values()):
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


def _render(raw, movie, want=None):
    """Re-encode the caption frames of one movie. Returns {frame number: (frame info, new bytes, qscale)}."""
    fr = mdec.frames(raw)
    caps = [c for c in captions() if c["movie"] == movie]
    max_words = max(struct.unpack_from("<H", f["data"])[0] for f in fr.values())
    jobs = []
    for n, f in sorted(fr.items()):
        here = [c for c in caps if c["first"] <= n <= c["last"]]
        if here and (want is None or n in want):
            jobs.append((bytes(f["data"][:f["size"]]), f["w"], f["h"], here, n, len(f["sectors"]) * mdec.PAYLOAD, max_words))
    return fr, jobs, [_frame_job(j) for j in jobs]  # a multiprocessing.Pool hung here on Windows; about 0.15 s a frame, and cached


def sectors():
    """{lba: 2352-byte sector} of every changed video sector, cached by the hash of the inputs; rendering takes minutes."""
    cache = CACHE.with_name(f"{CACHE.name}_{_key()}.npz")
    if cache.exists():
        z = np.load(cache)
        return z["lba"], z["raw"]
    lbas, raws, report = [], [], []
    with open(disc.BIN, "rb") as bf:
        for movie, (lba, count) in MOVIES.items():
            bf.seek(lba * disc.SS)
            raw = bytearray(bf.read(count * disc.SS))
            fr, jobs, results = _render(raw, movie)
            for fnum, (frame, q), _planes in results:
                _write_frame(raw, fr[fnum], frame)
                report.append(q > struct.unpack_from("<H", fr[fnum]["data"], 4)[0])
                for i in fr[fnum]["sectors"]:
                    lbas.append(lba + i)
                    raws.append(np.frombuffer(raw, np.uint8, disc.SS, i * disc.SS).copy())
    arr = np.stack(raws)
    for k in range(0, len(arr), 4096):
        disc.encode_form1(arr[k:k + 4096])
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez(cache, lba=np.array(lbas), raw=arr)
    print("movie_text:", len(report), "frames redrawn, qscale raised on", sum(report))
    return np.array(lbas), arr


def caption_lbas(path):
    """The LBAs a build may change in the movies: every sector of a caption frame."""
    out = []
    with open(path, "rb") as f:
        for movie, (lba, count) in MOVIES.items():
            f.seek(lba * disc.SS)
            fr = mdec.frames(f.read(count * disc.SS))
            for c in captions():
                if c["movie"] == movie:
                    for n in range(c["first"], c["last"] + 1):
                        out += [lba + i for i in fr[n]["sectors"]]
    return out


def apply(f):
    """Write the redrawn movie sectors into an open disc image."""
    lba, raw = sectors()
    for l, r in zip(lba.tolist(), raw):
        f.seek(l * disc.SS)
        f.write(r.tobytes())
    return len(lba)


def _tiles(movie, want):
    lba, count = MOVIES[movie]
    with open(disc.BIN, "rb") as bf:
        bf.seek(lba * disc.SS)
        raw = bytearray(bf.read(count * disc.SS))
    fr, _jobs, results = _render(raw, movie, want)
    done = {n: r[0] for n, r, _ in results}
    tiles = {}
    for n in sorted(want):
        f = fr[n]
        d = done.get(n, bytes(f["data"][:f["size"]]))
        q, blocks, _ = mdec.parse(d, f["w"], f["h"])
        im = Image.fromarray(mdec.to_rgb(*mdec.decode(q, blocks, f["w"], f["h"])))
        ImageDraw.Draw(im).text((1, 0), f"{n} q{q}", fill=(255, 255, 0))
        tiles[n] = im
    return tiles


def _montage(tiles, cols, div, out):
    W, H = tiles[0].width // div, tiles[0].height // div
    rows = (len(tiles) + cols - 1) // cols
    M = Image.new("RGB", (cols * (W + 2), rows * (H + 2)), (60, 0, 60))
    for k, t in enumerate(tiles):
        M.paste(t.resize((W, H), Image.BILINEAR) if div > 1 else t, (k % cols * (W + 2), k // cols * (H + 2)))
    M.save(out)


def sheet(movie, a, b, step, out):
    t = _tiles(movie, set(range(a, b + 1, step)))
    _montage([t[n] for n in sorted(t)], 4, 1, out)


def edges(out, per_page=13):
    """Each caption at its edges and middle, one row each, frames just outside it included: Japanese left uncovered shows here."""
    caps = captions()
    picks = {m: set() for m in MOVIES}
    rows = []
    for c in caps:
        a, b = c["first"], c["last"]
        row = [max(a - 2, 1), a + 1, a + 6, (a + b) // 2, b - 6, b - 1, b + 2]
        picks[c["movie"]].update(row)
        rows.append((c["movie"], row))
    tiles = {m: _tiles(m, s) for m, s in picks.items()}
    for p in range(0, len(rows), per_page):
        _montage([tiles[m][n] for m, row in rows[p:p + per_page] for n in row], 7, 2, f"{out}_{p // per_page}.png")


if __name__ == "__main__":
    if len(sys.argv) == 7 and sys.argv[1] == "sheet":
        sheet(int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6])
    elif len(sys.argv) == 3 and sys.argv[1] == "edges":
        edges(sys.argv[2])
    else:
        sys.exit(__doc__)

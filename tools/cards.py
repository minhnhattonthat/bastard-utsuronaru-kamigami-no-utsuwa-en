"""cards.py: picture text the build redraws (docs/re/graphics.md rows 1-5): area title cards, chapter ends, publisher card, icons.

    python -X utf8 tools/cards.py sheet [DIR]   the redrawn pictures as contact sheets, default work/qa/cards
"""
import csv
import glob
import json
import struct
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fcg

ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / "fonts/Cinzel.ttf"
MAX_W = 296  # of 304
RULE_MIN = 100  # a row with this long a run of ink is the rule under the name
# Cards whose picture names less than the map record does.
NAME_OVERRIDE = {302: "Ice Hell Tower", 350: "Hollow God King's Fort"}
CG_CARDS = {1194: "Forest Entrance", 1195: "Forgotten Beach", 1196: "Hermit Rock Fort"}  # 森林地帯入口, 忘却の浜辺, 寄岩砦
CHAPTER_END = {1479: "End of Chapter One", 1480: "End of Chapter Two", 1481: "End of Chapter Three", 1482: "End of Chapter Four"}


def font(size):
    f = ImageFont.truetype(str(FONT), size)
    f.set_variation_by_name("Bold")
    return f


def grays(clut):
    """Each CLUT index's brightness, 0-255."""
    out = []
    for k in range(0, len(clut) - 1, 2):
        v = struct.unpack_from("<H", clut, k)[0]
        r, g, b = v & 31, v >> 5 & 31, v >> 10 & 31
        # A CG palette holds colours too: a tinted entry must never be picked for a grey pixel.
        out.append((r + g + b) * 255 // 93 if max(r, g, b) - min(r, g, b) <= 1 else -9999)
    return out


def to_indices(t):
    """A texture as rows of palette indices."""
    w, h, px = t["w"], t["h"], t["pixels"]
    if t["mode"] == 1:
        return [list(px[y * w * 2:(y + 1) * w * 2]) for y in range(h)]
    return [[px[y * w * 2 + x // 2] >> (4 * (x & 1)) & 15 for x in range(w * 4)] for y in range(h)]


def from_indices(rows, mode):
    if mode == 1:
        return b"".join(bytes(r) for r in rows)
    return b"".join(bytes(r[x] | r[x + 1] << 4 for x in range(0, len(r), 2)) for r in rows)


def text_layer(lines, width, height):
    """(grey L image, its ink box): lines centred, each [(text, y baseline)]."""
    im = Image.new("L", (width, height), 0)
    d = ImageDraw.Draw(im)
    for text, base, f in lines:
        w = d.textlength(text, font=f)
        d.text(((width - w) / 2, base), text, font=f, fill=255, anchor="ls")
    return im


def fit_name(name):
    """[(line, font)]: one line at the largest size that fits, else two lines. Never below 18 px."""
    d = ImageDraw.Draw(Image.new("L", (4, 4)))
    for size in range(28, 21, -1):
        if d.textlength(name, font=font(size)) <= MAX_W:
            return [(name, font(size))]
    words = name.split()
    best = min(range(1, len(words)), key=lambda k: abs(len(" ".join(words[:k])) - len(" ".join(words[k:]))))
    parts = [" ".join(words[:best]), " ".join(words[best:])]
    for size in range(24, 17, -1):
        if max(d.textlength(p, font=font(size)) for p in parts) <= MAX_W:
            return [(p, font(size)) for p in parts]
    raise ValueError(f"name does not fit: {name}")


def rule_row(rows, bg):
    for y, r in enumerate(rows):
        run = best = 0
        for v in r:
            run = run + 1 if v != bg else 0
            best = max(best, run)
        if best >= RULE_MIN:
            return y
    raise ValueError("no rule")


def bands(rows, bg, y0):
    """[(first, last)] of the ink rows below y0."""
    out, start = [], None
    for y in range(y0, len(rows)):
        ink = any(v != bg for v in rows[y])
        if ink and start is None:
            start = y
        if not ink and start is not None:
            out.append((start, y - 1))
            start = None
    return out


def paint(rows, layer, gray, bg):
    """Draw a grey layer into rows with the nearest palette grey; black stays background."""
    p = layer.load()
    for y in range(layer.height):
        for x in range(layer.width):
            v = p[x, y]
            if v >= 24:
                rows[y][x] = min((i for i in range(len(gray)) if i != bg), key=lambda i: abs(gray[i] - v))


def redraw_card(t, name):
    """The rule stays, the name goes above it, the picture's own English subtitle moves up under it, the kanji goes."""
    rows = to_indices(t)
    bg = rows[0][0]
    rule = rule_row(rows, bg)
    sub = bands(rows, bg, rule + 1)
    out = [[bg] * len(rows[0]) for _ in rows]
    out[rule] = list(rows[rule])
    while sub and sub[0][0] == rule + 1:  # the rule's own shadow
        out[rule + 1] = list(rows[rule + 1])
        rule_shadow, sub = sub[0], sub[1:]
        assert rule_shadow[1] == rule + 1, name
    merged = []
    for a, b in sub:  # one blank row is inside a line of text (the dot of an i)
        if merged and a - merged[-1][1] <= 2:
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a, b))
    sub = merged
    if len(sub) not in (0, 2):
        raise ValueError(f"{name}: {len(sub)} rows of text under the rule")
    if sub:
        (ka, _), (a, b) = sub
        for y in range(a, b + 1):
            out[ka + y - a] = list(rows[y])
    parts = fit_name(name)
    base = rule - 6
    lines = []
    for text, f in reversed(parts):
        lines.append((text, base, f))
        base -= f.size + 3
    paint(out, text_layer(lines, len(rows[0]), rule), grays(t["clut"]), bg)
    return from_indices(out, t["mode"])


def redraw_chapter_end(t, text):
    rows = to_indices(t)
    bg = rows[0][0]
    h, w = len(rows), len(rows[0])
    ink = [(x, y) for y in range(h) for x in range(w) if rows[y][x] != bg]
    x1, y1 = max(p[0] for p in ink), max(p[1] for p in ink)
    out = [[bg] * w for _ in rows]
    im = Image.new("L", (w, h), 0)
    ImageDraw.Draw(im).text((x1, y1), text, font=font(13), fill=255, anchor="rs")
    paint(out, im, grays(t["clut"]), bg)
    return from_indices(out, t["mode"])


def redraw_publisher(t):
    rows = to_indices(t)
    bg = rows[0][0]
    rule = rule_row(rows, bg)
    w = len(rows[0])
    for y in range(rule):
        rows[y] = [bg] * w
    lines = [("Shueisha / SETA", 16, font(13)), ("BASTARD!! Production Committee", 34, font(12))]
    paint(rows, text_layer(lines, w, rule), grays(t["clut"]), bg)
    return from_indices(rows, t["mode"])


def redraw_logo(t):
    """Title screen, 304x192 8bpp though its header says 4bpp: the kanji subtitle goes, the sword between its halves stays."""
    t = dict(t, mode=1)
    rows = to_indices(t)
    bg = rows[0][0]
    for y in range(118, 136):
        for x in [*range(55, 138), *range(156, 237)]:
            rows[y][x] = bg
    im = Image.new("L", (304, 192), 0)
    ImageDraw.Draw(im).text((152, 135), "Vessel of the Hollow Gods", font=font(14), fill=215, anchor="ms")
    paint(rows, im, grays(t["clut"]), bg)
    return from_indices(rows, 1)


LETTERS = {  # 10 wide, 10 tall, block capitals for the 16 px command icons
    "M": ["##......##", "###....###", "####..####", "##.####.##", "##..##..##", "##......##", "##......##", "##......##", "##......##", "##......##"],
    "A": ["....##....", "...####...", "..##..##..", "..##..##..", ".##....##.", ".##....##.", ".########.", "##......##", "##......##", "##......##"],
}


def redraw_icon(t, letter):
    """Icon frame stays; the middle becomes the face colour with a letter in the kanji's own ink and shadow."""
    rows = to_indices(t)
    inner = [rows[y][x] for y in range(1, 15) for x in range(1, 15)]
    face = max(set(inner), key=inner.count)
    gray = grays(t["clut"])
    used = sorted({v for v in inner if v != face}, key=lambda i: gray[i])
    ink, shadow = used[-1], used[0]
    for y in range(1, 15):
        for x in range(1, 15):
            rows[y][x] = face
    for y, line in enumerate(LETTERS[letter]):
        for x, c in enumerate(line):
            if c == "#":
                rows[y + 3][x + 3] = shadow
    for y, line in enumerate(LETTERS[letter]):
        for x, c in enumerate(line):
            if c == "#":
                rows[y + 2][x + 2] = ink
    return from_indices(rows, t["mode"])


def card_names():
    """{entry id: English name}: a card sits before its map's dsg; several cards can share one."""
    en = {e["jp"]: e["en"] for e in json.loads((ROOT / "script/exe.json").read_text(encoding="utf-8")) if 0x974 <= e["off"] < 0xF88}
    by_dsg = {}
    for r in csv.DictReader(open(ROOT / "tools/debug/maps.tsv", encoding="utf-8"), delimiter="\t"):
        by_dsg.setdefault(int(r["dsg"]), r["name"])
    out = {}
    for f in sorted(glob.glob(str(ROOT / "work/rbb/*.fcg_.bin"))):
        eid = int(Path(f).name[:4])
        if eid < 394 and any((t["w"], t["h"], t["mode"]) == (76, 192, 0) for t in fcg.textures(Path(f).read_bytes())):
            dsg = min(d for d in by_dsg if d > eid)
            out[eid] = NAME_OVERRIDE.get(eid, en[by_dsg[dsg]])
    return out


def build(raw):
    """{entry id: new content}, raw(eid) giving an entry's original content."""
    out = {}
    for eid, name in card_names().items():
        d = raw(eid)
        for n, t in enumerate(fcg.textures(d)):
            if (t["w"], t["h"], t["mode"]) == (76, 192, 0):
                d = fcg.with_pixels(d, {n: redraw_card(t, name)})
        out[eid] = d
    for eid, name in CG_CARDS.items():
        d = raw(eid)
        out[eid] = fcg.with_pixels(d, {0: redraw_card(next(fcg.textures(d)), name)})
    for eid, text in CHAPTER_END.items():
        d = raw(eid)
        out[eid] = fcg.with_pixels(d, {0: redraw_chapter_end(next(fcg.textures(d)), text)})
    d = raw(1483)
    texs = list(fcg.textures(d))
    out[1483] = fcg.with_pixels(d, {3: redraw_logo(texs[3]), 4: redraw_publisher(texs[4])})
    d = raw(5)
    texs = list(fcg.textures(d))
    out[5] = fcg.with_pixels(d, {n: redraw_icon(texs[n], "M" if n < 7 else "A") for n in range(14)})
    return out


def sheet(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)

    def raw(eid):
        return Path(glob.glob(str(ROOT / f"work/rbb/{eid:04d}.*"))[0]).read_bytes()

    new = build(raw)
    tiles = []
    for eid, d in sorted(new.items()):
        for n, t in enumerate(fcg.textures(d)):
            if eid == 5 and n >= 14 or eid == 1483 and n != 4 or eid not in (5, 1483) and t["w"] * (4 if t["mode"] == 0 else 2) != 304:
                continue
            tiles.append((f"e{eid}/{n}", fcg.to_image(t)))
    per, cols = 24, 4
    for s in range(0, len(tiles), per):
        im = Image.new("RGB", (cols * 304, 6 * 204), (60, 0, 60))
        dr = ImageDraw.Draw(im)
        for k, (label, tile) in enumerate(tiles[s:s + per]):
            x, y = k % cols * 304, k // cols * 204
            im.paste(tile.resize((tile.width * 4, tile.height * 4), Image.NEAREST) if tile.width < 32 else tile, (x, y + 12))
            dr.text((x + 2, y), label, fill=(255, 255, 0))
        im.save(out / f"new_{s // per}.png")
    return len(tiles)


if __name__ == "__main__":
    if sys.argv[1:2] == ["sheet"]:
        print(sheet(sys.argv[2] if len(sys.argv) > 2 else ROOT / "work/qa/cards"), "tiles")
    else:
        sys.exit(__doc__)

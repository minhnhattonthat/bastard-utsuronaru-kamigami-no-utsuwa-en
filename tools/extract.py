"""extract.py: every game string -> script/*.json (see docs/re/text.md). Works from work/disc and work/rbb, the original files.

    python -X utf8 tools/extract.py dump [--force]   # writes only missing files; --force rewrites but keeps every `en`
    python -X utf8 tools/extract.py stats            # counts per source, control-byte census
Entry: id, off (in the source file), term ("0C", "00", or "" for a full fixed field), max (bytes up to the next thing), refs,
kind (text, data, debug, card, label: see docs/re/text.md), jp, en; scripts add ev (events), fn (stub the string goes to),
speaker (portrait id, -1 none) and who (its Japanese name).
"""
import glob
import json
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "debug"))
import gen_scenes  # events(): the script's event records
from strscan import sjis_pair
from tbl import Table

SCRIPT = ROOT / "script"
EXE = ROOT / "work" / "disc" / "SLPS_005.42"
EXE_BASE, OV_BASE = 0x8000F800, 0x800BF998  # docs/re/code.md; every overlay loads at OV_BASE, over the EXE's tail
GP = 28
STUB_SPEAKER = 0x290  # a0 = portrait, 0 = D.S.; set before dialogue
POOL = (0x8E180, 0x8E868)  # EXE: NUL-packed names read by index (800463CC), callers are all the debug stats editor
OV4_TEXT = (0x1B00, 0x50E8, 0xC8)  # overlay 4: fixed 200-byte ending blurbs, reached by base + index
# Where text lives; a pointer elsewhere lands in code or pixels. A string in these ranges with no pointer fails the coverage test.
RANGES = {
    "exe": [(0x800, 0x2100), (0x20000, 0x28000)],
    "ov1": [(0x0, 0x9000), (0x479A8, 0x479BE)],  # the second is `・` × 11, loaded by code at 0x398C8
    "ov2": [(0x0, 0xC00)],
    "ov4": [(0x1B00, 0x50E8)],
}
# EXE strings seen only on debug screens (docs/re/code.md), and the save header, which the memory card needs in Shift-JIS.
DEBUG_RANGES = [(0x800, 0x808), (0xF88, 0x10C0), (0x1D6C, 0x20E8)]
CARD = (0x1B70, 0x1BA4)
TABLES = {  # entry: header, stride, [(field offset, field size)], kind
    382: (8, 196, [(0, 12), (12, 36)], "text"),  # short and long character name
    386: (4, 32, [(2, 18)], "text"),  # a full 18-byte name has no NUL: the next field starts right after it
    388: (4, 32, [(2, 18)], "text"),
    392: (0, 44, [(4, 40)], "label"),  # developer map labels (テスト１): seen in game? phase 5
    393: (4, 108, [(24, 20), (44, 64)], "text"),  # formation name and description
    # A full 20-byte name has no NUL: the next field starts right after it, and can read as 0B or 0C (エクスキューショナー[14]).
    **{e: (0, 1316, [(4, 20)], "label") for e in range(551, 644)},  # encounter groups (オーク＊３)
    **{e: (8, 188, [(0, 20)], "label") for e in range(644, 737)},  # enemies and map objects (障害物零号機)
}


def _table():
    lines = ["0A={n}", "0B={page}", "0C={c}"]
    lines += [f"{c:02X}={chr(c)}" for c in range(0x20, 0x7F) if chr(c) not in "[{"]
    lines += [f"{c:02X}={bytes([c]).decode('cp932')}" for c in range(0xA1, 0xE0)]
    for hi in [*range(0x81, 0xA0), *range(0xE0, 0xFD)]:
        for lo in [*range(0x40, 0x7F), *range(0x80, 0xFD)]:
            try:
                ch = bytes([hi, lo]).decode("cp932")
            except UnicodeDecodeError:
                continue
            if ch not in "=\n":
                lines.append(f"{hi:02X}{lo:02X}={ch}")
    return Table(lines)


TBL = _table()


def decode(raw):
    return TBL.decode(raw, 0, len(raw))[0]


def encode(text):
    return TBL.encode(text)


def has_double(raw):
    i = 0
    while i < len(raw):
        if sjis_pair(raw, i):
            return True
        i += 1
    return False


def looks_text(raw):
    """Pointer targets in code or data can decode as SJIS by chance: real text has no lone high byte and at least one
    double-byte character. Low bytes stay allowed: battle messages open with a control byte (01..08)."""
    i = dbl = 0
    while i < len(raw):
        if sjis_pair(raw, i):
            dbl += 1
            i += 2
        elif raw[i] >= 0x7F or (raw[i] < 0x20 and raw[i] not in (0x0A, 0x0B, 0x0C) and dbl):
            return False  # the low bytes only open a message
        else:
            i += 1
    return dbl > 0


def span(d, o, stop=(0x00, 0x0C)):
    """Offset of the terminator ending the string at o."""
    j = o
    while j < len(d):
        if sjis_pair(d, j):
            j += 2
        elif d[j] in stop:
            return j
        else:
            j += 1
    return j


def room(d, end):
    """Bytes from `end` to the next nonzero byte after the terminator: how far a string could grow in place."""
    j = end + 1
    while j < len(d) and d[j] == 0:
        j += 1
    return j


def entry_path(eid):
    return glob.glob(str(ROOT / f"work/rbb/{eid:04d}.*"))[0]


def ssg_entries():
    return sorted(int(Path(p).name[:4]) for p in glob.glob(str(ROOT / "work/rbb/*.ssg_.bin")))


def bal_target(w, i):
    """Target offset of `bal` (bgezal $zero) at instruction i of the payload, else None."""
    return i * 4 + 4 + (((w & 0xFFFF) ^ 0x8000) - 0x8000) * 4 if w >> 16 == 0x0411 else None


def ssg_strings(d):
    """Entries of one script: every `ori rX,$zero,off` + `addu rX,rX,$gp`, with the event, stub and speaker around it."""
    if len(d) <= 0x18:
        return []
    pay, size = 0x18, struct.unpack_from("<I", d, 0x14)[0] & 0x7FFFFFFF
    gp = pay + 0x800
    n = size // 4
    ws = struct.unpack_from(f"<{n}I", d, pay)
    evs, _ = gen_scenes.events(d)
    starts = sorted((o + 8, name) for name, o in evs if name != "idx")
    k, cur, speaker = 0, None, -1
    found = {}
    for i, w in enumerate(ws):
        at = pay + i * 4
        while k < len(starts) and starts[k][0] <= at:
            cur, speaker = starts[k][1], -1
            k += 1
        if bal_target(w, i) == STUB_SPEAKER and i + 1 < n:
            ds = ws[i + 1]
            if ds >> 16 == 0x3404:  # ori $a0,$zero,N
                speaker = ds & 0xFFFF
            elif ds == 0x00002021 or ds == 0x00802021:  # move $a0,$zero
                speaker = 0
        if w >> 26 != 0x0D or (w >> 21) & 31 or i + 1 >= n:
            continue
        rt = (w >> 16) & 31
        nx = ws[i + 1]
        if nx & 0xFFFF07FF != (rt << 21 | GP << 16 | rt << 11 | 0x21) & 0xFFFF07FF:
            continue
        fn = next((t for j in range(i + 2, min(i + 6, n)) if (t := bal_target(ws[j], j)) is not None), None)
        e = found.setdefault(gp + (w & 0xFFFF), {"refs": [], "ev": [], "fn": [], "speaker": []})
        e["refs"].append(at)
        if cur is not None and cur not in e["ev"]:
            e["ev"].append(cur)
        if fn is not None and fn not in e["fn"]:
            e["fn"].append(fn)
        if speaker not in e["speaker"]:
            e["speaker"].append(speaker)
    out = []
    for o in sorted(found):
        end = span(d, o)
        out.append({"off": o, "end": end, "term": f"{d[end]:02X}", "max": room(d, end) - o, "kind": "text" if has_double(d[o:end]) else "data", **found[o]})
    return out


def lui_refs(d, base):
    """{address: [(lui offset, low-half offset)]} for lui + addiu/ori/load/store pairs within a short window."""
    n = len(d) // 4
    ws = struct.unpack_from(f"<{n}I", d)
    out = defaultdict(list)
    for i, w in enumerate(ws):
        if w >> 21 != 0x0F << 5:
            continue
        rt, hi = (w >> 16) & 31, (w & 0xFFFF) << 16
        for k in range(i + 1, min(i + 16, n)):
            x = ws[k]
            op = x >> 26
            if (op in (9, 13) or 0x20 <= op <= 0x2E) and (x >> 21) & 31 == rt:
                lo = x & 0xFFFF
                if op != 13 and lo >= 0x8000:
                    lo -= 0x10000
                out[(hi + lo) & 0xFFFFFFFF].append((i * 4, k * 4))
            dest = (x >> 11) & 31 if op == 0 else (x >> 16) & 31 if 8 <= op <= 15 or 0x20 <= op <= 0x26 else None
            if dest == rt or op == 2 or (op == 0 and x & 0x3F == 8):
                break
    return out


def data_refs(d, lo, hi):
    out = defaultdict(list)
    for i, (w,) in enumerate(struct.iter_unpack("<I", d[: len(d) & ~3])):
        if lo <= w < hi:
            out[w].append(i * 4)
    return out


def _load():
    exe = EXE.read_bytes()
    return exe, {o: Path(entry_path(o)).read_bytes() for o in range(5)}


def abs_strings():
    """{source: entries} for the EXE and overlays: every pointer target that is a NUL-terminated string with a double-byte character."""
    exe, ovs = _load()
    refs = {"exe": defaultdict(list), **{f"ov{o}": defaultdict(list) for o in ovs}}
    bases = {"exe": (exe, EXE_BASE), **{f"ov{o}": (ovs[o], OV_BASE) for o in ovs}}
    for name, (d, base) in bases.items():
        for addr, sites in lui_refs(d, base).items():
            refs[name][addr] += [f"{name}:c:{a:x}/{b:x}" for a, b in sites]
        for addr, sites in data_refs(d, 0x80010000, 0x80120000).items():
            refs[name][addr] += [f"{name}:d:{a:x}" for a in sites]
    out = {}
    for name, (d, base) in bases.items():
        hits = refs[name] if name == "exe" else {a: refs[name][a] for a in refs[name]}
        if name == "exe":  # an overlay's pointer below its own load address means the EXE
            hits = defaultdict(list, {a: list(v) for a, v in refs["exe"].items()})
            for ov in ovs:
                for a, v in refs[f"ov{ov}"].items():
                    if a < OV_BASE:
                        hits[a] += v
        rows = []
        for addr in sorted(hits):
            o = addr - base
            if not 0 <= o < len(d) or (name == "exe" and addr >= OV_BASE) or (name == "exe" and POOL[0] <= o < POOL[1]):
                continue
            if not any(a <= o < b for a, b in RANGES.get(name, [])):
                continue
            end = span(d, o, (0x00,))
            if end >= len(d) or d[end] or end == o or not looks_text(d[o:end]):
                continue
            kind = "text"
            if name == "exe":
                kind = "card" if o in CARD else "debug" if any(a <= o < b for a, b in DEBUG_RANGES) else "text"
            rows.append({"off": o, "end": end, "term": "00", "max": room(d, end) - o, "refs": hits[addr], "kind": kind})
        out[name] = _no_overlap(rows)
    a, b = POOL
    rows, o, index = [], a, 0
    for raw in exe[a:b].rstrip(b"\0").split(b"\0"):
        if looks_text(raw):  # the rest are placeholders such as `x`
            rows.append({"off": o, "end": o + len(raw), "term": "00", "max": len(raw) + 1, "refs": [f"exe:pool:{index}"], "kind": "debug"})
        o += len(raw) + 1
        index += 1
    out["exe"] = sorted(out["exe"] + rows, key=lambda e: e["off"])
    d = ovs[4]
    have = {e["off"] for e in out["ov4"]}
    for o in range(OV4_TEXT[0], OV4_TEXT[1], OV4_TEXT[2]):
        end = span(d, o, (0x00,))
        if o not in have and has_double(d[o:end]):
            out["ov4"].append({"off": o, "end": end, "term": "00", "max": OV4_TEXT[2], "refs": ["ov4:table"], "kind": "text"})
    out["ov4"].sort(key=lambda e: e["off"])
    return out


def _no_overlap(rows):
    """A pointer into the middle of a longer string is a suffix share: keep it noted on the longer one, once."""
    rows = sorted(rows, key=lambda e: e["off"])
    kept = []
    for e in rows:
        if kept and e["off"] < kept[-1]["end"]:
            kept[-1].setdefault("suffix", []).append({"off": e["off"], "refs": e["refs"]})
        else:
            kept.append(e)
    return kept


def table_strings(eid):
    d = Path(entry_path(eid)).read_bytes()
    head, stride, fields, kind = TABLES[eid]
    rows = []
    for r in range((len(d) - head + stride - 1) // stride):  # entry 382's last record is cut short
        for fo, fsize in fields:
            o = head + r * stride + fo
            if o + fsize > len(d):
                continue
            end = min(span(d, o, (0x00,)), o + fsize)
            if d[o] and looks_text(d[o:end]):
                rows.append({"off": o, "end": end, "term": "00" if d[end] == 0 else "", "max": fsize, "refs": [f"t{eid}:rec{r}"], "kind": kind})
    return rows


def text_runs(d, ranges=None, ends=(0, 0x0C)):
    """Independent of any pointer: [(start, end)] of runs that read as Japanese text, for the coverage test. Every pair is a
    real kana, punctuation or level-1 kanji code, ended by a byte in `ends`, 2+ characters, with kana or 3+ characters."""
    out = []
    for lo, hi in ranges or [(0, len(d))]:
        i = lo
        while i < hi - 1:
            j, cnt, kana = i, 0, 0
            while j < len(d) - 1:
                if sjis_pair(d, j):
                    code = d[j] << 8 | d[j + 1]
                    if not (0x8140 <= code <= 0x84BE or 0x889F <= code <= 0x9872) or bytes(d[j:j + 2]) not in TBL.dec:
                        break
                    cnt += 1
                    kana += 0x829F <= code <= 0x8396
                    j += 2
                elif cnt and (d[j] in (0x0A, 0x0B) or 0x20 <= d[j] < 0x7F):
                    j += 1
                else:
                    break
            if cnt >= 2 and d[j] in ends and (kana or cnt >= 3):
                out.append((i, j))
                i = j + 1
            else:
                i += 1
    return out


def leftovers():
    """[(file, offset, text)]: text runs no entry covers, over every script, table, overlay and EXE text range."""
    src = {stem: (d, rows) for stem, (_, d, rows) in sources().items()}
    for p in sorted(glob.glob(str(ROOT / "work/rbb/*.bin"))):  # entries with no strings at all: must have no text either
        eid, tag = int(Path(p).name[:4]), Path(p).name[5:9]
        if tag != "fcg_" and eid != 6 and f"ssg_{eid:04d}" not in src and f"tbl_{eid:04d}" not in src and f"ov{eid}" not in src:
            src[Path(p).name] = (Path(p).read_bytes(), [])
    out = []
    for stem, (d, rows) in src.items():
        cov = bytearray(len(d))
        for e in rows:
            cov[e["off"]:e["end"]] = b"\1" * (e["end"] - e["off"])
        # Table fields can fill up and run into the next field's bytes; elsewhere a wider end only finds code bytes.
        ends = range(0x20) if stem.startswith("tbl_") else (0, 0x0C)
        out += [(stem, a, decode(d[a:b])) for a, b in text_runs(d, ends=ends) if not any(cov[a:b])]
    return out


def sources():
    """{file stem: (source label, bytes, rows)}, in dump order."""
    out = {}
    for eid in ssg_entries():
        d = Path(entry_path(eid)).read_bytes()
        rows = ssg_strings(d)
        if rows:
            out[f"ssg_{eid:04d}"] = (f"s{eid:04d}", d, rows)
    exe, ovs = _load()
    ab = abs_strings()
    out["exe"] = ("exe", exe, ab["exe"])
    for o in (0, 1, 2, 3, 4):
        if ab[f"ov{o}"]:
            out[f"ov{o}"] = (f"ov{o}", ovs[o], ab[f"ov{o}"])
    for eid in TABLES:
        rows = table_strings(eid)
        if rows:
            out[f"tbl_{eid:04d}"] = (f"t{eid:04d}", Path(entry_path(eid)).read_bytes(), rows)
    return out


def speakers():
    """Portrait id -> Japanese name: entry 382's records for 0-26, then the EXE table at 0x8DF64 (stride 20) for 27-41."""
    d = Path(entry_path(382)).read_bytes()
    exe = EXE.read_bytes()
    names = {r: decode(d[o:span(d, o, (0x00,))]) for r in range(27) for o in [8 + r * 196]}
    for i in range(15):
        o = struct.unpack_from("<I", exe, 0x8DF64 + i * 20)[0] - EXE_BASE
        names[27 + i] = decode(exe[o:span(exe, o, (0x00,))])
    return names


def to_json(label, d, rows, names):
    out = []
    for e in rows:
        x = {"id": f"{label}_{e['off']:05x}", "off": e["off"], "term": e["term"], "max": e["max"], "kind": e["kind"], "refs": e["refs"]}
        for k in ("ev", "fn", "speaker", "suffix"):
            if k in e:
                x[k] = e[k]
        if "speaker" in e:
            x["who"] = [names.get(s, "") for s in e["speaker"]]
        x["jp"] = decode(d[e["off"]:e["end"]])
        x["en"] = ""
        out.append(x)
    return out


def dump(force=False):
    SCRIPT.mkdir(exist_ok=True)
    wrote = kept = 0
    names = speakers()
    for stem, (label, d, rows) in sources().items():
        p = SCRIPT / f"{stem}.json"
        new = to_json(label, d, rows, names)
        if p.exists():
            if not force:
                kept += 1
                continue
            old = {e["id"]: e["en"] for e in json.loads(p.read_text(encoding="utf-8"))}
            for e in new:
                e["en"] = old.get(e["id"], "")
        p.write_text(json.dumps(new, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        wrote += 1
    print(f"wrote {wrote} files, kept {kept}")


def stats():
    tot = Counter()
    ctl = Counter()
    for stem, (label, d, rows) in sources().items():
        group = stem.split("_")[0]
        tot[group, "files"] += 1
        tot[group, "strings"] += len(rows)
        tot[group, "text"] += sum(e["kind"] == "text" for e in rows)
        tot[group, "bytes"] += sum(e["end"] - e["off"] for e in rows)
        for e in rows:
            raw, i = d[e["off"]:e["end"]], 0
            while i < len(raw):
                if sjis_pair(raw, i):
                    i += 2
                    continue
                if raw[i] < 0x20 or raw[i] >= 0x7F:
                    ctl[group, f"{raw[i]:02X}"] += 1
                i += 1
    for k in sorted(tot):
        print(k, tot[k])
    print("single bytes outside ASCII:", sorted(ctl.items()))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "dump":
        dump("--force" in sys.argv)
    elif cmd == "stats":
        stats()
    else:
        sys.exit(__doc__)

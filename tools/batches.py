"""Translation batches (docs/translator-brief.md): split untranslated text, check translator output, merge it back.

    python -X utf8 tools/batches.py split [--size 3500] [--only REGEX]   work/tl/bNNN.tsv + .map.json for untranslated JP
    python -X utf8 tools/batches.py check [bNNN ...]      a batch's .out.tsv; with no batch, all shipped English (tests)
    python -X utf8 tools/batches.py merge bNNN ... [--overwrite]   check, then write the English into script/
    python -X utf8 tools/batches.py fix FILE              lines `id English`: replace those lines, repeats included (review fixes)
    python -X utf8 tools/batches.py fit "text" ID         print the wrapped lines and widths for that entry's box
    python -X utf8 tools/batches.py reflow                re-wrap shipped lines with the current wrap (breaks only, no word changes)

From the skill's assets/batches.py, fitted to this game. To save tokens over ~9,000 lines a batch line is `N speaker|JP` and
the output `N English`. Identical text is one line: N stands for every entry in the map file with that text.
Authored English has no {n}: the tool wraps to the box's real pixel budget (docs/re/windows.md) and adds pages when a box
overflows. ` | ` is {page}, ` // ` a forced line. Leading control codes and trailing {n} {page} %z are copied automatically.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import engine  # noqa: E402

TL = ROOT / "work/tl"
SCRIPT = ROOT / "script"
GLOSSARY = ROOT / "glossary.md"
WINDOWS = json.loads((ROOT / "tools/windows.json").read_text(encoding="utf-8"))
MAX_ENTRIES = 150
FORCED = {"s0153_00a30", "s0153_00b4c", "s0170_031b4", "s0268_011a0"}  # poems and chants, a line per verse: reflow leaves their breaks

CODE = r"\{c\}|\{n\}|\{page\}|\[[0-9A-F]{2}\]|%[a-zA-Z]"
TOKEN = re.compile(CODE)
HEAD = re.compile(r"^(?:\[[0-9A-F]{2}\]|\{c\}|%z)+")
TAIL = re.compile(r"(?:\{n\}|\{page\}|%z)+$")
ARG = re.compile(r"%[a-zA-Z]")
# Widest a substitution prints: enemy name 19 bytes and its letter (" A"), item 17, at about 6 px a letter.
ARG_PX = {"%s": 112, "%M": 72, "%i": 102, "%m": 60, "%l": 60, "%a": 48, "%d": 18, "%z": 0}
HONORIFICS = {"さん": "-san", "様": "-sama", "ちゃん": "-chan", "くん": "-kun", "君": "-kun", "殿": "-dono", "先生": "-sensei"}
# The text ring is cols x rows x 4 bytes and overflow keeps only the tail (docs/re/windows.md): 304 in a 228 px dialogue box, 288 in a 216 one.
RING = {"narration": 640, "dialogue": 288}
STUB_LINE = 6  # characters on a last line: under this, it's one orphaned word
STUB_PAGE = 3  # words on an added last page


def docs():
    for path in sorted(SCRIPT.glob("*.json")):
        yield path, json.loads(path.read_text(encoding="utf-8"))


def keep_jp():
    """{id: reason} from script/keep_jp.txt: the only player-side lines allowed to stay Japanese."""
    lines = (ln.partition(" ") for ln in (SCRIPT / "keep_jp.txt").read_text(encoding="utf-8").splitlines() if ln.strip() and ln[0] != "#")
    return {i: why.strip() for i, _, why in lines}


KEEP_JP = keep_jp()


def needs_english(e):
    return e["kind"] in ("text", "label") and e["id"] not in KEEP_JP and not e.get("en")


OV1_INFO = {"ov1_00c3c", "ov1_01360", "ov1_01388", "ov1_013b8"}  # the battle Information box
OV1_SUBMENU = {"ov1_010ec", "ov1_010f8", "ov1_01104", "ov1_01110", "ov1_0111c", "ov1_01124", "ov1_0112c", "ov1_01134"}  # Guard, Item, Equipment boxes


def box(e):
    """(px per line, lines, px on a page's last line, may add pages), from docs/re/windows.md."""
    i, jp, w = e["id"], e["jp"], WINDOWS.get(e["id"])
    if i[0] == "s":
        fn = e.get("fn") or []
        if {672, 664, 696, 760} & set(fn) or (w and w < 216):
            return 240, 1, 240, False
        if w == 216 or 560 in fn:
            return (216, 8, 204, True) if 560 in fn and w != 228 else (216, 4, 204, True)
        return 228, 4, 216, True
    if i.startswith("ov1"):
        if i == "ov1_011e4":  # %s = a party name and Unison/Chain, far under ARG_PX's 112 px each
            return 320, 1, 320, False
        if i in OV1_INFO:
            return 192, 2, 192, False
        if i in OV1_SUBMENU:
            return 52, 1, 52, False
        if not HEAD.match(jp) and "{n}" not in jp and "{page}" not in jp:
            return (32 if w and w <= 36 else 200), 1, 200, False  # labels
        return (216 if w == 216 else 228), 3, 216, True
    if i.startswith("ov2"):
        return (32 if len(jp) <= 2 else 212), 1, 212, False
    if i.startswith("ov4"):
        return 228, 5, 228, False
    if i.startswith("exe"):
        if e["off"] >= 0x20000 and e["max"] > 12:
            return 204, 2, 204, False
        return 240, 1, 240, False
    if i.startswith("t0393"):
        return (192, 2, 192, False) if e["max"] > 20 else (110, 1, 110, False)
    if i.startswith(("t0386", "t0388")):
        return 110, 1, 110, False
    return 120, 1, 120, False


def px(text):
    return sum(ARG_PX.get(t, 0) for t in ARG.findall(text)) + engine.width(ARG.sub("", text))


def fill(words, width):
    lines, cur = [], ""
    for word in words:
        if cur and px(cur + " " + word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = cur + " " + word if cur else word
    return lines + [cur]


def unstub_line(lines, start, last):
    """lines[start:] came from one run of text: give an orphaned last word company from the line above."""
    if len(lines) - start > 1 and len(lines[-1].strip()) < STUB_LINE and " " in lines[-2].strip():
        head, word = lines[-2].rsplit(" ", 1)
        if px(word + " " + lines[-1]) <= last:
            lines[-2:] = [head, word + " " + lines[-1]]


def unstub_page(chunks, width, last):
    """An added page of a word or two: end the page before it a row early, so the last page has a full row."""
    if len(chunks) < 2 or len(chunks[-1]) > 1 or len(chunks[-1][0].split()) > STUB_PAGE or len(chunks[-2]) < 2:
        return
    words = (chunks[-2].pop() + " " + chunks[-1][0]).split()
    while px(chunks[-2][-1]) > last:  # now the page's last row, so it has the arrow
        chunks[-2][-1], word = chunks[-2][-1].rsplit(" ", 1)
        words.insert(0, word)
    chunks[-1] = fill(words, width)
    if px(chunks[-1][-1]) > last:
        chunks[-1][-1:] = chunks[-1][-1].rsplit(" ", 1)
    unstub_line(chunks[-1], 0, last)


def wrap(text, e):
    """Authored English -> `{n}`/`{page}` text for e's box, or raises ValueError."""
    width, rows, last, pages = box(e)
    out = []
    for page in text.split(" | "):
        lines = []
        start = 0
        for forced in page.split(" // "):
            if rows == 1:
                lines.append(forced)
                continue
            start = len(lines)
            indent = forced[:len(forced) - len(forced.lstrip(" "))]  # centred lines keep their spaces
            cur = indent
            for word in forced.split():
                limit = last if len(lines) % rows == rows - 1 else width  # a full page's bottom row has the arrow
                if cur.strip() and px(cur + " " + word) > limit:
                    lines.append(cur)
                    cur = word
                else:
                    cur = cur + " " + word if cur.strip() else cur + word
            lines.append(cur)
            unstub_line(lines, start, last)
        if px(lines[-1]) > last and " " in lines[-1].strip():  # so has the page's last row, wherever it falls
            lines[-1:] = lines[-1].rsplit(" ", 1)
            unstub_line(lines, start, last)
        chunks = [lines[k:k + rows] for k in range(0, len(lines), rows)]
        unstub_page(chunks, width, last)
        out += ["{n}".join(c) for c in chunks]
    if len(out) > 1 and not pages:
        raise ValueError(f"{len(out)} pages in a {rows}-line box")
    return "{page}".join(out)


def affixes(jp):
    a = HEAD.match(jp)
    z = TAIL.search(jp)
    return a.group(0) if a else "", z.group(0) if z else ""


def core(jp):
    """The text a translator sees: no outer codes, no {n}."""
    a, z = affixes(jp)
    s = jp[len(a):len(jp) - len(z)] if z else jp[len(a):]
    return s.replace("{n}", "").replace("{page}", " | ")


def render(e, text):
    a, z = affixes(e["jp"])
    return a + wrap(text, e) + z


def core_raw(jp):
    """jp without its outer codes, {page} still in."""
    a, z = affixes(jp)
    return jp[len(a):len(jp) - len(z)] if z else jp[len(a):]


def authored(e):
    """An entry's English back in authored form."""
    a, z = affixes(e["jp"])
    s = e["en"][len(a):len(e["en"]) - len(z)] if z else e["en"][len(a):]
    return s.replace("{page}", " | ").replace("{n}", " ")


def glossary():
    """[(JP forms, EN forms, avoid forms, is_character)] from glossary.md's | JP | EN | max | notes | Avoid | tables."""
    rows, section = [], ""
    for line in GLOSSARY.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = line
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(cells) >= 2 and cells[0] not in ("JP", "") and not set(cells[0]) <= set("-: "):
            avoid = [x.strip() for x in cells[4].split("/") if x.strip()] if len(cells) > 4 else []
            rows.append(([x.strip() for x in cells[0].split("/")], [x.strip() for x in cells[1].split("/")], avoid, "Characters" in section))
    return rows


def kind(char):
    if "぀" <= char <= "ゟ":
        return "hiragana"
    if "゠" <= char <= "ヿ":
        return "katakana"
    if "一" <= char <= "鿿" or char == "々":
        return "kanji"
    return "other"


def has_term(jp, term):
    """term occurs as a whole kana or kanji run: ガラ isn't in ガラス, 魔 isn't in 魔法."""
    for m in re.finditer(re.escape(term), jp):
        a, b = m.start(), m.end()
        if (a == 0 or kind(jp[a - 1]) != kind(term[0])) and (b == len(jp) or kind(jp[b]) != kind(term[-1])):
            return True
    return False


def has_word(low, form):
    """form as a whole word, plural allowed: "Di" isn't in "did", "Gain" isn't in "again"."""
    return re.search(rf"(?<!\w){re.escape(form)}(?:e?s)?(?!\w)", low) is not None


def inner_codes(s):
    return Counter(t for t in TOKEN.findall(s) if t not in ("{n}", "{page}"))


def problems(e, en, terms):
    """Every rule, on one entry's finished `en`."""
    jp = e["jp"]
    out = []
    plain = TOKEN.sub("", en)
    bad = sorted({c for c in plain if not " " <= c <= "~"} | {c for c in plain if c in "[]{}%|"})
    if bad:
        out.append(f"unencodable or reserved characters {bad}")
    if ARG.findall(jp.replace("%z", "")) != ARG.findall(en.replace("%z", "")):
        out.append("arguments differ or moved (order is fixed)")
    if inner_codes(jp) != inner_codes(en):
        out.append("control codes differ")
    if affixes(jp)[0] != affixes(en)[0] or not en.endswith(affixes(jp)[1]):
        out.append("outer codes differ")
    if re.search(r"%d(st|nd|rd|th)\b", en):
        out.append("ordinal suffix after a variable")
    if re.search(r"\b[Aa]n? %[a-zA-Z]", en):
        out.append("a/an before a variable")
    jp_plain = TOKEN.sub("", jp)
    low = en.lower().replace("{n}", " ").replace("{page}", " ")
    for jps, ens, avoid, is_char in terms:
        if any(has_term(jp_plain, j) for j in jps) and not any(has_word(low, x.lower()) for x in ens):
            out.append(f"glossary: {jps[0]} -> {ens[0]}")
        out += [f"glossary Avoid: {a}" for a in avoid if re.search(rf"\b{re.escape(a)}\b", en)]
        if is_char:
            for form in jps:
                for h, en_h in HONORIFICS.items():
                    if form + h in jp_plain and en_h not in low:
                        out.append(f"honorific {form}{h} needs {en_h}")
    width, rows, last, _ = box(e)
    body = en[len(affixes(jp)[0]):]
    body = body[:len(body) - len(affixes(jp)[1])] if affixes(jp)[1] else body
    for page in body.split("{page}"):
        lines = page.split("{n}")
        if len(lines) > rows:
            out.append(f"{len(lines)} lines, box has {rows}")
        over = [ln for ln in lines if px(ln) > width] or ([lines[-1]] if px(lines[-1]) > last else [])
        if over:
            out.append(f"over {width}px: {over[0]!r} is {px(over[0])}")
        # A fixed box the tour measured (tools/windows.json). Scripts and the EXE have boxes that grow with the text: box() covers those.
        seen = WINDOWS.get(e["id"])
        wide = max(lines, key=px)
        if seen and e["id"][0] != "s" and not e["id"].startswith(("exe", "t0393")) and px(wide) > seen:  # t0393 names: the tour saw the marker's short id, the box is 110 px
            out.append(f"over the measured {seen}px box: {wide!r} is {px(wide)}")
    if rows > 1 and not e["id"].startswith(("exe", "t0")) and e["id"] not in FORCED:  # stat sheets and tables are laid out by hand
        pages = body.split("{page}")
        tail = pages[-1].split("{n}")
        if len(tail) > 1 and len(tail[-1].strip()) < STUB_LINE and " " in tail[-2].strip():
            out.append(f"stub last line: {tail[-1]!r}")
        if len(pages) > jp.count("{page}") + 1 and len(pages[-1].replace("{n}", " ").split()) <= STUB_PAGE:
            out.append(f"stub last page: {pages[-1]!r}")
    n = len(en.replace("{n}", "\n").replace("{page}", "\n"))
    if e["id"].startswith("t") or e["id"].startswith("ov4"):
        if n + 1 > e["max"]:
            out.append(f"{n} bytes, field holds {e['max'] - 1}")
    elif e["id"][0] == "s":
        cap = RING["narration"] if 560 in (e.get("fn") or []) else RING["dialogue"]
        if n > cap:
            out.append(f"{n} bytes, the text ring holds about {cap}: split it")
    return out


def index():
    return {e["id"]: e for _, rows in docs() for e in rows}


def existing():
    return sorted(TL.glob("b[0-9][0-9][0-9].tsv"))


def maps(name):
    return json.loads((TL / f"{name}.map.json").read_text(encoding="utf-8"))


def split(size, only=None):
    TL.mkdir(parents=True, exist_ok=True)
    taken = {i for p in existing() for ids in maps(p.stem).values() for i in ids}
    n = max((int(p.stem[1:]) for p in existing()), default=0)
    pat = re.compile(only) if only else None
    groups = {}
    known = {}
    for _, rows in docs():
        for e in rows:
            if e.get("en"):
                known.setdefault(core(e["jp"]), authored(e))
    carried = {}
    for _, rows in docs():
        for e in rows:
            if needs_english(e) and e["id"] not in taken and (not pat or pat.search(e["id"])):
                text = core(e["jp"])
                if text in known:  # same line elsewhere, already translated; a different box may wrap it differently
                    carried[e["id"]] = render(e, known[text])
                else:
                    groups.setdefault(text, []).append(e)
    if carried:
        write(carried, False)
    batches, cur, chars = [], [], 0
    for text, es in groups.items():
        if cur and (chars + len(text) > size or len(cur) >= MAX_ENTRIES):
            batches.append(cur)
            cur, chars = [], 0
        cur.append((text, es))
        chars += len(text)
    if cur:
        batches.append(cur)
    for batch in batches:
        n += 1
        name = f"b{n:03d}"
        lines, ids, last_ev, last_who = [], {}, None, None
        for k, (text, es) in enumerate(batch, 1):
            e = es[0]
            ev = (e["id"].split("_")[0], (e.get("ev") or [""])[0])
            if ev != last_ev:
                lines.append(f"# {ev[0]} ev {ev[1]}")
                last_ev, last_who = ev, None
            who = (e.get("who") or [""])[0] if e["id"][0] == "s" else ""
            if e["id"].startswith(("exe", "t0")):  # layout matters in tables: show the breaks
                text = e["jp"].replace("{n}", " // ")
            lines.append(f"{k} {who if who != last_who else ''}|{text}")
            last_who = who
            ids[k] = [x["id"] for x in es]
        (TL / f"{name}.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        (TL / f"{name}.map.json").write_text(json.dumps(ids), encoding="utf-8", newline="\n")
    print(f"{len(batches)} new batches, {len(taken)} ids already batched")


def read_out(batch):
    """{N: English}, or SystemExit on a bad line."""
    out = {}
    for line in (TL / f"{batch}.out.tsv").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        n, _, en = line.partition(" ")
        if not n.isdigit() or int(n) in out:
            sys.exit(f"{batch}: bad or duplicate line {line[:60]!r}")
        out[int(n)] = en
    return out


def check_batch(batch, entries, terms):
    ids = maps(batch)
    rows = read_out(batch)
    bad, new = [], {}
    if set(map(int, ids)) != set(rows):
        bad.append(f"lines differ: missing {sorted(set(map(int, ids)) - set(rows))[:12]} extra {sorted(set(rows) - set(map(int, ids)))[:12]}")
    for n, en in rows.items():
        for i in ids.get(str(n), []):
            try:
                text = render(entries[i], en)
            except ValueError as err:
                bad.append(f"{n} {i}: {err}: {en!r}")
                continue
            ps = problems(entries[i], text, terms)
            bad += [f"{n} {i}: {p}" for p in ps]
            new[i] = text
    return bad, new


def write(new, overwrite):
    if not overwrite:
        for _, rows in docs():
            for e in rows:
                if e["id"] in new and e.get("en") and e["en"] != new[e["id"]]:
                    sys.exit(f"{e['id']} would lose {e['en']!r}: pass --overwrite if that is meant")
    changed = 0
    for path, rows in docs():
        touched = False
        for e in rows:
            if e["id"] in new and e.get("en") != new[e["id"]]:
                e["en"] = new[e["id"]]
                touched = True
                changed += 1
        if touched:
            # extract.py's layout: keep one diff line per change
            path.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"merged: {changed} entries changed")


def fix(path, entries, terms):
    """`id English` per line: that entry and every entry with the same Japanese."""
    by_core = {}
    for e in entries.values():
        if needs_english(e) or e.get("en"):
            by_core.setdefault(core(e["jp"]), []).append(e)
    new, bad = {}, []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            i, _, en = line.partition(" ")
            for e in by_core[core(entries[i]["jp"])]:
                try:
                    new[e["id"]] = render(e, en)
                    bad += [f"{e['id']}: {p}" for p in problems(e, new[e["id"]], terms)]
                except ValueError as err:
                    bad.append(f"{e['id']}: {err}")
    if bad:
        print("\n".join(bad))
        return 1
    write(new, True)
    return 0


def reflow(entries):
    """Re-wrap shipped lines with the current wrap(): only line and page breaks change, never a word. Pages the Japanese has stay."""
    new, kept = {}, []
    for i, e in entries.items():
        if not e.get("en") or i in FORCED or not i.startswith(("s", "ov1", "ov4")) or box(e)[1] == 1:
            continue
        text = authored(e)
        if "{page}" not in core_raw(e["jp"]):
            text = text.replace(" | ", " ")
        try:
            new[i] = render(e, text)
        except ValueError as err:
            kept.append(f"{i}: {err}")
    if kept:
        print("\n".join(kept))
    write(new, True)
    return 1 if kept else 0


def main(argv):
    if not argv:
        sys.exit(__doc__)
    cmd, args = argv[0], argv[1:]
    if cmd == "split":
        size = int(args[args.index("--size") + 1]) if "--size" in args else 3500
        only = args[args.index("--only") + 1] if "--only" in args else None
        return split(size, only)
    entries, terms = index(), glossary()
    if cmd == "fit":
        text = render(entries[args[1]], args[0])
        print(box(entries[args[1]]))
        for page in text.split("{page}"):
            for ln in page.split("{n}"):
                print(f"{px(ln):4d} {ln}")
            print("  --")
        return 0
    if cmd == "fix":
        return fix(args[0], entries, terms)
    if cmd == "reflow":
        return reflow(entries)
    overwrite = "--overwrite" in args
    names = [a for a in args if a != "--overwrite"]
    if cmd == "check" and not names:
        bad = [f"{i}: {p}: {e['en']!r}" for i, e in entries.items() if e.get("en") for p in problems(e, e["en"], terms)]
        bad += [f"{i}: no English: {e['jp']!r}" for i, e in entries.items() if needs_english(e)]
        print(f"{len(entries)} entries, {len(bad)} problems")
        print("\n".join(bad[:200]))
        return 1 if bad else 0
    if cmd not in ("check", "merge") or not names:
        sys.exit(__doc__)
    new, failed = {}, 0
    for batch in names:
        bad, rows = check_batch(batch, entries, terms)
        new.update(rows)
        failed += bool(bad)
        print(f"{batch}: " + ("OK" if not bad else f"{len(bad)} problems"))
        for line in bad:
            print("  " + line)
    if failed:
        return 1
    if cmd == "merge":
        write(new, overwrite)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))

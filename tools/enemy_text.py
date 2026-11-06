"""enemy_text.py: enemy names (tools/monsters.tsv, hand translated) and encounter labels built from them.

    python -X utf8 tools/enemy_text.py     writes `en` into script/tbl_0551..0736 for every label it can build, lists the rest

Encounter labels (`ウルフ＊３＋サーベ`, tables 551-643, cut at 18 bytes) were never seen on screen in the marker tour: they look
like the developers' notes on each battle. They still get English in case one shows, built part by part, cut to the field.
Every run rewrites these labels, so change names in monsters.tsv, not in script/.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import batches  # noqa: E402

ASCII = str.maketrans("０１２３４５６７８９", "0123456789")


def part(text, names):
    """One side of a `＋`: name, count or brackets; the name may be cut short."""
    m = re.match(r"^(.*?)[（(]?[＊×]([０-９]+)[）)]?$", text)
    name, count = (m.group(1), m.group(2).translate(ASCII)) if m else (text, "")
    name = name.rstrip("（(＊×")
    en = names.get(name)
    if not en and len(name) >= 2:  # cut by the field: the longest name it starts
        hit = sorted((j for j in names if j.startswith(name)), key=len)
        en = names[hit[0]] if hit else None
    if not en and re.fullmatch(r"(雑魚ランク|ボスランク)[０-９]+", name):
        kind = re.match(r"(雑魚ランク|ボスランク)", name).group(1)
        en = names[kind] + " " + name[len(kind):].translate(ASCII)
    if not en:
        return None
    return en + (f" x{count}" if count else "")


def label(jp, names):
    if jp in names:
        return names[jp]
    parts = [part(p, names) for p in jp.split("＋") if p]
    if not parts or parts[0] is None:
        return None
    # a later part may be a cut-off stub with no match: the first parts carry the note
    return "+".join(p for p in parts if p)[:19].rstrip("+ x")


def main():
    names = dict(line.split("\t") for line in (ROOT / "tools/monsters.tsv").read_text(encoding="utf-8").splitlines() if line)
    terms = batches.glossary()
    new, left = {}, []
    for e in batches.index().values():
        if e["kind"] != "label" or e["id"].startswith("t0392") or batches.is_mark(e["jp"]):
            continue
        en = label(e["jp"], names)
        if not en or batches.problems(e, en, []):
            left.append(f"{e['id']} {e['jp']} {en} {batches.problems(e, en, terms) if en else ''}")
            continue
        new[e["id"]] = en
    batches.write(new, True)
    print(f"{len(left)} left:")
    print("\n".join(sorted(set(x.split(" ", 1)[1] for x in left))))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())

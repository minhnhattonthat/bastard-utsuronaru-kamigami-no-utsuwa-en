"""Write JP/EN pairs for reviewers: work/qa/review/pNN.txt, in script order.

python -X utf8 tools/pairs.py [--kb 110] [--only REGEX]
Each entry: `>> id | speaker | JP`, then `EN`. A line repeated elsewhere is listed once.
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "work/qa/review"
# (chapter, part, last ssg number in that part), from docs/synopsis.md's chapters
ARCS = [(1, 1, 22), (1, 2, 38), (1, 3, 64), (1, 4, 96), (1, 5, 118),
        (2, 1, 153), (2, 2, 170), (2, 3, 191), (2, 4, 199),
        (3, 1, 223), (3, 2, 285), (3, 3, 305),
        (4, 1, 317), (4, 2, 321), (4, 3, 342), (4, 4, 349), (4, 5, 372)]


def clean(text):
    return re.sub(r"\s*\{n\}\s*", " ", text.replace("{page}", " | ")).strip()


def stretches(only):
    """Story first, then the rest; a chunk only breaks between files."""
    files = sorted((ROOT / "script").glob("*.json"), key=lambda p: (not p.name.startswith("ssg"), p.name))
    seen = set()
    for path in files:
        if only and not re.search(only, path.stem):
            continue
        lines = []
        for e in json.loads(path.read_text(encoding="utf-8")):
            if not e.get("en") or e["en"] == e["jp"] or e.get("kind") == "debug" or e["jp"] in seen:
                continue
            seen.add(e["jp"])
            who = next(iter(e.get("who") or []), "")
            lines.append(f">> {e['id']} | {who} | {clean(e['jp'])}\n{clean(e['en'])}\n")
        if lines:
            yield path.stem, lines


def chapters():
    """Story-pass files, one per arc: a chapter is about 170k tokens, more than one fresh read holds. Fixed bounds, so a fix never moves a line to another file."""
    out = ROOT / "work/qa/story/chapters"
    out.mkdir(parents=True, exist_ok=True)
    arcs = {}
    for stem, lines in stretches(r"^ssg"):
        n = int(stem[4:])
        chapter, part, last = next(a for a in ARCS if n <= a[2])
        arcs.setdefault(f"ch{chapter}_{part}_to_s{last:04d}", []).extend([f"# {stem}\n", *lines])
    for name, lines in arcs.items():
        (out / f"{name}.txt").write_text("".join(lines), encoding="utf-8", newline="\n")
    print(len(arcs), "files in", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb", type=int, default=110)
    ap.add_argument("--only", default="")
    ap.add_argument("--chapters", action="store_true", help="write work/qa/story/chapters/ for the story pass")
    args = ap.parse_args()
    if args.chapters:
        return chapters()
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("p[0-9]*.txt"):
        old.unlink()
    chunks, cur, size = [], [], 0
    for stem, lines in stretches(args.only):
        for text in [f"# {stem}\n", *lines]:
            n = len(text.encode())
            if size + n > args.kb * 1024 and cur:
                chunks.append(cur)
                cur, size = [], 0
            cur.append(text)
            size += n
    if cur:
        chunks.append(cur)
    for i, chunk in enumerate(chunks):
        (OUT / f"p{i:02d}.txt").write_text("".join(chunk), encoding="utf-8")
    print(len(chunks), "files in", OUT)


if __name__ == "__main__":
    main()

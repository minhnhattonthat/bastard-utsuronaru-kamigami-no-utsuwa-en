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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb", type=int, default=110)
    ap.add_argument("--only", default="")
    args = ap.parse_args()
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

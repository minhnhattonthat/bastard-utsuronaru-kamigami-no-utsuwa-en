"""warp_report.py: after `warp.py all`, say what the event shots actually show, and make the proof sheets.
Black = every shot from the event's start on is black. Unchanged = they all equal the map's own field shot taken just
before the event, so the event ran without changing the screen. An event with no script string has nothing to show, so
only a text event in either class is a miss.
Writes work/qa/warp/event_report.tsv (name, class, text y/n, proof shot) and docs/screenshots/warp/*.png.
Exit 1 if a text event was never seen.
"""
import csv
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(Path(__file__).parent))
from gen_scenes import entry, event_codes, has_text, maps  # noqa: E402
from skill import SKILL  # noqa: E402

W = ROOT / "work/qa/warp"
SHEETS = ROOT / "docs/screenshots/warp"
BLACK_BYTES = 400  # an all-black PNG here is ~250 bytes; any picture is far larger
START = 1800  # the route presses start here (gen_scenes.FIELD)


def md5(p):
    return hashlib.md5(p.read_bytes()).hexdigest()


def classify(d):
    """(class, proof shot). The proof is the largest changed shot: text and portraits compress worst."""
    shots = sorted(p for p in d.glob("f*.png") if p.stem[1:].isdigit())
    after = [p for p in shots if int(p.stem[1:]) > START] + [d / "final.png"]
    before = next((p for p in reversed(shots) if int(p.stem[1:]) <= START), None)
    lit = [p for p in after if p.stat().st_size >= BLACK_BYTES]
    if not lit:
        return "black", None
    base = md5(before) if before else None
    changed = [p for p in lit if md5(p) != base]
    if not changed:
        return "unchanged", None
    return "changed", max(changed, key=lambda p: p.stat().st_size)


def sheet(paths, out):
    subprocess.check_call([sys.executable, "-X", "utf8", str(Path(SKILL) / "scripts/sheet.py"), *map(str, paths),
                           "--cols", "8", "--div", "3", "--max", "48", "--out", str(out)], stdout=subprocess.DEVNULL)


def text_events():
    exe = (ROOT / "work/disc/SLPS_005.42").read_bytes()
    out = set()
    for _, mid, _, ssg, _ in maps(exe):
        for ev, span in event_codes(entry(ssg)).items():
            if has_text(*span):
                out.add(f"ev_{mid}_{ev:04d}")
    return out


def main():
    texts = text_events()
    rows = [(d.name, *classify(d), d.name in texts) for d in sorted(W.glob("ev_*"))]
    with open(W / "event_report.tsv", "w", encoding="utf-8", newline="") as f:
        csv.writer(f, delimiter="\t").writerows((n, c, "y" if t else "n", p.name if p else "") for n, c, p, t in rows)
    for kind in ("changed", "unchanged", "black"):
        print(kind, sum(c == kind for _, c, _, _ in rows), "with text", sum(c == kind and t for _, c, _, t in rows))
    SHEETS.mkdir(parents=True, exist_ok=True)
    maps_dirs = sorted(d.name for d in W.glob("map_*"))
    sheet([W / n / "final.png" for n in maps_dirs], SHEETS / "maps.png")
    sheet([W / n / "f001200.png" for n in maps_dirs], SHEETS / "map_cards.png")
    with open(Path(__file__).with_name("scenes.tsv"), encoding="utf-8", newline="") as f:
        special = [r["name"] for r in csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE) if r["group"] not in ("event", "map", "sweep", "battlemap")]
    # the last shot, unless the scene has faded out by then (ending_thanks): then its fullest shot
    # (a sweep scene stops itself and has no final shot)
    sheet([W / n / "final.png" if (W / n / "final.png").exists() and (W / n / "final.png").stat().st_size >= BLACK_BYTES
           else max((W / n).glob("f0*.png"), key=lambda p: p.stat().st_size) for n in special], SHEETS / "special.png")
    proofs = W.parent / "warp_proofs"  # a directory: 400 paths overflow the Windows command line
    shutil.rmtree(proofs, ignore_errors=True)
    proofs.mkdir()
    seen = [(n, p) for n, c, p, _ in rows if c == "changed"]
    for i, (_, p) in enumerate(seen):
        shutil.copy(p, proofs / f"f{i:06d}.png")  # sheet.py labels a shot with its number; events_index.tsv names it
    (SHEETS / "events_index.tsv").write_text("".join(f"{i}\t{n}\n" for i, (n, _) in enumerate(seen)), encoding="utf-8")
    sheet([proofs], SHEETS / "events.png")
    missed = [n for n, c, _, t in rows if t and c != "changed"]
    print("text events never seen:", " ".join(missed) or "none")
    return 1 if missed else 0


if __name__ == "__main__":
    sys.exit(main())

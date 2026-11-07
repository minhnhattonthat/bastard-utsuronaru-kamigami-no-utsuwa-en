"""qa_full.py: full-size pages of the frames behind the gate's sheets, because tour sheets are half or third scale and their text can't be read.

    python -X utf8 tools/debug/qa_full.py    -> work/qa/full/<scene>/s*.png, and events/, cards/, battlemap/

Run it after qa_tour.py on the build under review, and before any tour on the original: qa_tour.py --out work/qa/tour_jp overwrites the same frames in work/qa/warp.
Which gate id a page answers for: <group>_<scene>_sheet* = full/<scene>; proof_events* = full/events (tile N is line N of docs/screenshots/warp/events_index.tsv); proof_map_cards* = full/cards; battlemap* = full/battlemap; proof_maps* and proof_special have no text of their own beyond the above, read them as they are.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from skill import SKILL  # noqa: E402

WARP = ROOT / "work/qa/warp"
OUT = ROOT / "work/qa/full"


def sheet(out, *args):
    (OUT / out).mkdir(parents=True, exist_ok=True)
    subprocess.check_call([sys.executable, "-X", "utf8", str(Path(SKILL) / "scripts/sheet.py"), *map(str, args), "--div", "1", "--out", str(OUT / out / "s.png")], stdout=subprocess.DEVNULL)


def main():
    for group in ("system", "menu", "battle", "ending"):
        for row in (WARP / f"results_{group}.tsv").read_text(encoding="utf-8").splitlines():
            name = row.split("\t")[0]
            if not name.startswith("ending_blurbs_") or name == "ending_blurbs_19":
                sheet(name, WARP / name, "--cols", 3, "--max", 12, "--changed", 0.004)
    sheet("events", WARP.parent / "warp_proofs", "--cols", 5, "--max", 30)
    sheet("cards", *sorted(WARP.glob("map_*/f001200.png")), "--cols", 5, "--max", 30)
    names = [r.split("\t")[0] for r in (WARP / "results_battlemap.tsv").read_text(encoding="utf-8").splitlines()]
    sheet("battlemap", *[WARP / n / "final.png" for n in names if (WARP / n / "final.png").exists()], "--crop", "0,120,304,72", "--cols", 5, "--max", 75)
    print(sum(1 for _ in OUT.rglob("*.png")), "pages in", OUT)


if __name__ == "__main__":
    main()

"""qa_tour.py: the sheets the visual QA gate judges, from warp scenes on one build. About 60 sheets, one per screen family.

    python -X utf8 tools/debug/qa_tour.py build/bastard_en.cue   -> work/qa/tour/*.png; then qa_gate.py init work/qa/manifest.tsv work/qa/tour --build build/bastard_en.cue --glob "*.png"
    python -X utf8 tools/debug/qa_tour.py rom/x.cue --out work/qa/tour_jp --groups system,menu,battle,ending    the same on the original, for comparing

Don't run tour_report.py after this: it reads the warp logs, and this run has no draw log (see README, Marker tours).
"""
import argparse
import glob
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from skill import SKILL  # noqa: E402

WARP = ROOT / "work/qa/warp"
FIRST_ONLY = {"camp_items_all", "battle_forms"}  # long scrolls: the first sheet shows the layout, the draw log the words


def warp(group, cue, jobs):
    return subprocess.call([sys.executable, "-X", "utf8", str(ROOT / "tools/debug/warp.py"), "all", "--group", group, "--cue", cue, "--jobs", str(jobs)], cwd=ROOT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cue")
    ap.add_argument("--out", default=str(ROOT / "work/qa/tour"))
    ap.add_argument("--groups", default="system,menu,battle,ending,battlemap,map,event")
    a = ap.parse_args()
    out = Path(a.out)
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    groups = a.groups.split(",")
    failed = 0
    for g in groups:
        # M7 in docs/status.md: battles time out under heavy parallel load
        failed += warp(g, a.cue, 3 if g.startswith("battle") else 7) != 0
        rows = [r.split("\t")[0] for r in (WARP / f"results_{g}.tsv").read_text(encoding="utf-8").splitlines()]
        if g in ("system", "menu", "battle", "ending"):
            for name in rows:
                for i, p in enumerate(sorted(glob.glob(str(WARP / name / "sheet*.png")))):
                    if name in FIRST_ONLY and i:
                        break
                    shutil.copy(p, out / f"{g}_{name}_{Path(p).stem}.png")
        elif g == "battlemap":  # one tile per area
            shots = [str(WARP / name / "final.png") for name in rows if (WARP / name / "final.png").exists()]
            subprocess.check_call([sys.executable, "-X", "utf8", str(Path(SKILL) / "scripts/sheet.py"), *shots, "--out", str(out / "battlemap.png")], cwd=ROOT)
    if "event" in groups:  # warp_report tiles the maps and each event's proof shot
        subprocess.call([sys.executable, "-X", "utf8", str(ROOT / "tools/debug/warp_report.py")], cwd=ROOT)
        for p in glob.glob(str(ROOT / "docs/screenshots/warp/*.png")):
            shutil.copy(p, out / f"proof_{Path(p).name}")
    print(len(list(out.glob("*.png"))), "sheets in", out, "; groups with a miss:", failed)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

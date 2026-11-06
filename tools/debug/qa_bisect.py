"""qa_bisect.py: which English lines make a scene fail where the Japanese passes. Restores groups of lines to Japanese with `build.py --qa`.

    python -X utf8 tools/debug/qa_bisect.py SCENE PREFIX [PREFIX ...]      e.g. save_menu ov2_ exe_0
Prefixes are tried one at a time; the first whose restoration makes the scene pass is halved until one line is left.
"""
import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import batches  # noqa: E402
import insert  # noqa: E402

CUE = ROOT / "build/bisect.cue"
QA = ROOT / "work/qa/bisect.json"


def scene(name):
    with open(ROOT / "tools/debug/scenes.tsv", encoding="utf-8", newline="") as f:
        return next(r for r in csv.DictReader(f, delimiter="\t") if r["name"] == name)


def passes(s, ids, entries):
    QA.write_text(json.dumps({i: entries[i]["jp"] for i in ids}, ensure_ascii=False), encoding="utf-8")
    subprocess.run([sys.executable, "-X", "utf8", "build.py", "--qa", str(QA), "--out", str(CUE.with_suffix(".bin"))], cwd=ROOT, check=True, capture_output=True)
    cmd = [sys.executable, "-X", "utf8", "tools/debug/warp.py", "bisect_run", "--vars", s["vars"], "--route", s["route"], "--frames", s["frames"], "--check", s["check"], "--cue", str(CUE)]
    ok = subprocess.run(cmd, cwd=ROOT, capture_output=True).returncode == 0
    print(f"{len(ids)} restored ({ids[0]}..{ids[-1]}): {'pass' if ok else 'fail'}", flush=True)
    return ok


def main():
    s = scene(sys.argv[1])
    entries = batches.index()
    for prefix in sys.argv[2:]:
        # A stack-buffer string can't take its Japanese back at full length in this build's check: those stay English.
        ids = sorted(i for i, e in entries.items() if i.startswith(prefix) and e.get("en") and insert.buffer_cap(e) is None)
        if not ids or not passes(s, ids, entries):
            continue
        while len(ids) > 1:
            half = ids[:len(ids) // 2]
            ids = half if passes(s, half, entries) else ids[len(ids) // 2:]
        print("culprit:", ids[0], repr(entries[ids[0]]["jp"]), repr(entries[ids[0]]["en"]))
        return 0
    print("no prefix fixed it, or more than one line is needed")
    return 1


if __name__ == "__main__":
    sys.exit(main())

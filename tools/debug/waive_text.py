"""waive_text.py: docs/text_unshown.tsv from work/qa/tour_unseen.txt (run tour_report.py first), one honest reason per id.
Nothing here says a string can't be reached: these were not reached by any scene, and each reason says what else checks them.

    python -X utf8 tools/debug/waive_text.py
"""
import json
import glob
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECKED = "bytes by verify_build, width by batches.check"
REASONS = (
    (("t0382",), f"not reached: character record field; camp_chars_all hangs on the marker build at the fourth character and passes on English, whose sheet shows them; {CHECKED}"),
    (("t0386",), f"not reached: item name past the end of the camp_items_all scroll; {CHECKED}"),
    (("t0393",), f"not reached: formation needing more than one member, which the warp's party lacks; {CHECKED}"),
    (("ov1",), f"not reached: battle line needing its spell, status or event with real arguments; {CHECKED}"),
    (("ov2",), f"not reached: camp or memory-card message on a path no scene runs (full bag, bad card); {CHECKED}"),
    (("ov4",), f"not reached: ending blurb; {CHECKED}"),
    (("exe",), f"not reached: {CHECKED}"),
)


def reason(i):
    n = int(i[1:5]) if i[0] == "t" and i[1:5].isdigit() else 0
    if 551 <= n <= 643:
        return f"not reached: encounter group label, never drawn by any scene (battle_m_* loads these tables in 73 areas); {CHECKED}"
    if 644 <= n <= 736:
        return f"not reached: enemy or object name of an encounter not run (battle_m_* runs encounter 1 per area); {CHECKED}"
    for prefixes, why in REASONS:
        if i.startswith(prefixes):
            return why
    raise SystemExit(f"no reason for {i}")


def main():
    listed = {ln.split("\t")[0] for ln in (ROOT / "build/strings.tsv").read_text(encoding="utf-8").splitlines()}
    table = {}
    for p in glob.glob(str(ROOT / "script/*.json")):
        table.update({e["id"]: e for e in json.loads(Path(p).read_text(encoding="utf-8"))})
    ids = [ln.split("\t")[0] for ln in (ROOT / "work/qa/tour_unseen.txt").read_text(encoding="utf-8").splitlines()]
    ids = [i for i in ids if i in listed]
    (ROOT / "docs/text_unshown.tsv").write_text("".join(f"{i}\t{reason(i)}\n" for i in ids), encoding="utf-8", newline="\n")
    print(len(ids), Counter(reason(i).split(":")[1].split(";")[0][:40] for i in ids).most_common())


if __name__ == "__main__":
    main()

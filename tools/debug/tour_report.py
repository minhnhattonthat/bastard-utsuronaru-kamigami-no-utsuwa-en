"""tour_report.py: read the drawlog.lua lines of a marker tour. Which strings were seen, in what box width, what stayed Japanese.

    python -X utf8 tools/debug/warp.py all --cue build/bastard_marker.cue --probe tools/debug/drawlog.lua
    python -X utf8 tools/debug/tour_report.py          # summary here; tools/windows.json = id -> smallest box width seen
                                                       # work/qa/tour_unseen.txt, work/qa/tour_jp.txt = the full lists
"""
import glob
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tools" / "windows.json"


def rows():
    out = {}
    for p in glob.glob(str(ROOT / "script/*.json")):
        for e in json.loads(Path(p).read_text(encoding="utf-8")):
            out[e["id"]] = e
    return out


def main():
    table = rows()
    by_tail = defaultdict(list)
    for i in table:
        by_tail[i[-5:]].append(i)
    widths, scenes, jp, jp_scene = defaultdict(set), Counter(), Counter(), {}
    ambiguous = 0
    logs = glob.glob(str(ROOT / "work/qa/warp/*/log.txt"))
    for log in logs:
        for ln in Path(log).read_text(encoding="utf-8", errors="replace").splitlines():
            if ln.startswith("ID "):
                parts = ln.split()
                if len(parts) != 3:
                    continue
                i, w = parts[1], int(parts[2])
                if i not in table:  # a tiny field shows only the id's tail
                    hits = [h for h in by_tail.get(i, []) if not h.startswith("s")]
                    if len(hits) != 1:
                        ambiguous += 1
                        continue
                    i = hits[0]
                widths[i].add(w)
                scenes[i] += 1
            elif ln.startswith("JP "):
                b = bytes.fromhex(ln[3:].replace(" ", ""))
                t = b.decode("cp932", "replace")
                jp[t] += 1
                jp_scene.setdefault(t, Path(log).parent.name)
    OUT.write_text(json.dumps({i: min(v) for i, v in sorted(widths.items())}, indent=0) + "\n", encoding="utf-8", newline="\n")
    total, shown = Counter(), Counter()
    for i, e in table.items():
        if e["kind"] in ("text", "label"):
            g = e["id"][0] + e["kind"][0]
            total[g] += 1
            shown[g] += i in widths
    print(len(logs), "scenes;", "shown / total by source + kind:", {k: f"{shown[k]}/{total[k]}" for k in sorted(total)}, "ambiguous tails", ambiguous)
    print("box widths seen:", sorted(Counter(min(v) for v in widths.values()).items()))
    unseen = sorted(i for i, e in table.items() if e["kind"] in ("text", "label") and i not in widths)
    (ROOT / "work/qa/tour_unseen.txt").write_text("\n".join(f"{i}\t{table[i]['jp'][:40]}" for i in unseen) + "\n", encoding="utf-8")
    (ROOT / "work/qa/tour_jp.txt").write_text("\n".join(f"{n}\t{jp_scene[t]}\t{t!r}" for t, n in jp.most_common()) + "\n", encoding="utf-8")
    print("still Japanese:", len(jp), "distinct runs; first:", [t[:24] for t, _ in jp.most_common(12)])


if __name__ == "__main__":
    main()

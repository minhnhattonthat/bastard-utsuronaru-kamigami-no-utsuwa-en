"""ssg_stress.py: a --qa file that grows one script to its 64 KB limit, to prove the game can load that much (docs/re/windows.md).

    python -X utf8 tools/debug/ssg_stress.py 321 [MARGIN] > work/qa/ssg_stress.json     (raise MARGIN if the build refuses the offset)
    python -X utf8 build.py --marker --qa work/qa/ssg_stress.json --out build/stress.bin
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import extract  # noqa: E402
import insert  # noqa: E402

GP_ROOM = 0x10000  # strings must start within 64 KB of $gp
RING = 620  # keep each string under the 648-byte text ring


def main():
    eid = int(sys.argv[1])
    d = next((ROOT / "work/rbb").glob(f"{eid:04d}.*")).read_bytes()
    code_end = insert.GP_OFF
    rows = json.loads((ROOT / f"script/ssg_{eid:04d}.json").read_text(encoding="utf-8"))
    text = [e for e in rows if e["kind"] in insert.SPEECH_KINDS]
    # Code stays where it is; the strings' old slots are reused and the rest goes to the tail: only the code eats the 64 KB.
    size = int.from_bytes(d[0x14:0x18], "little") & 0x7FFFFFFF
    slots = sum(insert._slot_end(0, len(extract.encode(e["jp"])) + 1) for e in text)
    budget = GP_ROOM - (0x18 + size - code_end - slots) - (int(sys.argv[2]) if len(sys.argv) > 2 else 6000)
    marked = {e["id"]: insert.marker(e) for e in text}
    used = sum(len(extract.encode(m)) + 2 for m in marked.values())
    each = max(0, budget - used) // len(text)
    out = {}
    for e in text:
        m = marked[e["id"]]
        out[e["id"]] = m + ("x" * min(each, RING - len(extract.encode(m))))
    print(f"ssg {eid}: {len(d)} bytes on disc, {len(text)} strings, +{each} bytes each", file=sys.stderr)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()

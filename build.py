"""build.py: original disc -> build/bastard_en.bin + .cue.

    python -X utf8 build.py                 English from script/*.json; untranslated lines stay Japanese
    python -X utf8 build.py --marker        every line shows its id: build/bastard_marker.cue (docs/re/text.md)
    python -X utf8 build.py --qa FILE.json  override lines: {"id": "text"}, on top of either build
tests/test_identity.py calls build(edits=False), which must equal the original disc byte for byte.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
import check_rom
import disc
import rbb

OUT = ROOT / "build" / "bastard_en.bin"
MARKER_OUT = ROOT / "build" / "bastard_marker.bin"


def _text_source(marker, qa):
    import insert

    def text_of(e, stem, limit):
        if e["id"] in qa:
            return qa[e["id"]]
        if marker:
            return insert.marker(e, limit)
        return e["en"] or None

    return text_of


def build(out=OUT, edits=True, marker=False, qa=None):
    check_rom.check()
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(disc.BIN, out)
    with open(out, "r+b") as f:
        exe = disc.read_form1(f, *disc.FILES["SLPS_005.42"])
        arc = disc.read_form1(f, *disc.FILES["RSRCALL.RBB"])
        report = {}
        if edits:
            import cards
            import insert

            table = rbb.index(arc)

            def raw(eid):
                return rbb.unwrap(rbb.entry(arc, *table[eid]))

            exe, new, report = insert.apply(exe, raw, _text_source(marker, qa or {}), qa=marker or bool(qa))
            new.update(cards.build(raw))
            replaced = {eid: rbb.rewrap(rbb.entry(arc, *table[eid]), data) for eid, data in new.items()}
            arc, spill = rbb.relocate(arc, replaced, (disc.FILES["DUMMY"][0] - disc.FILES["RSRCALL.RBB"][0]) * 2048)
            report["entries_changed"] = len(replaced)
            report["spill_bytes"] = len(spill)
            if spill:
                disc.write_file(f, "DUMMY", spill)
            disc.write_file(f, "SLPS_005.42", exe)
            disc.write_file(f, "RSRCALL.RBB", arc)
        else:
            disc.write_file(f, "SLPS_005.42", exe)
            disc.write_file(f, "RSRCALL.RBB", rbb.pack(arc))
    out.with_suffix(".cue").write_text(f'FILE "{out.name}" BINARY\n  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n')
    if report:
        print(json.dumps({k: v for k, v in report.items() if k != "inline"}), "inline:", report.get("inline"))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--marker", action="store_true")
    ap.add_argument("--qa", help="JSON file of id -> text overrides")
    ap.add_argument("--out", help="output .bin")
    a = ap.parse_args()
    qa = json.loads(Path(a.qa).read_text(encoding="utf-8")) if a.qa else None
    print(build(Path(a.out) if a.out else (MARKER_OUT if a.marker else OUT), marker=a.marker, qa=qa))

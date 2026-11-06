"""build.py: original disc -> build/bastard_en.bin + .cue. `python -X utf8 build.py`

No edits yet (phase 3), so tests/test_identity.py requires the output to equal the original disc."""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
import check_rom
import disc
import rbb

OUT = ROOT / "build" / "bastard_en.bin"


def build(out=OUT):
    check_rom.check()
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(disc.BIN, out)
    with open(out, "r+b") as f:
        for name in ("SLPS_005.42", "RSRCALL.RBB"):
            data = disc.read_form1(f, *disc.FILES[name])
            disc.write_file(f, name, rbb.pack(data) if name == "RSRCALL.RBB" else data)
    out.with_suffix(".cue").write_text(f'FILE "{out.name}" BINARY\n  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n')
    return out


if __name__ == "__main__":
    print(build())

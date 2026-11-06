"""disc.py: read files out of the raw MODE2/2352 image. `python -X utf8 tools/disc.py extract` -> work/disc/."""
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "rom" / "Bastard!! Utsuronaru Kamigami no Utsuwa (Japan) (Rev 1).bin"
SS = 2352
# name: (lba, size in bytes as the directory records it). Root directory listing of the original disc.
FILES = {
    "SYSTEM.CNF": (23, 68),
    "SLPS_005.42": (24, 1091584),
    "RSRCALL.RBB": (557, 78738528),
    "MOVIE.MMB": (39004, 185016320),
    "ANIME.MMB": (129344, 190767104),
    "DUMMY": (222492, 36864000),
}


def read_form1(f, lba, size):
    out = bytearray()
    for i in range((size + 2047) // 2048):
        f.seek((lba + i) * SS + 24)
        out += f.read(2048)
    return bytes(out[:size])


def extract(names=("SYSTEM.CNF", "SLPS_005.42", "RSRCALL.RBB")):
    d = ROOT / "work" / "disc"
    d.mkdir(parents=True, exist_ok=True)
    with open(BIN, "rb") as f:
        for n in names:
            lba, size = FILES[n]
            (d / n).write_bytes(read_form1(f, lba, size))
            print(n, size)


if __name__ == "__main__":
    if sys.argv[1:2] == ["extract"]:
        extract()
    else:
        sys.exit(__doc__)

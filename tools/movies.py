"""movies.py: index the STR movies inside MOVIE.MMB / ANIME.MMB from sector headers; sample frames with ffmpeg for the survey.

    python -X utf8 tools/movies.py index            # work/fmv/index.tsv: file, n, start lba, sectors, frames, WxH
    python -X utf8 tools/movies.py sample [--every S]  # work/fmv/<file>_<n>/f%04d.png, one frame every S seconds (default 2)

A movie starts where the STR frame number drops back. Video sectors: subheader submode 0x42, user data starts `60 01 01 80`.
XA audio sectors (submode 0x64) interleave them. Each movie is copied raw (2352 bytes per sector) so ffmpeg's psxstr demuxer reads it.
"""
import struct
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from disc import BIN, FILES, SS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "fmv"


def index():
    rows = []
    with open(BIN, "rb") as f:
        for name in ("MOVIE.MMB", "ANIME.MMB"):
            lba0, size = FILES[name]
            n_sectors = size // 2048
            f.seek(lba0 * SS)
            cur = None
            last_frame = 0
            data = f.read(n_sectors * SS)
            for i in range(n_sectors):
                s = data[i * SS:i * SS + 64]
                if s[18] & 0x02 and s[24:28] == b"\x60\x01\x01\x80":  # video sector with an STR header
                    frame = struct.unpack_from("<I", s, 24 + 8)[0]
                    w, h = struct.unpack_from("<HH", s, 24 + 16)
                    if cur is None or frame < last_frame:
                        cur = {"file": name, "lba": lba0 + i, "start": i, "frames": 0, "w": w, "h": h}
                        rows.append(cur)
                    cur["frames"] = max(cur["frames"], frame)
                    cur["end"] = i
                    last_frame = frame
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "index.tsv", "w", encoding="utf-8") as t:
        for n, r in enumerate(rows):
            t.write(f"{r['file']}\t{n}\t{r['lba']}\t{r['end'] - r['start'] + 1}\t{r['frames']}\t{r['w']}x{r['h']}\n")
    print(len(rows), "movies")
    return rows


def sample(every=2):
    rows = [l.rstrip("\n").split("\t") for l in open(OUT / "index.tsv", encoding="utf-8")]
    with open(BIN, "rb") as f:
        for name, n, lba, count, frames, wh in rows:
            d = OUT / f"{name[:5]}_{int(n):03d}"
            d.mkdir(parents=True, exist_ok=True)
            raw = d / "m.str"
            f.seek(int(lba) * SS)
            raw.write_bytes(f.read(int(count) * SS))
            r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "psxstr", "-i", str(raw), "-an", "-vf", f"fps=1/{every}", str(d / "f%04d.png")],
                               capture_output=True, text=True)
            raw.unlink()
            print(name, n, frames, wh, "ffmpeg", r.returncode, r.stderr[:120])


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "index":
        index()
    elif cmd == "sample":
        sample(int(sys.argv[sys.argv.index("--every") + 1]) if "--every" in sys.argv else 2)
    else:
        sys.exit(__doc__)

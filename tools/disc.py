"""disc.py: read and write files in the raw MODE2/2352 image. `python -X utf8 tools/disc.py extract` -> work/disc/."""
import struct
import sys
from pathlib import Path

import numpy as np

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


_F = np.array([i << 1 ^ (0x11D if i & 0x80 else 0) for i in range(256)], np.uint8)
_B = np.zeros(256, np.uint8)
_B[np.arange(256, dtype=np.uint8) ^ _F] = np.arange(256, dtype=np.uint8)
_EDC = np.array(
    [
        (lambda v: [v := v >> 1 ^ (0xD8018001 if v & 1 else 0) for _ in range(8)][-1])(i)
        for i in range(256)
    ],
    np.uint32,
)


def _ecc(src, raw, dest, majors, minors, mult, inc):
    """ECC parity of a Reed-Solomon product code, for all sectors at once. dest = offset of the parity in the sector."""
    size = majors * minors
    a = np.zeros((len(src), majors), np.uint8)
    b = a.copy()
    for minor in range(minors):
        idx = [((m >> 1) * mult + (m & 1) + minor * inc) % size for m in range(majors)]
        t = src[:, idx]
        a ^= t
        b ^= t
        a = _F[a]
    a = _B[_F[a] ^ b]
    raw[:, dest:dest + majors] = a
    raw[:, dest + majors:dest + 2 * majors] = a ^ b


def encode_form1(raw):
    """Fill EDC and ECC of n form 1 sectors (n x 2352 uint8 array, in place) from their subheader and data."""
    edc = np.zeros(len(raw), np.uint32)
    for k in range(16, 2072):
        edc = edc >> 8 ^ _EDC[(edc ^ raw[:, k]) & 0xFF]
    raw[:, 2072:2076] = np.frombuffer(edc.astype("<u4").tobytes(), np.uint8).reshape(-1, 4)
    src = raw[:, 12:].copy()
    src[:, :4] = 0  # form 1 ECC is computed with the address zeroed
    _ecc(src, raw, 0x81C, 86, 24, 2, 86)
    src[:, 0x81C - 12:0x8C8 - 12] = raw[:, 0x81C:0x8C8]
    _ecc(src, raw, 0x8C8, 52, 43, 86, 88)


def write_file(f, name, data):
    """Write a file's new bytes into its sectors. Address and subheaders stay; EDC and ECC are recomputed for all of them."""
    lba, size = FILES[name]
    if len(data) > size:
        sys.exit(f"{name}: {len(data)} bytes, directory holds {size}: growth needs a plan (AGENTS.md Gotchas)")
    count = (len(data) + 2047) // 2048
    f.seek(lba * SS)
    raw = np.frombuffer(f.read(count * SS), np.uint8).reshape(-1, SS).copy()
    raw[:, 24:2072] = np.frombuffer(data.ljust(count * 2048, b"\0"), np.uint8).reshape(-1, 2048)
    for k in range(0, count, 4096):
        encode_form1(raw[k:k + 4096])
    f.seek(lba * SS)
    f.write(raw.tobytes())


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

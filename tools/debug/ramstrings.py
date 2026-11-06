"""ramstrings.py: which marker ids sit in a savestate's RAM, by source. Tells what a forced print can reach from that scene.

    python -X utf8 tools/debug/ramstrings.py work/states/NAME.state [REGEX]    a marker-build state; REGEX lists matches with offsets
"""
import gzip
import re as regex
import sys
from collections import Counter


def main():
    raw = open(sys.argv[1], "rb").read()
    data = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
    data = data[:0x200000]  # the state starts with main RAM; what follows is emulator state (buffers hold stray disc data)
    ids = regex.findall(rb"\[((?:exe|ov\d|t\d{4})_[0-9a-f]{5})\]", data)
    tails = regex.findall(rb"\[([0-9a-f]{5})\]", data)
    print(len(data), Counter(i.split(b"_")[0].decode() for i in ids).most_common(30), "short ids", len(tails))
    if len(sys.argv) > 2:
        for m in regex.finditer(sys.argv[2].encode(), data):
            print(hex(m.start()), m.group().decode("latin1"))


if __name__ == "__main__":
    main()

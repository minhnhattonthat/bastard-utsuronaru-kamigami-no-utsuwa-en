"""re.py: code recon helpers over the EXE or an overlay.

  python -X utf8 tools/re.py imm 0xD368             instructions with that 16-bit immediate
  python -X utf8 tools/re.py jal 0x8004CA2C         callers
  python -X utf8 tools/re.py dis ADDR [N]           disassemble
  python -X utf8 tools/re.py str ADDR               SJIS string at an address
  --ov N  uses RBB entry N (0-4, overlays) instead of the EXE; --base HEX is its load address (default OV_BASE).
Addresses are RAM addresses; the EXE loads at 0x80010000 from file offset 0x800.
"""
import glob
import struct
import sys
from pathlib import Path

import capstone

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "work" / "disc" / "SLPS_005.42"
EXE_BASE = 0x8000F800  # RAM address of file offset 0
# Overlay load addresses, verified in docs/re/code.md.
OV_BASE = {0: 0x800BF998, 1: 0x800BF998, 2: 0x800BF998, 3: 0x800BF998, 4: 0x800BF998}


def load(ov=None):
    if ov is None:
        return EXE.read_bytes(), EXE_BASE
    return Path(glob.glob(str(ROOT / f"work/rbb/{ov:04d}.*"))[0]).read_bytes(), OV_BASE[ov]


def words(d):
    return struct.iter_unpack("<I", d[:len(d) & ~3])


def imm(d, base, value):
    return [base + i * 4 for i, (w,) in enumerate(words(d)) if w & 0xFFFF == value and w >> 26 not in (0, 2, 3)]


def jal(d, base, target):
    op = 0x0C000000 | ((target >> 2) & 0x03FFFFFF)
    return [base + i * 4 for i, (w,) in enumerate(words(d)) if w == op]


def dis(d, base, addr, n=40):
    md = capstone.Cs(capstone.CS_ARCH_MIPS, capstone.CS_MODE_MIPS32 + capstone.CS_MODE_LITTLE_ENDIAN)
    md.skipdata = True
    off = addr - base
    return [f"{i.address:08X} {i.mnemonic:8} {i.op_str}" for i in md.disasm(d[off:off + n * 4], addr)]


def cstr(d, base, addr):
    off = addr - base
    return d[off:off + 200].split(b"\0")[0].decode("cp932", "replace")


def main(argv):
    ov = None
    if "--ov" in argv:
        i = argv.index("--ov")
        ov = int(argv[i + 1])
        del argv[i:i + 2]
    base_override = None
    if "--base" in argv:
        i = argv.index("--base")
        base_override = int(argv[i + 1], 16)
        del argv[i:i + 2]
    if len(argv) < 2:
        sys.exit(__doc__)
    cmd, val = argv[0], int(argv[1], 16)
    d, base = load(ov)
    if base_override is not None:
        base = base_override
    if cmd == "imm":
        for a in imm(d, base, val):
            print("\n".join(dis(d, base, a, 1)))
    elif cmd == "jal":
        for a in jal(d, base, val):
            print(f"{a:08X}")
    elif cmd == "dis":
        print("\n".join(dis(d, base, val, int(argv[2]) if len(argv) > 2 else 40)))
    elif cmd == "str":
        print(cstr(d, base, val))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])

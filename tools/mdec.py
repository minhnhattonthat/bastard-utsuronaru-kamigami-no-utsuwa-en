"""mdec.py: PS1 STR v2 video frames: bitstream <-> blocks <-> YCbCr planes, for redrawing burned-in movie captions.

    python -X utf8 tools/mdec.py verify A.str [..]   every frame: parse, re-encode, must equal the original bytes

A frame's demuxed data: u16 words count, u16 0x3800, u16 qscale, u16 version 2, then a bitstream read as 16-bit LE words,
MSB first. Macroblocks run in columns (top to bottom, then right), each Cr, Cb, Y1, Y2, Y3, Y4. A block is a 10-bit
signed DC, then MPEG-1 table B.14 AC codes, then EOB `10`. Escape: 000001, 6-bit run, 10-bit signed level.
"""
import struct
import sys
from pathlib import Path

import numpy as np
from scipy.fft import dctn, idctn

SS = 2352
VIDEO_MAGIC = b"\x60\x01\x01\x80"
PAYLOAD = 2016  # video bytes per sector, after the 32-byte STR header
IQ = np.array(
    [2, 16, 19, 22, 26, 27, 29, 34, 16, 16, 22, 24, 27, 29, 34, 37, 19, 22, 26, 27, 29, 34, 34, 38, 22, 22, 26, 27, 29, 34, 37, 40,
     22, 26, 27, 29, 32, 35, 40, 48, 26, 27, 29, 32, 35, 40, 48, 58, 26, 27, 29, 34, 38, 46, 56, 69, 27, 29, 35, 38, 46, 56, 69, 83],
    float,
).reshape(8, 8)
ZIGZAG = [0, 1, 8, 16, 9, 2, 3, 10, 17, 24, 32, 25, 18, 11, 4, 5, 12, 19, 26, 33, 40, 48, 41, 34, 27, 20, 13, 6, 7, 14, 21, 28,
          35, 42, 49, 56, 57, 50, 43, 36, 29, 22, 15, 23, 30, 37, 44, 51, 58, 59, 52, 45, 38, 31, 39, 46, 53, 60, 61, 54, 47, 55, 62, 63]
_ZZ = np.array(ZIGZAG)
_ZZ_FLAT = IQ.flatten()[_ZZ]

# MPEG-1 B.14 without the sign bit: {run: [code of level 1, level 2, ...]}.
_AC = {
    0: "11 0100 00101 0000110 00100110 00100001 0000001010 000000011101 000000011000 000000010011 000000010000 0000000011010 "
       "0000000011001 0000000011000 0000000010111 00000000011111 00000000011110 00000000011101 00000000011100 00000000011011 "
       "00000000011010 00000000011001 00000000011000 00000000010111 00000000010110 00000000010101 00000000010100 00000000010011 "
       "00000000010010 00000000010001 00000000010000 000000000011000 000000000010111 000000000010110 000000000010101 "
       "000000000010100 000000000010011 000000000010010 000000000010001 000000000010000",
    1: "011 000110 00100101 0000001100 000000011011 0000000010110 0000000010101 000000000011111 000000000011110 000000000011101 "
       "000000000011100 000000000011011 000000000011010 000000000011001 0000000000010011 0000000000010010 0000000000010001 0000000000010000",
    2: "0101 0000100 0000001011 000000010100 0000000010100",
    3: "00111 00100100 000000011100 0000000010011",
    4: "00110 0000001111 000000010010",
    5: "000111 0000001001 0000000010010",
    6: "000101 000000011110 0000000000010100",
    7: "000100 000000010101",
    8: "0000111 000000010001",
    9: "0000101 0000000010001",
    10: "00100111 0000000010000",
    11: "00100011 0000000000011010",
    12: "00100010 0000000000011001",
    13: "00100000 0000000000011000",
    14: "0000001110 0000000000010111",
    15: "0000001101 0000000000010110",
    16: "0000001000 0000000000010101",
    17: "000000011111", 18: "000000011010", 19: "000000011001", 20: "000000010111", 21: "000000010110", 22: "0000000011111",
    23: "0000000011110", 24: "0000000011101", 25: "0000000011100", 26: "0000000011011", 27: "0000000000011111",
    28: "0000000000011110", 29: "0000000000011101", 30: "0000000000011100", 31: "0000000000011011",
}
AC = {(r, n + 1): c for r, codes in _AC.items() for n, c in enumerate(codes.split())}
EOB, ESC = "10", "000001"
END = "0111111111"  # after the last block
_WINDOW = 17  # longest code, 16 bits, plus its sign
_lut = None


def _table():
    """Lookup on the next 17 bits: (bits used, run, level); run -1 = EOB, -2 = escape."""
    global _lut
    if _lut is None:
        _lut = [None] * (1 << _WINDOW)

        def fill(code, entry):
            lo = int(code, 2) << (_WINDOW - len(code))
            _lut[lo:lo + (1 << (_WINDOW - len(code)))] = [entry] * (1 << (_WINDOW - len(code)))

        fill(EOB, (2, -1, 0))
        fill(ESC, (6, -2, 0))
        for (run, level), code in AC.items():
            fill(code + "0", (len(code) + 1, run, level))
            fill(code + "1", (len(code) + 1, run, -level))
    return _lut


def _signed10(v):
    return v - 1024 if v >= 512 else v


def parse(data, w, h):
    """Frame bytes -> (qscale, blocks, bits used). A block is (dc, [(run, level), ..]); blocks hold 6 per macroblock."""
    words, magic, q, version = struct.unpack_from("<HHHH", data)
    if magic != 0x3800 or version != 2:
        raise ValueError(f"not a v2 frame: {magic:#x} v{version}")
    body = np.frombuffer(data, "<u2", (len(data) - 8) // 2, 8).byteswap().tobytes()
    bits = np.unpackbits(np.frombuffer(body + b"\0" * 4, np.uint8))
    win = np.zeros(len(bits), np.uint32)
    for k in range(_WINDOW):
        win[:len(bits) - k] = win[:len(bits) - k] << 1 | bits[k:]
    win = win[:len(bits) - _WINDOW].tolist()
    lut = _table()
    pos, blocks = 0, []
    for _ in range(((w + 15) // 16) * ((h + 15) // 16) * 6):
        dc = _signed10(win[pos] >> (_WINDOW - 10))
        pos += 10
        ac = []
        while True:
            e = lut[win[pos]]
            if e is None:
                raise ValueError(f"bad code at bit {pos}")
            pos += e[0]
            if e[1] == -1:
                break
            if e[1] == -2:
                v = win[pos] >> (_WINDOW - 16)
                pos += 16
                ac.append((v >> 10, _signed10(v & 1023)))
            else:
                ac.append(e[1:])
        blocks.append((dc, ac))
    return q, blocks, pos


def _ac_bits(run, level):
    code = AC.get((run, abs(level)))
    if code is None:
        return f"{ESC}{run:06b}{level & 1023:010b}"
    return code + ("1" if level < 0 else "0")


def encode(q, blocks):
    """Blocks -> frame bytes, without the zero padding that fills the frame's sectors."""
    parts = []
    codes = 0
    for dc, ac in blocks:
        parts.append(f"{dc & 1023:010b}")
        parts.extend(_ac_bits(r, l) for r, l in ac)
        parts.append(EOB)
        codes += len(ac) + 2
    s = "".join(parts) + END
    s += "0" * (-len(s) % 32)  # frame sizes are multiples of 4; the 8-byte header keeps that
    body = int(s, 2).to_bytes(len(s) // 8, "big")
    body = np.frombuffer(body, ">u2").astype("<u2").tobytes()
    words = (codes + 1) // 2
    words = (words + 31) // 32 * 32  # a DMA block is 32 words
    return struct.pack("<HHHH", words, 0x3800, q, 2) + body


def decode(q, blocks, w, h):
    """Blocks -> float planes (Y, Cb, Cr), Y 0-255, chroma centred on 0."""
    mw, mh = (w + 15) // 16, (h + 15) // 16
    coef = np.zeros((len(blocks), 64))
    for n, (dc, ac) in enumerate(blocks):
        coef[n, 0] = dc * 2
        k = 0
        for run, level in ac:
            k += run + 1
            coef[n, ZIGZAG[k]] = int((level * q * _ZZ_FLAT[k] + (4 if level > 0 else -4)) / 8)
    px = idctn(coef.reshape(-1, 8, 8), axes=(1, 2), norm="ortho")
    y, cb, cr = np.zeros((mh * 16, mw * 16)), np.zeros((mh * 8, mw * 8)), np.zeros((mh * 8, mw * 8))
    for mx in range(mw):
        for my in range(mh):
            b = (mx * mh + my) * 6
            cr[my * 8:my * 8 + 8, mx * 8:mx * 8 + 8] = px[b]
            cb[my * 8:my * 8 + 8, mx * 8:mx * 8 + 8] = px[b + 1]
            y[my * 16:my * 16 + 16, mx * 16:mx * 16 + 16] = np.block([[px[b + 2], px[b + 3]], [px[b + 4], px[b + 5]]])
    return y + 128, cb, cr


def _plane_block(plane, q):
    c = dctn(plane, norm="ortho")
    dc = int(np.clip(np.rint(c[0, 0] / 2), -512, 511))
    level = np.clip(np.rint(c.flatten()[_ZZ] * 8 / (q * _ZZ_FLAT)), -512, 511).astype(int)
    level[0] = 0
    ac, run = [], 0
    for lv in level[1:].tolist():
        if lv:
            ac.append((run, lv))
            run = 0
        else:
            run += 1
    return dc, ac


def macroblock(y, cb, cr, mx, my, q):
    """The 6 blocks of one macroblock from float planes (decode's scale)."""
    out = [_plane_block(p[my * 8:my * 8 + 8, mx * 8:mx * 8 + 8], q) for p in (cr, cb)]
    for sy, sx in ((0, 0), (0, 8), (8, 0), (8, 8)):
        out.append(_plane_block(y[my * 16 + sy:my * 16 + sy + 8, mx * 16 + sx:mx * 16 + sx + 8] - 128, q))
    return out


def recode(data, w, h, changed, planes, limit, max_words):
    """New frame bytes: macroblocks flagged in `changed` (mh x mw bool) come from `planes`, all others stay verbatim.

    If the result passes `limit` bytes or the decoder's buffer (`max_words`), qscale rises and the whole frame is re-quantised.
    Returns (bytes, qscale used)."""
    q0, blocks, _ = parse(data, w, h)
    mw, mh = (w + 15) // 16, (h + 15) // 16
    y, cb, cr = planes
    out = list(blocks)
    for mx in range(mw):
        for my in range(mh):
            if changed[my, mx]:
                out[(mx * mh + my) * 6:(mx * mh + my + 1) * 6] = macroblock(y, cb, cr, mx, my, q0)
    frame = encode(q0, out)
    q = q0
    while len(frame) > limit or struct.unpack_from("<H", frame)[0] > max_words:
        q += 1
        if q > 63:
            raise ValueError("frame does not fit at any qscale")
        out = []
        for mx in range(mw):
            for my in range(mh):
                out.extend(macroblock(y, cb, cr, mx, my, q))
        frame = encode(q, out)
    return frame, q


def to_rgb(y, cb, cr):
    """Planes -> RGB uint8 as the MDEC outputs it (no filtering of the chroma), to look at frames."""
    cb2, cr2 = np.kron(cb, np.ones((2, 2))), np.kron(cr, np.ones((2, 2)))
    r = y + 1.402 * cr2
    g = y - 0.3437 * cb2 - 0.7143 * cr2
    b = y + 1.772 * cb2
    return np.clip(np.rint(np.stack((r, g, b), 2)), 0, 255).astype(np.uint8)


def frames(raw):
    """Video frames of a raw STR: {number: dict(sectors=[indices], data=bytes, w, h)}, with data at its sector capacity."""
    out = {}
    for i in range(len(raw) // SS):
        s = raw[i * SS:(i + 1) * SS]
        if s[18] & 2 and s[24:28] == VIDEO_MAGIC:
            n = struct.unpack_from("<I", s, 32)[0]
            f = out.setdefault(n, {"sectors": [], "data": bytearray(), "w": struct.unpack_from("<H", s, 40)[0], "h": struct.unpack_from("<H", s, 42)[0],
                                   "size": struct.unpack_from("<I", s, 36)[0]})
            f["sectors"].append(i)
            f["data"] += s[24 + 32:24 + 32 + PAYLOAD]
    return out


def verify(path):
    raw = Path(path).read_bytes()
    fr = frames(raw)
    bad = 0
    for n, f in fr.items():
        d = bytes(f["data"])
        try:
            q, blocks, _ = parse(d[:f["size"]], f["w"], f["h"])
        except (ValueError, IndexError) as e:
            print(path, n, "parse failed:", e)
            bad += 1
            continue
        new = encode(q, blocks)
        if new != d[:len(new)] or d[len(new):].strip(b"\0"):
            at = next((k for k in range(min(len(new), len(d))) if new[k] != d[k]), len(new))
            print(path, n, f"differs at byte {at}: new {len(new)}, frame size {f['size']}, tail {d[len(new):len(new) + 8].hex()}")
            bad += 1
            if bad > 8:
                break
    print(path, len(fr), "frames,", bad, "bad")
    return bad


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "verify":
        sys.exit(1 if sum(verify(p) for p in sys.argv[2:]) else 0)
    sys.exit(__doc__)

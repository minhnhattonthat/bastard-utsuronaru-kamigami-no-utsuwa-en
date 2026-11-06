"""The draw hook, run under unicorn with exact PC asserts, against the font file."""
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import engine

unicorn = pytest.importorskip("unicorn")
from unicorn import Uc, UC_ARCH_MIPS, UC_MODE_LITTLE_ENDIAN, UC_MODE_MIPS32  # noqa: E402
from unicorn import mips_const as M  # noqa: E402

RET = 0x80001000  # $ra: execution must stop exactly here
BUF = 0x80100000
SP = 0x80180000
WIDTH = 64
FG = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)


def phys(a):
    return a & 0x1FFFFFFF  # unicorn runs kseg0 addresses on the physical map


def machine(qa=False):
    uc = Uc(UC_ARCH_MIPS, UC_MODE_MIPS32 + UC_MODE_LITTLE_ENDIAN)
    uc.mem_map(0, 0x200000)
    blob, syms = engine.assemble(qa=qa)
    uc.mem_write(phys(engine.HOOK), blob)
    return uc, syms


@pytest.mark.parametrize("entry", ["vwf1", "vwf8"])
def test_qa_hook_logs_each_glyph_to_the_ring_and_still_draws(entry):
    uc, syms = machine(qa=True)
    uc.mem_write(phys(engine.COLOURS), bytes(16) + bytes(FG) + bytes(4))
    uc.mem_write(phys(SP + 0x10), struct.pack("<I", 1))
    for code in (ord("A"), ord("b")):
        for reg, val in ((M.UC_MIPS_REG_A0, BUF), (M.UC_MIPS_REG_A1, WIDTH), (M.UC_MIPS_REG_A2, 0), (M.UC_MIPS_REG_A3, code),
                         (M.UC_MIPS_REG_SP, SP), (M.UC_MIPS_REG_RA, RET)):
            uc.reg_write(reg, val)
        uc.emu_start(syms[entry], RET, count=200000)
        assert uc.reg_read(M.UC_MIPS_REG_PC) == RET
        assert uc.reg_read(M.UC_MIPS_REG_V0) == engine.FONT[code][0]
    assert struct.unpack("<I", uc.mem_read(phys(engine.RING - 4), 4))[0] == 8
    assert struct.unpack("<II", uc.mem_read(phys(engine.RING), 8)) == (WIDTH << 16 | ord("A"), WIDTH << 16 | ord("b"))


def run(code, x=0, colour=1, w=WIDTH, entry="vwf1"):
    uc, syms = machine()
    uc.mem_write(phys(engine.COLOURS), bytes(16) + bytes(FG) + bytes(4))
    uc.mem_write(phys(SP + 0x10), struct.pack("<I", colour))
    uc.mem_write(phys(BUF), b"\xAA" * (w // 2 * 16))  # stale pixels: the hook must overwrite the whole cell it draws
    for reg, val in ((M.UC_MIPS_REG_A0, BUF), (M.UC_MIPS_REG_A1, w), (M.UC_MIPS_REG_A2, x), (M.UC_MIPS_REG_A3, code),
                     (M.UC_MIPS_REG_SP, SP), (M.UC_MIPS_REG_RA, RET)):
        uc.reg_write(reg, val)
    uc.emu_start(syms[entry], RET, count=200000)
    assert uc.reg_read(M.UC_MIPS_REG_PC) == RET
    return uc, uc.reg_read(M.UC_MIPS_REG_V0)


def pixels(uc, w=WIDTH, rows=12):
    data = uc.mem_read(phys(BUF), w // 2 * rows)
    return [[(data[r * w // 2 + c // 2] >> (4 * (c & 1))) & 15 for c in range(w)] for r in range(rows)]


def expected(code, x):
    adv, rows = engine.FONT[code]
    want = {}
    for r in range(12):
        bits = rows[r] if r < engine.ROWS else 0
        above = rows[r - 1] if 0 < r <= engine.ROWS else 0
        for c in range(adv):
            on = bits & (0x80 >> c)
            shadow = c > 0 and above & (0x80 >> (c - 1))
            want[r, x + c] = FG[r] if on else 15 if shadow else 0
    return want


@pytest.mark.parametrize("code", [ord(c) for c in "AgM.!~ "])
@pytest.mark.parametrize("x", [0, 7, 12])
def test_draws_the_glyph_with_its_shadow_and_advances_by_its_width(code, x):
    uc, ret = run(code, x)
    px = pixels(uc)
    assert ret == x + engine.FONT[code][0]
    for (r, c), v in expected(code, x).items():
        assert px[r][c] == v, (chr(code), r, c)


def test_leaves_the_neighbouring_pixels_alone():
    uc, ret = run(ord("A"), 7)
    px = pixels(uc)
    assert px[0][6] == 0xA and px[0][ret] == 0xA


def test_clips_at_the_window_edge():
    uc, ret = run(ord("M"), 60)
    assert ret == 64


def test_font8_entry_draws_the_same_glyphs():
    uc, ret = run(ord("A"), 0, entry="vwf8")
    assert ret == engine.FONT[ord("A")][0]


@pytest.mark.parametrize("code,entry,orig", [(0x82A0, "vwf1", engine.ORIG[1]), (0x82A0, "vwf8", engine.ORIG[8]), (0x0A, "vwf1", engine.ORIG[1])])
def test_anything_else_goes_to_the_original_function(code, entry, orig):
    uc, syms = machine()
    uc.reg_write(M.UC_MIPS_REG_A3, code)
    uc.emu_start(syms[entry], orig, count=100)
    assert uc.reg_read(M.UC_MIPS_REG_PC) == orig


def call(uc, syms, name, **regs):
    for reg, val in regs.items():
        uc.reg_write(getattr(M, f"UC_MIPS_REG_{reg.upper()}"), val)
    uc.reg_write(M.UC_MIPS_REG_RA, RET)
    uc.emu_start(syms[name], RET, count=100000)
    assert uc.reg_read(M.UC_MIPS_REG_PC) == RET
    return uc.reg_read(M.UC_MIPS_REG_V0)


@pytest.mark.parametrize("text,cells", [
    (b"", 0),
    ("あいう".encode("cp932"), 3),      # Japanese counts as the original function did
    ("Ａ".encode("cp932"), 1),
    (b"\x0a", 1),
])
def test_cell_count_is_unchanged_for_japanese(text, cells):
    uc, syms = machine()
    uc.mem_write(phys(BUF), text + b"\0")
    assert call(uc, syms, "cells", a0=BUF) == cells


def test_cell_count_of_english_is_its_pixel_width_rounded_up():
    uc, syms = machine()
    text = "The quick brown fox"
    uc.mem_write(phys(BUF), text.encode() + b"\0")
    px = engine.width(text)
    assert call(uc, syms, "cells", a0=BUF) == (px + 11) // 12 < len(text)


def test_cell_count_mixes_english_and_japanese():
    uc, syms = machine()
    uc.mem_write(phys(BUF), b"AB" + "あ".encode("cp932") + b"\0")
    assert call(uc, syms, "cells", a0=BUF) == (engine.width("AB") + 12 + 11) // 12


@pytest.mark.parametrize("name", ["met1", "met8"])
def test_metric_gives_each_letters_advance(name):
    uc, syms = machine()
    call(uc, syms, name, a0=BUF, a1=ord("M"))
    w, h = struct.unpack("<HH", uc.mem_read(phys(BUF), 4))
    assert (w, h) == (engine.FONT[ord("M")][0], 12)


@pytest.mark.parametrize("name,font", [("met1", 1), ("met8", 8)])
def test_metric_of_anything_else_goes_to_the_original(name, font):
    uc, syms = machine()
    uc.reg_write(M.UC_MIPS_REG_A1, 0x82A0)
    uc.emu_start(syms[name], engine.METRIC[font], count=100)
    assert uc.reg_read(M.UC_MIPS_REG_PC) == engine.METRIC[font]


def test_font_fits_a_row_byte_and_covers_ascii():
    assert all(1 <= adv <= 8 for adv, _ in engine.FONT.values())
    assert sorted(engine.FONT) == list(range(0x20, 0x7F))


def test_window_pools_double_in_the_one_move_that_sets_size_and_limit():
    exe_path = ROOT / "work" / "disc" / "SLPS_005.42"
    if not exe_path.exists():
        pytest.skip("needs tools/disc.py extract")
    exe = bytearray(exe_path.read_bytes())
    engine.patch_exe(exe)
    at = engine.POOL_SIZE_ARG - 0x8000F800
    assert struct.unpack_from("<I", exe, at)[0] == 0x00058840  # sll $s1,$a1,1
    # 8004A8C4 still takes the size from $s1 for the allocation, 8004A8D0 for the limit
    assert struct.unpack_from("<I", exe, 0x8004A8C4 - 0x8000F800)[0] == 0x02203021
    assert struct.unpack_from("<I", exe, 0x8004A8D0 - 0x8000F800)[0] == 0xAE110064


def test_rebuilt_script_ends_every_string_on_its_own_nul():
    import json

    import insert
    raw_path = ROOT / "work" / "rbb" / "0010.ssg_.bin"
    if not raw_path.exists():
        pytest.skip("needs tools/rbb.py unpack")
    rows = json.loads((ROOT / "script" / "ssg_0010.json").read_text(encoding="utf-8"))
    # Every line longer than any Japanese slot goes to the tail, so strings sit back to back there.
    text = {e["id"]: e["id"] + " " + "x" * 300 for e in rows if e["kind"] in insert.SPEECH_KINDS}
    out = insert.rebuild_ssg(raw_path.read_bytes(), rows, "ssg_0010", lambda e, s, l: text.get(e["id"]))
    for e in rows:
        if e["id"] in text:
            at = (struct.unpack_from("<I", out, e["refs"][0])[0] & 0xFFFF) + insert.GP_OFF
            assert out[at:out.index(b"\0", at)] == insert.blob(text[e["id"]], e["term"])[:-1]


def _exe_row(eid):
    import json

    rows = json.loads((ROOT / "script" / "exe.json").read_text(encoding="utf-8"))
    return next(e for e in rows if e["id"] == eid)


@pytest.mark.parametrize("eid", ["exe_00920", "exe_00938", "exe_00894", "exe_008dc", "exe_012d0", "exe_00974"])
def test_marker_of_a_string_expanded_on_the_stack_keeps_within_its_buffer(eid):
    import extract
    import insert

    e = _exe_row(eid)
    assert len(extract.encode(insert.marker(e, insert.buffer_cap(e)))) + 1 <= insert.buffer_cap(e)


def test_full_field_name_leaves_the_next_field_alone():
    import insert

    jp = "アイウエオカキクケコ"  # 20 bytes, no NUL: the next field starts right after it
    d = bytearray(jp.encode("cp932") + b"\x14\0\0\0")
    e = {"id": "t", "off": 0, "term": "", "max": 20, "jp": jp}
    assert insert._field_room(d, e) == 20
    insert._write_fixed(d, e, "X" * 19)
    assert d == b"X" * 19 + b"\0\x14\0\0\0"
    with pytest.raises(ValueError):
        insert._write_fixed(d, e, "X" * 20)


def test_stack_buffer_sizes_match_the_code():
    sys.path.insert(0, str(ROOT / "tools" / "debug"))
    import extract
    import fmt_sites

    exe = ROOT / "work" / "disc" / "SLPS_005.42"
    if not exe.exists():
        pytest.skip("needs tools/disc.py extract")
    calls = {c[0]: c for c in fmt_sites.audit(exe.read_bytes(), extract.EXE_BASE)}
    assert calls[0x8003B300][4] == calls[0x8003B318][4] == 56


def test_hook_and_font_stay_in_the_free_block():
    blob, _ = engine.assemble()
    assert engine.HOOK + len(blob) < engine.LEVEL2[1]

"""engine.py: the English font and its draw hook (docs/re/text.md, Font). Assembled here with keystone, placed in the EXE.

The game's text goes through a table of draw functions per font id (0x8009E08C). Fonts 1 (12x12 text) and 8 (6x12 names)
draw Shift-JIS from the 12x11 font in the EXE and advance by a fixed cell. The hook sits in front of both: printable ASCII
draws from fonts/vwf12.txt and advances by the glyph's width, anything else goes to the original function. The renderer
already takes the returned x as the next pen position, so nothing else needs to know the font is proportional.

Space: the hook and font go in the font's level 2 kanji block (the script has no use for it once it is English). What is
left of the block holds strings moved out of the EXE and overlays: FREE.
"""
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FONT_FILE = ROOT / "fonts" / "vwf12.txt"
FIRST, LAST = 0x20, 0x7E
ROWS = 11  # rows of the source font's cell; the 12th row of the text cell only holds shadow
LEVEL2 = (0x80020484, 0x8002E59C)  # 8004DFF4: level 2 kanji start at 0x80020481; 0xD3E glyphs of 17 bytes
HOOK = LEVEL2[0]
FONT_TABLE = 0x8009E08C
ORIG = {1: 0x8004E1A8, 8: 0x8004EE04}
COLOURS = 0x8009E1A0  # 16 bytes per colour: the foreground per row, as both original functions read it
# Sizes follow the font too, or a box sized for n characters at 12 px each gets twice the width English needs, and a long
# line overruns the sprite pool and hangs the game (seen in the save menu). 8004DB9C sums a per-font metric function:
METRIC_TABLE = 0x8009E068
METRIC = {1: 0x8004DFD8, 8: 0x8004EDE4}
# Window code asks 8004FA7C for a string's length in cells: now pixels / 12, rounded up. Unchanged for Japanese.
CHAR_COUNT = 0x8004FA7C
# Each window holds its strings' bitmaps and primitives in one pool sized by its caller (8004A86C; the camp command box: 0x500).
# English can be wider than the Japanese it replaces; an overrun fails the assert at 8004A534 (sprman.cpp), which spins forever:
# the box never appears and input stops. All pools double: the one move sets both the allocation and the limit at +0x64.
POOL_SIZE_ARG = 0x8004A884
LIST_PAD = 0x80045DD0  # delay slot: the %-Ns width of the save list line
LIST_WIDEN = 0x80045DF0  # jal 80053E64: ASCII to full width
LIST_WIDEN_FN = 0x80053E64
# Field yes/no prompt, 8003AF88: x of button, label, button, label from the box's left, set for はい and いいえ (ink ends at 96 of 96).
# `Yes`, `No` end at 73, so the row sits 23 px left of centre.
PROMPT_SHIFT = 11
PROMPT_ROW = (  # (address, original word, new word): addiu reg,$s0,x
    (0x8003B048, 0x02003821, 0x26070000 + PROMPT_SHIFT),  # was move $a3,$s0
    (0x8003B078, 0x26050010, 0x26050010 + PROMPT_SHIFT),
    (0x8003B0A8, 0x2607002C, 0x2607002C + PROMPT_SHIFT),
    (0x8003B0BC, 0x2605003C, 0x2605003C + PROMPT_SHIFT),
)
LIST_COLUMN = 23  # a map name's longest; the format's own space makes it 24


def load_font(path=FONT_FILE):
    """{code: (advance, [row byte] * ROWS)}, MSB = leftmost. Advance = glyph width + 1 gap column, which holds the shadow."""
    glyphs, cur = {}, None
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.startswith("#") and not re.fullmatch(r"[#.]+", ln):
            continue
        if ln.startswith("= "):
            name = ln[2:]
            if name.startswith("space "):
                glyphs[0x20] = (int(name.split()[1]) + 1, [0] * ROWS)
                cur = None
            else:
                assert len(name) == 1, ln
                cur = []
                glyphs[ord(name)] = cur
        elif ln:
            cur.append(ln)
    out = {}
    for code, g in glyphs.items():
        if isinstance(g, tuple):
            out[code] = g
            continue
        w = max(map(len, g))
        assert 1 <= w <= 7 and len(g) <= ROWS - 1, (chr(code), w, len(g))
        rows = [0] + [int(r.replace(".", "0").replace("#", "1").ljust(8, "0"), 2) for r in g]
        out[code] = (w + 1, rows + [0] * (ROWS - len(rows)))
    missing = [chr(c) for c in range(FIRST, LAST + 1) if c not in out]
    assert not missing, missing
    return out


FONT = load_font()


def width(text):
    """Pixel width of plain ASCII text (no tokens) in the English font."""
    return sum(FONT[ord(c)][0] for c in text)


def font_bytes():
    n = LAST - FIRST + 1
    adv = bytes(FONT[c][0] for c in range(FIRST, LAST + 1))
    rows = b"".join(bytes(FONT[c][1]) for c in range(FIRST, LAST + 1))
    assert len(adv) == n and len(rows) == n * ROWS
    return adv + rows


def _hi(a):
    return (a + 0x8000) >> 16 & 0xFFFF


def _lo(a):
    return a & 0xFFFF


# QA builds only: every glyph drawn goes to a ring in low RAM as (box width << 16 | code), drained by tools/debug/drawlog.lua
# each frame. Breakpoints on the draw path run the emulator under the debugger, far too slow for a tour of every scene.
# Just below the stack, above the heap; QA only, a release never writes here. Not lower: at 801F0000 the marker build's heap
# reached it on map 2_11 (heap top 801F14D4) and the hook overwrote the loaded script, which hung two events.
# Moved again: the camp's heap (the 60-byte name buffer at 800C47B0) reached 801FCFFC with all characters joined, and the hook then
# overwrote live heap, so the marker build hung where English does not. Kernel RAM 8000C000-8000E000 stays zero in every state read.
RING = 0x8000C400
RING_SIZE = 0x1000
RING_LOG = """
    lui   $t9, {ring_hi}
    lw    $t1, {ring_idx}($t9)
    andi  $t0, $a3, 0xffff
    sll   $t2, $a1, 16
    or    $t0, $t0, $t2
    addu  $t2, $t9, $t1
    sw    $t0, {ring}($t2)
    addiu $t1, $t1, 4
    andi  $t1, $t1, {ring_mask}
    sw    $t1, {ring_idx}($t9)
"""

ASM = """
.set noreorder
vwf1:
{qa}
    andi  $t0, $a3, 0xffff
    addiu $t1, $t0, -0x20
    sltiu $t1, $t1, 0x5f
    bnez  $t1, body
    nop
    lui   $t9, {orig1_hi}
    addiu $t9, $t9, {orig1_lo}
    jr    $t9
    nop
vwf8:
{qa}
    andi  $t0, $a3, 0xffff
    addiu $t1, $t0, -0x20
    sltiu $t1, $t1, 0x5f
    bnez  $t1, body
    nop
    lui   $t9, {orig8_hi}
    addiu $t9, $t9, {orig8_lo}
    jr    $t9
    nop
met1:
    andi  $t0, $a1, 0xffff
    addiu $t0, $t0, -0x20
    sltiu $t1, $t0, 0x5f
    bnez  $t1, metric
    nop
    lui   $t9, {met1_hi}
    addiu $t9, $t9, {met1_lo}
    jr    $t9
    nop
met8:
    andi  $t0, $a1, 0xffff
    addiu $t0, $t0, -0x20
    sltiu $t1, $t0, 0x5f
    bnez  $t1, metric
    nop
    lui   $t9, {met8_hi}
    addiu $t9, $t9, {met8_lo}
    jr    $t9
    nop
metric:
    lui   $t9, {font_hi}
    addiu $t9, $t9, {font_lo}
    addu  $t9, $t9, $t0
    lbu   $t1, 0($t9)
    ori   $t2, $zero, 12
    sh    $t1, 0($a0)
    sh    $t2, 2($a0)
    ori   $t1, $zero, 4
    sb    $t1, 6($a0)
    jr    $ra
    sb    $zero, 7($a0)
cells:
    move  $v0, $zero
    lui   $t3, {font_hi}
    addiu $t3, $t3, {font_lo}
next:
    lbu   $v1, 0($a0)
    addiu $a0, $a0, 1
    beqz  $v1, cellsdone
    addiu $t0, $v1, -0x20
    sltiu $t1, $t0, 0x5f
    beqz  $t1, wide
    addu  $t2, $t3, $t0
    lbu   $t2, 0($t2)
    b     next
    addu  $v0, $v0, $t2
wide:
    addiu $t0, $v1, -0x81
    sltiu $t0, $t0, 0x1f
    bnez  $t0, lead
    addiu $t0, $v1, -0xe0
    sltiu $t0, $t0, 0x10
    beqz  $t0, onecell
    nop
lead:
    lbu   $t0, 0($a0)
    nop
    beqz  $t0, onecell
    nop
    addiu $a0, $a0, 1
onecell:
    b     next
    addiu $v0, $v0, 12
cellsdone:
    addiu $v0, $v0, 11
    ori   $t0, $zero, 12
    divu  $zero, $v0, $t0
    mflo  $v0
    jr    $ra
    nop
body:
    addiu $t0, $t0, -0x20
    lui   $t9, {font_hi}
    addiu $t9, $t9, {font_lo}
    addu  $t1, $t9, $t0
    lbu   $t2, 0($t1)
    sll   $t1, $t0, 3
    addu  $t1, $t1, $t0
    addu  $t1, $t1, $t0
    addu  $t1, $t1, $t0
    addu  $t3, $t9, $t1
    addiu $t3, $t3, 95
    lh    $t4, 0x10($sp)
    nop
    blez  $t4, colour
    nop
    ori   $t4, $zero, 1
colour:
    sll   $t4, $t4, 4
    lui   $t5, {col_hi}
    addiu $t5, $t5, {col_lo}
    addu  $t4, $t4, $t5
    sll   $a1, $a1, 16
    sra   $a1, $a1, 16
    sll   $a2, $a2, 16
    sra   $a2, $a2, 16
    addu  $v0, $a2, $t2
    slt   $t5, $a1, $v0
    beqz  $t5, start
    nop
    move  $v0, $a1
start:
    move  $t5, $zero
    move  $t2, $zero
    move  $v1, $zero
row:
    srl   $t6, $t2, 1
    move  $t7, $zero
    sltiu $at, $t5, 11
    beqz  $at, blank
    nop
    lbu   $t7, 0($t3)
    addiu $t3, $t3, 1
blank:
    move  $t2, $t7
    lbu   $t8, 0($t4)
    addiu $t4, $t4, 1
    move  $a3, $a2
col:
    slt   $at, $a3, $v0
    beqz  $at, rowdone
    nop
    move  $t9, $zero
    andi  $at, $t6, 0x80
    beqz  $at, noshadow
    nop
    ori   $t9, $zero, 15
noshadow:
    andi  $at, $t7, 0x80
    beqz  $at, plot
    nop
    move  $t9, $t8
plot:
    addu  $at, $v1, $a3
    sra   $at, $at, 1
    addu  $at, $a0, $at
    lbu   $t0, 0($at)
    andi  $t1, $a3, 1
    bnez  $t1, odd
    nop
    andi  $t0, $t0, 0xf0
    b     store
    or    $t0, $t0, $t9
odd:
    andi  $t0, $t0, 0x0f
    sll   $t9, $t9, 4
    or    $t0, $t0, $t9
store:
    sb    $t0, 0($at)
    addiu $a3, $a3, 1
    sll   $t7, $t7, 1
    b     col
    sll   $t6, $t6, 1
rowdone:
    addu  $v1, $v1, $a1
    addiu $t5, $t5, 1
    sltiu $at, $t5, 12
    bnez  $at, row
    nop
    jr    $ra
    nop
listname:
    move  $t0, $zero
listloop:
    lbu   $t1, 0($a1)
    nop
    sb    $t1, 0($a0)
    addiu $a1, $a1, 1
    addiu $t0, $t0, 1
    sltiu $at, $t0, 24
    bnez  $at, listloop
    addiu $a0, $a0, 1
    lui   $at, 0x8005
    ori   $at, $at, 0x3e64
    jr    $at
    nop
"""
LISTNAME_WORDS = 13  # instructions in listname, the last thing in ASM


def assemble(addr=HOOK, qa=False):
    """-> (bytes of code + font, {'vwf1': address, 'vwf8': address}). The font follows the code, word aligned."""
    import keystone  # build-time only

    ks = keystone.Ks(keystone.KS_ARCH_MIPS, keystone.KS_MODE_MIPS32 + keystone.KS_MODE_LITTLE_ENDIAN)
    log = RING_LOG.format(ring_hi=_hi(RING), ring_idx=_s16(RING - 4), ring=_s16(RING), ring_mask=RING_SIZE - 1) if qa else ""
    fmt = dict(orig1_hi=_hi(ORIG[1]), orig1_lo=_s16(ORIG[1]), orig8_hi=_hi(ORIG[8]), orig8_lo=_s16(ORIG[8]),
               col_hi=_hi(COLOURS), col_lo=_s16(COLOURS), qa=log, met1_hi=_hi(METRIC[1]), met1_lo=_s16(METRIC[1]),
               met8_hi=_hi(METRIC[8]), met8_lo=_s16(METRIC[8]))
    code = b""
    for _ in range(2):  # the font address depends on the code size, which does not depend on the address
        font = addr + len(code)
        src = ASM.format(font_hi=_hi(font), font_lo=_s16(font), **fmt)
        enc, _n = ks.asm(src, addr)
        code = bytes(enc)
    entry = (9 + (10 if qa else 0)) * 4
    met1 = addr + 2 * entry
    met8 = met1 + 9 * 4
    cells = met8 + 9 * 4 + 11 * 4
    return code + font_bytes(), {"vwf1": addr, "vwf8": addr + entry, "met1": met1, "met8": met8, "cells": cells,
                                 "listname": addr + len(code) - LISTNAME_WORDS * 4, "font": addr + len(code)}


def _s16(a):
    v = a & 0xFFFF
    return v - 0x10000 if v >= 0x8000 else v


def patch_exe(exe, base=0x8000F800, qa=False):
    """Write the hook and point fonts 1 and 8 at it, in place. -> first free address after the hook."""
    blob, syms = assemble(qa=qa)
    off = HOOK - base
    exe[off:off + len(blob)] = blob
    for font, sym, met in ((1, "vwf1", "met1"), (8, "vwf8", "met8")):
        slot = FONT_TABLE + 4 * font - base
        assert struct.unpack_from("<I", exe, slot)[0] == ORIG[font]
        struct.pack_into("<I", exe, slot, syms[sym])
        slot = METRIC_TABLE + 4 * font - base
        assert struct.unpack_from("<I", exe, slot)[0] == METRIC[font]
        struct.pack_into("<I", exe, slot, syms[met])
    at = CHAR_COUNT - base
    assert struct.unpack_from("<II", exe, at) == (0x08013EB9, 0x00002821)  # j 8004FAE4; move $a1,$zero
    struct.pack_into("<II", exe, at, 0x08000000 | (syms["cells"] & 0x0FFFFFFF) >> 2, 0)
    at = POOL_SIZE_ARG - base
    assert struct.unpack_from("<I", exe, at)[0] == 0x00A08821  # move $s1,$a1
    struct.pack_into("<I", exe, at, 0x00058840)  # sll $s1,$a1,1
    # Save list line, 80045D40: it pads the map name by its Japanese cells, then 80053E64 widens all ASCII to two bytes, so an
    # English name of 16+ letters overran the 64-byte record and the caller's stack. The name is now a plain 23-byte column;
    # listname copies the 24 bytes the caller shows as row 1, and only the rest (row 2) is widened.
    at = LIST_PAD - base
    assert struct.unpack_from("<I", exe, at)[0] == 0x2446000B  # addiu $a2,$v0,11
    struct.pack_into("<I", exe, at, 0x24060000 | LIST_COLUMN)  # addiu $a2,$zero,23
    at = LIST_WIDEN - base
    assert struct.unpack_from("<I", exe, at)[0] == 0x0C000000 | (LIST_WIDEN_FN & 0x0FFFFFFF) >> 2
    struct.pack_into("<I", exe, at, 0x0C000000 | (syms["listname"] & 0x0FFFFFFF) >> 2)
    for at, old, new in PROMPT_ROW:
        assert struct.unpack_from("<I", exe, at - base)[0] == old
        struct.pack_into("<I", exe, at - base, new)
    return (HOOK + len(blob) + 3) & ~3

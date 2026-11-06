# Text

## Encoding
Shift-JIS, stored as 2-byte codes (full-width everywhere seen, including `Ｄ・Ｓ`). Scan with `tools/strscan.py`, or `jp_left.py --sjis` for builds. Horizontal text.

Control bytes in `ssg` strings (verified by decoding 81 scripts; meaning of 0x0B and 0x0C confirmed only by reading the text flow, **verify in game** at the marker build):

| Byte | Meaning |
|---|---|
| 0x0A | Newline |
| 0x0B | Page break, wait for button |
| 0x0C | End of string |
| 0x00 | Padding to 2 or 4 bytes after 0x0C |

No speaker-name or variable codes noticed in the strings read so far (a sample, not a census: the phase 4 extractor must count every byte below 0x20). The EXE holds sentence fragments such as `つ手に入れた！` and `を手に入れた！` which are likely joined to item names at runtime (**guess**): watch for this when reordering sentences.

## Script files (`ssg`, 81 entries, 545 KB of text, 6,359 strings, largest file 50 KB)
Chunks: `ssg ` > `scr ` > `prg ` (u32 size, payload at file offset 0x18), then `idx ` and `000 `, `001 `... records holding code offsets. The payload is **compiled MIPS, position independent, with strings between functions**:

```
ori  $a0, $zero, off      ; off = string - gp, 16-bit unsigned
addu $a0, $a0, $gp        ; gp = payload + 0x800 = file 0x818
bal  <stub>               ; stub at the top of the payload calls the engine (jal)
```

**Verified:** in entry 14, 182 of 183 such pairs land exactly on string starts. Offset 0 is the first string. Other registers use the same shape rarely (seen `$s0,$s1,$s2`): the extractor must accept any register and report anything unmatched. The first 0x800 bytes of `prg` are zeros.

Consequences:
- Strings can move: rewrite the `ori` immediates, stay under 64 KB from `gp`, keep instruction word offsets intact. Appending all new text after the code grows `prg`; the `ssg`, `scr`, `prg` sizes and RIDX must follow.
- Buffer limit for a loaded `ssg` is unknown: measure in phase 5 (largest original 50,056 bytes, entry 321).
- Longest narration window seen: 18 cells × 8 lines at about 12×14 px per cell.

## Other text
| Where | What | Pointer form |
|---|---|---|
| EXE 0x800-0x1314 | Prompts (`この先へ進みますか？`), map names, debug menu strings | `lui`/`addiu` and `.data` pointer tables (verified: `忘却の浜辺` at 0x974 has both a lui pair at 0x31E58 and a pointer at 0x8C7A4) |
| EXE 0x1B83-0x205B8 | System text mixed with code, many false hits | Same; needs per-string verification |
| EXE 0x20EE0-0x27818 | Item and skill names and descriptions (24 KB) | Pointer tables (`ランク８　棍棒...` at 0x21964 has a pointer at 0x94914) |
| EXE 0x8E187-0x8EEF1 | Character names | Unchecked |
| Overlay 1 | Battle messages | Likely absolute pointers |
| Overlay 2 | Menu labels (`道具`, `個人`, `作戦`) | Absolute 32-bit; base 0x800BF998 |
| Overlay 4 | Ending narration | Unchecked |
| Tables 382, 386, 388, 392, 393 | Names | Fixed-width fields: 386/388 give about 20-30 bytes per name (**measure** before translating) |

Latin labels already in English exist in overlay 2 (`COMMAND`, `PARTY`, `STATUS`, `CNT`, `TEN`): ASCII is at least handled as data there, not proof the draw routine takes it.

## Font
**The game draws text from the BIOS kanji ROM.** EXE has one caller of B0:51 `Krom2RawAdd`: 0x8004E3F0, inside the glyph function starting at 0x8004E3B4 (arg a3 = 16-bit SJIS code). If the call returns -1 it falls back to a local glyph at 0x8009E170. It reads 15 rows of 2 bytes and draws them. **Verified statically** (one call site, and the on-screen style); confirm with a breakpoint in phase 5, per the skill's rule.

English plan for phase 5: hook this function to return glyphs from our own font for a private code range, then pair half-width or VWF letters into cells. Needs the real BIOS in QA (`tools/bios/scph5500.bin`), since OpenBIOS has no such font.

## Debug leftovers
EXE holds `最初から（デバッグあり版）`, `続きから（デバッグあり版）` and event-battle variants (0xFB8-0x1048, pointer table near 0x8DB68), plus `グローバルフラグ`, `システムフラグ`, `スクリプト`, a map list and `sdebug.cpp`, `Rdebug`, `DEBUG.LOG`. A built-in debug menu probably survives: first thing to try in phase 2.

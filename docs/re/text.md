# Text

## Encoding
Shift-JIS, stored as 2-byte codes (full-width everywhere seen, including `Ｄ・Ｓ`). Scan with `tools/strscan.py`, or `jp_left.py --sjis` for builds. Horizontal text.

Control bytes in `ssg` strings. **Verified by census:** the 6,381 script strings hold only pairs, printable ASCII (mostly `!?`), 0x0A and 0x0B, with no speaker or variable codes. Meaning of 0x0B and 0x0C read from the text flow only, **verify in game** at the marker build.

| Byte | Meaning | Token in `script/` |
|---|---|---|
| 0x0A | Newline | `{n}` |
| 0x0B | Page break, wait for button | `{page}` |
| 0x0C | End of a shown string | `term: "0C"` |
| 0x00 | End of a choice prompt, a choice, or a map id (`1_02`); padding to 2 or 4 bytes after 0x0C | `term: "00"` |

Bytes with no table entry decode as `[XX]`, so decode then encode is exact. `[` and `{` are always `[5B]`, `[7B]`.

Runtime joins: `  %sを%dつ手に入れた！` (item, count), `%sが仲間に加わった`, `%sへ向かいますか？`, `「%s」を捨てますか？`, and most battle messages: word order is set by the format string, so it can be reordered as long as the arguments keep their order.

## `script/*.json` (`tools/extract.py`)
`ssg_NNNN` (79), `exe`, `ov1`, `ov2`, `ov4`, `tbl_NNNN` (189). `kind` says what to do with an entry:

| kind | Count | Meaning |
|---|---|---|
| text | 9,609 (6,332 script, 794 EXE, 910 battle, 50 menu, 69 ending, 1,454 tables) | Translate. 8,906 once repeats inside each source are dropped |
| data | 49 | Script map ids in ASCII (`1_02`): never touch |
| debug | 169 | Debug screens and the EXE name pool: stay Japanese unless the marker tour shows one in a retail run |
| card | 2 | Memory card save title. The card directory needs Shift-JIS, so these stay full-width: EXE 0x1B70, 0x1BA4 |
| label | 2,919 | Tables 392, 551-736: developer labels, shown in game? **Unknown**, the marker tour decides (many repeat per area) |

Coverage: `text_runs` looks for Japanese with no pointer logic, over every script, overlay, table, map and the whole EXE; only two runs in EXE code are left over, and `tests/test_extract.py` names them. `fcg` entries hold images only and the sound bank (entry 6) is skipped.

## Script files (`ssg`, 79 with content, 6,381 strings, largest file 50 KB)
Chunks: `ssg ` > `scr ` > `prg ` (u32 size, payload at file offset 0x18), then `idx ` ($gp value) and `001 `, `002 `... event records holding code offsets from file offset 8 (`code.md`). The payload is **compiled MIPS, position independent, with strings between functions**:

```
ori  $a0, $zero, off      ; off = string - gp, 16-bit unsigned
addu $a0, $a0, $gp        ; gp = payload + 0x800 = file 0x818
bal  <stub>               ; stub at the top of the payload calls the engine (jal)
```

**Verified:** the 6,857 such pairs in all scripts give 6,381 strings that never overlap, so none points into the middle of another, and no script text is left without a pair. Any register can hold the offset. An `ori $a0,$zero,N` directly before another `ori $a0` is a delay-slot argument for the previous call, not a string: only the pair counts. 229 strings have more than one reference. The first 0x800 bytes of `prg` are zeros.

Stubs a string goes to (`fn`, offset from the top of the payload):

| fn | Engine | Use | Strings |
|---|---|---|---|
| 0x230 | 80043C3C | Narration | 1,512 |
| 0x270 | 80043EAC | Dialogue, with the portrait set by 0x290 | 4,645 |
| 0x2A0 | 80043FDC | Choice options (`はい`, `いいえ`) | 45 |

A few dozen strings show another stub because their pointer is saved in a register first (0x290 first, for one): `fn` and `speaker` are hints for translators, not proof. **Speaker:** `bal 0x290` with `a0` in its delay slot (`ori` or `move $a0,$zero`) picks the portrait, kept until the next call or the event's end; the extractor writes it as `speaker` and `who`. Ids 0-26 are entry 382's records in order (`Ｄ・Ｓ`=0, `ヴァイ`=7, `ヨーコ`=26), 27-41 the EXE table at 0x8DF64, stride 20 (`シーラ`=27, `ウンディーネＣ`=41). **Verified** by reading lines for ids 25-30, 35-37, 39-41: each fits. Not checked against a shot of the portrait.

Consequences:
- Strings can move: rewrite the `ori` immediates, stay under 64 KB from `gp`, keep instruction word offsets intact. Appending all new text after the code grows `prg`; the `ssg`, `scr`, `prg` sizes and RIDX must follow.
- Buffer limit for a loaded `ssg` is unknown: measure in phase 5 (largest original 50,056 bytes, entry 321).
- Longest narration window seen: 18 cells × 8 lines at about 12×14 px per cell.

## Other text
| Where | What | Pointer form |
|---|---|---|
| EXE 0x800-0x20E8 | Prompts, map names (table 0x8C7A4), names of ids 27-41, debug screens | `lui` + low half, `.data` tables |
| EXE 0x20000-0x28000 | Item and skill names and descriptions | Pointer tables (`ランク８　棍棒...` at 0x21964 has a pointer at 0x94914). 3 EXE strings have a second pointer into their tail: `suffix` in the entry |
| EXE 0x8E180-0x8E868 | NUL-packed pool read by index (800463CC): names and item names. Every caller is in the debug stats editor, 80046xxx | Index, so its total length matters, not pointers |
| Overlay 1, 0x23C-0x8A97 | Battle messages. Open with a control byte (01 x46, 02 x217, 03 x318), then custom codes `%z %M %i %m %l %a` next to `%s %d`, and `{page}` | `.data` pointers, 0x47E00-0x48D00, some `lui`. Meaning of the codes: **unknown**, phase 5 |
| Overlay 1, 0x479A8 | `・` × 11, loaded by code at 0x398C8 | `lui` |
| Overlay 2 | Menu labels, save and load messages. Base 0x800BF998 | `lui`, `.data` |
| Overlay 4, 0x1B00-0x50E0 | Ending blurbs per character, fixed 200-byte slots (base + index, one pointer only) | Fixed |
| Table 382 | Character names: short at record +0 (12 bytes), long at +12 (36) | Fixed |
| Tables 386, 388 | 501 item and 839 skill names (spells and attacks: `ダムド`, `接触攻撃`). Record: u16 id, `char[18]`, a full 18-byte name has no NUL | Fixed |
| Table 393 | 30 formations: name (20 bytes), description (64) | Fixed |

Overlays 0 and 3 hold no text. Latin labels already in English exist in overlay 2 (`COMMAND`, `PARTY`, `STATUS`, `CNT`, `TEN`).

**ASCII:** EXE 0x8EA50 is a table from ASCII to full-width SJIS (`0x20` -> `0x8140`, `A` -> `0x8260`...), which is probably why `!?` in scripts draws at all (**guess**, the caller is not traced). Phase 5: a possible way in for half-width letters.

## Font
**The game draws text from the BIOS kanji ROM.** EXE has one caller of B0:51 `Krom2RawAdd`: 0x8004E3F0, inside the glyph function starting at 0x8004E3B4 (arg a3 = 16-bit SJIS code). If the call returns -1 it falls back to a local glyph at 0x8009E170. It reads 15 rows of 2 bytes and draws them. **Verified statically** (one call site, and the on-screen style); confirm with a breakpoint in phase 5, per the skill's rule.

English plan for phase 5: hook this function to return glyphs from our own font for a private code range, then pair half-width or VWF letters into cells. Needs the real BIOS in QA (`tools/bios/scph5500.bin`), since OpenBIOS has no such font.

## Debug leftovers
EXE holds `最初から（デバッグあり版）`, `続きから（デバッグあり版）` and event-battle variants (0xFB8-0x1048, pointer table near 0x8DB68), plus `グローバルフラグ`, `システムフラグ`, `スクリプト`, a map list and `sdebug.cpp`, `Rdebug`, `DEBUG.LOG`. The start menu with those strings has no caller left, but the debug screens work: see `code.md`. These strings are never seen in a retail run, so they can stay Japanese.

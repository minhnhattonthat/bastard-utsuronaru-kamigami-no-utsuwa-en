# Box budgets (the width gate)

Measured in game on stress builds: `build.py --marker --qa FILE.json` with a ruler string (`A234567890B234567890...`, digits 6 px) in one line of each box, read off zoomed shots. Widths are English pixels from `engine.width()`. Shots: `work/qa/p5_stress/` (not in git; rebuild with `--qa`). Torture line (all printable ASCII, double spaces, `MW`/`il` runs): all glyphs right, `work/qa/p5_stress/torture/`.

**Text wraps by itself:** a script or battle line past its box's width wraps at the pixel, mid-word, onto the next row. Width is real pixels, not character cells: 60 `il` pairs stayed on one line. Always break lines with `{n}`; a wrap adds a row.

## Script text (`ssg`, by `fn`)
| Box | `fn` | px per line | Lines | Last line of a page | Evidence |
|---|---|---|---|---|---|
| Narration, teal box | 560 | 216 | 8 (a 9th shows, but the arrow overlaps it) | 216 at line 8; 204 if the page ends higher up (`{page}`'s arrow sits in the last cell of that row) | `L(36,8)`, `L(36,4)+{page}`, `L(36,9)` |
| Dialogue, portrait box | 624 | 228 | 4 | 216 on line 4 (arrow) | 38-char ruler x 4 |
| Choice | 672 | 240 (window grows with the text; it wraps onto itself near 256 px and runs off screen) | 1 | - | 60-char ruler in `QUESTION`; budget set under the fault |

The tour logged some `fn 624` strings in a 216 box and some `fn 560` in 228 (`fn` is a hint: `text.md`). A line takes the smaller budget if it ever shows in both: use `tools/windows.json`.

## Battle (`ov1`)
| Box | px | Lines | Evidence |
|---|---|---|---|
| Battle message | 228 (216 on the last line, arrow) | 3 | `battle_start`, `ev_3_11_0400` |
| Command labels (`陣形 移動 攻撃 防御 道具`) | 32 | 1 | `battle_commands`: past that it clips at the box edge |
| Formation row (`ov1_01044` box) | 46 | 1 | `battle_commands` |
| Formation name (table 393, 19 bytes) | 110, then the arrows | 1 | `battle_commands` |
| Information, formation description (table 393, 63 bytes) | 192 | 2 | `battle_commands`, log |
| Selected target, enemy name (tables 551-736, 19 bytes) | 120 (draw log; the HP starts 133 px in) | 1 | `ev_2_10_0700` with a 19-character ruler (114 px): it fits |

## Camp (`ov2`, EXE, tables)
| Box | px | Lines | Evidence |
|---|---|---|---|
| Command grid (`道具 個人 作戦 戻る`) | 32 per cell; the second column starts 35 px after the first and they overlap past that | 1 | `camp_menu` |
| Sub-command (`聖玉 道具 装備 奥義`) | 32 | 1 | `camp_items`, `camp_character_page` |
| Name bar, personal data (table 382 long, 23 bytes tried) | 120 | 1 | `camp_character` |
| Equipment row (table 386, 17 bytes) | 110 | 1 | `camp_character_page` |
| Item list row (table 386, 17 bytes) | 120 | 1 | `camp_item_list` |
| Item description (`ITEM SELECT`, `INFORMATION`) | 204 | 2 | `camp_item_list` |
| Save list (`ファイル%d：`) | 96, next column at about x 96 | 1 | `save_menu` |
| Save message | 212 | 2 | `save_menu`, log |

## Grows with the text (no fixed budget, still has a limit)
`CHAR_COUNT` follows the font, so these size themselves. Keep under 240 px. Measured on the item message (`ev_1_09_0006`, `--qa`): 240 px, exactly 20 cells, shows every glyph; at 259 px the last glyph is gone, as text past 256 px wraps onto the start of the bitmap. The choice box does the same.
Field messages (`exe_012f0 宝箱は開かない`), map names (`exe_00974`), party-join messages (`exe_012d0`). The 240 is measured on the item message only; the others are expected to behave the same, and the longest of them seen on the marker build was 180.

## Fixed byte limits
- Table 386/388 names: 17 bytes + NUL (`_write_fixed` refuses 18). Table 393 name 19, description 63. Table 382 short 11; long is up to 31, field by field (`insert._field_room`), not the 36 `max` says.
- Enemy names, `label` tables 551-736: **19 bytes** + NUL in a 20-byte field. Some Japanese names fill all 20 with no NUL and the next field follows at once; the build always writes a NUL and never touches that field.
- Ending blurbs, `ov4`: 199 bytes each, fixed slots, 228 px.
- Script strings can grow: they move to the end of `prg`, 64 KB from `$gp`, and the build refuses more. The game loads that much: entry 321, the largest, padded from 50,056 to 65,164 bytes (`tools/debug/ssg_stress.py`) ran `map_4_04`, `ev_4_04_0001` and `ev_4_04_0003`, its strings on screen. The ring holding queued text is cols x rows x 4 bytes (narration 648; dialogue 304 in a 228 px box, 288 in a 216 px one; cols = px / 12). **Measured** on `ev_1_01_0003` with `build.py --qa`: the string's bytes count, its closing `0C` too, and past the ring only the tail survives (length mod 304: 620 bytes showed the last 12, a 304-byte one showed nothing and skipped its wait). 288 and 302 bytes showed every page. `batches.RING` caps narration at 640 and dialogue at 288; the longest dialogue is 220.
- **Stack buffers.** These strings are expanded by sprintf into a fixed buffer on the stack; past its end they overwrite the saved registers and the return address. `insert.FORMAT_ROOM` holds the limits and the build refuses more; `tools/debug/fmt_sites.py` lists every sprintf in the EXE. Battle text (`80052E88`) uses a 4 KB work area, and the menu printer (`80049ED4`) has 128 bytes and an assert, so neither needs a limit beyond its box.

| String | Buffer | Literal text, tokens not counted | Longest argument |
|---|---|---|---|
| `exe_00920` item and count | 56 | 36 | item name 17 + count 2 |
| `exe_00938` item | 56 | 38 | item name 17 |
| `exe_00894`, `exe_008dc` go to, leave | 48 | 17 | map name 30 (every map name is capped at 30 bytes) |
| `exe_008a8`, `exe_008c4` warp, go on | 48 | 47 | - |
| `exe_012d0` joined the party | 32 | 11 | character name 20: **guess**, which name field it reads is not traced, so `%s joined the party!` (18) is out unless names stay under 13 bytes |

- **Item message icon:** the icon sits over the first 18 px of `exe_00920` and `exe_00938`, which is why the Japanese starts with spaces. A space is 4 px here, so the English needs **5 leading spaces**, not the original 2. Shot: `ev_1_09_0006`.
- `ov2` has 275 free bytes after the marker build, with spill to the EXE's free block.

## Which `label`s show
Enemy names in tables 551-736 do show: the tail `00a50` and others are drawn in battle messages (`%sが現れた！`), so **translate them**. Table 392 (`テスト２６`, `細くて眠りのマップ`) has not been seen on screen: developer labels, leave them.

## Strings read as pieces
- **Enemy letters, `ov1_00288`:** the code takes 2 bytes per enemy from this string (it was `ＡＢＣＤ`), so plain `ABCD` gave "Soldier AB". It's ` A B C D`: a space and a letter per enemy.
- **Choices, `ov2_00560`, `ov1_01220`:** each option has its button icon or cursor at a fixed x. Half-width spaces draw 12 px in Japanese and 4 px in English, so the English is padded to the Japanese offsets (`ov2_00560`: 0, 48, 108 px, from the icon xs in `ov2` at 0xA7B0-0xA800). Not seen on screen yet.
- **Name + `ov2_004b8`:** strcat onto a character's name (`ov2` 0x96A4, the only strcat of a literal in the game), so it starts with a space.

## Battle codes
Substitutions, keep each one and keep their order, since arguments are consumed in order: `%s` a name, `%d` a number, `%M` a spell, `%i` an item, `%m` a cause of death, `%l` a character (level up), `%a` a side (read from where each sits in the Japanese; `%M %i %m %l %a` are not traced in the code).
`%z` shows no text: it fires the battle's next step when the printer reaches it, so text before it shows before the effect (`[01]%sの攻撃！%z`). Leading `[01] [02] [03] [06]` are control bytes: leave them where they are. What each does is not traced; a marker build that kept them in place ran the win and loss battles.

## Engine notes
- `fonts/vwf12.txt` is the font. `tools/engine.py` hooks fonts 1 and 8 at `FONT_TABLE`, and the size metric too, so boxes size to the English.
- Window pools double (`POOL_SIZE_ARG`): a wide label overran the fixed pool, failed the `sprman.cpp` assert and hung the game.
- Script strings end `0C 00` (wait for key, end of string). `insert.blob` writes both; without the NUL the printer ran on into the next string, past the wait.

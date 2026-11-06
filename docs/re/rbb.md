# RSRCALL.RBB

`tools/rbb.py`. Header banner: `RC ver1.0 Copyright(C)1995 OpusCorp.`, date 96-1206-151709, operator azumada, build 0018. **Verified:** all 1,541 entries unpack to their declared sizes.

IFF-style `siff` file (u32 size = whole file):

| Offset | Chunk | Content |
|---|---|---|
| 0x008 | RSRC | 0x70 bytes, banner |
| 0x080 | RIDX | 1,541 × (u32 offset, u32 size). Offsets are relative to 0x5000, aligned to 0x800 |
| 0x30B0 | EXIX | 1,541 × u32, the same sizes |
| 0x48CC | GAP0 | 0x724 bytes of 0x1A, pads to 0x5000 |
| 0x4FF8 | RBB0 | u32 size, then entry data from 0x5000 |

## Compression (`00zL`)
Entry or nested data block: `00zL` `ATAD` u32 size, u32 0x1000, u32 csize, u32 usize, payload. Tags read reversed (`Lz00`, `DATA`). `size` = csize + 12; total block = 12 + size.

LZSS: flag byte read LSB first, 1 = literal. Match = 2 bytes `a b`: position `a | (b & 0x0F) << 8`, length `(b >> 4) + 3`. 4 KB window, zero filled, **write head starts at 0** (not the usual 0xFEE). Verified: readable strings across entries 0-4 and correct image pixels.

Encoder: `rbb.lzss_encode`, Okumura's binary tree with three changes: write head 0 (tree node deletion at F), one seed node at 0xFEE for the zeroed window instead of F of them, and the first F bytes not mirrored past the window (only ties in the last token show it). **Verified:** `rbb.py verify` re-encodes all 5,368 blocks (93 MB, about a minute) to the original bytes. Bytes after a block up to 4-byte alignment are the tool's uninitialised memory (`00` or `CD`); new blocks can pad with zero.

Rebuild: `rbb.pack(data, {id: bytes})` keeps ids, zero-pads gaps to 0x800 and rewrites RIDX, EXIX, RBB0 and siff sizes.

## Entry map
| Entries | Tag | Content |
|---|---|---|
| 0 | overlay `dun*.cpp` | Dungeon code. Header u32 5 |
| 1 | overlay `btl*.cpp, winmenu, btlwin` | Battle code and text (about 26 KB SJIS at 0x20-0x8A97). Header u32 4 |
| 2 | overlay `func, itemwin, mcard` | Camp menu, items, save. Absolute pointers; base 0x800BF998 (verified from its string table). Holds an embedded `fcg`. Header u32 6 |
| 3 | overlay `ttl_main.cpp` | Title. No Japanese. Header u32 7 |
| 4 | overlay `end_main.cpp` | Ending text (about 12 KB SJIS, 0xA1-0x5020). Header u32 8 |
| 5 | fcg | UI icons, portraits (skey names: developers' Latin spellings) |
| 6 | raw, 18.8 MB | `// Opus Lay-la Infomation` banner, then ADPCM-like data: sound bank (**guess**) |
| 7 | XAID | 0x390 bytes of records, XA clip table (**guess**) |
| 8, 9 | fdb | `vers 1.01`, `nbit`, `nlst`, 8-byte `lst` records. **Not a font** (fields look like block coordinates) |
| 10-379 | ssg, fcg, dsg (+ tables) | One event/map group per area: `fcg` title card, `dsg` map, `fcg` textures, `ssg` script. 81 `ssg`, 100 `dsg` |
| 382 | table | 27 character records, 196-byte stride, two name fields per record (first at +20) |
| 383-387 | tables | 386 = 501 equipment/item names, 32-byte stride (**guess** on record meaning) |
| 388 | table | 839 enemy names, 32-byte stride |
| 391-393 | tables | 392 = map names (44-byte stride, includes `テスト１`); 393 = 30 formations with description text |
| 394-550 | fcg | Sky/floor strips, no text |
| 551-645 | tables | Encounter groups, 1,316-byte stride, names use `＊３` style (developer labels: do they show in game? **unknown**) |
| 646-736 | tables | Object/trap names per area (`障害物零号機` etc.), 188-byte stride: developer labels (**guess**) |
| 737-835 | fcg | Enemy sprites (cast/tex) |
| 836-1482 | fcg | 304×192 `cut####.raw` event CG, 8bpp |
| 1483 | fcg | NEW GAME, CONTINUE, logo, publisher card |
| 1484 | fcg | Staff roll strips (English already), THANK YOU |
| 1485-1540 | fcg | 608×96 strips (scene backdrops, likely save-menu or map thumbnails) |

Entry ids are hardcoded by callers (**guess**: `rsrcctl.cpp`, entry numbers appear as immediates), so never renumber: replace in place and repack offsets only.

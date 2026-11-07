# Graphics and graphics text

## fcg format (`tools/fcg.py`, verified: portraits, cards and CG render correctly)
Chunks: tag + u32 size, bit 31 = container. `fcg ` > optional `cast` (u32), `tex ` > optional `skey` (name), `clut` { `xywh`, `data` }, `pxel` { `xywh`, `data` }. `xywh` = u16 x, y, w, h (VRAM units of 16 bits), u32 mode (low byte 0 = 4bpp, 1 = 8bpp, 2 = 15bpp), u32 with bit 31 set when `data` is `00zL`-compressed. Embedded `fcg` blocks also exist in the EXE (0x8EB10) and overlays 0 (0x11D9C, 0x129FC) and 2 (0x12B30).

## Survey
Static sweep: every texture of all 1,155 `fcg` entries plus the 4 embedded blocks (6,623 + 44 textures), deduped by pixel hash; `tools/fcg.py sweep` and survey scripts, nothing skipped by the parser. Movies: all 163 sampled every 3 s with ffmpeg.

Coverage read by eye: all title cards; all 647 event CG (9 of 9 sheets); entries 5, 1483, 1484, embedded blocks; samples of all 6 ANIME movies and 157 MOVIE clips. **Sampled only:** map and enemy textures (5 of 14 sheets, many render as noise here because they use a CLUT from another chunk, so reading them would prove little), backdrop strips (2 of 3), silhouette masks (1 of 3). Movie sampling is one frame per 3 s, so short captions can be missed. Those gaps close in the marker tour (phase 5) and the zoomed QA (phase 8).

| # | Element | Source | Japanese | Plan |
|---|---|---|---|---|
| 1 | Area title cards (91 unique of 92) | `fcg` 76×192 4bpp, 304×192 px, compressed; entries 11, 15, 19, 23... one before each map group, listed by `fcg.py sweep` as w=76 h=192 mode 0 | Big kanji with furigana, kanji subtitle, small English subtitle already present (`Amnesians`, `Encounter`) | Redraw all: English area name + existing English subtitle |
| 1b | Three more title cards in CG format: `森林地帯入口`, `忘却の浜辺`, `寄岩砦` (`Front line`) | entries 1194-1196, `cut4280`-`cut4300.raw`, 304×192 8bpp | Same layout as row 1 | Redraw |
| 2 | Chapter end `第一章……完`-`第四章……完` | entries 1479-1482, `cut####.raw` 304×192 8bpp | Small line bottom right | Redraw (`End of Chapter 1`) |
| 3 | Publisher card `集英社・セタ / バスタード!!製作委員会` | entry 1483/4 | Yes, plus English copyright line | Redraw |
| 4 | Title logo subtitle `―虚ろなる神々の器―` | entry 1483/3 (a logo variant) and the runtime title screen, also in movie 157 | Yes; the main logo is Latin | Keep logo, redraw subtitle in English |
| 5 | Battle/skill icons `魔`, `技` | entry 5, textures 0-13, 16×16 | Yes | Redraw (e.g. `M`, `S`; agree with the glossary) |
| 6 | Handwritten note | entry 1172, `cut4060.raw` | Scrawled Latin-style script with a doodle, not Japanese (zoomed). Check what the script says about it | Probably leave |
| 7 | Opening movie `ANIME` #157 (LBA 129344, 20,913 sectors, 2,089 frames, 304×192) | STR burned in | Staff (`原作 萩原一至`, `脚本 ベニー松山`, `作画監督 羽山淳一`, `アニメパート監督 浜津守`), tagline captions | Re-encode frames with English, see below |
| 8 | Movie `ANIME` #162 (LBA 214076, 8,416 sectors, 840 frames) | STR burned in | Two text pages, seen only as small thumbnails (a narration page, then a shouted line): read them from full frames before translating | Re-encode |
| 9 | Movies `ANIME` #158, 159 (320×176), 160, 161 | STR | No text in samples; #160 and #161 look near identical to each other (ending variants) | Confirm with a denser sample |

No Japanese seen, leave alone: event CG art, enemy sprites, map textures, the 157 effect clips, `HELP` icon, `WATCH OUT!`, `NOW LOADING`, NEW GAME/CONTINUE, compass letters, staff roll strips, overlay 2 fcg #26 (zoomed: a blue pictogram, not a character).

Japanese, left as art until the owner rules: the end card in entry 1484, brush calligraphy (probably `おわり`) over an English `THANK YOU!!` (`ending_thanks`, also in movie #162).

Still to tour: **in-game screens** (battle, menus, save, shop-less item screens, game over). Text there goes through the BIOS font unless this list says otherwise. The marker build in phase 5 is the real test: any Japanese that stays is a new row here.

**Redrawn by `tools/cards.py` (rows 1-5):** 94 cards keep the rule and their own English subtitle, with the area name above it (canyon names follow the furigana: Little Canyon, Great Canyon). 1483/3 is 304×192 8bpp, whatever its header says (mode 0, 256-colour CLUT). Icons: `魔` -> `M`, `技` -> `A` (Arts). Row 6 still needs a ruling from the script's context.

## Movies (rows 7-9)
No jPSXdec: `tools/mdec.py` reads and writes STR v2 frames itself, and `tools/movie_text.py` draws `tools/movie_text.tsv` into #157 and #162; `build.py` writes the changed sectors, cached in `work/fmv/`.

- Format, proved by re-encoding all 9,282 frames of the 6 ANIME movies byte-identical: 8-byte header (`words` = MDEC codes / 2, rounded up to 32; `0x3800`; qscale; version 2), 16-bit LE words read MSB first, macroblocks in columns, Cr Cb Y1-Y4, end marker `0111111111`, zero padding to a multiple of 4. Each sector's STR header holds the frame size and a copy of those 8 bytes. All frames are intra, 15 fps, 8 or 9 video sectors.
- Only macroblocks a caption box touches are re-encoded; every other macroblock keeps its original bits. A frame that outgrows its sectors or the movie's largest `words` gets a higher qscale, re-quantised whole.
- The box is a dark blur of the frame itself, opaque where the Japanese sits, soft at the edges. It fades in faster than the caption, so the Japanese doesn't show through. `movie_text.py edges OUT` shows each caption at its edges with frames just outside it.
- Row 9: #158-161 hold no text at the sample rates read (every 32 frames on #158-159, every 12 on #160-161).
- ffmpeg logs `ac-tex damaged at 0 0` on some frames, including an untouched original frame in a one-frame file. That isn't a fault in the frame: compare its samples instead.

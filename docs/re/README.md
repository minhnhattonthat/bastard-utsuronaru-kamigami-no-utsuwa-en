# Reverse-engineering notes

Each finding is marked **verified** (how) or **guess** (why). Promote a guess before code depends on it.

| File | Covers |
|---|---|
| `disc.md` | Disc layout, sector formats, free space |
| `rbb.md` | RSRCALL.RBB archive, LZSS, entry map |
| `text.md` | Encoding, control codes, pointer forms, font, text inventory |
| `graphics.md` | fcg format, graphics-text survey (tile-drawn and movie Japanese) |
| `code.md` | Sequence control, debug features, warp, map and script data, party, flags |

Prior work: no English patch or tools for the PS1 game found (web search 2026-11-06). The DeJap "Bastard!!" patch is a different game (Super Famicom). Cheat codes: `8014E9C8`/`8014EEB4` = 1st/2nd character EXP (gamegenie.com, unverified for this revision), which would make the character record 0x4EC bytes.

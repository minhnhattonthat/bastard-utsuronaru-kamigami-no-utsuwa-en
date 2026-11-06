# Game code: sequence control, warp, debug features

Addresses are RAM. All **verified** by running them from a cold boot unless marked. Tools: `tools/re.py` (disassemble, immediates, callers), `tools/debug/script_calls.py` (which events call an engine function).

## Sequence object (`seqctl.cpp`)
`*0x8009D3A8` points at a 0x510-byte object, built by 8003D364 and zeroed flags on every boot.

| Offset | Meaning |
|---|---|
| +0x00 | State, dispatched at 8003D25C: 0 field; 1, 2 = 8003E614(0/1): movie then field; 3, 4 = 8003E310(0/1): ending |
| +0x04 | Current map record (0 = ask with the debug map list) |
| +0x0C | Entry point: bits 4-11 letter, bits 12-21 number (0 = ask with the debug point list). New game: `p001`, map 0 |
| +0x28 | Loaded overlay: 0 dungeon, 1 battle, 2 camp, 3 title, 4 ending (loader 8003F348) |
| +0x34 | Field object; its +0xC points at the script object |
| +0x15C | Party object. +0x16C, +0x18C: flag objects (see below) |
| +0x1AC | Script object: +0x24 base, +0x28 stub destination, +0x30 set when a found event starts, and stays set |
| +0x2F8.. | Arguments of the last battle: encounter id +0x2F8, then +0x2FC, +0x300, +0x304, +0x308 |
| +0x314 | Battle result: 4 = lost, jumps back to the boot sequence (8003E01C), so defeat returns to the publisher card |
| +0x50C | Flags. Bit 2 (4) = debug; bit 1 (2) = alternate ending, set by script stub 80042C4C; bit 0 = saved in the save file |

## Debug features
The menu `最初から（デバッグあり版）` and friends (table 0x8009D368) has **no caller** left in this build. Its values show the old meanings (7 = debug + no battles, 0 = master). The debug code itself survives and depends on bit 2 only, which no retail code sets:

- New game with the bit set: map list (8003E8D0), then point list (8003EAEC, letters `dcbxwpefzg` only).
- Field keys, select held: start = map list again; R1 = flag viewer (8003C8A0); L1 = stats editor and item grant (80046648); square = replay battle from +0x2F8, so any encounter id can be poked in.
- A `P1` HUD in the corner. Start and Select menus don't open while the bit is set (checked at 80038038).

## Warp (`tools/debug/warp.lua`)
Patches the new-game branch **in RAM only** (table in the script, each word checked against the disc first): skip the title, write our map record, entry point and state, set the debug bit, restore the code on arrival. Disc untouched, so nothing can reach a release. `MASTER=1` clears the bit on arrival.

Event choice: map entry runs event 1000 through 80038D50 (`ori $a1,1000`). `ENTRY_EVENT` swaps that immediate. `EVENT` turns the Start branch at 80038160 into a call of the event runner 8003F8BC instead, so the field is up when the event starts. Script scenes run on a new-game state plus the flags their opening tests ask for. See `tools/debug/README.md`.

## Maps
Table 0x8009BFA4, 79 × 64 bytes: +0 name, +4 id bytes (chapter, map, sub), +8 id string (`1_01`), +0xC ssg entry, +0x10 u16[8] dsg entry per variant, +0x20 u16[4] fcg entries, +0x28 u16 music (**guess**), +0x2C per-variant bytes copied to the battle arguments (**guess**).

`dsg` chunks: `ded ` > `nevt` (count), `evt ` (points). Point: u32 w0 (x:9, z:9, y:7, top 4 bits = bytes after the 8-byte head), u32 w1 (letter:8, number:10). Letters seen: b c d e f g n p r w x z. `p` and `w` set the arrival position, `b` also calls 80039E0C. Every map parses cleanly (`gen_scenes.py` asserts the chunk size).

Eight dsg variants per map: 11 maps use more than one (e.g. 2_02_1, 3_08). How one is chosen is not traced (**guess**: a flag read at load). The warp takes what a fresh state picks.

## Scripts (`ssg`)
Extends `text.md`. After `prg` come 4-byte records named by event number, `1000` = map entry (verified, the warp swaps it), `1001` run by 80038D74 (**guess**: map exit; no script has one), and `idx`. **Offsets count from file offset 8.** `idx` is not an event: its value is `$gp` (a0 of 80047150 at 8003F870), which is why it equals the offset of the first string. 8003F7F0 looks a record up by name and calls it; 8003F8BC formats the number.

The first 0x800 bytes of `prg`, zero on disc, are filled at load (8003FA94) from the `j` stub table at EXE 0x80010B58-0x80010F58 (128 × `j f; nop`). A script calls `bal` to `f`'s table offset + 0x10.

Script `bal` targets worth knowing: 0x210 wait a0 frames, 0x240 narration, 0x280 dialogue, 0x2A0 speaker, 0x2B0 choice, 0x390 show event CG a0 (entry = 836 + a0), 0x3A8 hide it. A chapter end is `0x390` with 0x283-0x286 (entries 1479-1482): maps 1_24_1, one with 0x284, 3_20, 4_09_1.

Field yes/no prompt: 8003AF88(format, args), sprintf into a stack buffer, box `max(8, cells)`, buttons at fixed x (`engine.PROMPT_ROW`). Enemy tables load only for a battle, 80079E10: 551 and 644 + the area at 0x800A3D30; they are not in RAM in the field.

Stubs worth knowing: 800432F8 join party (a0 = character), 80042C14 ending state 3, 80042C4C alternate ending (state 3, bit 1), text output around 0x80043C8C (**guess**, from its string arguments).

Real ending triggers: 5_06 event 1, 6_01 event 10.

## Party and battle data
- `*0x800A3B48` = game state. Character records at +0xF30, 180 bytes each; +0x9C low bits 1 = joined. Setting that alone doesn't add a member to the active party: the player places them in `作戦` (Tactics), and the warp scenes do that with the real menu.
- First party member's current HP in battle: 0x80106C2C (u32; on-screen test, pinned to 1 in `battle_lose`). It is not valid in the field.
- A battle waits for its HP bar to reach the current value, so holding HP every frame hangs the fight (seen on screen). Set it once.
- Encounter 1: the three enemies' current HP sit at 0x801374B0, stride 0x1C0 (u32, 17 at the start). Setting them to 1 makes each die in one hit (`battle_win`). Other encounters not checked.
- The cheat addresses in `README.md` (`8014E9C8`) look like the same structure family but weren't needed: unverified still.
- HUD name for Vai is the Latin label `VIE`: check that against the glossary in phase 6.
- Inventory, in the game state: item ids u16 at +0x3190 (newest first), counts u8 at +0x358E (same positions), size u16 at +0x378E. Found with `tools/debug/ramdiff.py` across `ev_1_09_0006`; poked by `warp.lua ITEMS`, and the list then shows them (`1/486`: 15 of the 501 items never list, not traced why).
- Battle turn, from a `battle_party` state: first circle opens `Form` (up and down step through the formations), the next reaches `Move`, the next the command list.

## Flags (for when a scene needs story state)
Flag objects: seq+0x16C and seq+0x18C, built from entries 8 and 9 (`fdb`); `+0` = storage. The debug viewer labels them `グローバルフラグ` and `システムフラグ` (which is which: **guess**, not traced). A flag id: bits 11+ byte offset, bits 8-10 bit position, bits 0-2 width − 1. Read 80039900, write 80039940. Scripts read seq+0x18C through stub offset 0x50 (80042DA4) and write it through 0x58 (80042DD0). `SETFLAGS` writes that same storage from Lua, verified: `ev_2_11_0005` shows no text without it and shows text with it.

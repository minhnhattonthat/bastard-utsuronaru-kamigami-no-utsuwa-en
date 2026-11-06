# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 3. Identity build (next). Last build: none yet.
- **Done:** Step 0, phase 1 recon (`docs/re/`), phase 2 debug tool (`tools/debug/`, how it works in `docs/re/code.md`). `warp.py all` on the original disc from a cold boot: 844 of 844 scenes pass their RAM check (4 system, 10 menu, 3 debug, 6 battle, 5 ending, 79 map, 737 event; battle win and loss both reached), and the negative control fails as it should. Proof sheets: `docs/screenshots/warp/`. I read `special.png` tile by tile and sampled `map_cards.png`, `maps.png` and `events_3.png`; the other event pages were not read.
- **Event scenes, what the shots show:** 343 of 737 events have script text; 326 of those change the screen, and most of the sheet samples show a text box. The other 394 events have no script string, and 304 of them leave the screen unchanged.
- **Known gap:** 17 text events start but show nothing, because their first text sits behind a test the warp does not set (party, or untraced stubs): `ev_1_06_0018 ev_1_17_0004 ev_1_17_0006 ev_2_04_0008 ev_3_02_0004 ev_3_02_0005 ev_3_02_0101 ev_3_02_1000 ev_3_03_0004 ev_3_05_0004 ev_3_06_0100 ev_4_02_0009 ev_4_02_0010 ev_5_02_0002 ev_5_02_0100 ev_5_02_1_0100 ev_5_02_2_0101`. Each scene also shows one path only, so later branches of an event are unproven. Phase 5's marker build should use a draw log to find strings no tour shows. More gaps: `tools/debug/README.md`.
- **Next:** Phase 3: identity build. `build.py` unpacks and repacks with no edits, and a test proves the rebuilt disc is byte-identical to the original. Start from `tools/disc.py`, `tools/rbb.py` and `docs/re/`; note the RBB has no slack before MOVIE.MMB (AGENTS.md Gotchas).
- **Setup on a new machine:** `git config core.hooksPath tools/hooks`, `fetch_emu.py pcsx`, `fetch_emu.py psx-bios`, `tools/disc.py extract`, `tools/rbb.py unpack`.
- **Step 0 gaps:** PCSX-Redux GUI keyboard input not tested (headless agent; scripted input and Lua work). `tools/emu-config/` not created: emu.py writes its settings each run.
- **Open bugs:** none.
- **Waiting on the user:** Non-blocking: jPSXdec (needed by the skill's route for re-encoding the opening and ending movies with burned-in Japanese) was refused by the auto-mode classifier as downloaded code. Either allow it, or a later phase writes a Python MDEC encoder. Survey and sampling used the installed ffmpeg instead. Also: confirm or correct official English name spellings if you have a preference (seed list in `glossary.md`).

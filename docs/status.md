# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 2. Debug tool (next). Last build: none yet.
- **Done:** Step 0 (repo, emulator, BIOS, hooks, check) and phase 1 recon: `docs/re/` records disc layout, RBB archive + LZSS, text encoding, pointer forms, text inventory, BIOS kanji font, free space, graphics-text survey.
- **Next:** Phase 2: `tools/debug/` warp tool. Start from the built-in debug menu strings in the EXE (`最初から（デバッグあり版）` at 0xFB8, pointer table near 0x8DB68; `docs/re/text.md`), the event/map lists at EXE 0x974+, and the party record cheat addresses in `docs/re/README.md`. Prove every scene-list entry from a cold boot.
- **Setup on a new machine:** `git config core.hooksPath tools/hooks`, `fetch_emu.py pcsx`, `fetch_emu.py psx-bios`, `tools/disc.py extract`, `tools/rbb.py unpack`.
- **Step 0 gaps:** PCSX-Redux GUI keyboard input not tested (headless agent; scripted input and Lua-free runs work, a Lua probe log line is still to prove in phase 2). `tools/emu-config/` not created: emu.py writes its settings each run.
- **Open bugs:** none.
- **Waiting on the user:** Non-blocking: jPSXdec (needed by the skill's route for re-encoding the opening and ending movies with burned-in Japanese) was refused by the auto-mode classifier as downloaded code. Either allow it, or a later phase writes a Python MDEC encoder. Survey and sampling used the installed ffmpeg instead. Also: confirm or correct official English name spellings if you have a preference (seed list in `glossary.md`).

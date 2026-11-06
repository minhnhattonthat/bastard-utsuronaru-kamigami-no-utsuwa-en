# Bastard!! Utsuronaru Kamigami no Utsuwa (PS1, SLPS-00542) English translation

Skill: translate-retro-game (Claude Code: plugin, enabled in .claude/settings.json; others: `python tools/skill.py` prints its folder). Read its SKILL.md before ROM, text or QA work. `$SKILL` below = that folder; never paste a `plugins/cache/<hash>` path.

## Commands (run from repo root)
- Setup after clone: `git config core.hooksPath tools/hooks`; `python -X utf8 tools/disc.py extract`; `python -X utf8 tools/rbb.py unpack` (work/rbb/).
- Build:    not written yet (phase 3): will be `python -X utf8 build.py` -> build/bastard_en.cue
- Check:    `python -X utf8 tools/check.py` (tests; the pre-commit hook runs this)
- Smoke:    `python -X utf8 "$(python tools/skill.py)/scripts/emu.py" <cue> --out work/qa/smoke --route tools/routes/boot.txt --smoke`
- New game: `--route tools/routes/newgame.txt --mash 150 --mash-key circle --frames 20000 --timeout 500` (prologue movie can't be skipped; first narration at ~frame 16700)
- Warp:     `python -X utf8 tools/debug/warp.py NAME [--cue CUE]` (`list`, `all`; then `warp_report.py`; see `tools/debug/README.md`). Never ask the user to play to a scene.
- Release:  phase 9 (`tools/release.py`: xdelta against the .bin; never publish without the user)
- Clean:    `python -X utf8 tools/clean.py`

## Paths
- Original disc: `rom/*.bin`, `.cue` (gitignored; SHA-1 in `rom.sha1`, checked by `tools/check_rom.py`). Emulator: `tools/pcsx/` (PCSX-Redux nightly 30375.20261106.4 from distrib.app, `fetch_emu.py pcsx`; gitignored). BIOS: `tools/bios/scph5500.bin` (`fetch_emu.py psx-bios`), **required**: the game's text uses the BIOS kanji font. Savestates: `work/states/`.
- Extract/format tools: `tools/disc.py` (raw sectors), `tools/rbb.py` (RSRCALL.RBB + LZSS), `tools/fcg.py` (images), `tools/movies.py` (STR index + ffmpeg samples), `tools/strscan.py` (SJIS runs).
- RE notes index: `docs/re/README.md`. Glossary: `glossary.md`. Fonts and licences: `docs/fonts.md`. Text: `script/` (from phase 4).

## Rulings
- Edit source files (.py .lua .asm .tbl .json) only with the file-edit tool; scripts here read and analyse, never `.replace()` and write back.
- Subagents: dispatch the `.claude/agents/` types (translator, reviewer, visual-qa, playtester), never general-purpose. In a pre-approved Orca run nested workers are refused: do those reviews yourself in a fresh read-only pass.
- The user's decisions, with the options and reasons: `docs/decisions.md`. Read it before asking the user anything; add each new ruling there the same session.
- Player bug reports: GitHub issues (`gh issue list --label bug`). Copy the attached save into `work/states/`, reproduce in the emulator, fix, commit with `Fixes #N`, and update `docs/status.md`.
- Never run `gh release create` or change repo visibility. Runs end at a built and verified release zip.
- Gotchas: script strings are `$gp`-relative (`ori $a0,$zero,off; addu $a0,$a0,$gp`), so an offset is limited to 16 bits per script. Disc file RSRCALL.RBB has no slack before MOVIE.MMB: growth goes to the zeroed DUMMY file (36 MB) or by LZSS-packing raw `ssg` entries. Menu cursor presses need ~60 frames between them. Downloaded `jPSXdec` was refused by the auto-mode classifier: see `docs/status.md`.

## Status
`docs/status.md`: done, next, open bugs. Update it at the end of every session.

# Bastard!! Utsuronaru Kamigami no Utsuwa English translation

Unofficial English fan translation of **Bastard!! Utsuronaru Kamigami no Utsuwa** (PlayStation, SETA, 1996, SLPS-00542): the source text and tools
that build the patch. Work in progress: see `docs/status.md`.

**Just want to play?** Download the patch from [Releases](../../releases) and follow its README. This repository holds
no game data you can play; you need your own dump of the Japanese game.

**Found a bug?** [Report it](../../issues/new/choose): untranslated text, typos, overflow, crashes. Attaching a savestate
helps most.

## Translation status

| Part | Status |
|---|---|
| Dialogue and story | Translated |
| Menus, items, skills, enemy names, battle text, system messages | Translated |
| Title screen, area and chapter cards, graphics with text | Translated; the end card's brush calligraphy is left as art |
| Movies | Captions redrawn in English in the opening and the alternate ending; the others have no text |
| Memory card file header | Left in Japanese (must stay Shift-JIS) |
| Leftover developer debug screens | Left in Japanese |

Known issues: 3,858 of 12,504 strings were not shown on screen in testing (mostly rare enemy names, encounter labels and battle lines): they fit by measured width but nobody has seen them in the game. The battle HUD's name plate is game art and reads `VIE`, while the text says `Vai`. See [Issues](../../issues).

## What's here

| Path | What it is |
|---|---|
| `script/` | Every text block: original Japanese and English. Translation fixes go here. |
| `glossary.md` | Binding names, terms and style rules. |
| `tools/` | Python build chain: extract, insert, lint, release. |
| `tests/` | pytest suite (ROM-dependent tests skip when the ROM is absent). |
| `docs/re/` | Reverse-engineering notes. |
| `docs/decisions.md`, `docs/status.md` | Rulings with their reasons; current progress and open bugs. |
| `docs/fonts.md` | Fonts used and their licences. |
| `AGENTS.md` | Instructions for coding agents (`CLAUDE.md` points to it). |
| `.claude/agents/` | Subagent types (translator, reviewer, visual QA, playtester) with only the tools each needs. |

## Build your own patched ROM

Needs Python 3.12+ and your own dump of the Japanese game.

```sh
git clone https://github.com/minhnhattonthat/bastard-utsuronaru-kamigami-no-utsuwa-en
cd bastard-utsuronaru-kamigami-no-utsuwa-en
git config core.hooksPath tools/hooks
pip install numpy scipy pillow keystone-engine unicorn capstone
# copy your dump to: rom/Bastard!! Utsuronaru Kamigami no Utsuwa (Japan) (Rev 1).bin
#   (565989984 bytes, CRC32 4aed7dc5, MD5 187007de32557e27d933bdcacd9e9241,
#    SHA-1 589f9c8eb6d75d4011a22f2fc777e9f357d13761; the build refuses any other dump, see rom.sha1)
python -X utf8 tools/disc.py extract
python -X utf8 tools/rbb.py unpack
python -X utf8 build.py                                # -> build/bastard_en.bin, .cue
python -X utf8 tools/check.py                          # tests + text lint
```

Tested in PCSX-Redux with a real BIOS: the game's text uses the BIOS kanji font.

## Support

If you enjoy this translation, you can support my work on Ko-fi:

[![Support me on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/minhnhattonthat)

## Licence

Tools and English translation: MIT. The original Japanese text in `script/` is SETA's and is included only so
the translation can be checked against it. Bastard!! Utsuronaru Kamigami no Utsuwa is (c) SETA and its licensors; this project is not affiliated with them.
Do not share patched ROMs.

The translation was made with extensive AI assistance (Claude by Anthropic). Corrections are very welcome.

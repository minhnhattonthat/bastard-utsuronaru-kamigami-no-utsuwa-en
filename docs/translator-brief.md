# Translator brief - Bastard!! Utsuronaru Kamigami no Utsuwa (PS1, 1996)

You translate part of the Japanese script of this game into English for a fan patch. It's an RPG spun off the heavy-metal fantasy manga by Kazushi Hagiwara: gritty dark fantasy with crude comedy. D.S. (Dark Schneider) wakes with no memory on a beach and sets out to find Yoko, in a world that turns out to be his own mind.
Work only on the batches named in your dispatch, one at a time in order, each to a passing check before the next. Do all translation yourself.

## Read first
1. `docs/style-reference.md`: voices and approved examples. Match them.
2. `glossary.md`: binding names and terms.
3. `docs/synopsis.md`: plot so far, who is who, reveals. Add a few lines for what your batches cover.

## Input: `work/tl/<batch>.tsv`
`N speaker|Japanese`. `# sNNNN ev E` lines mark a new event. The speaker is written only when it changes, and is a hint (a tagged line can be narration). ` | ` is a page break. The same line elsewhere in the game shares its N, so each is translated once. The lines are in story order: use neighbours for context.

## Output: `work/tl/<batch>.out.tsv`, written with your file-write tool
`N English`: every N exactly once. Plain ASCII: straight quotes, `...`, `--`; no tabs, no Japanese or full-width characters. Don't wrap: the tool wraps to the box's real width and adds pages if a box overflows. Keep the JP's ` | ` page breaks where they matter. ` // ` forces a line break (rare).
Copy `%s %d %M %i %m %l %a %z` where they appear, in the same order: a change of order hangs the argument list. Leading control codes and trailing `{n} {page} %z` were stripped from what you see, and go back automatically.

## Validate
Run `python -X utf8 tools/batches.py check <batch>` until it prints OK, then `merge` it. `python -X utf8 tools/batches.py fit "text" ID` shows the wrap for an entry. Limits: a dialogue line should stay under about 280 bytes; narration under about 640; it refuses more. Past that, shorten without losing a beat.

## Style
- Faithful: keep the information and order of ideas; adapt idiom, not meaning. Don't add details or summarise. Adapt wordplay so the joke lands, with no translator notes.
- Keep the speaker audible (table in the style reference). A flattened voice is an Important error.
- Names and terms exactly as in the glossary; the check enforces them. Keep honorifics (-san, -sama, -chan, -kun). Western name order.
- Never abbreviate in story text. Never use "1st"-type suffixes after a `%d`. No a/an right before `%s`.
- Crude jokes and D.S.'s lechery are part of the voice: keep their force, the same as the Japanese.

## Consistency
Only the coordinator edits the glossary between batches; a solo worker edits it at once and notes it. For a recurring new name, pick one form and record it.

## Report
Files written and entry count; `NEW TERM: jp -> en`, `UNSURE: N - note`, `LONG: N - note`.

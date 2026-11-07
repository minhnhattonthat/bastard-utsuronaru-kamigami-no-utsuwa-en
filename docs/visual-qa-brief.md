# Visual-QA reviewer brief - Bastard!! Utsuronaru Kamigami no Utsuwa

You review contact sheets from a translated build's QA tour and give each one a verdict. Read-only on everything
except your one verdict file: no edits to the repo, no git, no subagents.

## Inputs (in your dispatch)
- A chunk file: one `id<TAB>path` line per sheet. Read every sheet in it; none may be skipped.
- Your verdict file: `work/qa/verdicts/<chunk>.tsv`.
- Optional: the original ROM's sheets (`work/qa/tour_jp/`, same ids) and `glossary.md`.

## How to look
- Tour sheets are half or third scale, so no text on them can be read, and zooming a sheet doesn't help. Read the full-size pages from `tools/debug/qa_full.py` (`work/qa/full/`, its docstring maps ids to pages; about 1,000 tokens a page of 12, 2,300 for a page of 30). A scene's first page is often boot, card and prologue.
- A battle's first log row is fixed and later rows scroll under it, on the original too: a row that stays put while the others move is not a bug.
- Read each sheet whole first. Where text is small, zoom into it with
  `python -X utf8 $SKILL/scripts/sheet.py SHEET.png --crop x,y,w,h --zoom 3 --out <scratch>.png` and read that.
- When something looks wrong, open the same id from `tour_jp/` (`sheet.py EN.png --compare JP.png`). If the
  original shows the same thing, it is the game's own behaviour: `ok`, with a note.
- Zoom into every Yes/No prompt, selection box, menu row and speech bubble: a few pixels of misalignment don't show
  at sheet scale. To measure one: `python -X utf8 $SKILL/scripts/inkbox.py SHOT.png x,y,w,h`.

## Judge
An `issue` is any of:
- Japanese still visible;
- text overflowing a box, clipped by a frame, or running off screen;
- text off-centre where the original centres it: an option in its selection box or cursor brackets, a label, a bubble;
- garbage tiles, wrong or missing glyphs, a strike or stray pixels across letters;
- broken line breaks: a word split mid-line, a page ending mid-sentence, a one-word last line;
- an empty box where text belongs;
- a name that differs from `glossary.md`.

Standing non-bugs, `ok` (the controller adds the game's own below):
- text still typing out, a box mid-fade or mid-scroll, a cursor caught mid-blink;
- a map or scene still loading after a warp;
- anything identical in the original's sheet.
- the battle HUD's name plate `VIE` is game art (`docs/status.md`, D9);
- the end card's brush art (entry 1484, with English `THANK YOU!!`) is left as art until the owner rules (`docs/status.md`);
- the handwritten note picture (entry 1172) is Latin scrawl in the original, not Japanese;
- `Head to %s?` and `Leave %s?` start at the box's left edge: their width depends on the map name;
- debug screens and the memory card header stay Japanese by intent (`docs/status.md`).

## Verdicts
Write your verdict file once you have read every sheet, one line per id in the chunk:
`id<TAB>ok|issue<TAB>what and where` (for an issue: which tile, which text, what is wrong).
Then return a short summary: counts, and the issues one per line.

# Decisions

The user's rulings on scope, style and trade-offs, newest last. Read before asking the user anything; if a later
decision replaces one, mark the old one "replaced by D<n>" instead of deleting it. Binding term spellings live in
`glossary.md`; this file holds the why.

| # | Date | Question | Options offered | Decision and reason |
|---|---|---|---|---|
| D1 | 2026-11-06 | Honorifics and name order | keep (-san), drop; JP or Western order | Keep honorifics; Western order (given name first). Owner's standing answer for one-shot runs. |
| D2 | 2026-11-06 | Romanization source for names | official art, earlier patch, Hepburn | Official English names where they exist, else an earlier fan patch, else Hepburn without macrons. Owner's standing answer. |
| D3 | 2026-11-06 | Credits | stay Japanese, translate | English. Owner's standing answer. |
| D4 | 2026-11-06 | Abbreviations | engine work first (default), abbreviate | Engine work first: skill default, no owner ruling against it. |
| D5 | 2026-11-06 | Graphics text left in Japanese | none (default), list | Translate all (titles, menus, banners, cards). Leave the original Japanese logo only if it has no official English version. The main logo here is already Latin, so only its kanji subtitle needs a redraw. |
| D6 | 2026-11-06 | Specs and plans | need approval, pre-approved | Pre-approved: keep going through every checkpoint. |
| D7 | 2026-11-06 | Existing saves, memory cards, savestates | use, none | None provided; build the debug tool as usual. |
| D8 | 2026-11-06 | Publishing | - | Never run `gh release create` or change repo visibility. The run ends at a built and verified release zip. Commits go to main and get pushed at each phase end. |
| D9 | 2026-11-07 | Names without an official spelling, and the Netflix/Viz spellings | seed list, official, game labels | Worker's default under D2, not an owner ruling: official where found (Lucien, Sean Ari, Di-Amon, Angus Yarn, Zion Sol Vandenverg, Yngwei), else the game's portrait labels (Macalpine, Blad, Ros), else readable Hepburn. ヴァイ = Vai, not the label `Vie`, since Steve Vai is the reference. Owner can correct in `glossary.md`. |
| D10 | 2026-11-07 | Story pass unit, `--.`, enemy `亜`/`云` | whole chapters or arc files; `--` or `...`; `Ah`/`Un` or a real name | Worker's defaults, not owner rulings. 17 fixed arc files, because a chapter doesn't fit one fresh read. `--`, the glossary's ――, and it never grows a line. `Agyo`/`Ungyo`: they appear as a pair, so read as the 阿吽 temple guardians; sprite not seen. |
| D11 | 2026-11-07 | `魔人` (D.S.'s epithet) | "demon" (movie, 6 lines), "fiend" (8 lines) | Worker's default, not an owner ruling. "Fiend" everywhere, script and opening movie: `魔族` is "demon" (Ichael's race), and this keeps the two apart. |
| D12 | 2026-11-07 | Publish v1.0 | Public repo + release; release keeping repo private; don't publish yet | Public repo + release v1.0, owner's explicit call, one-off override of D8. Accepts the 3,858-string waiver and QA read without an independent reviewer. D8 still holds for later runs. |

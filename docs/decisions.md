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
| D9 | 2026-11-07 | Names without an official spelling, and the Netflix/Viz spellings | seed list, official, game labels | Worker's default under D2, not an owner ruling: official where found (Lucien, Sean Ari, Di-Amon, Angus Yarn, Zion Sol Vandenverg, Yngwei), else the game's portrait labels (Macalpine, Blad, Ros), else readable Hepburn. ヴァイ = Vai, not the label `Vie`, since Steve Vai is the reference. Owner can correct in `glossary.md`. |
| D8 | 2026-11-06 | Publishing | - | Never run `gh release create` or change repo visibility. The run ends at a built and verified release zip. Commits go to main and get pushed at each phase end. |

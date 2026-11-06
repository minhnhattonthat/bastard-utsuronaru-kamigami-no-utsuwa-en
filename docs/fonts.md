# Fonts

Every font or glyph sheet the build reads ends up inside the released patch, so its licence must allow that. One row
per file; a font with no known licence doesn't go into a release.

| File | Source (URL, version) | Licence | Redistributable in a patch | Used for | Changes made |
|---|---|---|---|---|---|
| fonts/vwf12.txt | drawn for this project | same as repo | yes | all game text in the 12x12 cell (fonts 1 and 8) | - |
| fonts/Cinzel.ttf | github.com/google/fonts `ofl/cinzel/Cinzel[wght].ttf`, fetched 2026-11-07 | SIL OFL 1.1 (`fonts/Cinzel-OFL.txt`) | yes | title cards, chapter ends, publisher card, title subtitle (`tools/cards.py`, Bold instance), movie captions (`tools/movie_text.py`) | - |
| fonts/LibreBaskerville.ttf | github.com/google/fonts `ofl/librebaskerville/LibreBaskerville[wght].ttf`, fetched 2026-11-07 | SIL OFL 1.1 (`fonts/LibreBaskerville-OFL.txt`) | yes | text pages of movie #162 (`tools/movie_text.py`) | - |

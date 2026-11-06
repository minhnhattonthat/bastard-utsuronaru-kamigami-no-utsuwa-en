# Skill gotchas

One line per gotcha: the reference file it belongs in, then the fact.

- references/translation.md: with no subagents allowed (Orca worker), per-batch tokens decide the run. A batch line of `N speaker|JP` with the speaker only on change, identical lines deduped, `{n}` stripped, and output `N English` with a wrap tool to the box's pixel budget, is smaller than the template's `id<TAB>speaker<TAB>form<TAB>limit<TAB>jp` (saving not measured). Structured stat sheets and item descriptions can be generated from field tables instead of translated line by line.
- references/translation.md: `assets/batches.py` has no notion of authored vs wrapped English; when the tool wraps, keep `en` as the wrapped form and rebuild the authored form by `{n}` -> space (`batches.authored`) so repeats in other box widths re-wrap correctly.
- references/translation.md: a full review pass by one solo worker costs about 1.8 MB of JP/EN pairs (about 1.7M tokens: a 113 KB file measured about 100k), so at most 1 of 17 files per worker when no subagent or codex is available; `codex exec` quota can run out and every parallel run then exits rc=1 with no report: check the first log before waiting on the rest.
- references/emulator-qa.md: a marker tour cannot catch a run-time widening overflow: short marker ids fit the save list, while real English map names (16+ ASCII chars) doubled in a fixed full-width buffer and hung it. Re-run the menu and save scenes on the real text build, and on a blank memory card (emu.py --sav) for the format prompt.

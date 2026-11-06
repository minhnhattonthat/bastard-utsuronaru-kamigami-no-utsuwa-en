# Skill gotchas

One line per gotcha: the reference file it belongs in, then the fact.

- references/translation.md: with no subagents allowed (Orca worker), per-batch tokens decide the run. A batch line of `N speaker|JP` with the speaker only on change, identical lines deduped, `{n}` stripped, and output `N English` with a wrap tool to the box's pixel budget, is smaller than the template's `id<TAB>speaker<TAB>form<TAB>limit<TAB>jp` (saving not measured). Structured stat sheets and item descriptions can be generated from field tables instead of translated line by line.
- references/translation.md: `assets/batches.py` has no notion of authored vs wrapped English; when the tool wraps, keep `en` as the wrapped form and rebuild the authored form by `{n}` -> space (`batches.authored`) so repeats in other box widths re-wrap correctly.

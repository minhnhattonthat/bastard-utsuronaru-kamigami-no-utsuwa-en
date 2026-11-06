# Glossary - Bastard!! Utsuronaru Kamigami no Utsuwa

Binding for every translator and reviewer. `tools/batches.py check` enforces the tables: when a JP form is in a line, one of the EN forms must be in its English. Only the controller edits this file.

## Rulings (options and reasons in docs/decisions.md)
- Honorifics: kept (ヨーコさん = Yoko-san, ネイ様 = Nei-sama, the lint checks them after a character's name). Name order: Western (given name first).
- Romanisation source: official English names where they exist (Viz manga, the 2022 Netflix series), else an earlier fan patch (DeJap's Super Famicom patch), else Hepburn without macrons. The cast is named after metal musicians: when a name has no official spelling, keep it readable as the same word.
- Credits: English.
- Register: gritty dark fantasy with crude comedy. Narration is literary, the cast talks like the manga: D.S. arrogant, vulgar, lecherous.
- Abbreviations: full names and terms everywhere; item and skill names have 17 bytes and enemy names 19, so those may compress (never in story text). `D.S.` is canon, not an abbreviation of convenience.

## Style rules
- Punctuation map: 「」 -> "...", 『』 -> '...', “” (inner voice) -> "...", ・・・ / …… -> ..., ！？ -> !?, ―― -> `--`.
- Plain ASCII. No translator notes.
- Voices: `docs/style-reference.md`.

## Characters
| JP | EN | max | notes | Avoid |
|---|---|---|---|---|
| ダーク・シュナイダー / Ｄ・Ｓ | Dark Schneider / D.S. | | | |
| ルーシェ・レンレン / ルーシェ | Lucien | | official; game label `Rushie` | Rushie / Lushe |
| ティア・ノート・ヨーコ / ヨーコ | Yoko | | full: Tia Noto Yoko | |
| シーラ | Sheila | | full: Sheila Tuel Meta-llicana; game label `Sheera` | Sheera |
| ラーズ | Lars | | full: Lars Ul Meta-llicana | Larz |
| ガラ | Gara | | | |
| アーシェス・ネイ / ネイ | Nei | | full: Arshes Nei | |
| カル＝ス / カル | Kall | | full: Kall-Su | |
| アビゲイル | Abigail | | | |
| ヨシュア | Joshua | | full: Joshua Belahia | |
| シェン | Schen | | full: Schen Kar | |
| ヴァイ | Vai | | full: Vai Steave; game label `Vie`, Steve Vai is the reference | Vie |
| ヨルグ | Jorg | | full: Jorg Fisis | |
| アンガス | Angus | | full: Angus Yarn | |
| カイ | Kai | | full: Kai Harn | |
| シーン | Sean | | full: Sean Ari | |
| ダイ・アモン / ダイ | Di-Amon / Di | | official; short ダイ can be Di | Dai |
| イングヴェイ | Yngwei | | full: Yngwei von Malmsteen | Yngwie |
| ジオン | Zion | | full: Zion Sol Vandenverg | |
| マカパイン | Macalpine | | full: Macalpine Toni Strauss | |
| ボル | Bol | | full: Bol Gil Bol | |
| バ・ソリー | Ba Thory | | | |
| ザック | Zakk | | full: Zakk Walder | |
| ブラド | Blad | | full: Blad Kills | |
| ロス | Ros | | full: Ros the Boss Friedrich | |
| イダ | Ida | | full: Ida Deesna | |
| サイクス | Sykes | | full: Sykes von Snowhite | |
| シェラ | Shella | | full: Shella E. Lee; not Sheila (シーラ) | |
| ラン | Ran | | full: Ran Di-Rose Stein | |
| 鬼忍将 | High Ninja | | game label | |
| ジン | Jin | | | |
| 至高王 | High King | | game label | |
| ガイン | Gain | | | |
| 暗黒僧 | Dark Priest | | game label | |
| イーカル | Ichael | | game label | |
| ウンディーネ | Undine | | | |
| ロキ | Loki | | | |
| オクトール | Octol | | | |
| アンスラサクス | Anthrasax | | | |

## Places
Title cards carry the developers' own English subtitles (for example 忘却の浜辺 / 'D・S、喪失す' / `Amnesians`; 竜船 / `Encounter`): see `docs/re/graphics.md`. Keep those subtitles unless they are wrong.

| JP | EN | max | notes | Avoid |
|---|---|---|---|---|
| メタ＝リカーナ | Meta-llicana | | | |

## Items / skills / terms
| JP | EN | max | notes | Avoid |
|---|---|---|---|---|
| 一体技 | Unison | | two or more people strike one target as one | |
| 連続技 | Chain | | a linked attack | |
| 四天王 | Divine Kings | | official | |
| 魔戦将軍 | Sorcerer Generals | | official | |

## Decisions from earlier batches

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
| 地龍 | Earth Dragon | | | |
| 要石 | keystone | | | |
| 竜船 | Dragon Ship | | | |
| 聖玉 | Holy Orb / Orb | | also ヨーコ玉 = Yoko orb | |
| 魔操兵 | puppet | | | |
| 竜牙兵 | dragontooth soldier | | | |
| 妖斬糸 | demon-slash wire | | item-sheet short form: Wire | |
| 妖縛士 | demon binder | | Macalpine's class | |
| 影使い | shadow user | | Bol's class | |
| 侍大将 | Samurai General | | | |
| モノリス | monolith | | | |
| 一体技 | Unison | | two or more people strike one target as one | |
| 連続技 | Chain | | a linked attack | |
| 四天王 | Divine Kings | | official | |
| 魔戦将軍 | Sorcerer Generals / Sorcerer General | | official | |
| 破裏拳流 | Hariken School | | Kai's sword style | |
| 狼麒 | Loki | | the wolf-headed god; ロキ's kanji form | Wolf Qilin |
| 虚神 | Hollow God | | echoes the game title 虚ろなる神々 | False God |
| 虚神王 | Hollow God King | | | False God King |
| 魂喰らい | Soul Eater | | Gain's and later Zion's sword | |
| 魔神剣 | Demon Sword | | skill-table spelling | |
| 黒い断頭台 | Black Guillotine | | skill-table spelling | |
| 死黒核爆烈地獄 | Black Death Nuclear Hell | | chant ends: Dio Mi Geezer Ozzy | |
| 雷帝 | Thunder Empress | | Nei's title | |
| 巨獣 | great beast / Great Beast | | swims under the snowfield | |
| 魔紅玉 | Demon Ruby | | | |
| 水龍 | Water Dragon | | | |
| 氷結湖 | Frozen Lake | | | |
| 変蟲 | strange bug | | Ba Thory's pet; label Strange Bug | |
| 自走砦 | walking fort / Walking Fort | | the High Ninja's; capitalised only as a label; 自走天守閣 = walking keep | Mobile Fortress |
| 寄岩砦 | Hermit Rock Fort | | the fort docks into the rock like a hermit crab | |
| 鬼哭関 | Ogre Wail Gate | | plain 関門 = checkpoint | |
| 破界門 | World-Breaker Gate | | | |
| 霊子炉 | spirit reactor | | | |
| 霊子力 | spirit power | | | |
| 風神塔 | Wind God Tower / Wind Tower | | short form only in 19-byte enemy names | |
| 雷神塔 | Thunder God Tower / Thunder Tower / Thunder Key | | short forms only in 17-byte item and 19-byte enemy names | |
| 蟲使い | bug tamer | | Ba Thory's clan | |
| ムラサメ | Murasame / Murasame Blade | | cursed sword Jin haunts, Gara's | |
| 慶雲鬼忍剣 | Omen Ninja Sword | | the Murasame's secret art; skill-table spelling | |
| 七鍵守護神 | Seven-Key Guardian | | D.S.'s ultimate spell; chant: Kaizard Alzard Ki Sukuhanse Gros Silk | |
| 鏖帝 | Slaughter Emperor | | | |
| 魔雷妃 | Demon Thunder Queen | | | |
| 王鴉 | King Raven | | | |
| 三妖魅 | Three Fiends | | the queen's phantom bodies | |
| 三男神 | Three Male Gods | | Teutates, Esus, Taranis | |
| 樹棺城 | Tree-Coffin Castle | | | Tree Coffin Castle |
| 龍樹 | Dragon Tree | | | |
| 翼龍 | wyvern | | | |
| 翼龍の左眼 | Wyvern's Left Eye | | | |
| 鬼道衆 | Kido Corps | | Kai, Sean, Ran | |
| 黒騎士 | Black Knight | | Ran's title under the queen | |
| 影流 | Shadow School | | Zion and Schen's sword style | |
| 毒乙女 | Poison Maiden | | second of the Three Fiends | |
| 馬頭母 | Horsehead Mother | | third of the Three Fiends | |
| 荊の壁 | Wall of Thorns | | | |
| 水妖 | water spirit / Water Sprite | | the Undines; 水妖の湖 = water spirits' lake, label `Lake of the Water Sprite` | water demon |
| 夢幻鏡 | Dream Mirror | | | |
| 幻影城 | Phantom Castle | | item-sheet short form: Phantom Keep Key | |
| 宿り木の短刀 | Mistletoe Dagger | | | |
| 黒夜叉 | Black Yaksha | | Zion's sword | |
| 青爪邪核呪詛 | Blue Nail Evil Core Curse | | chant: Ki Orbs Plata Ro | |
| シナプスケーブル | synapse cable | | | |
| クォッ・ポー | Kwa Po | | Jorg's father's barehanded art | |
| ニルス・ショーン・ミフネ / ミフネ | Mifune | | full: Nils Shawn Mifune, Jorg's patron | |
| ダーシュ | Dahsh | | Nei's pet name for D.S. | |
| トライヴン | Trivun | | goddess composite of the Three Fiends; table spelling | |
| 天地爆烈 | Heaven-Earth Blast | | chant: Di Vumu Stein | |
| 氷獄塔 | Ice Hell Tower / Ice Tower | | Kall-Su's castle; short form only in item and enemy names | |
| マニプーラ | Manipura | | a stage of the journey (chakra name) | |
| 癌臓宮 | Cancer Palace | | label spelling | |
| 十賢者 | Ten Sages | | old-world scientists; Abigail left them | |
| 高次意識界 | Higher Consciousness Realm | | center of D.S.'s mind; 内宇宙 = inner universe, 精神世界 = spirit world | |
| サルデス器官 | Sardis organ | | the petal-valve accelerator; 螺の道 = "spiral" road | |
| 薬師丸 | Yakushimaru | | Schen's white-sheathed short sword | |
| ブラック・レネゲイド | Black Renegade | | Zion's armor | |
| 爆炎の征服者 | Conqueror of Explosive Flame | | D.S.'s title | |
| 皇龍破 | Imperial Dragon Burst | | | |
| 封神剣 | God-Sealing Sword | | Lars's sword | |
| 爆霊地獄 | Venom | | ベノン's kanji form; D.S.'s own spell, skill-table spelling | |
| 輸魂の秘法 | Soul Transfusion | | secret art; 輸魂術 in the skill table | |
| 超原子崩壊励起 | Super Atomic Collapse Excitation | | D.S.'s final spell; chant: Glenn Ken Hill Halford | |
| サードアイ | Third Eye | | the eye in the sky, exit from the spirit world | |
| 闇のアダム | Adam of Darkness | | Satan's name for D.S. | |

## Stat sheet terms (generated by `tools/item_text.py`, not lint-enforced)
Classes: 重戦 Heavy, 剣士 Fencer, 魔剣 Mystic, 侍 Samurai, 忍者 Ninja, 格闘 Brawler, 吸血 Vampire, 魔使 Mage. Slots: 両手主 Two-Hand, 片手主 Main, 片手副 Off, 片手兼 Either. Elements: 無 Neutral, 火 Fire, 水 Water, 地 Earth, 風 Wind, 光 Light, 闇 Dark. Status: 昏倒 Stun, 睡眠 Sleep, 脱力 Lethargy, 魅了 Charm, 不和 Discord, ノイズ Noise, 毒 Poison, 停止 Stop, 戦闘不能 incapacitated. Stats: 体力 Vitality, 知力 Wisdom, 素早さ Speed, 運 Luck, テンション Tension. Skill names and items: `script/tbl_0386.json`, `tbl_0388.json`; use those spellings in story text (ダムド = Damned, ディオ = Dio, エグ・ゾーダス = Exodus, ベノン = Venom). Enemy names: `tools/monsters.tsv`.

## Decisions from earlier batches
- 魔法剣士・侍: "magic swordsman, samurai". D.S. calling himself Ｄ・Ｓ様 = "the great D.S.-sama"; 俺様 = "the great me"; ハンサム様 = "Mister Handsome"; 超絶美形 = "super-gorgeous".

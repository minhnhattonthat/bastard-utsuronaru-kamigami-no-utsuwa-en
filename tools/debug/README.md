# Debug tool

Reach any scene from a cold boot, no save and no playthrough. How it works: `docs/re/code.md`. Everything is RAM pokes on top of the disc, so it works on the original and on any build, and is never in a release.

```
python -X utf8 tools/debug/warp.py list [GROUP]        # groups: system menu debug battle ending map event
python -X utf8 tools/debug/warp.py camp_items          # shots and log in work/qa/warp/camp_items/
python -X utf8 tools/debug/warp.py camp_items --cue build/bastard_en.cue
python -X utf8 tools/debug/warp.py all --group map     # exit 1 on a miss; work/qa/warp/results_map.tsv
python -X utf8 tools/debug/warp.py x --vars "MAP=12 POINT=e004 EVENT=5 MASTER=1" --frames 3000 --check event
```

Add `--state` to keep `work/states/NAME.state`. Regenerate after a rebuild, because states carry old code and file offsets. Re-run `gen_scenes.py` if map data changes. If hooks move code the warp patches, `warp.lua` stops with an error at frame 2000 and `tests/test_warp.py` fails: update its table.

`--vars` names and `CHECK` values are in the header of `warp.lua`. `maps.tsv` lists every map point. `pin.lua` holds RAM values. Don't hold HP during a battle: the battle waits for the HP bar to reach the value, and holding it hangs the fight, so set `PIN_ONCE=1`. `$SKILL/scripts/lua/probes/ramdump.lua` dumps RAM.

## Marker tours
`build.py --marker` then `warp.py all --cue build/bastard_marker.cue --probe tools/debug/drawlog.lua`; `--failed` re-runs what `results.tsv` does not list as ok. `tour_report.py` turns the logs into `tools/windows.json` (id -> smallest box width seen) and `work/qa/tour_unseen.txt`, `work/qa/tour_jp.txt`. `fmt_sites.py` lists every sprintf and its stack buffer; `ssg_stress.py` makes a `--qa` file that grows one script to its limit.

Warped events have no triggering object, so `warp.lua` skips the chest animation (800C16F0): with an index past the object table it calls through heap garbage, which hung some scenes on the marker build. On the original disc the same read happens to do nothing, but it hangs there too under the debugger. A chest opening is therefore not shown by these scenes.

## Scene list
`scenes.tsv` (from `gen_scenes.py`): title and real boot path, every menu, debug screens, battles (start, commands, win, loss, boss, with party), all movies and ending branches, all 79 maps with their title cards, and every script event of every map.

## What a pass means
- Each scene with a check passed that RAM test: map record and dungeon overlay, battle or ending overlay, field after a battle (`won`), title after a battle (`lost`), or `event`: the script object was armed for the event, which only happens when that event was found. A negative control (event 999, absent) fails as it should.
- Scenes with check `none` (real-boot, movies) were read by eye, as were the sheets in `docs/screenshots/warp/`.
- `event` proves the start of the script only, and a RAM pass can hide a black screen (the party scenes did). After `warp.py all`, run `warp_report.py`: it compares the shots with the field just before the event, and picks each event's proof shot. `events_index.tsv` names the tiles in `events*.png`. Its exit 1 lists text events never seen.

## Event scenes
- `gen_scenes.py` reads the flag tests that open each event and sets those flags (`SETFLAGS`), so the event runs past them. Later branches still take whatever the state gives, so a scene shows one path, not every line.
- An event with no script string in its code usually shows nothing: "unchanged" is the expected result for those.
- Events run from the Start branch of the field loop. `ENTRY_EVENT` uses the map-entry hook instead: only that path fades the field back in after an event that ends on black, so the party scenes use it.

## Gaps
- **Text events never seen: current list from `warp_report.py`.** Each one's script starts, but its first text sits behind a test `SETFLAGS` does not handle. 80043224, 80043538 and 80043178 ask the party object; 80043A2C, 80042E04 and 80042F30 are not traced. `tests/test_warp.py` does not check this. Phase 5's marker build should measure which string ids a tour actually shows (a draw log) and add state for what is left.
- Map variants: only the variant a fresh state picks. 11 maps have more than one dsg.
- No scene for: `ここではセーブできません`, chests and locked doors text (`宝箱は開かない`, in the EXE), level-up. Reach them by walking in a map scene if a string needs it.
- Battle with a full party: `battle_party` has one placed member. Other members join through the events `script_calls.py 0x800432F8` lists.

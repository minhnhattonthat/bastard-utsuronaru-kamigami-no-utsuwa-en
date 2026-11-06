"""gen_scenes.py: write tools/debug/maps.tsv (every dsg point) and tools/debug/scenes.tsv (the scene list warp.py runs).
Run after any change to the map data: python -X utf8 tools/debug/gen_scenes.py

Map table: EXE RAM 0x8009BFA4, 79 records of 64 bytes (docs/re/code.md).
evt record: u32 w0 (x:9, z:9, y:7, top 4 bits = extra bytes after the 8-byte head), u32 w1 (letter:8, number:10, ...).
"""
import glob
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = 0x8000F800
TABLE, COUNT = 0x8009BFA4, 79
HERE = Path(__file__).parent
COLUMNS = ["name", "group", "vars", "route", "frames", "mash", "check"]
# Map card done, player has control. Original disc: arrival ~1300 + card ~500. A build with scripts in DUMMY arrives ~70
# frames later for the long seek, so leave room.
FIELD = "2200 -"
BATTLE_KEY = FIELD + ";20 select;10 select+square;170 -"
STAFF_FRAMES = 15000


def cstr(exe, addr):
    o = addr - BASE
    return exe[o:o + 64].split(b"\0")[0].decode("cp932")


def maps(exe):
    for i in range(COUNT):
        w = struct.unpack_from("<4I", exe, TABLE - BASE + 64 * i)
        dsgs = struct.unpack_from("<8H", exe, TABLE - BASE + 64 * i + 16)
        yield i, cstr(exe, w[2]), cstr(exe, w[0]), w[3], dsgs


def chunks(d, off, end):
    """Tag + u32 size; the top size bit marks a container, whose children follow."""
    while off + 8 <= end:
        tag, size = d[off:off + 4], struct.unpack_from("<I", d, off + 4)[0]
        yield tag, off + 8, size & 0x7FFFFFFF
        off += 8 + (size & 0x7FFFFFFF)


def evt_records(d):
    assert d[:4] == b"dsg "
    for tag, off, size in chunks(d, 8, len(d)):
        if tag == b"ded ":
            count = None
            for t2, o2, s2 in chunks(d, off, off + size):
                if t2 == b"nevt":
                    count = struct.unpack_from("<I", d, o2)[0]
                elif t2 == b"evt ":
                    p = o2
                    for _ in range(count):
                        w0, w1 = struct.unpack_from("<II", d, p)
                        yield chr(w1 & 0xFF), (w1 >> 8) & 0x3FF, w0 & 0x1FF, (w0 >> 9) & 0x1FF, (w0 >> 18) & 0x7F
                        p += 8 + (w0 >> 28)
                    assert p == o2 + s2, (p, o2 + s2)
                    return
    raise ValueError("no evt chunk")


def ssg_events(d):
    """Names of the event records after `prg`, without `idx` (that record is the script's $gp value: docs/re/code.md)."""
    if len(d) <= 0x18:
        return []
    prg = 0x18 + (struct.unpack_from("<I", d, 0x14)[0] & 0x7FFFFFFF)
    return [int(t) for t, _, _ in ((t.decode("latin1").strip(), o, s) for t, o, s in chunks(d, prg, len(d))) if t != "idx"]


def events(d):
    """[(name, offset)] sorted by offset, plus the file offset where the event records begin. Includes `idx`, the first
    string's offset, so the next record always ends an event's code."""
    prg = 0x18 + (struct.unpack_from("<I", d, 0x14)[0] & 0x7FFFFFFF)
    out = []
    for t, o, _ in chunks(d, prg, len(d)):
        out.append((t.decode("latin1").strip(), struct.unpack_from("<I", d, o)[0]))
    return sorted(out, key=lambda e: e[1]), prg


def event_codes(d):
    """{event number: its code}. Offsets count from file offset 8, so the code keeps its own offset as a slice base."""
    if len(d) <= 0x18:
        return {}
    evs, prg = events(d)
    code = d[8:prg]
    ends = [o for _, o in evs[1:]] + [len(code)]
    return {int(n): (code, o, end) for (n, o), end in zip(evs, ends) if n != "idx"}


def has_text(code, o, end):
    """True if the event loads a script string: `ori $aN,$zero,off` then `addu $aN,$aN,$gp`."""
    for i in range(o, min(end, len(code)) - 7, 4):
        w, w2 = struct.unpack_from("<II", code, i)
        r = (w >> 16) & 31
        if w >> 21 == 0x0D << 5 and w2 & 0xFFFF07FF == (r << 21 | 28 << 16 | r << 11 | 0x21) & 0xFFFF07FF:
            return True
    return False


FLAG_READ_STUB = 0x50  # script stub for 80042DA4 (flag id in $a0, value in $v0)


def guards(code, o, end):
    """[(flag id, value)] for the flag tests at the top of an event, the values that let it run past them.
    Stops at the first instruction that is not part of such a test."""
    out, a0, v1, read, in_slot, at_least = [], 0, 0, None, False, 0
    for i in range(o, min(end, len(code)) - 3, 4):
        w = struct.unpack_from("<I", code, i)[0]
        hi, lo = w >> 16, w & 0xFFFF
        was_slot, in_slot = in_slot, False
        if w == 0 or hi == 0x27BD or w >> 21 == 0x57D:  # nop, addiu $sp, sw rt,x($sp)
            pass
        elif hi == 0x3C04:  # lui $a0
            a0 = lo << 16
        elif hi == 0x3484:  # ori $a0,$a0
            a0 |= lo
        elif hi == 0x3404:  # ori $a0,$zero
            a0 = lo
        elif hi == 0x3403:  # ori $v1,$zero
            v1 = lo
        elif hi == 0x0411 and i + 4 + struct.unpack_from("<h", code, i)[0] * 4 == FLAG_READ_STUB:
            in_slot = True
        elif read is not None and hi == 0x2842:  # slti $v0,$v0,n: `flag >= n` for the branch after it
            at_least = lo
        elif read is not None and hi in (0x1440, 0x1C40, 0x1040, 0x1443):  # bnez, bgtz, beqz $v0; bne $v0,$v1
            out.append((read, {0x1440: at_least, 0x1C40: 0, 0x1040: 0 if at_least else 1, 0x1443: v1}[hi]))
            read, at_least = None, 0
        else:
            break
        if was_slot:  # the id is often finished in the bal's delay slot
            read = a0
    return out


def entry(n):
    return Path(glob.glob(str(ROOT / f"work/rbb/{n:04d}.*"))[0]).read_bytes()


def scene(name, group, vars="", route="", frames=None, mash=0, check="none"):
    if frames is None:  # a run must outlast its route, or the last presses never happen and the shot proves nothing
        frames = sum(int(step.split()[0]) for step in route.split(";")) if route else 1800
    assert frames >= sum(int(step.split()[0]) for step in route.split(";") if step), name
    return [name, group, vars, route, str(frames), str(mash), check]


def special_scenes():
    w = "MAP=1 POINT=p001"
    camp = FIELD + ";10 start;200 -;"
    join = "MAP=0 POINT=p001 ENTRY_EVENT=3"
    through = FIELD + "".join(";6 circle;90 -" for _ in range(80))
    # Tactics: open slot, pick the character, place, then back out to the field: the member now fights.
    placed = through + ";10 start;200 -;6 down;60 -;6 circle;300 -;6 circle;300 -;6 circle;300 -;6 cross;300 -;6 cross;300 -;6 cross;300 -"
    placed_at = sum(int(step.split()[0]) for step in placed.split(";"))
    s = [
        # No warp: the real boot path, so these also prove the title and the unpatched new game.
        scene("opening_movie", "system", "NOWARP=1", "2400 -"),
        # A 6-frame start can fall between the movie's pad reads: on the English build it did at frame 3000.
        scene("title_menu", "system", "NOWARP=1", "3000 -;30 start;300 -"),
        scene("continue_menu", "system", "NOWARP=1", "3000 -;30 start;250 -;6 down;60 -;6 circle;900 -"),
        scene("new_game_prologue", "system", "NOWARP=1", "3000 -;30 start;250 -;6 up;60 -;6 down;60 -;6 up;60 -;6 circle;13200 -",
              20000, 150),
        # Menus (Start and Select only answer with the debug bit off).
        scene("camp_menu", "menu", w + " MASTER=1", camp + "1 -", check="map"),
        scene("camp_items", "menu", w + " MASTER=1", camp + "6 circle;300 -", check="map"),
        scene("camp_character", "menu", w + " MASTER=1", camp + "6 right;60 -;6 circle;300 -", check="map"),
        scene("camp_character_page", "menu", w + " MASTER=1", camp + "6 right;60 -;6 circle;120 -;6 circle;300 -", check="map"),
        scene("camp_tactics", "menu", w + " MASTER=1", camp + "6 down;60 -;6 circle;300 -", check="map"),
        scene("save_menu", "menu", w + " MASTER=1", FIELD + ";10 select;300 -", check="map"),
        # A real party: 1_01 event 3 joins a member (tools/debug/script_calls.py 0x800432F8 lists every join), then
        # the route plays through its text with circle, so the next scene is the game's own state, not a poke.
        scene("camp_party", "menu", join + " MASTER=1", through + ";10 start;300 -", check="event"),
        scene("camp_tactics_party", "menu", join + " MASTER=1", through + ";10 start;200 -;6 down;60 -;6 circle;120 -;6 circle;300 -",
              check="event"),
        scene("camp_tactics_placed", "menu", join + " MASTER=1", placed, check="event"),
        scene("camp_item_list", "menu", join + " MASTER=1", through + ";10 start;200 -;6 circle;120 -;6 down;60 -;6 circle;300 -",
              check="event"),
        # Every item, poked into the inventory (warp.lua ITEMS), and the list scrolled past each name and description.
        scene("camp_items_all", "menu", join + " MASTER=1 ITEMS=501 ITEM_COUNT=5",
              through + ";10 start;200 -;6 circle;120 -;6 down;60 -;6 circle;300 -" + ";6 down;24 -" * 490, check="event"),
        # Every character joined (warp.lua ALLCHARS): the Self page's portrait strip, right steps through them.
        scene("camp_chars_all", "menu", join + " MASTER=1 ALLCHARS=1",
              through + ";10 start;200 -;6 right;60 -;6 circle;200 -" + ";6 right;90 -" * 28, check="event"),
        scene("battle_party", "battle", join + f" MASTER=1 BATTLE=1 DEBUG_AT={placed_at}", placed + ";20 select;10 select+square;900 -",
              check="event"),
        # The Form command's list: each formation's name and description, down steps through them.
        scene("battle_forms", "battle", join + f" MASTER=1 BATTLE=1 DEBUG_AT={placed_at}",
              placed + ";20 select;10 select+square;930 -;6 circle;120 -" + ";6 down;40 -" * 35, check="event"),
        # Debug screens the release never shows; they prove the debug bit and hold the flag editor.
        scene("debug_flags", "debug", w, FIELD + ";20 select;10 select+r1;300 -", check="map"),
        scene("debug_stats", "debug", w, FIELD + ";20 select;10 select+l1;300 -", check="map"),
        scene("debug_map_select", "debug", w, FIELD + ";20 select;10 select+start;400 -"),
        # Battles: any encounter id by the debug replay key.
        scene("battle_start", "battle", w + " BATTLE=1", BATTLE_KEY + ";400 -", 3200, 0, "battle"),
        scene("battle_commands", "battle", w + " BATTLE=1", BATTLE_KEY + ";500 -;6 circle;200 -", 3400, 0, "battle"),
        # Current HP of the first party member in battle is at 0x80106C2C (tested on screen): held high to win, 1 to lose.
        # Winning needs a placed member: with no one on the board only the enemies act.
        # The three enemies' current HP in encounter 1 (17, stride 0x1C0; 0x801374B0 on the original disc) go to 1 once the fight has loaded.
        scene("battle_win", "battle", join + f" MASTER=1 BATTLE=1 DEBUG_AT={placed_at} PIN_FROM={placed_at + 500} PIN_ONCE=1"
              # 800BB210 is rand()'s seed. A counter-attack can kill, and its dice follow the rand() calls made so far, which vary with
              # the build's text: without a fixed seed some builds lose every time (seeds 2-4 lose on the marker build; 1 wins).
              " ENEMY_HP=17 PINS=80106C2C:4:500,800BB210:4:1",
              placed + ";20 select;10 select+square;930 -" + "".join(";6 circle;90 -" for _ in range(90)), check="won"),
        scene("battle_boss", "battle", w + " BATTLE=800", BATTLE_KEY + ";600 -", 3400, 0, "battle"),
        scene("battle_lose", "battle", w + " BATTLE=1 PIN_FROM=3000 PINS=80106C2C:4:1", BATTLE_KEY, 12400, 60, "lost"),
        # Movies and endings: the states the sequence controller dispatches on.
        scene("movie_prologue", "ending", w + " STATE=1", "", 13000, 0, "none"),
        scene("movie_midgame", "ending", w + " STATE=2", "", 13000, 0, "none"),
        scene("ending_main", "ending", w + " STATE=3", "", STAFF_FRAMES, 0, "ending"),
        scene("ending_alt", "ending", w + " STATE=3 FLAGBITS=2", "", STAFF_FRAMES, 0, "ending"),
        scene("ending_thanks", "ending", w + " STATE=4", "", 6000, 0, "ending"),
    ]
    return s


SWEEP_KIND = {560: "n", 624: "d", 672: "c"}  # `fn` of a string -> sweep.lua's call; a fn that is only a hint (`text.md`) shows as dialogue


def sweep_scene(mid, here, ssg, codes):
    """One scene that prints every script string of a map (sweep.lua), and its list in work/qa/sweep/."""
    rows = json.loads((ROOT / f"script/ssg_{ssg:04d}.json").read_text(encoding="utf-8"))
    lines = []
    for e in rows:
        if e["kind"] == "text" and e["refs"]:
            kind = next((SWEEP_KIND[f] for f in e.get("fn", []) if f in SWEEP_KIND), "d")
            who = e["speaker"][0] if e.get("speaker") else -1
            lines.append(f"{e['refs'][0]} {kind} {who}")
    ev = min(n for n in codes if n != 1000)
    out = ROOT / "work/qa/sweep"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{ssg:04d}.txt").write_text("\n".join([str(codes[ev][1])] + lines) + "\n", encoding="utf-8")
    return scene(f"sweep_{mid}", "sweep", here + f" MASTER=1 EVENT={ev} SWEEP={ssg:04d}", FIELD + ";10 start;10 -", 2300 + len(lines) * 240, 30, "event")


def main():
    exe = (ROOT / "work/disc/SLPS_005.42").read_bytes()
    point_rows = ["map\tid\tname\tdsg\tssg\tpoint\tx\tz\ty"]
    scenes = special_scenes()
    linked = set()
    for i, mid, name, ssg, dsgs in maps(exe):
        points = list(evt_records(entry(dsgs[0])))
        for letter, num, x, z, y in points:
            point_rows.append(f"{i}\t{mid}\t{name}\t{dsgs[0]}\t{ssg}\t{letter}{num:03d}\t{x}\t{z}\t{y}")
        starts = sorted(f"{p[0]}{p[1]:03d}" for p in points if p[0] == "p") or [f"{points[0][0]}{points[0][1]:03d}"]
        here = f"MAP={i} POINT={starts[0]}"
        scenes.append(scene(f"map_{mid}", "map", here + " MASTER=1", "", 2100, 0, "map"))
        linked.add(ssg)
        codes = event_codes(entry(ssg))
        for ev in ssg_events(entry(ssg)):
            route = "" if ev == 1000 else FIELD + ";10 start;10 -"  # 1000 runs by itself on map entry
            need = ",".join(f"{f:#x}:{v}" for f, v in guards(*codes[ev]))
            flags = f" SETFLAGS={need}" if need else ""
            # mash = twice warp.py's event shot interval, so every text box gets a shot before the press clears it
            scenes.append(scene(f"ev_{mid}_{ev:04d}", "event", here + f" MASTER=1 EVENT={ev}" + flags, route, 4500, 240, "event"))
        scenes.append(sweep_scene(mid, here, ssg, codes))
    (HERE / "maps.tsv").write_text("\n".join(point_rows) + "\n", encoding="utf-8")
    rows = ["\t".join(COLUMNS)] + ["\t".join(s) for s in scenes]
    (HERE / "scenes.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    all_ssg = {int(Path(f).name[:4]) for f in glob.glob(str(ROOT / "work/rbb/*.ssg_.bin"))}
    print("scenes", len(scenes), "points", len(point_rows) - 1, "ssg with no map:", sorted(all_ssg - linked))


if __name__ == "__main__":
    main()

"""Debug tool: the warp patch table must match the disc, and the scene list must cover the map data."""
import csv
import re
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "debug"))
EXE = ROOT / "work/disc/SLPS_005.42"
BASE = 0x8000F800
needs_disc = pytest.mark.skipif(not (ROOT / "work/rbb/0010.ssg_.bin").exists(), reason="disc not extracted")


def scene_rows():
    with open(ROOT / "tools/debug/scenes.tsv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))


def test_scene_names_are_unique_and_runs_outlast_their_routes():
    rows = scene_rows()
    assert len({r["name"] for r in rows}) == len(rows)
    for r in rows:
        route = sum(int(step.split()[0]) for step in r["route"].split(";") if step)
        assert int(r["frames"]) >= route, r["name"]


@needs_disc
def test_warp_patches_the_code_it_was_written_against():
    exe = EXE.read_bytes()
    lua = (ROOT / "tools/debug/warp.lua").read_text(encoding="utf-8")
    pairs = re.findall(r"\{ (0x[0-9A-F]{8}), (0x[0-9A-F]{8}),", lua)
    assert len(pairs) == 21  # new-game branch 10, event trigger 6, chest animation 4, entry event 1
    for addr, word in pairs:
        assert struct.unpack_from("<I", exe, int(addr, 16) - BASE)[0] == int(word, 16), addr


@needs_disc
def test_scene_list_has_every_map_and_every_event():
    import gen_scenes

    names = {r["name"] for r in scene_rows()}
    exe = EXE.read_bytes()
    all_maps = list(gen_scenes.maps(exe))
    assert len(all_maps) == 79
    for _, mid, _, ssg, _ in all_maps:
        assert f"map_{mid}" in names
        for ev in gen_scenes.ssg_events(gen_scenes.entry(ssg)):
            assert f"ev_{mid}_{ev:04d}" in names


def test_guards_reads_the_flag_tests_that_open_an_event():
    import gen_scenes

    def asm(*words):
        return b"".join(struct.pack("<I", w) for w in words)

    bal = lambda at: 0x04110000 | ((0x50 - at - 4) // 4 & 0xFFFF)  # noqa: E731
    code = bytes(0x100) + asm(
        0x27BDFFE0, 0xAFBF0018,              # addiu sp; sw ra
        0x3C040002, bal(0x10C), 0x34844300,  # lui a0,2; bal flag; ori a0,a0,0x4300 (id finished in the delay slot)
        0x14400040, 0x3C040002,              # bnez v0; lui a0,2
        bal(0x11C), 0x34844200,              # bal flag; ori a0,a0,0x4200
        0x10400040, 0,                       # beqz v0; nop
        0x3404000C, bal(0x130), 0,           # ori a0,zero,12; bal flag; nop
        0x34030002, 0x14430040, 0,           # ori v1,zero,2; bne v0,v1; nop
        0x3404000D, bal(0x148), 0,           # ori a0,zero,13; bal flag; nop
        0x28420002, 0x14400040, 0,           # slti v0,v0,2; bnez v0 (leaves when flag < 2); nop
        0x3404000E, bal(0x160), 0,           # ori a0,zero,14; bal flag; nop
        0x1C400040, 0,                       # bgtz v0; nop
        0x34040005, 0x04110000,              # first real call ends the tests
    )
    assert gen_scenes.guards(code, 0x100, len(code)) == [(0x24300, 0), (0x24200, 1), (12, 2), (13, 2), (14, 0)]


def test_has_text_needs_a_gp_relative_string():
    import gen_scenes

    with_string = struct.pack("<II", 0x34044BA8, 0x009C2021)  # ori a0,zero,0x4ba8; addu a0,a0,gp
    assert gen_scenes.has_text(with_string, 0, 8)
    assert not gen_scenes.has_text(struct.pack("<II", 0x34044BA8, 0x00852021), 0, 8)  # addu a0,a0,a1


@needs_disc
def test_script_stub_lookup_finds_the_known_party_join(capsys):
    import script_calls

    script_calls.main(0x800432F8)
    assert "1_01 003 7" in capsys.readouterr().out


@needs_disc
def test_sweep_lists_every_script_string_and_each_ref_is_an_ori():
    from gen_scenes import entry
    if not (ROOT / "work/qa/sweep").exists():
        pytest.skip("gen_scenes.py not run")
    total = 0
    for row in scene_rows():
        if row["group"] != "sweep":
            continue
        ssg = int(re.search(r"SWEEP=(\d+)", row["vars"]).group(1))
        if ssg >= 9000:  # finds its strings in RAM (sweep.lua `=` lines): no script behind it
            continue
        d = entry(ssg)
        for ln in (ROOT / f"work/qa/sweep/{ssg:04d}.txt").read_text(encoding="utf-8").splitlines()[1:]:
            assert struct.unpack_from("<I", d, int(ln.split()[0]))[0] >> 26 == 0x0D, (ssg, ln)  # sweep.lua reads the string's offset from it
            total += 1
    assert total == 6332  # every `text` string of the 79 scripts

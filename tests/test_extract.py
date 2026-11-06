"""Phase 4: every extracted string re-encodes to the original bytes, and no Japanese text is left outside script/."""
import json
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import extract as X

need_disc = pytest.mark.skipif(not X.EXE.exists() or not (ROOT / "work/rbb/0010.ssg_.bin").exists(), reason="run tools/disc.py extract and tools/rbb.py unpack")


def test_codec_keeps_controls_and_unknown_bytes():
    raw = "あ!?\n".encode("cp932") + b"\x0b\x01\xff[{" + "漢".encode("cp932")
    text = X.decode(raw)
    assert text == "あ!?{n}{page}[01][FF][5B][7B]漢"
    assert X.encode(text) == raw


def test_span_stops_at_the_first_terminator():
    assert X.span(b"\x8c\x40\x0c\x00", 0) == 2
    assert X.span(bytes([0x8A, 0x40, 0x82, 0xA0, 0x00]), 0) == 4
    assert X.span(b"\x8c\x40\x0c\x82\xa0\x00", 0, (0x00,)) == 5  # overlay strings keep 0x0C as a control


def test_looks_text_rejects_code_bytes():
    assert X.looks_text("\x03%zあ".encode("cp932"))
    assert X.looks_text("あ\n\x0b".encode("cp932"))
    assert not X.looks_text(b"\x82\xa0\xff")  # lone high byte
    assert not X.looks_text(b"\x82\xa0\x08\x01")  # low control after text
    assert not X.looks_text(b"abc")


def test_bal_target_is_relative_to_the_delay_slot():
    assert X.bal_target(0x04110000 | 0xFFFF, 4) == 16 + 4 - 4
    assert X.bal_target(0x34040001, 4) is None


@pytest.fixture(scope="module")
def src():
    return X.sources()


@need_disc
def test_every_string_roundtrips_and_is_terminated(src):
    n = 0
    for stem, (_, d, rows) in src.items():
        for e in rows:
            raw = d[e["off"]:e["end"]]
            assert X.encode(X.decode(raw)) == raw, (stem, hex(e["off"]))
            assert not e["term"] or d[e["end"]] == int(e["term"], 16), (stem, hex(e["off"]))
            n += 1
    assert n > 12000


@need_disc
def test_strings_do_not_overlap_in_any_source(src):
    for stem, (_, _, rows) in src.items():
        ordered = sorted(rows, key=lambda e: e["off"])
        for a, b in zip(ordered, ordered[1:]):
            assert a["end"] <= b["off"], (stem, hex(a["off"]), hex(b["off"]))


@need_disc
def test_no_japanese_text_is_left_uncovered():
    # Code bytes that happen to read as text; each was read and has no pointer. Add to this list only with a reason.
    noise = {("exe", 0xFBC3), ("exe", 0x11DD9)}
    left = [x for x in X.leftovers() if (x[0], x[1]) not in noise]
    assert not left, left[:20]


@need_disc
def test_every_item_description_pointer_has_an_entry(src):
    d = X.EXE.read_bytes()
    have = {e["off"] for e in src["exe"][2]}
    missed = []
    for i in range(750):  # table 0x94808, one description per item
        o = struct.unpack_from("<I", d, 0x94808 + i * 4)[0] - X.EXE_BASE
        if 0 <= o < len(d) and o not in have and X.has_double(d[o:X.span(d, o, (0,))]):
            missed.append((i, hex(o)))
    assert not missed, missed


@need_disc
def test_speaker_table_lines_up_with_the_portraits():
    n = X.speakers()
    assert (n[0], n[7], n[26], n[27], n[41]) == ("Ｄ・Ｓ", "ヴァイ", "ヨーコ", "シーラ", "ウンディーネＣ")


@need_disc
def test_script_files_match_a_fresh_extraction(src):
    names = X.speakers()
    for stem, (label, d, rows) in src.items():
        disk = json.loads((X.SCRIPT / f"{stem}.json").read_text(encoding="utf-8"))
        assert [(e["id"], e["jp"], e["kind"]) for e in disk] == [(e["id"], e["jp"], e["kind"]) for e in X.to_json(label, d, rows, names)], stem


@need_disc
def test_dump_never_clobbers_english(tmp_path, monkeypatch, src):
    monkeypatch.setattr(X, "SCRIPT", tmp_path)
    monkeypatch.setattr(X, "sources", lambda: {"ov2": src["ov2"]})
    X.dump()
    p = tmp_path / "ov2.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    data[0]["en"] = "Items"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    X.dump()
    assert json.loads(p.read_text(encoding="utf-8"))[0]["en"] == "Items"
    X.dump(force=True)
    assert json.loads(p.read_text(encoding="utf-8"))[0]["en"] == "Items"

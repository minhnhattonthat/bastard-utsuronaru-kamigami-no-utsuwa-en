"""The shipped build, made fresh here: every write in its place and every pointer leading to its English (tools/verify_build.py)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
import batches
import build
import verify_build


def test_built_disc_verifies(tmp_path):
    out = build.build(tmp_path / "bastard_en.bin")
    assert verify_build.verify(out) == []


def test_wrap_gives_a_lone_last_word_company():
    e = {"id": "s0000_00000", "jp": "x", "fn": [624], "kind": "text", "en": ""}
    text = "In dimensional terms it appears to be a single, isolated world. Even the subspace I travel in has no access to anywhere but this world. And we have been cast out into it."
    pages = batches.wrap(text, e).split("{page}")
    assert all(" " in p.split("{n}")[-1] for p in pages)


def test_wrap_ends_a_page_on_a_full_sentence_when_it_can():
    e = {"id": "s0000_00000", "jp": "x", "fn": [624], "kind": "text", "en": ""}
    text = "Pretty organic, ain't it. So this walking fort's a kind of living weapon. And since it's got its own spirit reactor, it's packing some super-destructive weapon beyond nuclear power, too."
    assert batches.wrap(text, e).split("{page}")[0].endswith("living weapon.")


def test_battle_log_top_row_is_one_line():
    e = {"id": "ov1_00000", "jp": "[01]%sの魔法攻撃！%M%z%z", "kind": "text", "en": ""}
    assert batches.box(e)[:2] == (216, 1)
    e = {"id": "ov1_00000", "jp": "%sが叫ぶと、{n}床から", "kind": "text", "en": ""}
    assert batches.box(e)[:2] == (216, 2)


def test_target_leader_dots_outlast_the_longest_name():
    # the game prints this string from byte strlen(name) on; past its end it prints whatever lies next (a stray `e`)
    entries = json.loads((ROOT / "script/ov1.json").read_text(encoding="utf-8"))
    assert len(next(e for e in entries if e["id"] == "ov1_479a8")["en"]) >= 22


def test_wrap_ends_a_page_early_rather_than_leave_a_word_or_two():
    e = {"id": "s0000_00000", "jp": "x", "fn": [624], "kind": "text", "en": ""}
    text = "...You are a frightening man. Bingo. Even I do not know who they are, but I can sense beings of tremendous magical power. They are the ones who put us in this situation, and...!"
    pages = batches.wrap(text, e).split("{page}")
    assert len(pages[-1].replace("{n}", " ").split()) > batches.STUB_PAGE


def test_lint_catches_codes_a_before_a_variable_and_word_substrings():
    terms = [(["ダイ"], ["Di"], [], False)]
    e = {"id": "s0000_00000", "jp": "ダイ[02]x", "fn": [624], "kind": "text"}
    probs = batches.problems(e, "So did a %s", terms)
    assert any("control codes" in p for p in probs)
    assert any("a/an" in p for p in probs)
    assert any("glossary" in p for p in probs)

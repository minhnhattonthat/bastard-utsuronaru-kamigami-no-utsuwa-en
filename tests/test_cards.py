"""Picture text: the redraw touches only what it declares, and the fcg rewrite keeps every other byte."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import cards
import fcg

need = pytest.mark.skipif(not (ROOT / "work/rbb/1483.fcg_.bin").exists(), reason="run tools/rbb.py unpack")


def entry(eid):
    return (ROOT / f"work/rbb/{eid:04d}.fcg_.bin").read_bytes()


@need
def test_fcg_rewrite_with_no_edit_is_identity():
    for eid in (5, 11, 1194, 1483):
        assert fcg.with_pixels(entry(eid), {}) == entry(eid)


@need
def test_logo_changes_only_the_subtitle_rows():
    t = list(fcg.textures(entry(1483)))[3]
    t1 = dict(t, mode=1)
    old, new = cards.to_indices(t1), cards.to_indices(dict(t1, pixels=cards.redraw_logo(t)))
    changed = {y for y in range(192) if old[y] != new[y]}
    assert changed and min(changed) >= 118 and max(changed) <= 136
    assert all(old[y][138:156] == new[y][138:156] for y in range(0, 124))  # the sword


@need
def test_publisher_keeps_the_rule_and_the_copyright():
    t = list(fcg.textures(entry(1483)))[4]
    old, new = cards.to_indices(t), cards.to_indices(dict(t, pixels=cards.redraw_publisher(t)))
    rule = cards.rule_row(old, old[0][0])
    assert old[rule:] == new[rule:] and old[:rule] != new[:rule]


@need
def test_every_card_has_a_name_and_keeps_its_rule():
    names = cards.card_names()
    assert len(names) >= 90
    t = list(fcg.textures(entry(11)))[0]
    old, new = cards.to_indices(t), cards.to_indices(dict(t, pixels=cards.redraw_card(t, names[11])))
    rule = cards.rule_row(old, old[0][0])
    assert old[rule] == new[rule] and names[11] == "Forgotten Beach"

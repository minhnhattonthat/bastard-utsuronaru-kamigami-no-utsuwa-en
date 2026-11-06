"""The batch tool: wrap to the measured boxes, and every shipped line passes the lint."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import batches  # noqa: E402

DLG = {"id": "s0_1", "jp": "あ", "fn": [624], "max": 99, "off": 0, "kind": "text"}
NAR = {"id": "s0_2", "jp": "あ", "fn": [560], "max": 99, "off": 0, "kind": "text"}
BAT = {"id": "ov1_1", "jp": "[02]%sの攻撃！%z{page}", "max": 99, "off": 0, "kind": "text"}


def test_wrap_adds_pages_and_clears_the_arrow():
    text = batches.wrap(" ".join(["word"] * 50), DLG)
    assert "{page}" in text
    for page in text.split("{page}"):
        lines = page.split("{n}")
        assert len(lines) <= 4 and all(batches.px(x) <= 228 for x in lines) and batches.px(lines[-1]) <= 216
    assert not batches.problems(DLG, text, [])


def test_forced_break_and_page():
    assert batches.wrap("One // Two | Three", NAR) == "One{n}Two{page}Three"


def test_codes_are_kept_and_checked():
    assert batches.render(BAT, "%s attacks!") == "[02]%s attacks!%z{page}"
    assert any("arguments" in p for p in batches.problems(BAT, "[02]attack!%z{page}", []))
    assert batches.core("[02]%sの{n}攻撃！%z{page}") == "%sの攻撃！"


def test_one_line_box_refuses_pages():
    choice = dict(DLG, fn=[672])
    try:
        batches.wrap("a | b", choice)
        raise AssertionError
    except ValueError:
        pass


def test_shipped_english_passes():
    entries, terms = batches.index(), batches.glossary()
    bad = [(i, p) for i, e in entries.items() if e.get("en") for p in batches.problems(e, e["en"], terms)]
    assert not bad, bad[:20]

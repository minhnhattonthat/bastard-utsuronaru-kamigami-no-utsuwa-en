"""Recon tools: LZSS layout, string scan, and (when the disc has been extracted) the archive itself."""
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import rbb
from strscan import runs


def test_lzss_literals_then_match_from_absolute_window_position():
    # flag 0b00000111: 3 literals, then a match of length 3 at window position 0 (write head starts at 0).
    src = bytes([0x07]) + b"abc" + bytes([0x00, 0x00])
    assert rbb.lzss_decode(src, 6)[0] == b"abcabc"


def test_lzss_match_length_is_high_nibble():
    src = bytes([0x01]) + b"x" + bytes([0x00, 0x20])  # literal, then length (2)+3 at position 0: overlapping copy
    assert rbb.lzss_decode(src, 6)[0] == b"xxxxxx"


def test_lzss_reads_zeros_from_unwritten_window():
    src = bytes([0x01]) + b"x" + bytes([0xEE, 0x0F])  # position 0xFEE is still zero
    assert rbb.lzss_decode(src, 4)[0] == b"x\0\0\0"


def test_strscan_keeps_control_bytes_and_stops_at_end_code():
    d = b"\0\0" + "あいう\nえお\x0bか\x0c".encode("cp932") + b"\0\0"
    assert [(o, s.decode("cp932")) for o, s in runs(d)] == [(2, "あいう\nえお\x0bか\x0c")]


@pytest.mark.skipif(not rbb.RBB.exists(), reason="run tools/disc.py extract first")
def test_every_compressed_entry_decodes_to_its_declared_size():
    data = rbb.RBB.read_bytes()
    ents = rbb.index(data)
    assert len(ents) == 1541
    for off, size in ents[:40]:  # shortcut: first 40 entries, keeps pre-commit fast; `rbb.py unpack` asserts them all
        e = rbb.entry(data, off, size)
        if e[:4] == b"00zL":
            csize, usize = struct.unpack_from("<II", e, 16)
            assert len(rbb.lzss_decode(e[24:24 + csize], usize)[0]) == usize

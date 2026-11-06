"""Identity build: unpack and repack with no edits gives the original disc, and the LZSS encoder round-trips."""
import hashlib
import struct
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
import build
import disc
import rbb


def test_lzss_encode_round_trips_past_the_window():
    runs = [
        b"",
        b"a",
        b"ab",
        bytes(10000),
        b"abc" * 3000,
        bytes(range(256)) * 40,
        hashlib.sha256(b"x").digest() * 300 + bytes(5000),
    ]
    for raw in runs:
        assert rbb.lzss_decode(rbb.lzss_encode(raw), len(raw))[0] == raw


def test_lzss_encode_matches_the_zeroed_window_from_the_first_token():
    assert rbb.lzss_encode(bytes(32))[0] & 1 == 0


def test_ecc_of_zero_sector_is_zero():
    raw = np.zeros((1, disc.SS), np.uint8)
    disc.encode_form1(raw)
    assert not raw.any()


def test_pack_moves_later_entries_and_keeps_ids():
    a, b = b"fcg \1\2\3", b"tail"
    head = bytearray(rbb.BASE)
    head[:4] = b"siff"
    head[0x80:0x84] = b"RIDX"
    struct.pack_into("<I", head, 0x84, 16)
    struct.pack_into("<IIII", head, 0x88, 0, len(a), 0x800, len(b))
    old = bytes(head) + a + bytes(0x800 - len(a)) + b
    assert rbb.index(rbb.pack(old)) == rbb.index(old)
    new = rbb.pack(old, {0: bytes(0x801)})
    assert rbb.index(new) == [(0, 0x801), (0x1000, len(b))]
    assert rbb.entry(new, 0x1000, len(b)) == b
    assert struct.unpack_from("<I", new, rbb.EXIX)[0] == 0x801


needs_rom = pytest.mark.skipif(not disc.BIN.exists(), reason="no original disc")


@needs_rom
def test_real_lzss_blocks_reencode_byte_for_byte():
    with open(disc.BIN, "rb") as f:
        data = disc.read_form1(f, *disc.FILES["RSRCALL.RBB"])
    off, size = rbb.index(data)[184]  # shortcut: one entry keeps pre-commit fast; `rbb.py verify` covers all 5,368 blocks
    e = rbb.entry(data, off, size)
    found = list(rbb.blocks(e))[:8]
    assert found
    for p, csize, usize in found:
        stream = e[p + 24:p + 24 + csize]
        assert rbb.lzss_encode(rbb.lzss_decode(stream, usize)[0]) == stream


@needs_rom
def test_encode_form1_restores_wiped_edc_and_ecc():
    lba = disc.FILES["RSRCALL.RBB"][0]
    with open(disc.BIN, "rb") as f:
        f.seek(lba * disc.SS)
        want = np.frombuffer(f.read(8 * disc.SS), np.uint8).reshape(-1, disc.SS)
    raw = want.copy()
    raw[:, 2072:] = 0
    disc.encode_form1(raw)
    assert (raw == want).all()


@needs_rom
def test_identity_build_equals_original_disc(tmp_path):
    out = build.build(tmp_path / "identity.bin")
    want = (ROOT / "rom.sha1").read_text(encoding="utf-8").splitlines()[1].split()[0]
    with open(out, "rb") as f:
        assert hashlib.file_digest(f, "sha1").hexdigest() == want

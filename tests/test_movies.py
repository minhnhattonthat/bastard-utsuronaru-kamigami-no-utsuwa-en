"""Movie captions: the VLC table against the original frames and ffmpeg, and caption frames that fit."""
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import disc
import mdec
import movie_text

need = pytest.mark.skipif(not disc.BIN.exists(), reason="no original disc")


def movie(n):
    lba, count = movie_text.MOVIES[n]
    with open(disc.BIN, "rb") as f:
        f.seek(lba * disc.SS)
        return bytearray(f.read(count * disc.SS))


def test_table_is_prefix_free_and_complete():
    assert len(mdec.AC) == 111
    codes = sorted([*mdec.AC.values(), mdec.EOB, mdec.ESC])
    assert not any(b.startswith(a) for a, b in zip(codes, codes[1:]))


@need
def test_original_frames_reencode_byte_identical():
    raw = movie(162)
    fr = mdec.frames(raw)
    for n in (1, 3, 130, 500, 700, 840):
        f = fr[n]
        d = bytes(f["data"][:f["size"]])
        q, blocks, _ = mdec.parse(d, f["w"], f["h"])
        assert mdec.encode(q, blocks) == d


@need
def test_video_sectors_have_real_edc_and_ecc():
    raw = np.frombuffer(bytes(movie(162)[:20 * disc.SS]), np.uint8).reshape(-1, disc.SS)
    video = raw[raw[:, 18] == 0x42].copy()
    want = video.copy()
    disc.encode_form1(video)
    assert (video == want).all()


@need
@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="no ffmpeg")
def test_every_code_and_escape_decodes_the_same_in_ffmpeg(tmp_path):
    """A frame holding every (run, level), both signs, plus escapes: ffmpeg must read it as our decode does."""
    raw = movie(162)
    f = mdec.frames(raw)[840]
    w, h, q = f["w"], f["h"], 2
    pairs = [(r, s * l) for (r, l) in mdec.AC for s in (1, -1)] + [(0, 41), (0, -41), (2, 6), (5, -300), (0, 500), (40, 3)]
    blocks = []
    for n in range(((w + 15) // 16) * ((h + 15) // 16) * 6):
        run, level = pairs[n % len(pairs)]
        blocks.append((n % 40 - 20, [(run, level)] if run < 63 else []))
    frame = mdec.encode(q, blocks)
    assert mdec.parse(frame, w, h)[1] == blocks
    movie_text._write_frame(raw, f, frame)
    one = tmp_path / "one.str"
    one.write_bytes(b"".join(bytes(raw[i * disc.SS:(i + 1) * disc.SS]) for i in f["sectors"]))
    # ffmpeg logs `ac-tex damaged` on this one-frame file even for an untouched original frame, so its log proves nothing: compare samples.
    out = subprocess.run(["ffmpeg", "-loglevel", "quiet", "-threads", "1", "-f", "psxstr", "-i", str(one), "-an", "-f", "rawvideo", "-pix_fmt", "yuv420p", "-"], capture_output=True)
    assert len(out.stdout) >= w * h * 3 // 2
    y_ff = np.frombuffer(out.stdout, np.uint8, w * h).reshape(h, w).astype(float)
    y = np.clip(mdec.decode(q, blocks, w, h)[0], 0, 255)
    assert np.abs(y - y_ff).mean() < 2


@need
def test_captions_fit_and_touch_only_their_macroblocks():
    raw = movie(157)
    fr = mdec.frames(raw)
    caps = [c for c in movie_text.captions() if c["movie"] == 157]
    c = caps[0]
    f = fr[(c["first"] + c["last"]) // 2]
    d = bytes(f["data"][:f["size"]])
    q, blocks, _ = mdec.parse(d, f["w"], f["h"])
    planes = mdec.decode(q, blocks, f["w"], f["h"])
    new, touched = movie_text.compose(planes, [c], 40, f["w"], f["h"])
    mh, mw = touched.shape[0] // 16, touched.shape[1] // 16
    changed = touched.reshape(mh, 16, mw, 16).any(axis=(1, 3))
    frame, q2 = mdec.recode(d, f["w"], f["h"], changed, new, len(f["sectors"]) * mdec.PAYLOAD, 1 << 16)
    _, out, _ = mdec.parse(frame, f["w"], f["h"])
    assert q2 == q
    for mx in range(mw):
        for my in range(mh):
            if not changed[my, mx]:
                at = (mx * mh + my) * 6
                assert out[at:at + 6] == blocks[at:at + 6]


def test_tsv_lines_fit_the_frame():
    for c in movie_text.captions():
        movie_text.text_mask(c, 304, 192)  # exits on an overflowing line
        assert c["first"] <= c["last"]

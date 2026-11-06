"""verify_build.py: check a built disc against the original and script/, from the built bytes alone.

    python -X utf8 tools/verify_build.py [build/bastard_en.bin]     exit 1 and a list on any failure

1. Sectors outside the EXE, RSRCALL.RBB and DUMMY are unchanged.
2. Inside them (romdiff.py, file by file), bytes changed only in: string slots, their pointers, script size words, the
   hook's free block and its fixed sites. An RBB entry no script file names is byte-identical.
3. Every pointer of every translated string leads to that string's English. The same pointer in the original led to the
   Japanese, so a wrong slot in the extractor fails too.
4. Nothing still points at a string's old slot (pointer word or lui pair) once it has moved.
5. No branch lands inside a hook's overwritten span.
"""
import json
import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import cards  # noqa: E402
import disc  # noqa: E402
import engine  # noqa: E402
import extract  # noqa: E402
import insert  # noqa: E402
import mdec  # noqa: E402
import movie_text  # noqa: E402
import rbb  # noqa: E402
import romdiff  # noqa: E402

EXE_BASE, OV_BASE = extract.EXE_BASE, extract.OV_BASE
EDITED = ("SLPS_005.42", "RSRCALL.RBB", "DUMMY")
SPILL_AT = (disc.FILES["DUMMY"][0] - disc.FILES["RSRCALL.RBB"][0]) * 2048
SIZE_WORDS = (0x04, 0x0C, 0x14)  # ssg, scr, prg sizes
FONT_LOOKALIKES = {0x2884, 0x179C0}  # kanji bitmaps in the EXE whose bytes happen to read as an address (dumped and read)
# The hook's fixed sites in the EXE, as file offsets.
SITES = [engine.FONT_TABLE + 4 * f - EXE_BASE for f in engine.ORIG] + [engine.METRIC_TABLE + 4 * f - EXE_BASE for f in engine.METRIC]
SITES += [engine.POOL_SIZE_ARG - EXE_BASE, engine.CHAR_COUNT - EXE_BASE, engine.CHAR_COUNT + 4 - EXE_BASE]
SITES += [engine.LIST_PAD - EXE_BASE, engine.LIST_WIDEN - EXE_BASE]


def sectors(orig_path, new_path):
    """Sectors that differ outside the files the build may write."""
    a = np.memmap(orig_path, np.uint8, "r").reshape(-1, disc.SS)
    b = np.memmap(new_path, np.uint8, "r")
    if b.size != a.size:
        return [f"disc size {b.size}, original {a.size}"]
    b = b.reshape(-1, disc.SS)
    keep = np.ones(len(a), bool)
    for name in EDITED:
        lba, size = disc.FILES[name]
        keep[lba:lba + (size + 2047) // 2048] = False
    keep[movie_text.caption_lbas(orig_path)] = False
    bad = np.flatnonzero(keep & (a != b).any(axis=1))
    return [f"sector {s} changed, outside the EDITED files and the movie caption frames" for s in bad[:20]]


def check_movies(orig_path, new_path):
    """A redrawn frame parses to its full block count, fills only its own sectors, keeps its STR header but for size, and stays in the decoder's buffer."""
    errs = []
    with open(orig_path, "rb") as fa, open(new_path, "rb") as fb:
        for movie, (lba, count) in movie_text.MOVIES.items():
            fa.seek(lba * disc.SS)
            fb.seek(lba * disc.SS)
            old, new = mdec.frames(fa.read(count * disc.SS)), mdec.frames(fb.read(count * disc.SS))
            max_words = max(struct.unpack_from("<H", f["data"])[0] for f in old.values())
            for n, f in new.items():
                o = old[n]
                if f["sectors"] != o["sectors"] or (f["w"], f["h"]) != (o["w"], o["h"]):
                    errs.append(f"movie {movie} frame {n}: sectors or size changed")
                    continue
                if f["data"] == o["data"]:
                    continue
                d = bytes(f["data"][:f["size"]])
                q, blocks, _ = mdec.parse(d, f["w"], f["h"])
                if mdec.encode(q, blocks) != d or f["data"][f["size"]:].strip(b"\0"):
                    errs.append(f"movie {movie} frame {n}: not a clean frame")
                if struct.unpack_from("<H", d)[0] > max_words:
                    errs.append(f"movie {movie} frame {n}: {struct.unpack_from('<H', d)[0]} words, the movie's largest is {max_words}")
    return errs


def read_all(path):
    with open(path, "rb") as f:
        exe = disc.read_form1(f, *disc.FILES["SLPS_005.42"])
        arc = disc.read_form1(f, *disc.FILES["RSRCALL.RBB"])
        spill = disc.read_form1(f, *disc.FILES["DUMMY"])
    return exe, arc, spill


def entries(arc, spill):
    """{id: an entry's bytes}; an offset past the archive reads from DUMMY."""
    out = {}
    for n, (off, size) in enumerate(rbb.index(arc)):
        at = rbb.BASE + off
        out[n] = spill[at - SPILL_AT:at - SPILL_AT + size] if at >= SPILL_AT else arc[at:at + size]
    return out


def word(d, off):
    return struct.unpack_from("<I", d, off)[0]


def resolve(f, ref):
    """The address a `src:d:off` or `src:c:lui/low` reference gives in file bytes f."""
    _src, kind, where = insert._ref_parts(ref)
    if kind == "d":
        return word(f, int(where, 16))
    a, b = (int(x, 16) for x in where.split("/"))
    low = word(f, b)
    lo = low & 0xFFFF
    if low >> 26 != 13 and lo >= 0x8000:
        lo -= 0x10000
    return ((word(f, a) & 0xFFFF) << 16) + lo & 0xFFFFFFFF


def ref_words(ref):
    """File offsets of the words a reference occupies."""
    _src, kind, where = insert._ref_parts(ref)
    return [int(where, 16)] if kind == "d" else [int(x, 16) for x in where.split("/")]


def span(lo, hi):
    return range(lo, hi)


def word_span(off):
    return range(off, off + 4)


def check_ssg(stem, rows, old, new, errs):
    """Pointers lead to the English; only slots, pointers and sizes differ; the tail is the only growth."""
    end = 0x18 + (word(old, 0x14) & 0x7FFFFFFF)
    grow = len(new) - len(old)
    if grow < 0 or new[end + grow:] != old[end:]:
        errs.append(f"{stem}: data after prg moved or changed")
        return
    allowed = set()
    for at in SIZE_WORDS:
        allowed.update(word_span(at))
    for e in rows:
        if e["kind"] not in insert.SPEECH_KINDS or not e.get("en"):
            continue
        allowed.update(span(e["off"], insert._slot_end(e["off"], len(extract.encode(e["jp"])) + 1)))
        want = insert.blob(e["en"], e["term"])
        for ref in e["refs"]:
            allowed.update(word_span(ref))
            if (word(old, ref) & 0xFFFF) + insert.GP_OFF != e["off"]:
                errs.append(f"{e['id']}: original slot {ref:#x} does not lead to the string")
            at = (word(new, ref) & 0xFFFF) + insert.GP_OFF
            if new[at:at + len(want)] != want:
                errs.append(f"{e['id']}: pointer {ref:#x} leads to {new[at:at + len(want)]!r}")
    # A moved string reuses a freed slot or the tail, so the slots are only checked against old bytes, not for what's there now.
    bad, _ = romdiff.check(old[:end], new[:end], allowed, [])
    errs += [f"{stem}: {x}" for x in bad]


def check_tbl(stem, rows, old, new, errs):
    allowed = set()
    for e in rows:
        if e["kind"] not in insert.SPEECH_KINDS or not e.get("en"):
            continue
        room = insert._field_room(old, e)
        allowed.update(span(e["off"], e["off"] + room))
        want = extract.encode(e["en"]) + b"\0"
        if new[e["off"]:e["off"] + len(want)] != want:
            errs.append(f"{e['id']}: field holds {new[e['off']:e['off'] + len(want)]!r}")
    bad, _ = romdiff.check(old, new, allowed, [])
    errs += [f"{stem}: {x}" for x in bad]


def target(files, stem, addr):
    """(file name, offset) of an address read from `stem`: its own overlay window, else the EXE."""
    if stem != "exe" and OV_BASE <= addr < OV_BASE + len(files[stem]):
        return stem, addr - OV_BASE
    if EXE_BASE <= addr < EXE_BASE + len(files["exe"]):
        return "exe", addr - EXE_BASE
    return None, None


def check_abs(docs, old, new, errs):
    """EXE and overlays. Returns {file: moved strings' old (lo, hi, row)}."""
    allowed = {k: set() for k in old}
    blob_lo = engine.LEVEL2[0] - EXE_BASE
    allowed["exe"].update(span(blob_lo, engine.LEVEL2[1] - EXE_BASE))
    for at in SITES:
        allowed["exe"].update(word_span(at))
    moved = {k: [] for k in old}
    for stem, rows in docs.items():
        base = EXE_BASE if stem == "exe" else OV_BASE
        for e in rows:
            if e["kind"] not in insert.SPEECH_KINDS or not e.get("en"):
                continue
            size = len(extract.encode(e["jp"]))
            hi = insert._slot_end(e["off"], size + 1)
            fixed = stem == "ov4" or insert._inline(old, e["refs"])
            room = e["max"] if stem == "ov4" else hi - e["off"]
            allowed[stem].update(span(e["off"], e["off"] + room))
            want = insert.blob(e["en"], e["term"])
            if fixed:
                if new[stem][e["off"]:e["off"] + len(want)] != want:
                    errs.append(f"{e['id']}: fixed slot holds {new[stem][e['off']:e['off'] + 40]!r}")
                continue
            for ref in e["refs"]:
                src = insert._ref_parts(ref)[0]
                for w in ref_words(ref):
                    allowed[src].update(word_span(w))
                if resolve(old[src], ref) != base + e["off"]:
                    errs.append(f"{e['id']}: original {ref} does not lead to the string")
                name, at = target(new, src, resolve(new[src], ref))
                if name is None or bytes(new[name][at:at + len(want)]) != want:
                    errs.append(f"{e['id']}: {ref} leads to {'nowhere' if name is None else new[name][at:at + len(want)]!r}")
            moved[stem].append((base + e["off"], base + e["off"] + size + 1, e))
    # Strings moved out of an overlay land in the EXE's free block, which is already allowed.
    for k in old:
        bad, _ = romdiff.check(bytes(old[k]), bytes(new[k]), allowed[k], [])
        errs += [f"{k}: {x}" for x in bad]
    return moved


def check_stale(moved, old, new, errs):
    """Any reference in the original to inside a string's old slot must be one the build rewrote (or a suffix it knows)."""
    for stem, rows in moved.items():
        if not rows:
            continue
        rows.sort(key=lambda r: r[0])
        starts = np.array([r[0] for r in rows], np.int64)
        ends = np.array([r[1] for r in rows], np.int64)
        for src in ("exe", stem):
            d = bytes(old[src])
            n = len(d) // 4
            words = np.frombuffer(d, "<u4", n).astype(np.int64)
            hit = np.searchsorted(starts, words, side="right") - 1
            inside = (hit >= 0) & (words < ends[np.clip(hit, 0, None)])
            lui = extract.lui_refs(d, 0)
            sites = [(int(k) * 4, int(words[k]), int(hit[k])) for k in np.flatnonzero(inside)]
            for addr, pairs in lui.items():
                i = int(np.searchsorted(starts, addr, side="right")) - 1
                if i >= 0 and addr < ends[i]:
                    sites += [(p[0], addr, i) for p in pairs]
            for off, addr, i in sites:
                if src == "exe" and off in FONT_LOOKALIKES:
                    continue
                e = rows[i][2]
                if addr == rows[i][0] and off in {w for ref in e["refs"] if insert._ref_parts(ref)[0] == src for w in ref_words(ref)}:
                    continue
                if any(off in [w for r in s["refs"] if insert._ref_parts(r)[0] == src for w in ref_words(r)] for s in e.get("suffix", [])):
                    if word(new[src], off) == word(old[src], off) and not _kept_in_place(e, new, stem):
                        errs.append(f"{e['id']}: suffix pointer at {src}:{off:#x} was left behind")
                    continue
                if word(new[src], off) == word(old[src], off) and not _kept_in_place(e, new, stem):
                    errs.append(f"{e['id']}: {src}:{off:#x} still points at the old slot ({addr:#x})")


def _kept_in_place(e, new, stem):
    """The string still sits at its own slot, so an old pointer to it is still right."""
    want = insert.blob(e["en"], e["term"])
    return bytes(new[stem][e["off"]:e["off"] + len(want)]) == want


def check_hook_spans(exe, errs):
    """A branch or jump into the middle of an overwritten span would run half a hook. Only the two-word CHAR_COUNT site has a middle."""
    inside = engine.CHAR_COUNT + 4
    n = len(exe) // 4
    ws = np.frombuffer(exe, "<u4", n)
    for i in np.flatnonzero(np.isin(ws >> 26, [1, 2, 3, 4, 5, 6, 7, 20, 21, 22, 23])):
        w, pc = int(ws[i]), EXE_BASE + int(i) * 4
        op = w >> 26
        if op in (2, 3):
            to = (pc & 0xF0000000) | (w & 0x3FFFFFF) << 2
        else:
            imm = w & 0xFFFF
            to = pc + 4 + ((imm - 0x10000 if imm >= 0x8000 else imm) << 2)
        if to == inside:
            errs.append(f"branch at {pc:#x} lands inside the CHAR_COUNT hook")


def verify(new_path):
    errs = sectors(disc.BIN, new_path)
    errs += check_movies(disc.BIN, new_path)
    exe0, arc0, _ = read_all(disc.BIN)
    exe1, arc1, spill = read_all(new_path)
    old_e, new_e = entries(arc0, b""), entries(arc1, spill)
    docs, ssg, tbl = {}, {}, {}
    for p in sorted((ROOT / "script").glob("*.json")):
        rows = json.loads(p.read_text(encoding="utf-8"))
        if p.stem.startswith("ssg_"):
            ssg[int(p.stem[4:])] = (p.stem, rows)
        elif p.stem.startswith("tbl_"):
            tbl[int(p.stem[4:])] = (p.stem, rows)
        else:
            docs[p.stem] = rows
    old = {"exe": bytearray(exe0)}
    new = {"exe": bytearray(exe1)}
    for o in (0, 1, 2, 4):
        old[f"ov{o}"] = bytearray(rbb.unwrap(old_e[o]))
        new[f"ov{o}"] = bytearray(rbb.unwrap(new_e[o]))
    pictures = cards.build(lambda eid: rbb.unwrap(old_e[eid]))
    for eid in old_e:
        if eid in pictures:
            if rbb.unwrap(new_e[eid]) != pictures[eid]:
                errs.append(f"entry {eid}: not the redrawn picture")
        elif eid in ssg:
            check_ssg(ssg[eid][0], ssg[eid][1], rbb.unwrap(old_e[eid]), rbb.unwrap(new_e[eid]), errs)
        elif eid in tbl:
            check_tbl(tbl[eid][0], tbl[eid][1], bytearray(rbb.unwrap(old_e[eid])), rbb.unwrap(new_e[eid]), errs)
        elif eid not in (0, 1, 2, 4) and old_e[eid] != new_e[eid]:
            errs.append(f"entry {eid} changed: no script file names it")
    moved = check_abs(docs, old, new, errs)
    check_stale(moved, old, new, errs)
    check_hook_spans(exe0, errs)
    return errs


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build/bastard_en.bin"
    found = verify(path)
    print(f"{path.name}: {len(found)} problems")
    print("\n".join(found[:60]))
    sys.exit(1 if found else 0)

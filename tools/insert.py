"""insert.py: script/*.json -> new bytes for the EXE and RBB entries (docs/re/text.md, Insertion).

    apply(exe, entry_raw, text_of) -> (new exe, {entry id: new raw bytes}, report)
text_of(row, stem, limit) gives the string to write (in the same token form as `jp`), or None to keep the original.

Where strings go: its own slot if it fits, else any freed slot in the same file, else (scripts) the end of `prg`, else
(EXE and overlays) the free block in the EXE from engine.py. Fixed slots stay put and `limit` says how long they can be:
tables and the ending blurbs, and inline copies (a low half on a load: the compiler's char buf[] = "..." copies a fixed
number of bytes, so the string cannot move).
"""
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "debug"))
import engine
import extract

SCRIPT = ROOT / "script"
EXE_BASE, OV_BASE = extract.EXE_BASE, extract.OV_BASE
GP_OFF = 0x818  # file offset of $gp in every ssg: payload 0x18 + 0x800
SPEECH_KINDS = ("text", "label")
# Strings expanded into stack buffers (tools/debug/fmt_sites.py): an overrun smashes the return address and the game hangs.
# id -> bytes of literal text, tokens not counted, after room for the longest argument. Buffer sizes: docs/re/windows.md.
MAP_NAME_ROOM = engine.LIST_COLUMN  # the save list's column (engine.patch_exe); the go-to messages would take 30
ITEM_ROOM = 17
FORMAT_ROOM = {
    "exe_00920": 56 - 1 - ITEM_ROOM - 2,  # item name and a count up to 99
    "exe_00938": 56 - 1 - ITEM_ROOM,
    "exe_00894": 48 - 1 - MAP_NAME_ROOM,
    "exe_008dc": 48 - 1 - MAP_NAME_ROOM,
    "exe_008a8": 47,
    "exe_008c4": 47,
    "exe_012d0": 32 - 1 - 20,  # a character's name: up to 20 bytes
}
MAP_TABLE = (0x8C7A4, 0x8C7A4 + 79 * 64)


def _rows():
    for p in sorted(SCRIPT.glob("*.json")):
        yield p.stem, json.loads(p.read_text(encoding="utf-8"))


def blob(text, term):
    """A string as stored. Script text ends 0C 00: the 0C is the wait-for-key code and the NUL ends the C string, so without it
    the printer runs on into whatever string was placed next, past the wait."""
    return extract.encode(text) + (bytes.fromhex(term) if term else b"") + (b"\0" if term == "0C" else b"")


def _slot_end(off, length):
    """End of a string's own space: its bytes, terminator and the pad to the next word. Zeros past that may be code."""
    return (off + length + 3) & ~3


class Pool:
    """First-fit allocator over byte ranges."""

    def __init__(self, ranges=()):
        self.free = sorted(ranges)

    def add(self, lo, hi):
        if hi > lo:
            self.free.append((lo, hi))

    def take(self, n):
        for i, (lo, hi) in enumerate(self.free):
            if hi - lo >= n:
                self.free[i] = (lo + n, hi)
                return lo
        return None

    def left(self):
        return sum(hi - lo for lo, hi in self.free)


def rebuild_ssg(d, rows, stem, text_of):
    """New bytes of one script. Strings are reached by `ori rX,$zero,off` with off = string - $gp."""
    out = bytearray(d)
    size = struct.unpack_from("<I", d, 0x14)[0] & 0x7FFFFFFF
    end = 0x18 + size
    pool, todo = Pool(), []
    for e in rows:
        if e["kind"] not in SPEECH_KINDS:
            continue
        t = text_of(e, stem, None)
        if t is None:
            continue
        old = len(extract.encode(e["jp"])) + 1
        new = blob(t, e["term"])
        lo, hi = e["off"], _slot_end(e["off"], old)
        out[lo:hi] = bytes(hi - lo)
        pool.add(lo, hi)
        todo.append((e, new))
    tail = bytearray()
    for e, new in sorted(todo, key=lambda x: -len(x[1])):
        at = pool.take(len(new))
        if at is None:
            at = end + len(tail)
            tail += new
        else:
            out[at:at + len(new)] = new
        imm = at - GP_OFF
        if not 0 <= imm < 0x10000:
            raise ValueError(f"{e['id']}: offset {imm:#x} from $gp does not fit 16 bits")
        for ref in e["refs"]:
            w = struct.unpack_from("<I", out, ref)[0]
            struct.pack_into("<I", out, ref, (w & 0xFFFF0000) | imm)
    if not tail:
        return bytes(out)
    tail += bytes(-len(tail) & 3)
    for at in (0x04, 0x0C, 0x14):
        struct.pack_into("<I", out, at, struct.unpack_from("<I", out, at)[0] + len(tail))
    return bytes(out[:end]) + bytes(tail) + bytes(out[end:])


def _is_load(word):
    return 0x20 <= word >> 26 <= 0x26


def _ref_parts(ref):
    src, kind, *where = ref.split(":", 2)
    return src, kind, where[0] if where else ""


def _inline(files, refs):
    """True if a code reference reads the string with a load: a fixed-size inline copy."""
    for ref in refs:
        src, kind, where = _ref_parts(ref)
        if kind == "c":
            low = int(where.split("/")[1], 16)
            if _is_load(struct.unpack_from("<I", files[src], low)[0]):
                return True
    return False


def _write_ref(files, lui_uses, ref, addr):
    src, kind, where = _ref_parts(ref)
    f = files[src]
    if kind == "d":
        struct.pack_into("<I", f, int(where, 16), addr)
        return
    if kind != "c":
        raise ValueError(f"cannot move a string with reference {ref}")
    a, b = (int(x, 16) for x in where.split("/"))
    low = struct.unpack_from("<I", f, b)[0]
    unsigned = low >> 26 == 13
    hi = addr >> 16 if unsigned else (addr + 0x8000) >> 16
    old_hi = struct.unpack_from("<I", f, a)[0]
    if old_hi & 0xFFFF != hi and lui_uses[src].get(a, 1) > 1:
        raise ValueError(f"{ref}: lui is shared and the new address needs another high half")
    struct.pack_into("<I", f, a, (old_hi & 0xFFFF0000) | hi)
    struct.pack_into("<I", f, b, (low & 0xFFFF0000) | (addr & 0xFFFF))


def _lui_uses(d):
    uses = {}
    for sites in extract.lui_refs(d, 0).values():
        for a, _b in sites:
            uses[a] = uses.get(a, 0) + 1
    return uses


def apply(exe, entries, text_of, qa=False):
    """exe: original EXE bytes. entries(id) -> original raw bytes of an RBB entry. -> (exe, {id: raw}, report dict).
    qa: the hook also logs every glyph for tools/debug/drawlog.lua."""
    files = {"exe": bytearray(exe)}
    for o in (0, 1, 2, 4):
        files[f"ov{o}"] = bytearray(entries(o))
    free = engine.patch_exe(files["exe"], qa=qa)
    exe_pool = Pool([(free, engine.LEVEL2[1])])
    out, report = {}, {"moved_to_exe": 0, "inline": []}
    uses = {k: _lui_uses(v) for k, v in files.items()}
    base = {"exe": EXE_BASE, **{f"ov{o}": OV_BASE for o in (0, 1, 2, 4)}}

    for stem, rows in _rows():
        if stem.startswith("ssg_"):
            eid = int(stem[4:])
            d = entries(eid)
            new = rebuild_ssg(d, rows, stem, text_of)
            if new != d:
                out[eid] = new
        elif stem.startswith("tbl_"):
            eid = int(stem[4:])
            d = bytearray(entries(eid))
            for e in rows:
                if e["kind"] not in SPEECH_KINDS:
                    continue
                t = text_of(e, stem, _field_room(d, e))
                if t is not None:
                    _write_fixed(d, e, t)
            if bytes(d) != entries(eid):
                out[eid] = bytes(d)
        else:
            _rebuild_abs(stem, rows, files, base, uses, exe_pool, text_of, report)

    for o in (0, 1, 2, 4):
        if bytes(files[f"ov{o}"]) != entries(o):
            out[o] = bytes(files[f"ov{o}"])
    report["exe_free_left"] = exe_pool.left()
    return bytes(files["exe"]), out, report


def _field_room(d, e):
    """Bytes a fixed field can take: up to the first nonzero byte past the string's terminator, within the field. A field
    can hide flags after its string (a zero-filled field once wiped flags and gave a black boot)."""
    old = len(extract.encode(e["jp"]))
    lim = e["max"]
    j = e["off"] + old + 1
    while j < e["off"] + lim and d[j] == 0:
        j += 1
    return min(j - e["off"], lim)  # a string that fills its field stops there: the next byte is the next field's


def _write_fixed(d, e, t):
    room = _field_room(d, e)
    new = extract.encode(t) + b"\0"  # always, even where the Japanese filled the field: the printer stops at nothing else
    if len(new) > room:
        raise ValueError(f"{e['id']}: {len(new)} bytes, field holds {room}")
    d[e["off"]:e["off"] + room] = new.ljust(room, b"\0")


def buffer_cap(e):
    """Bytes (terminator and tokens included) a movable string may take because a stack buffer holds it, or None."""
    if e["id"] in FORMAT_ROOM:
        tokens = "".join(_TOKEN.findall(e["jp"]))
        return FORMAT_ROOM[e["id"]] + len(extract.encode(tokens)) + 1
    for ref in e["refs"]:
        src, kind, where = _ref_parts(ref)
        if src == "exe" and kind == "d" and MAP_TABLE[0] <= int(where, 16) < MAP_TABLE[1] and (int(where, 16) - MAP_TABLE[0]) % 64 == 0:
            return MAP_NAME_ROOM + 1
    return None


def _rebuild_abs(stem, rows, files, base, uses, exe_pool, text_of, report):
    """EXE or overlay: strings reached by pointers and lui pairs."""
    f = files[stem]
    pool, todo = Pool(), []
    for e in rows:
        if e["kind"] not in SPEECH_KINDS:
            continue
        old = len(extract.encode(e["jp"]))
        fixed = stem == "ov4"  # 200-byte slots reached by base + index
        inline = _inline(files, e["refs"])
        if fixed or inline:
            room = e["max"] if fixed else _slot_end(0, old + 1)
            t = text_of(e, stem, room)
            if t is None:
                continue
            new = blob(t, e["term"])
            if len(new) > room:
                raise ValueError(f"{e['id']}: {len(new)} bytes in a fixed slot of {room}")
            f[e["off"]:e["off"] + room] = new.ljust(room, b"\0")
            if inline:
                report["inline"].append(e["id"])
            continue
        cap = buffer_cap(e)
        t = text_of(e, stem, cap)
        if t is None:
            continue
        lo, hi = e["off"], _slot_end(e["off"], old + 1)
        f[lo:hi] = bytes(hi - lo)
        pool.add(lo, hi)
        new = blob(t, e["term"])
        if cap is not None and len(new) > cap:
            raise ValueError(f"{e['id']}: {len(new)} bytes, its stack buffer leaves {cap}")
        todo.append((e, new))
    for e, new in sorted(todo, key=lambda x: -len(x[1])):
        at = pool.take(len(new))
        if at is not None:
            f[at:at + len(new)] = new
            addr = base[stem] + at
        else:
            addr = exe_pool.take(len(new))
            if addr is None:
                raise ValueError(f"{e['id']}: no room left in the EXE block")
            off = addr - EXE_BASE
            files["exe"][off:off + len(new)] = new
            report["moved_to_exe"] += 1
        for ref in e["refs"]:
            _write_ref(files, uses, ref, addr)
    report.setdefault("own_free_left", {})[stem] = pool.left()


# --- marker text ---
_TOKEN = re.compile(r"(%[-0-9.]*[a-zA-Z]|\[[0-9A-F]{2}\]|\{c\})")
_FILL = "The quick brown fox jumps over the lazy dog. Pack my box with five dozen liquor jugs. "
_KEEP = ("▲", "▼", "△", "▽")  # cursor and page marks drawn as strings, not words


def _fit(text, px):
    out, w = "", 0
    for ch in text:
        w += engine.FONT[ord(ch)][0]
        if w > px:
            break
        out += ch
    return out


def marker(e, limit=None):
    """`[id] pangram`, line for line with the Japanese: each line as wide as the Japanese line was (12 px a character), so
    it fills whatever box the original filled. Keeps format codes and control bytes in order, or the arguments desync."""
    if e["jp"] in _KEEP:
        return e["jp"]
    tag = "[5B]" + e["id"] + "] "
    short = "[5B]" + e["id"][-5:] + "]"
    out, filler, first = [], _FILL, True
    # Text between tokens is replaced where it stands: the battle's %z fires when it is reached, so moving it breaks the fight.
    for part in re.split(r"(\{page\}|\{n\}|\{c\}|%[-0-9.]*[a-zA-Z]|\[[0-9A-F]{2}\])", e["jp"]):
        if part == "" or re.fullmatch(r"\{page\}|\{n\}|\{c\}|%[-0-9.]*[a-zA-Z]|\[[0-9A-F]{2}\]", part):
            out.append(part)
            continue
        px = len(part) * 12
        head = ""
        if first:
            # A label wider than its window's cells takes the window down (camp menu: fine at 36 px, gone at 51), so keep to the short
            # id there. Scripts keep the full id: their boxes are wide, and the tail alone is not unique across scripts.
            head = tag if e["id"].startswith("s") or engine.width(tag.replace("[5B]", "[")) < px else short
            px -= engine.width(head.replace("[5B]", "["))
            first = False
        fill = _fit(filler, max(px, 0)).rstrip()
        filler = filler[len(fill):].lstrip() or _FILL
        out.append(head + fill)
    if first:  # no text at all, only codes
        out.append(short)
    text = "".join(out)
    if limit is not None:
        cap = limit - 1
        if len(extract.encode(text)) > cap:
            keep = "".join(_TOKEN.findall(e["jp"]))
            text = keep + short
            while len(extract.encode(text)) > cap and text.endswith("]"):
                text = text[:-1]  # a tiny field keeps what it can of the id
            if len(extract.encode(text)) > cap:
                text = text[: cap]
    return text

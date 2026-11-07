"""release.py: build, check and package the patch. Stops at the first failure, so a release can't skip a gate.

    python -X utf8 tools/release.py VERSION [--force] [--dump-only DIR]

Order: build, tests, smoke, verify_build, jp_left, QA gates (every work/qa/**/manifest.tsv), textcover, polish list,
README placeholders, debug off, xdelta patch, re-apply to the clean original and compare, zip.
--dump-only DIR writes the EXE and every text-bearing RBB entry of the built disc for jp_left, and stops.
Output: release/Bastard_EN_vVERSION.zip (patch + PATCHING.txt). The playable image stays in build/. Publishing is the owner's.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import zipfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import disc  # noqa: E402
import rbb  # noqa: E402
from skill import SKILL  # noqa: E402

SCRIPTS = Path(SKILL) / "scripts"
BUILT = ROOT / "build/bastard_en.bin"
PY = [sys.executable, "-X", "utf8"]
PLACEHOLDER = re.compile(r"<[A-Za-z][A-Za-z /,_-]*>")
ZIP_README = """Bastard!! Utsuronaru Kamigami no Utsuwa - English translation patch v{version}
Unofficial fan translation. No game data is included: bring your own dump.

Base disc: {base_name}
  size {size} bytes, CRC32 {crc}, MD5 {md5}, SHA-1 {sha1}
Patched .bin: CRC32 {new_crc}, SHA-1 {new_sha1}

How to patch
1. Check your .bin against the hashes above. Other dumps or revisions will not work.
2. xdelta3 -d -B {size} -s "your.bin" {patch} "bastard_en.bin"
   (or xdelta UI / Delta Patcher: original file = your .bin, patch = {patch})
3. Copy your original .cue next to bastard_en.bin and edit its FILE line to read: FILE "bastard_en.bin" BINARY
4. Boot the .cue. Start a new game or load a save; savestates made on the Japanese disc hold old text and code.

Tested in PCSX-Redux with a real BIOS. The game's text uses the BIOS kanji font, so HLE BIOS will not do.
Known issues: https://github.com/minhnhattonthat/bastard-utsuronaru-kamigami-no-utsuwa-en/issues
Made with extensive AI assistance (Claude by Anthropic). Corrections welcome. Please do not share patched images.
"""


def step(name, cmd=None):
    print(f"== {name}", flush=True)
    if cmd and subprocess.call(cmd, cwd=ROOT) != 0:
        sys.exit(f"release stopped: {name} failed")


def digests(path):
    crc, md5, sha = 0, hashlib.md5(), hashlib.sha1()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            crc = zlib.crc32(block, crc)
            md5.update(block)
            sha.update(block)
    return f"{crc:08x}", md5.hexdigest(), sha.hexdigest()


def dump_text(out):
    """jp_left works on files: strings sit unpacked in the EXE and in the unwrapped RBB entries that script/ names."""
    out.mkdir(parents=True, exist_ok=True)
    with open(BUILT, "rb") as f:
        (out / "exe.bin").write_bytes(disc.read_form1(f, *disc.FILES["SLPS_005.42"]))
        arc = disc.read_form1(f, *disc.FILES["RSRCALL.RBB"])
    table = rbb.index(arc)
    for path in (ROOT / "script").glob("*.json"):
        m = re.fullmatch(r"(?:ssg|tbl)_(\d+)|ov(\d)", path.stem)
        if m:
            eid = int(m.group(1) or m.group(2))
            (out / f"{path.stem}.bin").write_bytes(rbb.unwrap(rbb.entry(arc, *table[eid])))
    return sorted(out.glob("*.bin"))


def unintended(path, keep):
    """jp_left's runs in one dumped file, less those inside a slot meant to stay Japanese (debug, memory card header, keep_jp.txt)."""
    entries = json.loads((ROOT / "script" / f"{path.stem}.json").read_text(encoding="utf-8"))
    slots = [(e["off"], e["off"] + e["max"]) for e in entries if e.get("kind") in ("debug", "card") or e["id"] in keep]
    out = subprocess.run([*PY, str(SCRIPTS / "jp_left.py"), str(path), "--sjis", "--limit", "100000"], capture_output=True, encoding="utf-8").stdout
    runs = [ln for ln in out.splitlines() if ln.startswith("0x")]
    return [f"{path.stem} {ln}" for ln in runs if not any(a <= int(ln.split()[0], 16) < b for a, b in slots)]


def jp_left(work):
    keep = {ln.split()[0] for ln in (ROOT / "script/keep_jp.txt").read_text(encoding="utf-8").splitlines() if ln.strip() and ln[0] != "#"}
    bad = [run for path in dump_text(work) for run in unintended(path, keep)]
    if bad:
        sys.exit("release stopped: Japanese left in the build:\n" + "\n".join(bad))


def debug_off():
    import engine

    with open(BUILT, "rb") as f:
        exe = disc.read_form1(f, *disc.FILES["SLPS_005.42"])
    if engine.assemble(qa=False)[0] not in exe or engine.assemble(qa=True)[0] in exe:
        sys.exit("release stopped: the build's hook is not the plain one (QA log still in)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("version")
    ap.add_argument("--force", action="store_true", help="overwrite this version's existing files")
    ap.add_argument("--dump-only", help="write the built disc's text files to this dir and stop")
    a = ap.parse_args()
    if a.dump_only:
        print(len(dump_text(Path(a.dump_only))), "files")
        return
    out = ROOT / "release"
    patch = out / f"Bastard_EN_v{a.version}.xdelta"
    pack = out / f"Bastard_EN_v{a.version}.zip"
    if not a.force and (patch.exists() or pack.exists()):
        sys.exit(f"{pack.name} exists: pass --force to replace it")

    step("build", [*PY, "build.py"])
    step("tests", [*PY, "tools/check.py"])
    step("smoke", [*PY, str(SCRIPTS / "emu.py"), "build/bastard_en.cue", "--out", "work/qa/smoke", "--route", "tools/routes/boot.txt", "--smoke"])
    step("verify_build", [*PY, "tools/verify_build.py"])
    step("batch check", [*PY, "tools/batches.py", "check"])
    with tempfile.TemporaryDirectory() as tmp:
        step("jp_left")
        jp_left(Path(tmp))
    manifests = sorted((ROOT / "work/qa").rglob("manifest.tsv"))
    if len(manifests) < 2:
        sys.exit("release stopped: expected the tour and story manifests under work/qa")
    for m in manifests:
        step(f"qa_gate {m.parent.name}", [*PY, str(SCRIPTS / "qa_gate.py"), "check", str(m), str(m.parent / "verdicts")])
    step("textcover", [*PY, str(SCRIPTS / "textcover.py"), "work/qa/cover", "build/strings.tsv", "--waive", "docs/text_unshown.tsv"])

    step("polish list")
    open_lines = [ln for ln in (ROOT / "docs/polish.md").read_text(encoding="utf-8").splitlines() if ln.startswith("- [ ]")]
    if open_lines:
        sys.exit("release stopped: unticked lines in docs/polish.md:\n" + "\n".join(open_lines))
    step("README")
    found = PLACEHOLDER.findall((ROOT / "README.md").read_text(encoding="utf-8"))
    if found:
        sys.exit(f"release stopped: template placeholders in README.md: {sorted(set(found))}")
    step("debug off")
    debug_off()

    step("patch")
    out.mkdir(exist_ok=True)
    size = disc.BIN.stat().st_size
    patch.unlink(missing_ok=True)
    step("xdelta", ["xdelta3", "-e", "-9", "-S", "djw", "-B", str(size), "-s", str(disc.BIN), str(BUILT), str(patch)])
    with tempfile.TemporaryDirectory() as tmp:
        back = Path(tmp) / "back.bin"
        step("re-apply", ["xdelta3", "-d", "-B", str(size), "-s", str(disc.BIN), str(patch), str(back)])
        if digests(back) != digests(BUILT):
            sys.exit("release stopped: the patch does not rebuild the image")
    crc, md5, sha = digests(disc.BIN)
    new_crc, _, new_sha = digests(BUILT)
    text = ZIP_README.format(version=a.version, base_name=disc.BIN.name, size=size, crc=crc, md5=md5, sha1=sha,
                             new_crc=new_crc, new_sha1=new_sha, patch=patch.name)
    with zipfile.ZipFile(pack, "w", zipfile.ZIP_STORED) as z:
        z.write(patch, patch.name)
        z.writestr("PATCHING.txt", text)
    if sorted(zipfile.ZipFile(pack).namelist()) != sorted([patch.name, "PATCHING.txt"]):
        sys.exit("release stopped: unexpected zip contents")
    print(json.dumps({"zip": str(pack), "bytes": pack.stat().st_size, "patched_crc32": new_crc, "patched_sha1": new_sha}))


if __name__ == "__main__":
    main()

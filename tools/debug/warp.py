"""warp.py: reach any scene from a cold boot. No save, no playthrough.

    python -X utf8 tools/debug/warp.py list [GROUP]
    python -X utf8 tools/debug/warp.py NAME [--cue build/x.cue] [--state]   one scene; shots in work/qa/warp/NAME/
    python -X utf8 tools/debug/warp.py all [--group map] [--jobs 8] [--cue C] [--state]
                                                           every scene; writes work/qa/warp/results.tsv, exit 1 on a miss
A scene passes when its RAM check logs "WARP ok" (scenes with check `none` need only a clean exit: read their shots).
Scenes come from tools/debug/scenes.tsv (made by gen_scenes.py). Ad hoc: warp.py x --vars "MAP=3 POINT=e004 EVENT=4".
--state saves work/states/NAME.state at the end of the run.
"""
import argparse
import csv
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from skill import SKILL  # noqa: E402

OUT = ROOT / "work/qa/warp"
EMU = str(Path(SKILL) / "scripts/emu.py")
PROBES = []  # --probe FILE: extra Lua; under the debugger (slower) if it uses L.on_exec


def scenes():
    with open(Path(__file__).with_name("scenes.tsv"), encoding="utf-8", newline="") as f:
        return {r["name"]: r for r in csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE)}


def lua_vars(text, check):
    out = []
    for item in text.split():
        k, v = item.split("=")
        out += ["--var", f"{k}={v}" if v.lstrip("-").isdigit() else f"{k}='{v}'"]
    return out + ["--var", f"CHECK='{check}'"]


def default_cue():
    return str(next((ROOT / "rom").glob("*.cue")))


def run(s, cue, state=False):
    name, out = s["name"], OUT / s["name"]
    nowarp = "NOWARP" in s["vars"]
    cmd = [sys.executable, "-X", "utf8", EMU, cue, "--out", str(out), "--frames", s["frames"], "--shot-every",
           "120" if s["group"] in ("event", "adhoc") else "300", "--sheet", "--timeout", "280"]
    if not nowarp:
        cmd += ["--script", str(Path(__file__).with_name("warp.lua"))] + lua_vars(s["vars"], s["check"])
        if "PINS=" in s["vars"]:
            cmd += ["--script", str(Path(__file__).with_name("pin.lua"))]
    if s["route"]:
        cmd += ["--route-str", s["route"]]
    if int(s["mash"]):
        cmd += ["--mash", s["mash"], "--mash-key", "circle"]
    if state:
        cmd += ["--state-out", str(ROOT / f"work/states/{name}.state")]
    for p in PROBES:
        cmd += ["--script", p] + (["--debugger"] if "L.on_exec" in Path(p).read_text(encoding="utf-8") else [])
    shutil.rmtree(out, ignore_errors=True)  # a shot left by an earlier run must never pass as proof of this one
    out.mkdir(parents=True)
    with open(out / "emu.log", "w", encoding="utf-8") as lf:
        for _ in range(10):
            code = subprocess.call(cmd, cwd=ROOT, stdout=lf, stderr=subprocess.STDOUT)
            if code != 0xC0000142:  # Windows could not start the process (machine out of desktop heap): 507 scenes lost in one tour
                break
            time.sleep(60)
    log = (out / "log.txt").read_text(encoding="utf-8", errors="replace") if (out / "log.txt").exists() else ""
    if code != 0:
        return name, "FAIL", f"emu exit {code}"
    if s["check"] != "none" and "WARP ok" not in log:
        return name, "FAIL", f"no RAM check pass ({s['check']})"
    line = next((ln for ln in log.splitlines() if "WARP ok" in ln), "clean exit")
    return name, "ok", line


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name")
    ap.add_argument("group_arg", nargs="?")
    ap.add_argument("--group")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--cue", default=None)
    ap.add_argument("--state", action="store_true")
    ap.add_argument("--vars", help="ad hoc scene: Lua globals as NAME=VALUE NAME=VALUE")
    ap.add_argument("--route", default="")
    ap.add_argument("--frames", default="3000")
    ap.add_argument("--check", default="none", help="ad hoc scene: map, event, battle, lost, ending or none")
    ap.add_argument("--probe", action="append", default=[], help="extra Lua script with L.on_exec hooks")
    ap.add_argument("--failed", action="store_true", help="with all: only the scenes results.tsv does not list as ok")
    a = ap.parse_args()
    PROBES[:] = [str(Path(p).resolve()) for p in a.probe]
    table = scenes()
    if a.name == "list":
        for r in table.values():
            if not a.group_arg or r["group"] == a.group_arg:
                print(r["name"], r["group"], r["vars"], sep="\t")
        return 0
    cue = a.cue or default_cue()
    if a.vars:
        s = dict(name=a.name, group="adhoc", vars=a.vars, route=a.route, frames=a.frames, mash="0", check=a.check)
        results = [run(s, cue, a.state)]
    elif a.name == "all":
        todo = [r for r in table.values() if not a.group or r["group"] == a.group]
        suffix = f"_{a.group}" if a.group else ""
        OUT.mkdir(parents=True, exist_ok=True)
        results_tsv = OUT / f"results{suffix}.tsv"
        done = []
        if a.failed:
            done = [tuple(ln.split("\t")) for ln in results_tsv.read_text(encoding="utf-8").splitlines()]
            done = [r for r in done if r[1] == "ok"]
            kept = {r[0] for r in done}
            todo = [r for r in todo if r["name"] not in kept]
        with ThreadPoolExecutor(a.jobs) as pool:
            results = []
            for i, res in enumerate(pool.map(lambda r: run(r, cue, a.state), todo), 1):
                results.append(res)
                if res[1] != "ok" or i % 50 == 0:
                    print(i, "/", len(todo), *res, flush=True)
        results = done + results
        results_tsv.write_text("\n".join("\t".join(r) for r in results) + "\n", encoding="utf-8")
    else:
        results = [run(table[a.name], cue, a.state)]
    bad = [r for r in results if r[1] != "ok"]
    for r in (results if len(results) < 6 else bad):
        print(*r, sep="\t")
    print(f"{len(results) - len(bad)} of {len(results)} ok")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

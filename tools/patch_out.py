"""patch_out.py bNNN N=text ... : replace lines of a translator output file (data, not source)."""
import sys
from pathlib import Path
b = sys.argv[1]
p = Path(f"work/tl/{b}.out.tsv")
rep = {}
for a in sys.argv[2:]:
    k, v = a.split("=", 1)
    rep[k] = v
out = []
for line in p.read_text(encoding="utf-8").splitlines():
    n = line.split(" ", 1)[0]
    out.append(f"{n} {rep.pop(n)}" if n in rep else line)
assert not rep, rep
p.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")

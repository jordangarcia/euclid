"""Append a searched layout to manual.py as M[n].

usage: add_manual.py N layouts.json INDEX "comment line" ["more comment" ...]
"""
import json
import os
import sys

from lib import CSIG, sig

HERE = os.path.dirname(os.path.abspath(__file__))

n = int(sys.argv[1])
layout = json.load(open(sys.argv[2]))[int(sys.argv[3])]
comments = sys.argv[4:]

for t, p in layout["pieces"]:
    if sig(p) != CSIG[t]:
        raise SystemExit(f"{t} not congruent: {sig(p)}")

lines = ",\n".join(
    "  ('%s',[%s])" % (t, ",".join("(%.9f,%.9f)" % (x, y) for x, y in p)) for t, p in layout["pieces"]
)
block = "".join(f"# {c}\n" for c in comments) + f"M[{n}]=dict(theta=0,pieces=[\n{lines}])\n"

path = os.path.join(HERE, "manual.py")
src = open(path).read()
marker = "if __name__=='__main__':"
src = src.replace(marker, block + marker)
open(path, "w").write(src)
print(f"added M[{n}] ({len(layout['pieces'])} pieces, iou {layout['iou']})")

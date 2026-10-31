"""Compare candidate solutions for puzzles against the live one (affine-tolerant IoU).

usage: cand.py out.png N:path.json[:key] ...
  path.json is a fits-style file (single fit dict, or a dict keyed by puzzle number);
  each candidate is exported, scored and drawn next to the live solution.
"""
import json
import sys

from PIL import Image

import score
from export import export

live = {p["n"]: p for p in json.load(open("../data/puzzles.json"))}
rows = []
for spec in sys.argv[2:]:
    n, path = spec.split(":", 1)
    n = int(n)
    fit = json.load(open(path))
    if "pieces" not in fit:
        fit = fit[str(n)]
    fit = dict(fit, n=n)
    cand = export({str(n): fit}, [n])[0]

    row = Image.new("RGB", (300, 150), "white")
    if n in live:
        res, m, r = score.score(live[n], True)
        row.paste(score.tile(f"{n} live", res["iou"], m, r), (0, 0))
        a = res["iou"]
    else:
        a = None
    res, m, r = score.score(cand, True)
    row.paste(score.tile(f"{n} cand", res["iou"], m, r), (150, 0))
    print(f"{n:3d} live={a} cand={res['iou']}", flush=True)
    rows.append(row)

cols = 4
sheet = Image.new("RGB", (cols * 310, ((len(rows) + cols - 1) // cols) * 150), "white")
for i, r in enumerate(rows):
    sheet.paste(r, ((i % cols) * 310, (i // cols) * 150))
sheet.save(sys.argv[1])

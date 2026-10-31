"""Tile an ideal polygon exactly with the solver.

Rasterizes a hand-specified outline (puzzle units, y down) as a synthetic mask
and runs bb at the given frame angles. A cost of 0–2 means an exact tiling.

usage: ideal.py N "x,y x,y ..." [theta ...]   -> data/ideal/NNN.json if exact
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

import fit
import fit2

HERE = os.path.dirname(os.path.abspath(__file__))
PX = 40


def ideal_mask(points):
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    pad = 1.0
    w = int((max(xs) - min(xs) + 2 * pad) * PX)
    h = int((max(ys) - min(ys) + 2 * pad) * PX)
    im = Image.new("L", (w, h), 0)
    ImageDraw.Draw(im).polygon([((x - min(xs) + pad) * PX, (y - min(ys) + pad) * PX) for x, y in points], fill=1)
    return np.array(im).astype(np.uint8)


if __name__ == "__main__":
    n = int(sys.argv[1])
    points = [tuple(map(float, p.split(","))) for p in sys.argv[2].split()]
    thetas = [float(t) for t in sys.argv[3:]] or [0.0]
    mask = ideal_mask(points)
    print(f"ideal area {mask.sum() / PX ** 2:.3f}")

    fit.mask_for = lambda _n: mask
    fit2.mask_for = lambda _n: mask

    best = None
    for th in thetas:
        r = fit2.fit(n, limit=40_000_000, ths=[th])
        if r is None:
            print(f"theta {th}: no tiling")
            continue
        print(f"theta {th}: cost {r['cost']} iou {r['iou']:.3f}")
        if best is None or r["cost"] < best["cost"]:
            best = r

    if best is not None and best["cost"] <= 2:
        best.pop("grid", None)
        best["ideal"] = points
        json.dump(best, open(os.path.join(HERE, "..", "data", "ideal", f"{n:03d}.json"), "w"))
        print(f"exact tiling saved (cost {best['cost']})")

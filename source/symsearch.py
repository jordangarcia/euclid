"""Exact search for mirror-symmetric silhouettes.

The axis is x=0, y points down, the shape's lowest point sits at y=0.
Fixed pieces are given in those coordinates (they may straddle the axis);
a config can list several fixed alternatives (e.g. the square at each height).
The remaining pieces are placed on the left half only, one at a time, each
snapped vertex-to-vertex onto something already placed (or onto the axis),
at angles from the 0°, 45° and 26.57°-tilted families. The right half is the mirror image.

Every placement must sit mostly inside the target mask (aligned by axis and
bottom), which keeps the search small. Finished layouts are ranked by IoU
with score.py and the best few are written out as manual-style pieces.

usage: symsearch.py N out.json
       (fixed pieces and the left-half piece list are set in CONFIGS below)
"""
import itertools
import json
import math
import os
import sys

import numpy as np
from PIL import Image
from shapely import contains_xy
from shapely.geometry import Polygon
from shapely.ops import unary_union

from lib import CANON, CSIG, sig
import score

A = math.degrees(math.atan(0.5))
ANGLES = sorted(set(round((o + k * 90) % 360, 4) for o in (0, A, 2 * A, 45 - A, 45, 45 + A, 90 - 2 * A, 90 - A) for k in range(4)))
H = 1 / math.sqrt(2)

def centered_square(top, diamond=False):
    """The square straddling the axis: axis-aligned with its top edge at y=top, or a diamond with its top vertex there."""
    if diamond:
        return ("S", [(0, top), (H, top + H), (0, top + 2 * H), (-H, top + H)])
    return ("S", [(-0.5, top), (0.5, top), (0.5, top + 1), (-0.5, top + 1)])


def square_options(max_depth=3.0):
    """Every axis-aligned or diamond square on the axis, tops on a 0.25 grid, above y=0."""
    opts = []
    for k in range(0, int(max_depth / 0.25) + 1):
        top = -k * 0.25
        if top + 1 <= 1e-9:
            opts.append([centered_square(top)])
        if top + 2 * H <= 1e-9:
            opts.append([centered_square(top, diamond=True)])
    return opts


CONFIGS = {
    # 5: arrow. Square stem on the axis, roof = 2B + 2T + 2s.
    5: dict(fixed=[[("S", [(-0.5, -1), (0.5, -1), (0.5, 0), (-0.5, 0)])]], left=["B", "T", "s"]),
    # 9: rectangle with a shallow V notch along the bottom. Square somewhere on the axis.
    9: dict(fixed=square_options(2.5), left=["B", "T", "s"]),
    # 20: "!" — a V over a separate diamond. The diamond is the square on its corner with
    # its bottom vertex at y=0; the V's tip sits on the axis just above it.
    20: dict(fixed=[[centered_square(-2 * H, diamond=True)]], left=["B", "T", "s"], parts=2,
             anchors=[(0.0, -2 * H - gap) for gap in (0.1, 0.2, 0.3)]),
}

INSIDE_MIN = 0.7


def load_frame(n):
    path = os.path.join(score.MASKS, f"{n:03d}.png")
    m = np.array(Image.open(path).convert("L")) > 127
    scale = math.sqrt(m.sum() / 5.0)
    ys, xs = np.nonzero(m)
    ybot = ys.max()
    low = ys > ybot - 0.5 * scale
    x0 = xs[low].mean()
    return m, scale, x0, ybot


def make_inside(m, scale, x0, ybot):
    def inside_frac(poly):
        minx, miny, maxx, maxy = poly.bounds
        gx, gy = np.meshgrid(np.arange(minx, maxx, 0.04), np.arange(miny, maxy, 0.04))
        keep = contains_xy(poly, gx, gy)
        px = (x0 + gx[keep] * scale).astype(int)
        py = (ybot + gy[keep] * scale).astype(int)
        ok = (px >= 0) & (py >= 0) & (px < m.shape[1]) & (py < m.shape[0])
        hit = np.zeros(len(px), bool)
        hit[ok] = m[py[ok], px[ok]]
        return hit.mean() if len(hit) else 0

    return inside_frac


def orientations(t):
    out = []
    for f in (0, 1):
        pts = [(-x, y) if f else (x, y) for x, y in CANON[t]]
        for a in ANGLES:
            r = math.radians(a)
            c, s = math.cos(r), math.sin(r)
            out.append([(c * x - s * y, s * x + c * y) for x, y in pts])
    return out


ORIENT = {t: orientations(t) for t in "SBTs"}


def vertices(polys):
    vs = set()
    for p in polys:
        for x, y in p.exterior.coords[:-1]:
            vs.add((round(x, 6), round(y, 6)))
    return vs


def axis_anchors(extra=()):
    return {(0.0, -k * 0.25) for k in range(0, 21)} | {(round(x, 6), round(y, 6)) for x, y in extra}


def placements_at(t, anchor, inside_frac, cache):
    """All left-half placements of piece t with some vertex on anchor that sit inside the mask."""
    key = (t, anchor)
    if key in cache:
        return cache[key]

    ax, ay = anchor
    found = {}
    for pl in ORIENT[t]:
        for vx, vy in pl:
            pts = [(x - vx + ax, y - vy + ay) for x, y in pl]
            maxx = max(x for x, _ in pts)
            maxy = max(y for _, y in pts)
            if maxx > 1e-6 or maxy > 1e-6:
                continue
            k = tuple(sorted((round(x, 4), round(y, 4)) for x, y in pts))
            if k in found:
                continue
            q = Polygon(pts)
            if inside_frac(q) < INSIDE_MIN:
                continue
            found[k] = q

    cache[key] = list(found.items())
    return cache[key]


def candidates(placed, t, inside_frac, cache, extra_anchors=()):
    anchors = [a for a in vertices(placed) | axis_anchors(extra_anchors) if a[0] <= 1e-6]
    seen = {}
    for anchor in anchors:
        for k, q in placements_at(t, anchor, inside_frac, cache):
            if k in seen:
                continue
            if any(p.intersection(q).area > 1e-6 for p in placed):
                continue
            # buffer: shared edges come back as points without it due to float error
            touches = any(p.boundary.buffer(1e-6).intersection(q.boundary).length > 0.2 for p in placed)
            on_axis = q.bounds[2] > -1e-6
            if not (touches or on_axis):
                continue
            seen[k] = (t, q)
    return list(seen.values())


def mirror(poly):
    return Polygon([(-x, y) for x, y in poly.exterior.coords[:-1]])


def outline_of(polys):
    U = unary_union([p.buffer(1e-7, join_style=2) for p in polys]).buffer(-1e-7, join_style=2)
    geoms = list(U.geoms) if U.geom_type == "MultiPolygon" else [U]
    rings = [[list(g.exterior.coords)[:-1]] + [list(r.coords)[:-1] for r in g.interiors] for g in geoms]
    return U, rings


def search(n):
    cfg = CONFIGS[n]
    m, scale, x0, ybot = load_frame(n)
    inside_frac = make_inside(m, scale, x0, ybot)
    finals = {}
    cache = {}
    for fixed_spec, order in itertools.product(cfg["fixed"], set(itertools.permutations(cfg["left"]))):
        fixed = [(t, Polygon(p)) for t, p in fixed_spec]
        if any(inside_frac(p) < INSIDE_MIN for _, p in fixed):
            continue
        frontier = [[]]
        for t in order:
            nxt = []
            for left in frontier:
                placed = [p for _, p in fixed] + [p for _, p in left]
                for cand in candidates(placed, t, inside_frac, cache, cfg.get("anchors", ())):
                    nxt.append(left + [cand])
            frontier = nxt
        for left in frontier:
            right = [(t, mirror(p)) for t, p in left]
            allp = fixed + left + right
            polys = [p for _, p in allp]
            if any(polys[i].intersection(polys[j]).area > 1e-6 for i in range(len(polys)) for j in range(i + 1, len(polys))):
                continue
            U, rings = outline_of(polys)
            n_parts = 1 if U.geom_type == "Polygon" else len(U.geoms)
            if n_parts != cfg.get("parts", 1) or abs(U.area - 5) > 1e-4:
                continue
            key = tuple(sorted(tuple(sorted((round(x, 4), round(y, 4)) for x, y in p.exterior.coords[:-1])) for p in polys))
            finals[key] = (allp, rings)

    ranked = []
    for allp, rings in finals.values():
        res, _, _ = score.score({"n": n, "outline": rings}, True)
        if res["mirror"]:
            continue
        pieces = [(t, [list(c) for c in p.exterior.coords[:-1]]) for t, p in allp]
        assert all(sig(p) == CSIG[t] for t, p in pieces)
        ranked.append(dict(iou=res["iou"], pieces=pieces))
    ranked.sort(key=lambda r: -r["iou"])
    return ranked


if __name__ == "__main__":
    n = int(sys.argv[1])
    ranked = search(n)
    print(f"{n}: {len(ranked)} layouts", [r["iou"] for r in ranked[:8]])
    json.dump(ranked[:8], open(sys.argv[2], "w"))

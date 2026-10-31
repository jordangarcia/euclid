"""Score each exported puzzle against its target mask.

Rasterizes the solution outline at the mask's scale, aligns centroids and
searches rotation (and mirror, to catch flipped data). Prints IoU per puzzle
and writes a contact sheet: mask in grey, solution in green, mismatch in red.

usage: score.py puzzles.json out.png [n ...] [--affine]
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
MASKS = os.path.join(HERE, "..", "data", "target_masks")


def load_mask(n):
    m = np.array(Image.open(os.path.join(MASKS, f"{n:03d}.png")).convert("L")) > 127
    return m


def raster(outline, scale, rot, mirror, shape, center, warp=(1.0, 1.0, 0.0)):
    # warp = (x stretch, y stretch, shear) applied after rotation, to absorb photo keystone
    c, s = math.cos(rot), math.sin(rot)
    sx, sy, sh = warp

    def tx(v):
        x, y = v
        if mirror:
            x = -x
        rx, ry = c * x - s * y, s * x + c * y
        return (center[0] + (sx * rx + sh * ry) * scale, center[1] + sy * ry * scale)

    img = Image.new("L", (shape[1], shape[0]), 0)
    d = ImageDraw.Draw(img)
    for poly in outline:
        d.polygon([tx(v) for v in poly[0]], fill=1)
        for hole in poly[1:]:
            d.polygon([tx(v) for v in hole], fill=0)
    return np.array(img) > 0


def centroid_of(outline):
    # area-weighted centroid of the union outline (holes subtract)
    A = cx = cy = 0.0
    for poly in outline:
        for k, ring in enumerate(poly):
            sign = 1 if k == 0 else -1
            for i in range(len(ring)):
                x0, y0 = ring[i]
                x1, y1 = ring[(i + 1) % len(ring)]
                cr = x0 * y1 - x1 * y0
                A += sign * cr
                cx += sign * (x0 + x1) * cr
                cy += sign * (y0 + y1) * cr
    A /= 2
    return cx / (6 * A), cy / (6 * A)


def score(p, affine=False):
    m = load_mask(p["n"])
    pad = 40
    m = np.pad(m, pad)
    scale = math.sqrt(m.sum() / 5.0)
    ys, xs = np.nonzero(m)
    center = (xs.mean(), ys.mean())
    ox, oy = centroid_of(p["outline"])
    outline = [[[(x - ox, y - oy) for x, y in ring] for ring in poly] for poly in p["outline"]]

    def iou(rot, mirror, warp=(1.0, 1.0, 0.0)):
        r = raster(outline, scale, rot, mirror, m.shape, center, warp)
        return (r & m).sum() / (r | m).sum(), r

    best = None
    for mirror in (False, True):
        for deg in range(0, 360, 3):
            v, _ = iou(math.radians(deg), mirror)
            if best is None or v > best[0]:
                best = (v, deg, mirror)
    v0, deg0, mirror = best
    for d in np.arange(deg0 - 3, deg0 + 3.01, 0.5):
        v, _ = iou(math.radians(d), mirror)
        if v > best[0]:
            best = (v, d, mirror)
    v, deg, mirror = best
    warp = (1.0, 1.0, 0.0)

    # Photos are slightly keystoned; let the outline stretch/shear a little so a
    # correct shape isn't penalised for camera distortion.
    if affine:
        steps = (-0.12, -0.06, 0.0, 0.06, 0.12)
        for d in (-1.5, 0, 1.5):
            for sx in steps:
                for sy in steps:
                    for sh in steps:
                        w = (1 + sx, 1 + sy, sh)
                        val, _ = iou(math.radians(deg + d), mirror, w)
                        if val > v:
                            v, warp, best_d = val, w, d
        deg = deg + (best_d if warp != (1.0, 1.0, 0.0) else 0)

    _, r = iou(math.radians(deg), mirror, warp)
    return dict(n=p["n"], iou=round(float(v), 3), rot=float(deg), mirror=mirror, warp=warp), m, r


def tile(n, v, m, r, size=150):
    rgb = np.full(m.shape + (3,), 255, np.uint8)
    rgb[m & r] = (40, 120, 80)
    rgb[m & ~r] = (170, 170, 170)
    rgb[~m & r] = (220, 50, 50)
    ys, xs = np.nonzero(m | r)
    rgb = rgb[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]
    im = Image.fromarray(rgb)
    im.thumbnail((size - 10, size - 24))
    out = Image.new("RGB", (size, size), "white")
    out.paste(im, ((size - im.width) // 2, 20))
    ImageDraw.Draw(out).text((4, 4), f"{n}  {v:.2f}", fill=(0, 0, 0))
    return out


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--affine"]
    affine = "--affine" in sys.argv
    puzzles = json.load(open(args[0]))
    out_png = args[1]
    only = set(map(int, args[2:]))
    if only:
        puzzles = [p for p in puzzles if p["n"] in only]

    tiles = []
    for p in puzzles:
        res, m, r = score(p, affine)
        flag = " MIRROR" if res["mirror"] else ""
        print(f"{res['n']:3d} {res['iou']:.3f}{flag}", flush=True)
        tiles.append(tile(res["n"], res["iou"], m, r))

    cols = 10
    rows = math.ceil(len(tiles) / cols)
    sheet = Image.new("RGB", (cols * 150, rows * 150), "white")
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * 150, (i // cols) * 150))
    sheet.save(out_png)

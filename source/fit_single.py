# Fits a GPT-drawn silhouette to an exact 7-piece Euclid arrangement and verifies it.
# Usage: fit_single.py raw/NN.png out/NN.json
import sys, json, math, time
import cv2, numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union
import fit2
from lib import CANON, CSIG, sig

def load_mask(path):
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    dark = (img < 110).astype(np.uint8)
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))

    # Keep components that matter; drops specks and stray marks the model sometimes adds.
    n, lab, stats, _ = cv2.connectedComponentsWithStats(dark)
    areas = stats[1:, cv2.CC_STAT_AREA]
    if not len(areas):
        raise ValueError(f"no silhouette found in {path}")
    keep = [i + 1 for i, a in enumerate(areas) if a > 0.05 * areas.max()]

    return np.isin(lab, keep).astype(np.uint8)

def search(mask):
    fit2.mask_for = lambda _n: mask

    coarse = []
    for th in np.arange(0, 90, 4.5):
        r = fit2.fit(0, limit=600_000, ths=[float(th)])
        if r:
            coarse.append(r)
    coarse.sort(key=lambda r: r["cost"])
    if not coarse:
        return None

    best = coarse[0]
    for seed in coarse[:2]:
        for d in (-1.5, -0.75, 0, 0.75, 1.5):
            r = fit2.fit(0, limit=6_000_000, ths=[round(seed["theta"] + d, 2)])
            if r and r["cost"] < best["cost"]:
                best = r

    return best

def verify(pieces):
    polys = [(t, Polygon(pts)) for t, pts in pieces]
    counts = {k: sum(1 for t, _ in polys if t == k) for k in "SBTs"}
    congruent = all(sig(list(p.exterior.coords)[:-1]) == CSIG[t] for t, p in polys)

    overlap = 0.0
    for i in range(len(polys)):
        for j in range(i + 1, len(polys)):
            overlap += polys[i][1].intersection(polys[j][1]).area

    union = unary_union([p for _, p in polys])

    # Pieces must join along real edges (>= 0.5 units), not just at corners,
    # or the silhouette reads as loose fragments.
    adj = {i: set() for i in range(len(polys))}
    for i in range(len(polys)):
        for j in range(i + 1, len(polys)):
            shared = polys[i][1].buffer(1e-6).intersection(polys[j][1].buffer(1e-6)).length / 2
            if shared >= 0.5:
                adj[i].add(j)
                adj[j].add(i)
    seen, stack = {0}, [0]
    while stack:
        for nb in adj[stack.pop()] - seen:
            seen.add(nb)
            stack.append(nb)
    edge_connected = len(seen) == len(polys)

    ok = (
        counts == {"S": 1, "B": 2, "T": 2, "s": 2}
        and congruent
        and overlap < 1e-9
        and abs(union.area - 5) < 1e-9
    )

    return {
        "ok": ok,
        "counts": counts,
        "congruent": congruent,
        "overlap": overlap,
        "area": union.area,
        "parts": len(getattr(union, "geoms", [union])),
        "edge_connected": edge_connected,
    }

if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    t0 = time.time()

    try:
        mask = load_mask(src)
        best = search(mask)
    except Exception as e:
        print(f"{src}: failed {e}", flush=True)
        sys.exit(1)

    if best is None:
        print(f"{src}: no 7-piece fit", flush=True)
        sys.exit(1)

    proof = verify(best["pieces"])
    best.pop("grid")
    best["proof"] = proof
    json.dump(best, open(out, "w"))
    print(f"{src}: iou={best['iou']:.3f} cost={best['cost']} ok={proof['ok']} parts={proof['parts']} edges={proof['edge_connected']} {time.time()-t0:.0f}s", flush=True)
